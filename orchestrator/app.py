import os
from flask import Flask, render_template, request, jsonify, Response, redirect, url_for

from .config import config
from .models import db, Tournament, Team
from .tournament_registry import TournamentRegistry
from .subscription_manager import SubscriptionManager


def create_app(config_name: str = None) -> Flask:
    """Application factory for the orchestrator service."""
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')
    
    app = Flask(__name__, 
                template_folder='templates',
                static_folder='static')
    app.config.from_object(config[config_name])
    
    # Initialize extensions
    db.init_app(app)
    
    # Initialize services
    registry = TournamentRegistry()
    subscriptions = SubscriptionManager()
    
    # Create tables
    with app.app_context():
        db.create_all()
    
    # Store services on app for access in routes
    app.registry = registry
    app.subscriptions = subscriptions
    
    # Register routes
    register_routes(app)
    register_api_routes(app)
    
    # Register Play Blueprint (Monolith Mode)
    from .routes import play
    app.register_blueprint(play.bp)
    
    return app


def register_routes(app: Flask):
    """Register HTML view routes."""
    
    @app.route('/')
    def index():
        """Home page with tournament overview."""
        return render_template('home.html', active_page='home')
    
    @app.route('/tournaments')
    def tournaments_list():
        """List all tournaments."""
        status = request.args.get('status')
        tournaments = app.registry.list_tournaments(status=status)
        return render_template('tournaments.html', 
                             tournaments=tournaments,
                             active_page='tournaments',
                             current_filter=status)
    
    @app.route('/tournaments/new')
    def tournament_new():
        """Create new tournament form."""
        return render_template('tournament_form.html', 
                             active_page='tournaments',
                             tournament=None)
    
    @app.route('/tournaments/<tournament_id>')
    def tournament_detail(tournament_id: str):
        """Tournament detail/management page."""
        tournament = app.registry.get_tournament(tournament_id)
        if not tournament:
            return render_template('404.html'), 404
        
        return render_template('tournament_detail.html',
                             tournament=tournament,
                             active_page='tournaments')
    
    @app.route('/tournaments/<tournament_id>/live')
    def tournament_live(tournament_id: str):
        """Redirect to the internal tournament play interface."""
        tournament = app.registry.get_tournament(tournament_id)
        if not tournament:
            return render_template('404.html'), 404
        
        # In Monolith mode, we just redirect to the internal route
        return redirect(url_for('play.play_index', tournament_id=tournament_id))
    
    @app.route('/dashboard')
    def user_dashboard():
        """User dashboard with subscriptions and notifications."""
        # TODO: Get user_id from session/auth
        user_id = request.args.get('user_id', 'anonymous')
        subscribed_ids = app.subscriptions.get_user_subscriptions(user_id)
        
        subscribed_tournaments = []
        for tid in subscribed_ids:
            t = app.registry.get_tournament(tid)
            if t:
                subscribed_tournaments.append(t)
        
        return render_template('dashboard.html',
                             user_id=user_id,
                             subscriptions=subscribed_tournaments,
                             active_page='dashboard')


