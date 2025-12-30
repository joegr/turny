from flask import Blueprint, render_template, request, jsonify, Response, current_app, url_for
from shared.state_machine import TournamentStateMachine, TournamentState, TransitionError
from orchestrator.match_engine import MatchEngine
from orchestrator.models import Tournament, Team, db

bp = Blueprint('play', __name__)

def get_match_engine(tournament_id):
    return MatchEngine(tournament_id)

def get_state_machine(tournament_id):
    t = Tournament.query.filter_by(tournament_id=tournament_id).first()
    if not t:
        return TournamentStateMachine(TournamentState.REGISTRATION)
    
    # Map database status to StateMachine state
    # If DB has status 'active', we need to check if it matches a valid state
    # The state machine uses: 'registration', 'active', 'completed'
    return TournamentStateMachine.from_state_string(t.status)

def save_state(tournament_id, sm):
    t = Tournament.query.filter_by(tournament_id=tournament_id).first()
    if t:
        t.status = sm.state.value
        db.session.commit()

def advance_tournament(tournament_id, tournament_type):
    sm = get_state_machine(tournament_id)
    match_engine = get_match_engine(tournament_id)
    
    if tournament_type == 'round_robin':
        is_complete, next_matches = match_engine.advance_round_robin()
    else:
        is_complete, next_matches = match_engine.advance_single_elimination()
    
    if is_complete:
        match_engine.get_tournament_winner() # Just to ensure calculation if needed
        sm.transition('complete')
        save_state(tournament_id, sm)
        
        # Update DB explicit status if needed (save_state does it)
            
    # No need to publish events. Client polls for changes.

# --- Routes ---

@bp.route('/tournaments/<tournament_id>/play')
def play_index(tournament_id):
    """Main game interface for a tournament."""
    t = Tournament.query.filter_by(tournament_id=tournament_id).first()
    if not t:
        return render_template('404.html'), 404
        
    sm = get_state_machine(tournament_id)
    match_engine = get_match_engine(tournament_id)
    
    return render_template('results_form.html',
        tournament_id=tournament_id,
        tournament_type=t.tournament_type,
        state=sm.state.value,
        form_access=sm.form_access,
        allowed_actions=sm.allowed_actions,
        is_monolith=True
    )

@bp.route('/api/v1/play/<tournament_id>/state')
def get_state(tournament_id):
    t = Tournament.query.filter_by(tournament_id=tournament_id).first()
    if not t:
        return jsonify({'error': 'Not found'}), 404
        
    sm = get_state_machine(tournament_id)
    match_engine = get_match_engine(tournament_id)
    
    return jsonify({
        'tournament_id': tournament_id,
        'tournament_type': t.tournament_type,
        'state': sm.state.value,
        'form_access': sm.form_access,
        'allowed_actions': sm.allowed_actions,
        'current_round': match_engine.get_current_round()
    })

@bp.route('/api/v1/play/<tournament_id>/teams', methods=['GET'])
def get_teams(tournament_id):
    match_engine = get_match_engine(tournament_id)
    return jsonify(match_engine.get_teams())

@bp.route('/api/v1/play/<tournament_id>/teams', methods=['POST'])
def register_team(tournament_id):
    sm = get_state_machine(tournament_id)
    match_engine = get_match_engine(tournament_id)
    
    if not sm.can_perform('register_team'):
        return jsonify({'error': f'Cannot register teams in {sm.state.value} state'}), 400
    
    data = request.json
    team_id = data.get('team_id') or f"team_{len(match_engine.get_teams()) + 1}"
    name = data.get('name')
    captain = data.get('captain')
    
    if not name or not captain:
        return jsonify({'error': 'Name and captain are required'}), 400
    
    try:
        match_engine.register_team(team_id, name, captain)
        return jsonify({'team_id': team_id, 'message': 'Team registered'})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@bp.route('/api/v1/play/<tournament_id>/matches', methods=['GET'])
def get_matches(tournament_id):
    match_engine = get_match_engine(tournament_id)
    return jsonify(match_engine.get_matches())

@bp.route('/api/v1/play/<tournament_id>/matches/<match_id>/result', methods=['POST'])
def record_result(tournament_id, match_id):
    sm = get_state_machine(tournament_id)
    match_engine = get_match_engine(tournament_id)
    
    if not sm.can_perform('record_result'):
        return jsonify({
            'error': f'Cannot record results in {sm.state.value} state',
            'state': sm.state.value
        }), 400
    
    data = request.json
    winner = data.get('winner')
    
    if not winner:
        return jsonify({'error': 'Winner is required'}), 400
    
    success, message = match_engine.record_result(match_id, winner)
    
    if not success:
        return jsonify({'error': message}), 400
    
    if match_engine.all_matches_complete():
        t = Tournament.query.filter_by(tournament_id=tournament_id).first()
        advance_tournament(tournament_id, t.tournament_type)
    
    return jsonify({'message': message, 'match_id': match_id, 'winner': winner})

@bp.route('/api/v1/play/<tournament_id>/start', methods=['POST'])
def start_tournament(tournament_id):
    sm = get_state_machine(tournament_id)
    match_engine = get_match_engine(tournament_id)
    
    t = Tournament.query.filter_by(tournament_id=tournament_id).first()
    if not t:
        return jsonify({'error': 'Tournament not found'}), 404
        
    teams = match_engine.get_teams()
    min_teams = 4 if t.tournament_type == 'single_elimination' else 2
    
    if len(teams) < min_teams:
        return jsonify({'error': f'Need at least {min_teams} teams to start'}), 400
    
    try:
        sm.transition('start')
        save_state(tournament_id, sm)
        
        if t.tournament_type == 'round_robin':
            matches = match_engine.create_round_robin_schedule()
            first_round = matches[0] if matches else []
        else:
            first_round = match_engine.create_single_elimination_matches()
        
        return jsonify({
            'message': 'Tournament started',
            'state': sm.state.value,
            'matches_count': len(first_round)
        })
    except TransitionError as e:
        return jsonify({'error': str(e)}), 400

@bp.route('/api/v1/play/<tournament_id>/standings')
def get_standings(tournament_id):
    match_engine = get_match_engine(tournament_id)
    return jsonify(match_engine.get_standings())
