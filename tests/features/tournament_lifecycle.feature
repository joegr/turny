Feature: Tournament Lifecycle Management
  As a tournament organizer
  I want to manage tournament states and transitions
  So that tournaments progress through their lifecycle correctly

  Background:
    Given the tournament system is initialized

  # Tournament Creation
  Scenario: Create a single elimination tournament
    When I create a tournament with name "Championship 2024"
    And tournament type is "single_elimination"
    And max teams is 16
    Then the tournament should be created successfully
    And the tournament status should be "draft"
    And the tournament ID should be a friendly name format

  Scenario: Create a hybrid tournament with groups
    When I create a tournament with name "World Cup 2024"
    And tournament type is "hybrid"
    And num_groups is 4
    And teams_per_group_advance is 2
    Then the tournament should be created successfully
    And allow_draws should be True
    And knockout_type should be "single_elimination"

  Scenario: Create a round robin tournament
    When I create a tournament with name "League Season"
    And tournament type is "round_robin"
    Then the tournament should be created successfully
    And the tournament status should be "draft"

  # State Transitions
  Scenario: Publish a draft tournament
    Given a tournament "Test Cup" in "draft" state
    When I publish the tournament
    Then the tournament status should be "registration"
    And the service URL should be set

  Scenario: Cannot publish an already published tournament
    Given a tournament "Test Cup" in "registration" state
    When I try to publish the tournament
    Then the operation should fail
    And the error should mention invalid state transition

  Scenario: Start a tournament with enough teams
    Given a tournament "Test Cup" in "registration" state
    And the tournament has 8 registered teams
    When I start the tournament
    Then the tournament status should be "active"
    And matches should be created

  Scenario: Cannot start tournament without minimum teams
    Given a tournament "Test Cup" in "registration" state
    And the tournament has 2 registered teams
    When I try to start the tournament
    Then the operation should fail
    And the error should mention minimum team requirement

  Scenario: Complete a tournament when all matches are done
    Given a tournament "Test Cup" in "active" state
    And all matches are completed
    When I complete the tournament
    Then the tournament status should be "completed"

  Scenario: Archive a completed tournament
    Given a tournament "Test Cup" in "completed" state
    When I archive the tournament
    Then the tournament status should be "archived"

  Scenario: Cannot archive an active tournament
    Given a tournament "Test Cup" in "active" state
    When I try to archive the tournament
    Then the operation should fail

  # Tournament Deletion
  Scenario: Delete a draft tournament
    Given a tournament "Test Cup" in "draft" state
    When I delete the tournament
    Then the tournament should be removed from the system

  Scenario: Cannot delete a published tournament
    Given a tournament "Test Cup" in "registration" state
    When I try to delete the tournament
    Then the operation should fail
    And the error should mention only draft tournaments can be deleted

  # Tournament Listing
  Scenario: List all tournaments
    Given there are 5 tournaments in the system
    When I list all tournaments
    Then I should receive 5 tournaments
    And they should be ordered by creation date descending

  Scenario: Filter tournaments by status
    Given there are 3 draft tournaments
    And there are 2 active tournaments
    When I list tournaments with status "active"
    Then I should receive 2 tournaments
    And all should have status "active"

  Scenario: Paginate tournament list
    Given there are 100 tournaments in the system
    When I list tournaments with limit 20 and offset 40
    Then I should receive 20 tournaments
    And they should be the 41st through 60th tournaments
