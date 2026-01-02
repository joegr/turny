Feature: ELO Rating Calculator
  As a tournament system
  I want to calculate ELO ratings and win probabilities
  So that matches can be fairly assessed and ratings updated

  Background:
    Given an ELO calculator with K-factor of 32

  # Win Probability Calculation
  Scenario: Calculate win probability for equally rated teams
    Given team A has ELO rating 1500
    And team B has ELO rating 1500
    When I calculate win probabilities
    Then team A win probability should be 0.5
    And team B win probability should be 0.5

  Scenario: Calculate win probability when team A is stronger
    Given team A has ELO rating 1600
    And team B has ELO rating 1400
    When I calculate win probabilities
    Then team A win probability should be greater than 0.7
    And team B win probability should be less than 0.3

  Scenario: Calculate win probability when team B is stronger
    Given team A has ELO rating 1300
    And team B has ELO rating 1700
    When I calculate win probabilities
    Then team A win probability should be less than 0.2
    And team B win probability should be greater than 0.8

  Scenario: Win probabilities always sum to 1
    Given team A has ELO rating 1234
    And team B has ELO rating 1567
    When I calculate win probabilities
    Then the sum of win probabilities should equal 1.0

  # Rating Change Calculation
  Scenario: Rating change when higher rated team wins (expected outcome)
    Given winner has ELO rating 1600
    And loser has ELO rating 1400
    When I calculate rating change
    Then winner should gain less than 16 points
    And loser should lose less than 16 points

  Scenario: Rating change when lower rated team wins (upset)
    Given winner has ELO rating 1400
    And loser has ELO rating 1600
    When I calculate rating change
    Then winner should gain more than 16 points
    And loser should lose more than 16 points

  Scenario: Rating changes are symmetric
    Given winner has ELO rating 1500
    And loser has ELO rating 1500
    When I calculate rating change
    Then winner gain should equal loser loss

  Scenario: Total rating points are conserved
    Given winner has ELO rating 1550
    And loser has ELO rating 1450
    When I calculate rating change
    Then total rating points should remain constant

  # Edge Cases
  Scenario: Very large rating difference
    Given team A has ELO rating 2400
    And team B has ELO rating 800
    When I calculate win probabilities
    Then team A win probability should be greater than 0.99

  Scenario: Custom K-factor affects rating change magnitude
    Given an ELO calculator with K-factor of 16
    And winner has ELO rating 1500
    And loser has ELO rating 1500
    When I calculate rating change
    Then winner should gain exactly 8 points

  Scenario: Get rating change amount without applying
    Given winner has ELO rating 1600
    And loser has ELO rating 1400
    When I get rating change amount
    Then I should receive winner change and loser change values
    And winner change should be positive
    And loser change should be negative
