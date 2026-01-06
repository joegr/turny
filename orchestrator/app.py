import os
import uuid
from datetime import datetime
from flask import Flask, render_template, request, jsonify, Response, redirect, url_for, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user

from .config import config
from .models import db, Tournament, Team, User
from .tournament_registry import TournamentRegistry
from .subscription_manager import SubscriptionManager

login_manager = LoginManager()


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
    login_manager.init_app(app)
    login_manager.login_view = None  # We use modal, not redirect
    
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
    register_auth_routes(app)
    
    # Register Play Blueprint (Monolith Mode)
    from .routes import play
    app.register_blueprint(play.bp)
    
    return app


@login_manager.user_loader
def load_user(user_id):
    """Load user by their database ID."""
    try:
        return User.query.get(int(user_id))
    except (ValueError, TypeError):
        return None


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
        """Create a new tournament. Admin only."""
        # Check if user is authenticated and is admin
        if not current_user.is_authenticated:
            return jsonify({'error': 'Authentication required'}), 401
        
        if not current_user.is_admin:
            return jsonify({'error': 'Admin access required to create tournaments'}), 403
        
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
        """Register a team for a tournament. Redirects to play API."""
        # Consolidated to /api/v1/play/<tournament_id>/teams
        # This endpoint kept for backwards compatibility but forwards to play blueprint
        from flask import redirect, url_for
        return redirect(url_for('play.register_team', tournament_id=tournament_id), code=307)
    
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


def register_auth_routes(app: Flask):
    """Register authentication routes."""
    
    from datetime import timedelta
    
    @app.route('/api/v1/auth/login', methods=['POST'])
    def auth_login():
        """Login with username only - creates session."""
        # Always logout any existing session first
        logout_user()
        
        data = request.json or {}
        username = data.get('username', '').strip()
        
        if not username:
            return jsonify({'error': 'Username is required'}), 400
        
        if len(username) < 2 or len(username) > 50:
            return jsonify({'error': 'Username must be 2-50 characters'}), 400
        
        # Generate unique session ID
        session_id = str(uuid.uuid4())
        
        # Create user with encrypted username
        user = User.create_user(username=username, session_id=session_id)
        db.session.add(user)
        db.session.commit()
        
        # Log in the user (regular users get default session duration)
        login_user(user, remember=True)
        
        return jsonify({
            'message': 'Logged in successfully',
            'user': user.to_dict()
        })
    
    @app.route('/api/v1/auth/admin-register', methods=['POST'])
    def auth_admin_register():
        """Register a new admin with username and password."""
        # Always logout any existing session first
        logout_user()
        
        data = request.json or {}
        username = data.get('username', '').strip()
        password = data.get('password', '')
        
        if not username or not password:
            return jsonify({'error': 'Username and password are required'}), 400
        
        if len(username) < 2 or len(username) > 50:
            return jsonify({'error': 'Username must be 2-50 characters'}), 400
        
        if len(password) < 6:
            return jsonify({'error': 'Password must be at least 6 characters'}), 400
        
        # Check if admin with this username already exists
        existing = User.find_admin_by_username(username)
        if existing:
            return jsonify({'error': 'Admin username already exists'}), 400
        
        # Generate unique session ID
        session_id = str(uuid.uuid4())
        
        # Create admin user with encrypted username and password
        user = User.create_user(username=username, session_id=session_id, is_admin=True, password=password)
        db.session.add(user)
        db.session.commit()
        
        # Log in with 7-day remember duration
        login_user(user, remember=True, duration=timedelta(days=7))
        
        return jsonify({
            'message': 'Admin registered successfully',
            'user': user.to_dict()
        })
    
    @app.route('/api/v1/auth/admin-login', methods=['POST'])
    def auth_admin_login():
        """Admin login with username and password - 7 day session."""
        # Always logout any existing session first
        logout_user()
        
        data = request.json or {}
        username = data.get('username', '').strip()
        password = data.get('password', '')
        
        if not username or not password:
            return jsonify({'error': 'Username and password are required'}), 400
        
        # Find existing admin by username
        admin = User.find_admin_by_username(username)
        if not admin:
            return jsonify({'error': 'Invalid credentials'}), 401
        
        if not admin.check_password(password):
            return jsonify({'error': 'Invalid credentials'}), 401
        
        # Update session ID for new login
        admin.session_id = str(uuid.uuid4())
        admin.last_seen = datetime.utcnow()
        db.session.commit()
        
        # Log in with 7-day remember duration
        login_user(admin, remember=True, duration=timedelta(days=7))
        
        return jsonify({
            'message': 'Admin logged in successfully',
            'user': admin.to_dict()
        })
    
    @app.route('/api/v1/auth/logout', methods=['POST'])
    def auth_logout():
        """Logout current user."""
        logout_user()
        return jsonify({'message': 'Logged out successfully'})
    
    @app.route('/api/v1/auth/me', methods=['GET'])
    def auth_me():
        """Get current user info."""
        if current_user.is_authenticated:
            return jsonify({
                'authenticated': True,
                'user': current_user.to_dict()
            })
        return jsonify({
            'authenticated': False,
            'user': None
        })
    
    @app.route('/api/v1/auth/update-display-name', methods=['POST'])
    def auth_update_display_name():
        """Update user's public display name."""
        if not current_user.is_authenticated:
            return jsonify({'error': 'Not authenticated'}), 401
        
        data = request.json or {}
        display_name = data.get('display_name', '').strip()
        
        if not display_name:
            return jsonify({'error': 'Display name is required'}), 400
        
        if len(display_name) < 2 or len(display_name) > 50:
            return jsonify({'error': 'Display name must be 2-50 characters'}), 400
        
        current_user.display_name = display_name
        db.session.commit()
        
        return jsonify({
            'message': 'Display name updated',
            'user': current_user.to_dict()
        })
    
    @app.route('/api/v1/auth/reveal-captain/<tournament_id>/<match_id>', methods=['GET'])
    def reveal_opponent_captain(tournament_id, match_id):
        """
        Reveal the opponent captain's encrypted username.
        Only works if the current user is a captain in this match.
        """
        if not current_user.is_authenticated:
            return jsonify({'error': 'Authentication required'}), 401
        
        from .models import Tournament, Team, Match
        
        t = Tournament.query.filter_by(tournament_id=tournament_id).first()
        if not t:
            return jsonify({'error': 'Tournament not found'}), 404
        
        match = Match.query.filter_by(tournament_id=t.id, match_id=match_id).first()
        if not match:
            return jsonify({'error': 'Match not found'}), 404
        
        # Find teams in this match
        team1 = Team.query.filter_by(tournament_id=t.id, team_id=match.team1_id).first()
        team2 = Team.query.filter_by(tournament_id=t.id, team_id=match.team2_id).first()
        
        # Check if current user is captain of one of the teams
        user_team = None
        opponent_team = None
        
        if team1 and team1.captain_user_id == current_user.id:
            user_team = team1
            opponent_team = team2
        elif team2 and team2.captain_user_id == current_user.id:
            user_team = team2
            opponent_team = team1
        
        if not user_team:
            return jsonify({'error': 'You are not a captain in this match'}), 403
        
        if not opponent_team or not opponent_team.captain_user:
            return jsonify({
                'opponent_team': opponent_team.name if opponent_team else None,
                'captain_username': None,
                'message': 'Opponent captain not registered'
            })
        
        # Reveal the opponent captain's encrypted username
        return jsonify({
            'opponent_team': opponent_team.name,
            'captain_username': opponent_team.captain_user.username,  # Decrypted
            'captain_display_name': opponent_team.captain_user.display_name
        })
