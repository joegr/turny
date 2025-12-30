import os
import sys
import json
from flask import Flask, render_template, request, jsonify, Response
import redis

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.state_machine import TournamentStateMachine, TournamentState, TransitionError
from shared.events import (
    Event, EventType, state_changed_event, match_result_event, 
    round_started_event, tournament_completed_event
)
from shared.pubsub import PubSubClient
from tournament_service.match_engine import MatchEngine

app = Flask(__name__)

TOURNAMENT_ID = os.getenv('TOURNAMENT_ID', 'default')
TOURNAMENT_TYPE = os.getenv('TOURNAMENT_TYPE', 'single_elimination')
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379')

redis_client = redis.from_url(REDIS_URL, decode_responses=True)
pubsub = PubSubClient(REDIS_URL)
match_engine = MatchEngine(redis_client, TOURNAMENT_ID)


def get_state_machine() -> TournamentStateMachine:
    state_str = redis_client.get(f"t:{TOURNAMENT_ID}:state")
    if state_str:
        return TournamentStateMachine.from_state_string(state_str)
    return TournamentStateMachine(TournamentState.REGISTRATION)


def save_state(sm: TournamentStateMachine):
    redis_client.set(f"t:{TOURNAMENT_ID}:state", sm.state.value)


def publish_event(event: Event):
    pubsub.publish_tournament_event(TOURNAMENT_ID, event)
    pubsub.log_event(TOURNAMENT_ID, event)


@app.route('/')
def index():
    sm = get_state_machine()
    return render_template('results_form.html',
        tournament_id=TOURNAMENT_ID,
        tournament_type=TOURNAMENT_TYPE,
        state=sm.state.value,
        form_access=sm.form_access,
        allowed_actions=sm.allowed_actions
    )


@app.route('/api/state')
def get_state():
    sm = get_state_machine()
    return jsonify({
        'tournament_id': TOURNAMENT_ID,
        'tournament_type': TOURNAMENT_TYPE,
        'state': sm.state.value,
        'form_access': sm.form_access,
        'allowed_actions': sm.allowed_actions,
        'current_round': match_engine.get_current_round()
    })


@app.route('/api/teams', methods=['GET'])
def get_teams():
    return jsonify(match_engine.get_teams())


@app.route('/api/teams', methods=['POST'])
def register_team():
    sm = get_state_machine()
    
    if not sm.can_perform('register_team'):
        return jsonify({'error': f'Cannot register teams in {sm.state.value} state'}), 400
    
    data = request.json
    team_id = data.get('team_id') or f"team_{len(match_engine.get_teams()) + 1}"
    name = data.get('name')
    captain = data.get('captain')
    
    if not name or not captain:
        return jsonify({'error': 'Name and captain are required'}), 400
    
    match_engine.register_team(team_id, name, captain)
    
    return jsonify({'team_id': team_id, 'message': 'Team registered'})


@app.route('/api/teams/<team_id>', methods=['DELETE'])
def unregister_team(team_id):
    sm = get_state_machine()
    
    if not sm.can_perform('unregister_team'):
        return jsonify({'error': f'Cannot unregister teams in {sm.state.value} state'}), 400
    
    if match_engine.unregister_team(team_id):
        return jsonify({'message': 'Team unregistered'})
    return jsonify({'error': 'Team not found'}), 404


@app.route('/api/matches', methods=['GET'])
def get_matches():
    return jsonify(match_engine.get_matches())


@app.route('/api/matches/<match_id>/result', methods=['POST'])
def record_result(match_id):
    sm = get_state_machine()
    
    if not sm.can_perform('record_result'):
        return jsonify({
            'error': f'Cannot record results in {sm.state.value} state',
            'state': sm.state.value,
            'form_access': sm.form_access
        }), 400
    
    data = request.json
    winner = data.get('winner')
    
    if not winner:
        return jsonify({'error': 'Winner is required'}), 400
    
    success, message = match_engine.record_result(match_id, winner)
    
    if not success:
        return jsonify({'error': message}), 400
    
    match = next((m for m in match_engine.get_matches() if m['id'] == match_id), None)
    if match:
        event = match_result_event(TOURNAMENT_ID, match_id, winner, match.get('round', 1))
        publish_event(event)
    
    if match_engine.all_matches_complete():
        advance_tournament()
    
    return jsonify({'message': message, 'match_id': match_id, 'winner': winner})


