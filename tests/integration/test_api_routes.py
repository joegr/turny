"""
Integration tests for API routes.
Tests all endpoints in the play blueprint and main app routes.
"""
import pytest
import json


class TestHealthEndpoint:
    """Tests for /api/v1/health endpoint."""
    
    def test_health_check(self, client):
        """Health check should return 200."""
        response = client.get('/api/v1/health')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'status' in data
        assert 'database' in data


class TestTournamentCRUD:
    """Tests for tournament CRUD operations."""
    
    def test_create_tournament(self, client):
        """POST /api/v1/tournaments should create tournament."""
        response = client.post('/api/v1/tournaments', 
            json={
                'name': 'Test Championship',
                'tournament_type': 'single_elimination',
                'max_teams': 16
            }
        )
        
        assert response.status_code == 201
        data = json.loads(response.data)
        assert 'tournament_id' in data
        assert data['name'] == 'Test Championship'
        assert data['status'] == 'draft'
    
    def test_create_hybrid_tournament(self, client):
        """POST /api/v1/tournaments should create hybrid tournament."""
        response = client.post('/api/v1/tournaments',
            json={
                'name': 'World Cup',
                'tournament_type': 'hybrid',
                'num_groups': 4,
                'teams_per_group_advance': 2
            }
        )
        
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['tournament_type'] == 'hybrid'
        assert data['allow_draws'] is True
    
    def test_create_tournament_missing_name(self, client):
        """POST /api/v1/tournaments without name should fail."""
        response = client.post('/api/v1/tournaments',
            json={'tournament_type': 'single_elimination'}
        )
        
        assert response.status_code == 400
    
    def test_get_tournament(self, client, sample_tournament):
        """GET /api/v1/tournaments/{id} should return tournament."""
        response = client.get(f'/api/v1/tournaments/{sample_tournament.tournament_id}')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['tournament_id'] == sample_tournament.tournament_id
    
    def test_get_tournament_not_found(self, client):
        """GET /api/v1/tournaments/{id} with invalid ID should 404."""
        response = client.get('/api/v1/tournaments/nonexistent')
        assert response.status_code == 404
    
    def test_list_tournaments(self, client, app, db_session):
        """GET /api/v1/tournaments should list tournaments."""
        # Create some tournaments first
        with app.app_context():
            for i in range(3):
                client.post('/api/v1/tournaments',
                    json={'name': f'Tournament {i}', 'tournament_type': 'single_elimination'}
                )
        
        response = client.get('/api/v1/tournaments')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert len(data) >= 3
    
    def test_delete_draft_tournament(self, client, sample_tournament):
        """DELETE /api/v1/tournaments/{id} should delete draft tournament."""
        response = client.delete(f'/api/v1/tournaments/{sample_tournament.tournament_id}')
        assert response.status_code == 200


class TestTournamentStateOperations:
    """Tests for tournament state operations."""
    
    def test_publish_tournament(self, client, sample_tournament):
        """POST /api/v1/tournaments/{id}/publish should publish."""
        response = client.post(f'/api/v1/tournaments/{sample_tournament.tournament_id}/publish')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'registration'
    
    def test_publish_already_published(self, client, sample_tournament):
        """Publishing already published tournament should fail."""
        # First publish
        client.post(f'/api/v1/tournaments/{sample_tournament.tournament_id}/publish')
        
        # Second publish should fail
        response = client.post(f'/api/v1/tournaments/{sample_tournament.tournament_id}/publish')
        assert response.status_code == 400


class TestTeamRegistration:
    """Tests for team registration endpoints."""
    
    def test_register_team(self, client, sample_tournament):
        """POST /api/v1/tournaments/{id}/teams should register team."""
        # First publish the tournament
        client.post(f'/api/v1/tournaments/{sample_tournament.tournament_id}/publish')
        
        response = client.post(
            f'/api/v1/tournaments/{sample_tournament.tournament_id}/teams',
            json={'name': 'Dragons', 'captain': 'John Smith'}
        )
        
        assert response.status_code == 201
        data = json.loads(response.data)
        assert 'team_id' in data
    
    def test_register_team_missing_captain(self, client, sample_tournament):
        """Registering team without captain should fail."""
        client.post(f'/api/v1/tournaments/{sample_tournament.tournament_id}/publish')
        
        response = client.post(
            f'/api/v1/tournaments/{sample_tournament.tournament_id}/teams',
            json={'name': 'Dragons'}
        )
        
        assert response.status_code == 400
    
    def test_get_teams(self, client, sample_tournament, sample_teams):
        """GET /api/v1/play/{id}/teams should return teams."""
        response = client.get(f'/api/v1/play/{sample_tournament.tournament_id}/teams')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data) == len(sample_teams)