def register_api_routes(app: Flask):
    """Register API routes."""
    
    # ==================== Tournament CRUD ====================
    
    @app.route('/api/v1/tournaments', methods=['GET'])
    def api_list_tournaments():
        """List tournaments with optional filtering."""
        status = request.args.get('status')
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        tournaments = app.registry.list_tournaments(
            status=status,
            limit=limit,
            offset=offset
        )
        
        return jsonify({
            'tournaments': [t.to_dict() for t in tournaments],
            'count': len(tournaments),
            'limit': limit,
            'offset': offset
        })
    
    @app.route('/api/v1/tournaments', methods=['POST'])
    def api_create_tournament():
        """Create a new tournament."""
        data = request.json or {}
        
        name = data.get('name')
        if not name:
            return jsonify({'error': 'Tournament name is required'}), 400
        
        tournament = app.registry.create_tournament(
            name=name,
            tournament_type=data.get('tournament_type', 'single_elimination'),
            max_teams=data.get('max_teams', 16),
            min_teams=data.get('min_teams', 4),
            num_groups=data.get('num_groups', 0),
            group_stage_rounds=data.get('group_stage_rounds', 3),
            knockout_type=data.get('knockout_type', 'single_elimination'),
            teams_per_group_advance=data.get('teams_per_group_advance', 2),
            allow_draws=data.get('allow_draws', False)
        )
        
        return jsonify({
            'message': 'Tournament created',
            'tournament': tournament.to_dict()
        }), 201
    
    @app.route('/api/v1/tournaments/<tournament_id>', methods=['GET'])
    def api_get_tournament(tournament_id: str):
        """Get tournament details."""
        tournament = app.registry.get_tournament(tournament_id)
        if not tournament:
            return jsonify({'error': 'Tournament not found'}), 404
        
        return jsonify(tournament.to_dict())
    
    @app.route('/api/v1/tournaments/<tournament_id>', methods=['DELETE'])
    def api_delete_tournament(tournament_id: str):
        """Delete a tournament (draft only)."""
        success, message = app.registry.delete_tournament(tournament_id)
        if not success:
            return jsonify({'error': message}), 400
        return jsonify({'message': message})
    
    # ==================== Tournament Lifecycle ====================
    
    @app.route('/api/v1/tournaments/<tournament_id>/publish', methods=['POST'])
    def api_publish_tournament(tournament_id: str):
        """Publish tournament and spawn service."""
        success, message = app.registry.publish_tournament(tournament_id)
        if not success:
            return jsonify({'error': message}), 400
        
        tournament = app.registry.get_tournament(tournament_id)
        return jsonify({
            'message': message,
            'tournament': tournament.to_dict()
        })
    
    @app.route('/api/v1/tournaments/<tournament_id>/archive', methods=['POST'])
    def api_archive_tournament(tournament_id: str):
        """Archive a completed tournament."""
        success, message = app.registry.archive_tournament(tournament_id)
        if not success:
            return jsonify({'error': message}), 400
        return jsonify({'message': message})
    
    # ==================== Team Registration ====================
    
    @app.route('/api/v1/tournaments/<tournament_id>/teams', methods=['GET'])
    def api_list_teams(tournament_id: str):
        """List teams in a tournament."""
        tournament = app.registry.get_tournament(tournament_id)
        if not tournament:
            return jsonify({'error': 'Tournament not found'}), 404
        
        return jsonify({
            'teams': [t.to_dict() for t in tournament.teams],
            'count': len(tournament.teams)
        })
    
    @app.route('/api/v1/tournaments/<tournament_id>/teams', methods=['POST'])
    def api_register_team(tournament_id: str):
        """Register a team for a tournament."""
        tournament = app.registry.get_tournament(tournament_id)
        if not tournament:
            return jsonify({'error': 'Tournament not found'}), 404
        
        if tournament.status != 'registration':
            return jsonify({'error': f'Cannot register teams in {tournament.status} state'}), 400
        
        if len(tournament.teams) >= tournament.max_teams:
            return jsonify({'error': 'Tournament is full'}), 400
        
        data = request.json or {}
        name = data.get('name')
        captain = data.get('captain')
        
        if not name or not captain:
            return jsonify({'error': 'Team name and captain are required'}), 400
        
        team_id = data.get('team_id') or f"team_{len(tournament.teams) + 1}"
        
        team = Team(
            team_id=team_id,
            tournament_id=tournament.id,
            name=name,
            captain=captain
        )
        db.session.add(team)
        db.session.commit()
        
        return jsonify({
            'message': 'Team registered',
            'team': team.to_dict()
        }), 201
    
    # ==================== Subscriptions ====================
    
    @app.route('/api/v1/subscriptions', methods=['POST'])
    def api_subscribe():
        """Subscribe to a tournament."""
        data = request.json or {}
        user_id = data.get('user_id')
        tournament_id = data.get('tournament_id')
        
        if not user_id or not tournament_id:
            return jsonify({'error': 'user_id and tournament_id required'}), 400
        
        app.subscriptions.subscribe(
            user_id=user_id,
            tournament_id=tournament_id,
            notify_on_start=data.get('notify_on_start', True),
            notify_on_match=data.get('notify_on_match', True),
            notify_on_complete=data.get('notify_on_complete', True)
        )
        
        return jsonify({'message': 'Subscribed successfully'})
    
    @app.route('/api/v1/subscriptions', methods=['DELETE'])
    def api_unsubscribe():
        """Unsubscribe from a tournament."""
        data = request.json or {}
        user_id = data.get('user_id')
        tournament_id = data.get('tournament_id')
        
        if not user_id or not tournament_id:
            return jsonify({'error': 'user_id and tournament_id required'}), 400
        
        app.subscriptions.unsubscribe(user_id, tournament_id)
        return jsonify({'message': 'Unsubscribed successfully'})
    
    @app.route('/api/v1/users/<user_id>/subscriptions', methods=['GET'])
    def api_user_subscriptions(user_id: str):
        """Get user's subscriptions."""
        tournament_ids = app.subscriptions.get_user_subscriptions(user_id)
        return jsonify({
            'user_id': user_id,
            'tournament_ids': tournament_ids
        })
    
    # ==================== Health Check ====================
    
    @app.route('/health')
    @app.route('/api/v1/health')
    def health_check():
        """Health check endpoint - returns actual database connection status."""
        import time
        start = time.time()
        
        try:
            db.session.execute(db.text('SELECT 1'))
            db_ok = True
            db_error = None
        except Exception as e:
            db_ok = False
            db_error = str(e)
        
        latency_ms = round((time.time() - start) * 1000, 2)
        status = 'healthy' if db_ok else 'unhealthy'
        code = 200 if status == 'healthy' else 503
        
        return jsonify({
            'status': status,
            'database': {
                'connected': db_ok,
                'latency_ms': latency_ms if db_ok else None,
                'error': db_error
            },
            'timestamp': time.time()
        }), code