def advance_tournament():
    sm = get_state_machine()
    
    if TOURNAMENT_TYPE == 'round_robin':
        is_complete, next_matches = match_engine.advance_round_robin()
    else:
        is_complete, next_matches = match_engine.advance_single_elimination()
    
    if is_complete:
        winner = match_engine.get_tournament_winner()
        old_state = sm.state.value
        sm.transition('complete')
        save_state(sm)
        
        event = state_changed_event(TOURNAMENT_ID, old_state, sm.state.value)
        publish_event(event)
        
        event = tournament_completed_event(TOURNAMENT_ID, winner, TOURNAMENT_TYPE)
        publish_event(event)
    elif next_matches:
        current_round = match_engine.get_current_round()
        event = round_started_event(TOURNAMENT_ID, current_round, len(next_matches))
        publish_event(event)


@app.route('/api/start', methods=['POST'])
def start_tournament():
    sm = get_state_machine()
    
    teams = match_engine.get_teams()
    min_teams = 4 if TOURNAMENT_TYPE == 'single_elimination' else 2
    
    if len(teams) < min_teams:
        return jsonify({'error': f'Need at least {min_teams} teams to start'}), 400
    
    try:
        old_state = sm.state.value
        sm.transition('start')
        save_state(sm)
        
        if TOURNAMENT_TYPE == 'round_robin':
            matches = match_engine.create_round_robin_schedule()
            first_round = matches[0] if matches else []
        else:
            first_round = match_engine.create_single_elimination_matches()
        
        event = state_changed_event(TOURNAMENT_ID, old_state, sm.state.value)
        publish_event(event)
        
        event = round_started_event(TOURNAMENT_ID, 1, len(first_round))
        publish_event(event)
        
        return jsonify({
            'message': 'Tournament started',
            'state': sm.state.value,
            'matches_count': len(first_round)
        })
    except TransitionError as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/standings')
def get_standings():
    return jsonify(match_engine.get_standings())


@app.route('/api/events')
def stream_events():
    def generate():
        ps = redis_client.pubsub()
        ps.subscribe(f"tournament:{TOURNAMENT_ID}:events")
        
        for message in ps.listen():
            if message['type'] == 'message':
                yield f"data: {message['data']}\n\n"
    
    return Response(generate(), mimetype='text/event-stream')


def report_ready():
    """Report to orchestrator that this service is ready."""
    port = int(os.getenv('PORT', 6001))
    try:
        pubsub.report_service_status(TOURNAMENT_ID, "ready", port=port)
        print(f"[{TOURNAMENT_ID}] Service ready on port {port}", flush=True)
    except Exception as e:
        print(f"[{TOURNAMENT_ID}] Failed to report ready status: {e}", flush=True)


if __name__ == '__main__':
    port = int(os.getenv('PORT', 6001))
    
    # Report starting status
    try:
        pubsub.report_service_status(TOURNAMENT_ID, "starting", port=port)
        print(f"[{TOURNAMENT_ID}] Starting tournament service on port {port}...", flush=True)
    except Exception as e:
        print(f"[{TOURNAMENT_ID}] Failed to report starting status: {e}", flush=True)
    
    # Initialize state in Redis if not exists
    if not redis_client.exists(f"t:{TOURNAMENT_ID}:state"):
        redis_client.set(f"t:{TOURNAMENT_ID}:state", TournamentState.REGISTRATION.value)
        print(f"[{TOURNAMENT_ID}] Initialized state to REGISTRATION", flush=True)
    
    # Report ready after brief delay (Flask needs to start)
    from threading import Timer
    Timer(1.0, report_ready).start()
    
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
