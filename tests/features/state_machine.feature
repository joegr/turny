Feature: Tournament State Machine
  As a tournament system
  I want to enforce valid state transitions
  So that tournaments follow a consistent lifecycle

  Background:
    Given a tournament state machine

  # Initial State
  Scenario: New state machine starts in draft
    When I create a new state machine
    Then the state should be "draft"

  Scenario: Create state machine from state string
    When I create state machine from string "registration"
    Then the state should be "registration"

  Scenario: Invalid state string defaults to draft
    When I create state machine from string "invalid_state"
    Then the state should be "draft"

  # Valid Transitions
  Scenario: Draft to Registration via publish
    Given state machine is in "draft" state
    When I perform action "publish"
    Then the state should be "registration"
    And the transition should be recorded in history

  Scenario: Draft to Draft via edit
    Given state machine is in "draft" state
    When I perform action "edit"
    Then the state should be "draft"

  Scenario: Registration to Active via start
    Given state machine is in "registration" state
    When I perform action "start"
    Then the state should be "active"

  Scenario: Registration to Draft via cancel
    Given state machine is in "registration" state
    When I perform action "cancel"
    Then the state should be "draft"

  Scenario: Active to Active via advance
    Given state machine is in "active" state
    When I perform action "advance"
    Then the state should be "active"

  Scenario: Active to Completed via complete
    Given state machine is in "active" state
    When I perform action "complete"
    Then the state should be "completed"

  Scenario: Completed to Archived via archive
    Given state machine is in "completed" state
    When I perform action "archive"
    Then the state should be "archived"

  # Invalid Transitions
  Scenario: Cannot start from draft
    Given state machine is in "draft" state
    When I try to perform action "start"
    Then a TransitionError should be raised
    And the state should remain "draft"

  Scenario: Cannot publish from active
    Given state machine is in "active" state
    When I try to perform action "publish"
    Then a TransitionError should be raised

  Scenario: Cannot archive from active
    Given state machine is in "active" state
    When I try to perform action "archive"
    Then a TransitionError should be raised

  Scenario: Cannot transition from archived
    Given state machine is in "archived" state
    When I try to perform action "publish"
    Then a TransitionError should be raised

  # Can Transition Check
  Scenario: Can transition returns true for valid action
    Given state machine is in "draft" state
    When I check can_transition for "publish"
    Then it should return True

  Scenario: Can transition returns false for invalid action
    Given state machine is in "draft" state
    When I check can_transition for "start"
    Then it should return False

  # Can Perform Check
  Scenario: Can perform returns true for allowed action
    Given state machine is in "registration" state
    When I check can_perform for "register_team"
    Then it should return True

  Scenario: Can perform returns false for disallowed action
    Given state machine is in "draft" state
    When I check can_perform for "register_team"
    Then it should return False

  # Allowed Actions
  Scenario: Draft state allowed actions
    Given state machine is in "draft" state
    When I get allowed actions
    Then allowed actions should include "edit"
    And allowed actions should include "publish"
    And allowed actions should include "delete"

  Scenario: Registration state allowed actions
    Given state machine is in "registration" state
    When I get allowed actions
    Then allowed actions should include "register_team"
    And allowed actions should include "unregister_team"
    And allowed actions should include "start"
    And allowed actions should include "cancel"

  Scenario: Active state allowed actions
    Given state machine is in "active" state
    When I get allowed actions
    Then allowed actions should include "record_result"
    And allowed actions should include "abandon_match"
    And allowed actions should include "advance"

  # Form Access
  Scenario: Draft state shows config form
    Given state machine is in "draft" state
    When I get form access
    Then form access should be "config"

  Scenario: Registration state shows signup form
    Given state machine is in "registration" state
    When I get form access
    Then form access should be "signup"

  Scenario: Active state shows results form
    Given state machine is in "active" state
    When I get form access
    Then form access should be "results"

  Scenario: Completed state is readonly
    Given state machine is in "completed" state
    When I get form access
    Then form access should be "readonly"

  # History Tracking
  Scenario: Transitions are recorded in history
    Given state machine is in "draft" state
    When I perform action "publish"
    And I perform action "start"
    Then history should have 2 entries
    And first entry should show draft to registration
    And second entry should show registration to active

  # Guard Conditions
  Scenario: Transition with guard that passes
    Given a transition with minimum teams guard of 4
    And context has 8 teams
    When I perform guarded transition
    Then the transition should succeed

  Scenario: Transition with guard that fails
    Given a transition with minimum teams guard of 4
    And context has 2 teams
    When I try to perform guarded transition
    Then a TransitionError should be raised
    And the error should mention guard condition failed

  # Set State Directly
  Scenario: Set state directly
    Given state machine is in "draft" state
    When I set state to "active"
    Then the state should be "active"
    And no history entry should be added
