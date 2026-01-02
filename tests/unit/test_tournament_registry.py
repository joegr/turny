"""
Unit tests for TournamentRegistry class.
Tests: create_tournament, get_tournament, list_tournaments, publish_tournament,
       archive_tournament, delete_tournament, get_service_url
"""
import pytest
from orchestrator.tournament_registry import TournamentRegistry
from orchestrator.models import db, Tournament


class TestCreateTournament:
    """Tests for create_tournament method."""
    
    def test_create_single_elimination(self, app, db_session):
        """Should create single elimination tournament."""
        with app.app_context():
            registry = TournamentRegistry()
            tournament = registry.create_tournament(
                name="Test Championship",
                tournament_type="single_elimination",
                max_teams=16
            )
            
            assert tournament is not None
            assert tournament.name == "Test Championship"
            assert tournament.tournament_type == "single_elimination"
            assert tournament.status == "draft"
            assert tournament.max_teams == 16
    
    def test_create_hybrid_tournament(self, app, db_session):
        """Should create hybrid tournament with correct defaults."""
        with app.app_context():
            registry = TournamentRegistry()
            tournament = registry.create_tournament(
                name="World Cup",
                tournament_type="hybrid",
                num_groups=4,
                teams_per_group_advance=2
            )
            
            assert tournament.tournament_type == "hybrid"
            assert tournament.num_groups == 4
            assert tournament.teams_per_group_advance == 2
            assert tournament.allow_draws is True  # Auto-enabled for hybrid
    
    def test_create_round_robin(self, app, db_session):
        """Should create round robin tournament."""
        with app.app_context():
            registry = TournamentRegistry()
            tournament = registry.create_tournament(
                name="League Season",
                tournament_type="round_robin"
            )
            
            assert tournament.tournament_type == "round_robin"
    
    def test_tournament_id_generated(self, app, db_session):
        """Tournament ID should be auto-generated friendly name."""
        with app.app_context():
            registry = TournamentRegistry()
            tournament = registry.create_tournament(name="Test")
            
            assert tournament.tournament_id is not None
            assert '-' in tournament.tournament_id  # Friendly name format
    
    def test_unique_tournament_ids(self, app, db_session):
        """Generated tournament IDs should be unique."""
        with app.app_context():
            registry = TournamentRegistry()
            ids = set()
            
            for i in range(10):
                tournament = registry.create_tournament(name=f"Test {i}")
                ids.add(tournament.tournament_id)
            
            assert len(ids) == 10
    
    def test_default_values(self, app, db_session):
        """Default values should be set correctly."""
        with app.app_context():
            registry = TournamentRegistry()
            tournament = registry.create_tournament(name="Test")
            
            assert tournament.min_teams == 4
            assert tournament.max_teams == 16
            assert tournament.tournament_type == "single_elimination"


class TestGetTournament:
    """Tests for get_tournament method."""
    
    def test_get_existing_tournament(self, app, db_session):
        """Should return tournament by ID."""
        with app.app_context():
            registry = TournamentRegistry()
            created = registry.create_tournament(name="Test")
            
            found = registry.get_tournament(created.tournament_id)
            
            assert found is not None
            assert found.id == created.id
    
    def test_get_nonexistent_tournament(self, app, db_session):
        """Should return None for non-existent ID."""
        with app.app_context():
            registry = TournamentRegistry()
            found = registry.get_tournament("nonexistent-id")
            
            assert found is None


class TestListTournaments:
    """Tests for list_tournaments method."""
    
    def test_list_all(self, app, db_session):
        """Should list all tournaments."""
        with app.app_context():
            registry = TournamentRegistry()
            
            for i in range(5):
                registry.create_tournament(name=f"Test {i}")
            
            tournaments = registry.list_tournaments()
            
            assert len(tournaments) == 5
    
    def test_list_with_status_filter(self, app, db_session):
        """Should filter by status."""
        with app.app_context():
            registry = TournamentRegistry()
            
            # Create draft tournaments
            for i in range(3):
                registry.create_tournament(name=f"Draft {i}")
            
            # Create and publish some
            for i in range(2):
                t = registry.create_tournament(name=f"Published {i}")
                registry.publish_tournament(t.tournament_id)
            
            drafts = registry.list_tournaments(status="draft")
            assert len(drafts) == 3
            
            published = registry.list_tournaments(status="registration")
            assert len(published) == 2
    
    def test_list_with_pagination(self, app, db_session):
        """Should support limit and offset."""
        with app.app_context():
            registry = TournamentRegistry()
            
            for i in range(10):
                registry.create_tournament(name=f"Test {i}")
            
            page1 = registry.list_tournaments(limit=5, offset=0)
            page2 = registry.list_tournaments(limit=5, offset=5)
            
            assert len(page1) == 5
            assert len(page2) == 5
            
            # Should be different tournaments
            page1_ids = {t.id for t in page1}
            page2_ids = {t.id for t in page2}
            assert page1_ids.isdisjoint(page2_ids)
    
    def test_list_ordered_by_created_at(self, app, db_session):
        """Should be ordered by created_at descending."""
        with app.app_context():
            registry = TournamentRegistry()
            
            for i in range(3):
                registry.create_tournament(name=f"Test {i}")
            
            tournaments = registry.list_tournaments()
            
            # Most recent first
            for i in range(len(tournaments) - 1):
                assert tournaments[i].created_at >= tournaments[i+1].created_at


