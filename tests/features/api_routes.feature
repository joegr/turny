Feature: Tournament API Routes
  As an API client
  I want to interact with tournament endpoints
  So that I can manage tournaments programmatically

  Background:
    Given the API server is running

  # Tournament CRUD Operations
  Scenario: Create tournament via API
    When I POST to "/api/v1/tournaments" with:
      | name            | Spring Championship |
      | tournament_type | single_elimination  |
      | max_teams       | 16                  |
    Then the response status should be 201
    And the response should contain tournament_id
    And the response should contain status "draft"

  Scenario: Create hybrid tournament via API
    When I POST to "/api/v1/tournaments" with:
      | name                    | World Cup        |
      | tournament_type         | hybrid           |
      | num_groups              | 4                |
      | teams_per_group_advance | 2                |
    Then the response status should be 201
    And the response should contain allow_draws true

  Scenario: Get tournament details
    Given a tournament "test-cup" exists
    When I GET "/api/v1/tournaments/test-cup"
    Then the response status should be 200
    And the response should contain tournament details

  Scenario: Get non-existent tournament
    When I GET "/api/v1/tournaments/non-existent"
    Then the response status should be 404

  Scenario: List all tournaments
    Given 5 tournaments exist
    When I GET "/api/v1/tournaments"
    Then the response status should be 200
    And the response should contain 5 tournaments

  Scenario: Delete draft tournament
    Given a draft tournament "test-cup" exists
    When I DELETE "/api/v1/tournaments/test-cup"
    Then the response status should be 200

  Scenario: Cannot delete active tournament
    Given an active tournament "test-cup" exists
    When I DELETE "/api/v1/tournaments/test-cup"
    Then the response status should be 400

  # Tournament State Operations
  Scenario: Publish tournament
    Given a draft tournament "test-cup" exists
    When I POST to "/api/v1/tournaments/test-cup/publish"
    Then the response status should be 200
    And tournament status should be "registration"

  # Team Registration
  Scenario: Register team
    Given a tournament "test-cup" in registration state
    When I POST to "/api/v1/tournaments/test-cup/teams" with:
      | name    | Dragons     |
      | captain | John Smith  |
    Then the response status should be 201
    And the team should be registered

  Scenario: Register team with missing fields
    Given a tournament "test-cup" in registration state
    When I POST to "/api/v1/tournaments/test-cup/teams" with:
      | name | Dragons |
    Then the response status should be 400
    And the error should mention missing captain

  Scenario: Get teams for tournament
    Given a tournament "test-cup" with 4 teams
    When I GET "/api/v1/play/test-cup/teams"
    Then the response status should be 200
    And the response should contain 4 teams

  # Match Operations
  Scenario: Start tournament
    Given a tournament "test-cup" with 8 teams in registration state
    When I POST to "/api/v1/play/test-cup/start"
    Then the response status should be 200
    And matches should be created
    And tournament status should be "active"

  Scenario: Start tournament with insufficient teams
    Given a tournament "test-cup" with 2 teams in registration state
    When I POST to "/api/v1/play/test-cup/start"
    Then the response status should be 400
    And the error should mention minimum teams

  Scenario: Get matches
    Given an active tournament "test-cup" with matches
    When I GET "/api/v1/play/test-cup/matches"
    Then the response status should be 200
    And the response should contain match list

  Scenario: Record match result
    Given an active tournament "test-cup"
    And a pending match "match-001"
    When I POST to "/api/v1/play/test-cup/matches/match-001/result" with:
      | winner | team-1 |
    Then the response status should be 200
    And the match should be marked completed

  Scenario: Record match result with scores
    Given a hybrid tournament "test-cup" in group stage
    And a pending match "match-001"
    When I POST to "/api/v1/play/test-cup/matches/match-001/result" with:
      | winner      | team-1 |
      | team1_score | 3      |
      | team2_score | 1      |
    Then the response status should be 200
    And scores should be recorded

  Scenario: Record draw result
    Given a hybrid tournament "test-cup" in group stage
    And a pending match "match-001"
    When I POST to "/api/v1/play/test-cup/matches/match-001/result" with:
      | is_draw     | true |
      | team1_score | 2    |
      | team2_score | 2    |
    Then the response status should be 200
    And the match should be marked as draw

  # Standings
  Scenario: Get standings
    Given an active tournament "test-cup" with some completed matches
    When I GET "/api/v1/play/test-cup/standings"
    Then the response status should be 200
    And teams should be sorted by performance

  Scenario: Get group standings for hybrid tournament
    Given a hybrid tournament "test-cup" with group matches
    When I GET "/api/v1/play/test-cup/group-standings"
    Then the response status should be 200
    And the response should contain standings per group

  # Stage Status and Advancement
  Scenario: Get stage status for hybrid tournament
    Given a hybrid tournament "test-cup" in group stage
    When I GET "/api/v1/play/test-cup/stage-status"
    Then the response status should be 200
    And current_stage should be "group"
    And group_stage.is_complete should be false

  Scenario: Advance to knockout stage
    Given a hybrid tournament "test-cup" with completed group stage
    When I POST to "/api/v1/play/test-cup/advance-to-knockout"
    Then the response status should be 200
    And knockout matches should be created

  Scenario: Cannot advance if group stage incomplete
    Given a hybrid tournament "test-cup" with pending group matches
    When I POST to "/api/v1/play/test-cup/advance-to-knockout"
    Then the response status should be 400
    And the error should mention group stage not complete

  # Team Details
  Scenario: Get team details
    Given an active tournament "test-cup"
    And a team "team-1" with match history
    When I GET "/api/v1/play/test-cup/teams/team-1"
    Then the response status should be 200
    And the response should contain team info
    And the response should contain match history
    And the response should contain ELO history

  # Health Check
  Scenario: Health check endpoint
    When I GET "/api/v1/health"
    Then the response status should be 200
    And the response should contain database status

  # SSE Events
  Scenario: Subscribe to tournament events
    Given an active tournament "test-cup"
    When I connect to SSE at "/api/v1/play/test-cup/events"
    Then I should receive a connection confirmation
    And I should receive events when matches are updated
