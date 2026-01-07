from flask import Blueprint, render_template, request, jsonify, Response, current_app, url_for, stream_with_context
from shared.state_machine import TournamentStateMachine, TournamentState, TransitionError
from orchestrator.match_engine import MatchEngine
from orchestrator.models import Tournament, Team, db, EloHistory, Match
from orchestrator.pubsub_manager import get_pubsub_manager
import json
import time

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
    elif tournament_type == 'hybrid':
        # Hybrid uses single elimination for knockout stage only
        is_complete, next_matches = match_engine.advance_single_elimination(is_hybrid=True)
    else:
        is_complete, next_matches = match_engine.advance_single_elimination()
    
    if is_complete:
        match_engine.get_tournament_winner()
        sm.transition('complete')
        save_state(tournament_id, sm)

# --- Routes ---

@bp.route('/tournaments/<tournament_id>/play')
def play_index(tournament_id):
    """Main game interface - redirects to bracket view by default."""
    from flask import redirect, url_for
    return redirect(url_for('play.bracket_view', tournament_id=tournament_id))

@bp.route('/tournaments/<tournament_id>/list')
def list_view(tournament_id):
    """List view for tournament management and results."""
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
    from flask_login import current_user
    
    # Require authentication
    if not current_user.is_authenticated:
        return jsonify({'error': 'Authentication required to register a team'}), 401
    
    t = Tournament.query.filter_by(tournament_id=tournament_id).first()
    if not t:
        return jsonify({'error': 'Tournament not found'}), 404
    
    sm = get_state_machine(tournament_id)
    match_engine = get_match_engine(tournament_id)
    
    if not sm.can_perform('register_team'):
        return jsonify({'error': f'Cannot register teams in {sm.state.value} state'}), 400
    
    # Check if tournament is full
    if len(match_engine.get_teams()) >= t.max_teams:
        return jsonify({'error': 'Tournament is full'}), 400
    
    # Check if user already has a team in this tournament
    existing_team = Team.query.filter_by(tournament_id=t.id, captain_user_id=current_user.id).first()
    if existing_team:
        return jsonify({'error': f'You already have a team in this tournament: {existing_team.name}'}), 400
    
    data = request.json or {}
    name = data.get('name', '').strip()
    captain = data.get('captain', '').strip() or current_user.display_name
    
    if not name:
        return jsonify({'error': 'Team name is required'}), 400
    
    # Generate team_id
    team_id = f"team_{len(match_engine.get_teams()) + 1}"
    
    try:
        match_engine.register_team(team_id, name, captain)
        
        # Link current user as captain
        team = Team.query.filter_by(tournament_id=t.id, team_id=team_id).first()
        if team:
            team.captain_user_id = current_user.id
            db.session.commit()
        
        return jsonify({
            'team_id': team_id, 
            'name': name,
            'captain': captain,
            'message': 'Team registered successfully'
        })
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
    is_draw = data.get('is_draw', False)
    team1_score = data.get('team1_score')
    team2_score = data.get('team2_score')
    
    # Either winner or is_draw must be specified
    if not winner and not is_draw:
        return jsonify({'error': 'Winner or is_draw is required'}), 400
    
    success, message = match_engine.record_result(
        match_id, 
        winner_id=winner, 
        is_draw=is_draw,
        team1_score=team1_score,
        team2_score=team2_score
    )
    
    if not success:
        return jsonify({'error': message}), 400
    
    # Check for advancement
    t = Tournament.query.filter_by(tournament_id=tournament_id).first()
    
    if t.tournament_type == 'hybrid':
        # For hybrid tournaments:
        # - Group stage: just record results, accumulate points (no auto-advancement)
        # - Knockout stage: advance like single elimination
        match = Match.query.filter_by(tournament_id=t.id, match_id=match_id).first()
        
        if match and match.stage == 'knockout':
            # Check if current knockout round is complete
            current_round = match.round_num
            pending_in_round = Match.query.filter_by(
                tournament_id=t.id,
                stage='knockout',
                round_num=current_round,
                status='pending'
            ).count()
            
            if pending_in_round == 0:
                # Advance to next knockout round (pass 'hybrid' to use is_hybrid=True)
                advance_tournament(tournament_id, 'hybrid')
        # Group stage: no auto-advancement, wait for explicit advance-to-knockout call
        # Points are already recorded, just return success
    elif match_engine.all_matches_complete():
        advance_tournament(tournament_id, t.tournament_type)
    
    return jsonify({
        'message': message, 
        'match_id': match_id, 
        'winner': winner,
        'is_draw': is_draw
    })

