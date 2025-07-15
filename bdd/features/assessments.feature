@assessment
Feature: TODO

  @wip
  @gpd
  Scenario: Organization interacting with GPD creates a debt position with balance information
    Given a simple debt position with balance created by organization interacting with GPD
    When the citizen pays the installment of payment option 1
    Then the receipt is processed correctly
    And the debt position is in status paid
    And the assessment is created correctly
    And the assessment detail is created correctly