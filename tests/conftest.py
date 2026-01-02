"""
Pytest configuration and fixtures for tournament platform tests.
"""
import os
import sys
import pytest

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Set testing environment before importing app
os.environ['FLASK_ENV'] = 'testing'
os.environ['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'

from orchestrator.app import create_app
from orchestrator.models import db, Tournament, Team, Match, EloHistory, Subscription


@pytest.fixture(scope='session')
def app():
    """Create application for testing."""
    app = create_app('testing')
    
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture(scope='function')
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture(scope='function')
def db_session(app):
    """Create database session for testing."""
    with app.app_context():
        # Clear all tables before each test
        db.session.remove()
        
        for table in reversed(db.metadata.sorted_tables):
            db.session.execute(table.delete())
        db.session.commit()
        
        yield db.session
        
        db.session.rollback()


@pytest.fixture
def sample_tournament(app, db_session):
    """Create a sample tournament for testing."""
    with app.app_context():
        tournament = Tournament(
            tournament_id='test-tournament-001',
            name='Test Tournament',
            tournament_type='single_elimination',
            status='draft',
            max_teams=16,
            min_teams=4
        )
        db.session.add(tournament)
        db.session.commit()
        
        # Refresh to get ID
        db.session.refresh(tournament)
        return tournament


@pytest.fixture
def sample_hybrid_tournament(app, db_session):
    """Create a sample hybrid tournament for testing."""
    with app.app_context():
        tournament = Tournament(
            tournament_id='test-hybrid-001',
            name='Test Hybrid Tournament',
            tournament_type='hybrid',
            status='draft',
            max_teams=16,
            min_teams=4,
            num_groups=2,
            teams_per_group_advance=2,
            allow_draws=True
        )
        db.session.add(tournament)
        db.session.commit()
        
        db.session.refresh(tournament)
        return tournament


@pytest.fixture
def sample_teams(app, db_session, sample_tournament):
    """Create sample teams for testing."""
    with app.app_context():
        teams = []
        for i in range(8):
            team = Team(
                team_id=f'team-{i+1}',
                tournament_id=sample_tournament.id,
                name=f'Team {i+1}',
                captain=f'Captain {i+1}',
                elo_rating=1500 + (i * 50)
            )
            db.session.add(team)
            teams.append(team)
        
        db.session.commit()
        
        for team in teams:
            db.session.refresh(team)
        
        return teams


@pytest.fixture
def sample_match(app, db_session, sample_tournament, sample_teams):
    """Create a sample match for testing."""
    with app.app_context():
        match = Match(
            match_id='test-match-001',
            tournament_id=sample_tournament.id,
            round_num=1,
            team1_id=sample_teams[0].team_id,
            team2_id=sample_teams[1].team_id,
            team1_win_probability=0.55,
            team2_win_probability=0.45,
            status='pending'
        )
        db.session.add(match)
        db.session.commit()
        
        db.session.refresh(match)
        return match


@pytest.fixture
def elo_calculator():
    """Create EloCalculator instance."""
    from orchestrator.elo_calculator import EloCalculator
    return EloCalculator()


@pytest.fixture
def mock_pubsub(mocker):
    """Mock PubSub manager."""
    mock = mocker.patch('orchestrator.match_engine.get_pubsub_manager')
    mock_instance = mocker.MagicMock()
    mock_instance.publish_event = mocker.MagicMock()
    mock.return_value = mock_instance
    return mock_instance