@bp.route('/api/v1/play/<tournament_id>/start', methods=['POST'])
def start_tournament(tournament_id):
    sm = get_state_machine(tournament_id)
    match_engine = get_match_engine(tournament_id)
    
    t = Tournament.query.filter_by(tournament_id=tournament_id).first()
    if not t:
        return jsonify({'error': 'Tournament not found'}), 404
        
    teams = match_engine.get_teams()
    
    # Determine minimum teams based on tournament type
    if t.tournament_type == 'single_elimination':
        min_teams = 4
    elif t.tournament_type == 'hybrid':
        # Hybrid needs at least 2 teams per group
        min_teams = max(4, (t.num_groups or 2) * 2)
    else:
        min_teams = 2
    
    if len(teams) < min_teams:
        return jsonify({'error': f'Need at least {min_teams} teams to start'}), 400
    
    try:
        sm.transition('start')
        save_state(tournament_id, sm)
        
        # Ensure Pub/Sub topic and subscription exist
        pubsub = get_pubsub_manager()
        pubsub.ensure_topic_exists(tournament_id)
        pubsub.ensure_subscription_exists(tournament_id)
        
        if t.tournament_type == 'round_robin':
            matches = match_engine.create_round_robin_schedule()
            first_round = matches[0] if matches else []
        elif t.tournament_type == 'hybrid':
            # Hybrid: create group stage matches first
            first_round = match_engine.create_group_stage_matches()
        else:
            first_round = match_engine.create_single_elimination_matches()
        
        # Publish tournament started event
        pubsub.publish_event(
            tournament_id,
            'tournament_started',
            {'match_count': len(first_round), 'tournament_type': t.tournament_type}
        )
        
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
    group = request.args.get('group')
    standings = match_engine.get_standings(group_name=group)
    return jsonify(standings)

@bp.route('/api/v1/play/<tournament_id>/group-standings')
def get_group_standings(tournament_id):
    match_engine = get_match_engine(tournament_id)
    group_standings = match_engine.get_group_standings()
    return jsonify(group_standings)

@bp.route('/api/v1/play/<tournament_id>/stage-status')
def get_stage_status(tournament_id):
    """Get current stage status for hybrid tournaments."""
    t = Tournament.query.filter_by(tournament_id=tournament_id).first()
    if not t:
        return jsonify({'error': 'Tournament not found'}), 404
    
    match_engine = get_match_engine(tournament_id)
    
    # Count matches by stage
    group_matches = Match.query.filter_by(tournament_id=t.id, stage='group').all()
    knockout_matches = Match.query.filter_by(tournament_id=t.id, stage='knockout').all()
    
    group_pending = sum(1 for m in group_matches if m.status == 'pending')
    group_complete = sum(1 for m in group_matches if m.status == 'completed')
    knockout_pending = sum(1 for m in knockout_matches if m.status == 'pending')
    knockout_complete = sum(1 for m in knockout_matches if m.status == 'completed')
    
    # Determine current stage
    if t.tournament_type != 'hybrid':
        current_stage = 'knockout'
    elif len(knockout_matches) > 0:
        current_stage = 'knockout'
    elif group_pending == 0 and group_complete > 0:
        current_stage = 'group_complete'
    else:
        current_stage = 'group'
    
    return jsonify({
        'tournament_type': t.tournament_type,
        'current_stage': current_stage,
        'group_stage': {
            'total': len(group_matches),
            'pending': group_pending,
            'completed': group_complete,
            'is_complete': group_pending == 0 and group_complete > 0
        },
        'knockout_stage': {
            'total': len(knockout_matches),
            'pending': knockout_pending,
            'completed': knockout_complete,
            'is_generated': len(knockout_matches) > 0
        }
    })

