Feature: Match Engine
  As a tournament system
  I want to manage matches, teams, and results
  So that tournaments can progress correctly

  Background:
    Given a tournament "Test Championship" exists
    And the tournament is in "registration" state

  # Team Registration
  Scenario: Register a team
    When I register team "Dragons" with captain "John"
    Then the team should be added to the tournament
    And the team should have default ELO rating of 1500
    And a team_registered event should be published

  Scenario: Register multiple teams
    When I register 8 teams
    Then the tournament should have 8 teams
    And each team should have a unique team_id

  Scenario: Unregister a team
    Given team "Dragons" is registered
    When I unregister team "Dragons"
    Then the team should be removed from the tournament

  Scenario: Unregister non-existent team
    When I try to unregister team "NonExistent"
    Then the operation should return False

  # Single Elimination Match Creation
  Scenario: Create single elimination matches for 8 teams
    Given 8 teams are registered
    When I create single elimination matches
    Then 4 matches should be created for round 1
    And each match should have two teams
    And each match should have win probabilities calculated
    And current round should be 1

  Scenario: Create single elimination matches for 4 teams
    Given 4 teams are registered
    When I create single elimination matches
    Then 2 matches should be created for round 1

  Scenario: Teams are seeded by ELO rating
    Given 8 teams with varying ELO ratings are registered
    When I create single elimination matches
    Then higher rated teams should face lower rated teams

  # Round Robin Match Creation
  Scenario: Create round robin schedule for 4 teams
    Given 4 teams are registered
    When I create round robin schedule
    Then 6 total matches should be created
    And 3 rounds should be created
    And each team should play every other team once

  Scenario: Create round robin schedule for odd number of teams
    Given 5 teams are registered
    When I create round robin schedule
    Then each team should have a bye in one round

  # Group Stage Match Creation (Hybrid)
  Scenario: Create group stage matches for hybrid tournament
    Given a hybrid tournament with 2 groups
    And 8 teams are registered
    When I create group stage matches
    Then teams should be assigned to groups A and B
    And 4 teams should be in each group
    And matches should be created within each group
    And all matches should have stage "group"

  Scenario: Auto-assign teams to groups
    Given a hybrid tournament with 4 groups
    And 16 teams are registered without group assignments
    When I create group stage matches
    Then teams should be evenly distributed across 4 groups
    And each group should have 4 teams

  # Recording Results - Standard
  Scenario: Record match result with winner
    Given a pending match between "Dragons" and "Phoenix"
    When I record "Dragons" as the winner
    Then the match status should be "completed"
    And the winner_id should be "Dragons"
    And Dragons wins should increase by 1
    And Phoenix losses should increase by 1
    And ELO ratings should be updated

  Scenario: Cannot record result for non-existent match
    When I try to record result for match "non-existent"
    Then the operation should fail
    And the error should mention match not found

  Scenario: Cannot record result for completed match
    Given a completed match
    When I try to record a new result
    Then the operation should fail
    And the error should mention match is not pending

  Scenario: Cannot record invalid winner
    Given a pending match between "Dragons" and "Phoenix"
    When I try to record "Tigers" as the winner
    Then the operation should fail
    And the error should mention winner not in match

  # Recording Results - Football Style (Draws)
  Scenario: Record match result with scores and winner
    Given a group stage match between "Dragons" and "Phoenix"
    And draws are allowed
    When I record result with Dragons score 3 and Phoenix score 1
    Then the match status should be "completed"
    And Dragons should be the winner
    And Dragons should have 3 points
    And Dragons goals_for should increase by 3
    And Dragons goals_against should increase by 1

  Scenario: Record a draw in group stage
    Given a group stage match between "Dragons" and "Phoenix"
    And draws are allowed
    When I record a draw with score 2-2
    Then the match status should be "completed"
    And is_draw should be True
    And both teams should have 1 point added
    And no winner_id should be set

  Scenario: Cannot record draw in knockout stage
    Given a knockout stage match between "Dragons" and "Phoenix"
    When I try to record a draw
    Then the operation should fail
    And the error should mention draws not allowed in knockout

  # Standings
  Scenario: Get standings for single elimination
    Given 4 teams with different win records
    When I get standings
    Then teams should be sorted by wins descending
    And each team should have rank assigned

  Scenario: Get standings with football points
    Given a group stage with completed matches
    When I get standings
    Then teams should be sorted by points
    And tiebreaker should be goal difference
    And secondary tiebreaker should be goals for

  Scenario: Get group standings for hybrid tournament
    Given a hybrid tournament with 2 groups
    And group stage matches are partially complete
    When I get group standings
    Then I should receive standings for each group
    And each group should be sorted independently

  # Group Stage Completion and Knockout Advancement
  Scenario: Check if group stage is complete
    Given all group stage matches are completed
    When I check if group stage is complete
    Then it should return True

  Scenario: Check if group stage is incomplete
    Given some group stage matches are pending
    When I check if group stage is complete
    Then it should return False

  Scenario: Create knockout from groups
    Given all group stage matches are completed
    And 2 teams per group should advance
    When I create knockout from groups
    Then knockout matches should be created
    And only top 2 teams from each group should participate
    And matches should have stage "knockout"

  # Advancing Rounds
  Scenario: Advance to next round after all matches complete
    Given round 1 matches are all completed
    When I check for round advancement
    Then next round matches should be created
    And winners should face each other