class TestMatchOperations:
    """Tests for match-related endpoints."""
    
    def test_start_tournament(self, client, sample_tournament, sample_teams):
        """POST /api/v1/play/{id}/start should start tournament."""
        # Publish first
        client.post(f'/api/v1/tournaments/{sample_tournament.tournament_id}/publish')
        
        response = client.post(f'/api/v1/play/{sample_tournament.tournament_id}/start')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['state'] == 'active'
        assert 'matches_count' in data
    
    def test_start_tournament_insufficient_teams(self, client, sample_tournament):
        """Starting tournament with too few teams should fail."""
        client.post(f'/api/v1/tournaments/{sample_tournament.tournament_id}/publish')
        
        response = client.post(f'/api/v1/play/{sample_tournament.tournament_id}/start')
        
        assert response.status_code == 400
    
    def test_get_matches(self, client, sample_tournament, sample_match):
        """GET /api/v1/play/{id}/matches should return matches."""
        response = client.get(f'/api/v1/play/{sample_tournament.tournament_id}/matches')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data) >= 1
    
    def test_record_result(self, client, app, sample_tournament, sample_match, sample_teams):
        """POST /api/v1/play/{id}/matches/{match_id}/result should record result."""
        with app.app_context():
            # Set tournament to active state
            from orchestrator.models import Tournament, db
            t = Tournament.query.filter_by(tournament_id=sample_tournament.tournament_id).first()
            t.status = 'active'
            db.session.commit()
        
        response = client.post(
            f'/api/v1/play/{sample_tournament.tournament_id}/matches/{sample_match.match_id}/result',
            json={'winner': sample_teams[0].team_id}
        )
        
        assert response.status_code == 200
    
    def test_record_result_with_scores(self, client, app, sample_hybrid_tournament):
        """Recording result with scores should work for hybrid tournaments."""
        with app.app_context():
            from orchestrator.models import Tournament, Team, Match, db
            
            # Setup tournament with teams and match
            t = Tournament.query.filter_by(tournament_id=sample_hybrid_tournament.tournament_id).first()
            t.status = 'active'
            
            team1 = Team(team_id='team-a', tournament_id=t.id, name='Team A', captain='Cap A')
            team2 = Team(team_id='team-b', tournament_id=t.id, name='Team B', captain='Cap B')
            db.session.add(team1)
            db.session.add(team2)
            
            match = Match(
                match_id='group-match-1',
                tournament_id=t.id,
                round_num=1,
                team1_id='team-a',
                team2_id='team-b',
                stage='group',
                status='pending'
            )
            db.session.add(match)
            db.session.commit()
        
        response = client.post(
            f'/api/v1/play/{sample_hybrid_tournament.tournament_id}/matches/group-match-1/result',
            json={
                'winner': 'team-a',
                'team1_score': 3,
                'team2_score': 1
            }
        )
        
        assert response.status_code == 200
    
    def test_record_draw(self, client, app, sample_hybrid_tournament):
        """Recording a draw should work for group stage matches."""
        with app.app_context():
            from orchestrator.models import Tournament, Team, Match, db
            
            t = Tournament.query.filter_by(tournament_id=sample_hybrid_tournament.tournament_id).first()
            t.status = 'active'
            
            team1 = Team(team_id='team-c', tournament_id=t.id, name='Team C', captain='Cap C')
            team2 = Team(team_id='team-d', tournament_id=t.id, name='Team D', captain='Cap D')
            db.session.add(team1)
            db.session.add(team2)
            
            match = Match(
                match_id='group-match-2',
                tournament_id=t.id,
                round_num=1,
                team1_id='team-c',
                team2_id='team-d',
                stage='group',
                status='pending'
            )
            db.session.add(match)
            db.session.commit()
        
        response = client.post(
            f'/api/v1/play/{sample_hybrid_tournament.tournament_id}/matches/group-match-2/result',
            json={
                'is_draw': True,
                'team1_score': 2,
                'team2_score': 2
            }
        )
        
        assert response.status_code == 200


class TestStandingsEndpoints:
    """Tests for standings-related endpoints."""
    
    def test_get_standings(self, client, sample_tournament, sample_teams):
        """GET /api/v1/play/{id}/standings should return standings."""
        response = client.get(f'/api/v1/play/{sample_tournament.tournament_id}/standings')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data, list)
    
    def test_get_group_standings(self, client, sample_hybrid_tournament):
        """GET /api/v1/play/{id}/group-standings should return group standings."""
        response = client.get(f'/api/v1/play/{sample_hybrid_tournament.tournament_id}/group-standings')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data, dict)


class TestStageStatusEndpoints:
    """Tests for hybrid tournament stage status endpoints."""
    
    def test_get_stage_status(self, client, sample_hybrid_tournament):
        """GET /api/v1/play/{id}/stage-status should return status."""
        response = client.get(f'/api/v1/play/{sample_hybrid_tournament.tournament_id}/stage-status')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'tournament_type' in data
        assert 'current_stage' in data
        assert 'group_stage' in data
        assert 'knockout_stage' in data
    
    def test_advance_to_knockout_incomplete(self, client, app, sample_hybrid_tournament):
        """Advancing to knockout with incomplete group stage should fail."""
        with app.app_context():
            from orchestrator.models import Tournament, db
            t = Tournament.query.filter_by(tournament_id=sample_hybrid_tournament.tournament_id).first()
            t.status = 'active'
            db.session.commit()
        
        response = client.post(f'/api/v1/play/{sample_hybrid_tournament.tournament_id}/advance-to-knockout')
        
        assert response.status_code == 400


class TestTeamDetailEndpoint:
    """Tests for team detail endpoint."""
    
    def test_get_team_detail(self, client, sample_tournament, sample_teams):
        """GET /api/v1/play/{id}/teams/{team_id} should return team details."""
        response = client.get(
            f'/api/v1/play/{sample_tournament.tournament_id}/teams/{sample_teams[0].team_id}'
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'team' in data
        assert 'match_history' in data
        assert 'elo_history' in data
    
    def test_get_team_detail_not_found(self, client, sample_tournament):
        """GET with invalid team ID should 404."""
        response = client.get(
            f'/api/v1/play/{sample_tournament.tournament_id}/teams/nonexistent'
        )
        
        assert response.status_code == 404


class TestTournamentState:
    """Tests for tournament state endpoint."""
    
    def test_get_state(self, client, sample_tournament):
        """GET /api/v1/play/{id}/state should return state info."""
        response = client.get(f'/api/v1/play/{sample_tournament.tournament_id}/state')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'state' in data
        assert 'allowed_actions' in data
        assert 'form_access' in data
