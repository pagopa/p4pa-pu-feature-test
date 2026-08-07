@assessments
Feature: Assessment storage from payments

  @gpd
  Scenario: An assessment detail is created from the installment balance after a payment
    Given a simple debt position with balance created by organization interacting with GPD
    When the citizen pays the installment of payment option 1
    Then the receipt is processed correctly
    And the debt position is in status paid
    And the assessment is in status closed
    And the assessment detail is created correctly based on balance

  @gpd
  Scenario: An assessment detail is created from the debt position type org balance after a payment
    Given a simple debt position created by organization interacting with GPD
    When the citizen pays the installment of payment option 1
    Then the receipt is processed correctly
    And the debt position is in status paid
    And the installment has balance field populated
    And the assessment is in status closed
    And the assessment detail is created correctly based on balance

  @gpd
  Scenario: An assessment detail is created from the assessment registry after a payment
    Given a simple debt position of type FEATURE_TEST_2 created by organization interacting with GPD
    When the citizen pays the installment of payment option 1
    Then the receipt is processed correctly
    And the debt position is in status paid
    And the installment has balance field populated
    And the assessment is in status closed
    And the assessment detail is created correctly based on balance