class TestPublishTournament:
    """Tests for publish_tournament method."""
    
    def test_publish_draft_tournament(self, app, db_session):
        """Should publish draft tournament."""
        with app.app_context():
            registry = TournamentRegistry()
            tournament = registry.create_tournament(name="Test")
            
            success, message = registry.publish_tournament(tournament.tournament_id)
            
            assert success is True
            
            # Verify state changed
            updated = registry.get_tournament(tournament.tournament_id)
            assert updated.status == "registration"
    
    def test_publish_sets_service_url(self, app, db_session):
        """Publishing should set service_url."""
        with app.app_context():
            registry = TournamentRegistry()
            tournament = registry.create_tournament(name="Test")
            
            registry.publish_tournament(tournament.tournament_id)
            
            updated = registry.get_tournament(tournament.tournament_id)
            assert updated.service_url is not None
    
    def test_publish_nonexistent_tournament(self, app, db_session):
        """Should fail for non-existent tournament."""
        with app.app_context():
            registry = TournamentRegistry()
            
            success, message = registry.publish_tournament("nonexistent")
            
            assert success is False
            assert "not found" in message.lower()
    
    def test_publish_already_published(self, app, db_session):
        """Should fail for already published tournament."""
        with app.app_context():
            registry = TournamentRegistry()
            tournament = registry.create_tournament(name="Test")
            
            # First publish
            registry.publish_tournament(tournament.tournament_id)
            
            # Second publish should fail
            success, message = registry.publish_tournament(tournament.tournament_id)
            
            assert success is False


class TestArchiveTournament:
    """Tests for archive_tournament method."""
    
    def test_archive_completed_tournament(self, app, db_session):
        """Should archive completed tournament."""
        with app.app_context():
            registry = TournamentRegistry()
            tournament = registry.create_tournament(name="Test")
            
            # Manually set to completed state
            tournament.status = "completed"
            db.session.commit()
            
            success, message = registry.archive_tournament(tournament.tournament_id)
            
            assert success is True
            
            updated = registry.get_tournament(tournament.tournament_id)
            assert updated.status == "archived"
    
    def test_archive_active_tournament(self, app, db_session):
        """Should fail for active tournament."""
        with app.app_context():
            registry = TournamentRegistry()
            tournament = registry.create_tournament(name="Test")
            
            # Set to active state
            tournament.status = "active"
            db.session.commit()
            
            success, message = registry.archive_tournament(tournament.tournament_id)
            
            assert success is False
    
    def test_archive_nonexistent(self, app, db_session):
        """Should fail for non-existent tournament."""
        with app.app_context():
            registry = TournamentRegistry()
            
            success, message = registry.archive_tournament("nonexistent")
            
            assert success is False


class TestDeleteTournament:
    """Tests for delete_tournament method."""
    
    def test_delete_draft_tournament(self, app, db_session):
        """Should delete draft tournament."""
        with app.app_context():
            registry = TournamentRegistry()
            tournament = registry.create_tournament(name="Test")
            tid = tournament.tournament_id
            
            success, message = registry.delete_tournament(tid)
            
            assert success is True
            assert registry.get_tournament(tid) is None
    
    def test_delete_published_tournament(self, app, db_session):
        """Should fail for published tournament."""
        with app.app_context():
            registry = TournamentRegistry()
            tournament = registry.create_tournament(name="Test")
            registry.publish_tournament(tournament.tournament_id)
            
            success, message = registry.delete_tournament(tournament.tournament_id)
            
            assert success is False
            assert "draft" in message.lower()
    
    def test_delete_nonexistent(self, app, db_session):
        """Should fail for non-existent tournament."""
        with app.app_context():
            registry = TournamentRegistry()
            
            success, message = registry.delete_tournament("nonexistent")
            
            assert success is False


class TestGetServiceUrl:
    """Tests for get_service_url method."""
    
    def test_get_service_url(self, app, db_session):
        """Should return service URL."""
        with app.app_context():
            registry = TournamentRegistry()
            
            url = registry.get_service_url("test-tournament")
            
            assert url is not None
            assert "test-tournament" in url


class TestDeprecatedMethods:
    """Tests for deprecated methods (monolith mode)."""
    
    def test_spawn_service(self, app, db_session):
        """spawn_service should return success (no-op)."""
        with app.app_context():
            registry = TournamentRegistry()
            tournament = registry.create_tournament(name="Test")
            
            success, message = registry.spawn_service(tournament)
            
            assert success is True
    
    def test_stop_service(self, app, db_session):
        """stop_service should return success (no-op)."""
        with app.app_context():
            registry = TournamentRegistry()
            tournament = registry.create_tournament(name="Test")
            
            success, message = registry.stop_service(tournament)
            
            assert success is True
