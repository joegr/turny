Feature: Subscription Manager
  As a tournament system
  I want to manage user subscriptions to tournaments
  So that users can receive notifications about tournaments they follow

  Background:
    Given the subscription system is initialized

  # Basic Subscription Operations
  Scenario: Subscribe user to tournament
    Given user "user-123" exists
    And tournament "test-cup" exists
    When user "user-123" subscribes to "test-cup"
    Then the subscription should be created
    And all notification preferences should be enabled by default

  Scenario: Subscribe with custom notification preferences
    Given user "user-123" exists
    And tournament "test-cup" exists
    When user "user-123" subscribes to "test-cup" with:
      | notify_on_start    | true  |
      | notify_on_match    | false |
      | notify_on_complete | true  |
    Then the subscription should be created
    And notify_on_match should be false

  Scenario: Update existing subscription preferences
    Given user "user-123" is subscribed to "test-cup"
    When user "user-123" subscribes again with different preferences
    Then the existing subscription should be updated
    And no duplicate subscription should be created

  Scenario: Unsubscribe from tournament
    Given user "user-123" is subscribed to "test-cup"
    When user "user-123" unsubscribes from "test-cup"
    Then the subscription should be removed

  Scenario: Unsubscribe when not subscribed
    Given user "user-123" is not subscribed to "test-cup"
    When user "user-123" unsubscribes from "test-cup"
    Then the operation should succeed gracefully

  # Query Operations
  Scenario: Get user subscriptions
    Given user "user-123" is subscribed to 3 tournaments
    When I get subscriptions for "user-123"
    Then I should receive 3 tournament IDs

  Scenario: Get user subscriptions when none exist
    Given user "user-123" has no subscriptions
    When I get subscriptions for "user-123"
    Then I should receive an empty list

  Scenario: Get tournament subscribers
    Given tournament "test-cup" has 5 subscribers
    When I get subscribers for "test-cup"
    Then I should receive 5 user IDs

  Scenario: Check if user is subscribed
    Given user "user-123" is subscribed to "test-cup"
    When I check if "user-123" is subscribed to "test-cup"
    Then it should return True

  Scenario: Check if user is not subscribed
    Given user "user-123" is not subscribed to "test-cup"
    When I check if "user-123" is subscribed to "test-cup"
    Then it should return False

  # Event-Based Subscriber Queries
  Scenario: Get subscribers for tournament start event
    Given tournament "test-cup" has subscribers with various preferences
    And 3 subscribers have notify_on_start enabled
    When I get subscribers for event "tournament.started"
    Then I should receive 3 user IDs

  Scenario: Get subscribers for match result event
    Given tournament "test-cup" has subscribers with various preferences
    And 2 subscribers have notify_on_match enabled
    When I get subscribers for event "match.result"
    Then I should receive 2 user IDs

  Scenario: Get subscribers for tournament complete event
    Given tournament "test-cup" has subscribers with various preferences
    And 4 subscribers have notify_on_complete enabled
    When I get subscribers for event "tournament.completed"
    Then I should receive 4 user IDs

  Scenario: Get subscribers for unknown event type
    Given tournament "test-cup" has 5 subscribers
    When I get subscribers for event "unknown.event"
    Then I should receive all 5 subscribers as fallback

  # Edge Cases
  Scenario: Multiple users subscribe to same tournament
    Given 10 users exist
    When all 10 users subscribe to "test-cup"
    Then tournament "test-cup" should have 10 subscribers

  Scenario: User subscribes to multiple tournaments
    Given 5 tournaments exist
    When user "user-123" subscribes to all 5 tournaments
    Then user "user-123" should have 5 subscriptions