@bp.route('/api/v1/play/<tournament_id>/advance-to-knockout', methods=['POST'])
def advance_to_knockout(tournament_id):
    """Generate knockout matches from group stage results."""
    t = Tournament.query.filter_by(tournament_id=tournament_id).first()
    if not t:
        return jsonify({'error': 'Tournament not found'}), 404
    
    if t.tournament_type != 'hybrid':
        return jsonify({'error': 'Only hybrid tournaments can advance to knockout'}), 400
    
    match_engine = get_match_engine(tournament_id)
    
    # Check if group stage is complete
    if not match_engine.group_stage_complete():
        return jsonify({'error': 'Group stage is not complete yet'}), 400
    
    # Check if knockout already generated
    existing_knockout = Match.query.filter_by(tournament_id=t.id, stage='knockout').count()
    if existing_knockout > 0:
        return jsonify({'error': 'Knockout stage already generated'}), 400
    
    # Create knockout matches
    knockout_matches = match_engine.create_knockout_from_groups()
    
    return jsonify({
        'message': 'Knockout stage generated',
        'matches_count': len(knockout_matches),
        'matches': knockout_matches
    })

@bp.route('/api/v1/play/<tournament_id>/teams/<team_id>')
def get_team_detail(tournament_id, team_id):
    t = Tournament.query.filter_by(tournament_id=tournament_id).first()
    if not t:
        return jsonify({'error': 'Tournament not found'}), 404
    
    team = Team.query.filter_by(tournament_id=t.id, team_id=team_id).first()
    if not team:
        return jsonify({'error': 'Team not found'}), 404
    
    # Get match history
    matches = Match.query.filter(
        Match.tournament_id == t.id,
        ((Match.team1_id == team_id) | (Match.team2_id == team_id))
    ).order_by(Match.created_at.desc()).all()
    
    match_history = []
    for m in matches:
        opponent_id = m.team2_id if m.team1_id == team_id else m.team1_id
        opponent = Team.query.filter_by(tournament_id=t.id, team_id=opponent_id).first()
        
        match_history.append({
            'match_id': m.match_id,
            'round': m.round_num,
            'opponent': opponent.name if opponent else opponent_id,
            'opponent_id': opponent_id,
            'result': 'win' if m.winner_id == team_id else 'loss' if m.winner_id else 'pending',
            'status': m.status,
            'created_at': m.created_at.isoformat() if m.created_at else None
        })
    
    # Get ELO history
    elo_history = EloHistory.query.filter_by(team_id=team.id).order_by(EloHistory.created_at.asc()).all()
    elo_data = [{
        'match_id': h.match_id,
        'old_rating': h.old_rating,
        'new_rating': h.new_rating,
        'rating_change': h.rating_change,
        'opponent_rating': h.opponent_rating,
        'result': h.result,
        'created_at': h.created_at.isoformat() if h.created_at else None
    } for h in elo_history]
    
    return jsonify({
        'team': team.to_dict(),
        'match_history': match_history,
        'elo_history': elo_data
    })

@bp.route('/tournaments/<tournament_id>/teams/<team_id>')
def team_detail_page(tournament_id, team_id):
    t = Tournament.query.filter_by(tournament_id=tournament_id).first()
    if not t:
        return render_template('404.html'), 404
    
    team = Team.query.filter_by(tournament_id=t.id, team_id=team_id).first()
    if not team:
        return render_template('404.html'), 404
    
    return render_template('team_detail.html',
                         tournament_id=tournament_id,
                         team_id=team_id,
                         team=team)

@bp.route('/<tournament_id>/bracket')
def bracket_view(tournament_id):
    t = Tournament.query.filter_by(tournament_id=tournament_id).first()
    if not t:
        return "Tournament not found", 404
    
    return render_template('bracket_view.html',
                         tournament_id=tournament_id,
                         tournament=t)

@bp.route('/tournaments/<tournament_id>/standings')
def standings_view(tournament_id):
    """Team standings/leaderboard view."""
    t = Tournament.query.filter_by(tournament_id=tournament_id).first()
    if not t:
        return render_template('404.html'), 404
    
    return render_template('standings.html',
                         tournament_id=tournament_id,
                         tournament=t)

@bp.route('/api/v1/play/<tournament_id>/events')
def tournament_events_stream(tournament_id):
    """Server-Sent Events endpoint - keepalive only, use polling for updates."""
    t = Tournament.query.filter_by(tournament_id=tournament_id).first()
    if not t:
        return jsonify({'error': 'Tournament not found'}), 404
    
    def event_stream():
        yield f"data: {json.dumps({'event_type': 'connected', 'tournament_id': tournament_id})}\n\n"
        # Keepalive only - clients poll /api/v1/play/<id>/bracket for actual updates
        for _ in range(60):
            yield ": keepalive\n\n"
            time.sleep(5)
    
    return Response(
        stream_with_context(event_stream()),
        mimetype='text/event-stream',
        headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'}
    )
