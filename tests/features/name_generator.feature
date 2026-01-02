Feature: Name Generator
  As a tournament system
  I want to generate friendly names for tournaments and matches
  So that they are memorable and easy to reference

  # Tournament Name Generation
  Scenario: Generate tournament name
    When I generate a tournament name
    Then the name should follow pattern "adjective-noun-descriptor"
    And the name should contain hyphens as separators
    And all parts should be lowercase

  Scenario: Tournament names are random
    When I generate 100 tournament names
    Then at least 90 should be unique

  Scenario: Tournament name uses valid adjectives
    When I generate a tournament name
    Then the first part should be from the adjectives list

  Scenario: Tournament name uses valid nouns
    When I generate a tournament name
    Then the second part should be from the nouns list

  Scenario: Tournament name uses valid descriptors
    When I generate a tournament name
    Then the third part should be from the match descriptors list

  # Match Name Generation
  Scenario: Generate match name with round and match number
    When I generate a match name for round 2, match 3
    Then the name should start with "r2-"
    And the name should follow pattern "r{round}-adjective-noun-descriptor"

  Scenario: Match names include round information
    When I generate match names for rounds 1 through 5
    Then each name should correctly encode its round number

  # Short ID Generation
  Scenario: Generate short ID without prefix
    When I generate a short ID without prefix
    Then the ID should be 8 characters long
    And the ID should be hexadecimal

  Scenario: Generate short ID with prefix
    When I generate a short ID with prefix "team-"
    Then the ID should start with "team-"
    And the total length should be prefix length plus 8

  Scenario: Short IDs are unique
    When I generate 1000 short IDs
    Then all should be unique
