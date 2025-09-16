@assessments
Feature: Storing assessments starting from an installment payment

  @gpd
  Scenario: As a positive result of payment, the assessment detail, about installment with balance information, is created
    Given a simple debt position with balance created by organization interacting with GPD
    When the citizen pays the installment of payment option 1
    Then the receipt is processed correctly
    And the debt position is in status paid
    And the assessment is in status closed
    And the assessment detail is created correctly

  @gpd
  Scenario: As a positive result of payment, the assessment detail, about installment with balance information from debt position type org, is created
    Given a simple debt position created by organization interacting with GPD
    When the citizen pays the installment of payment option 1
    Then the receipt is processed correctly
    And the debt position is in status paid
    And the installment has balance fields populated
    And the assessment is in status closed
    And the assessment detail is created correctly

  @gpd
  Scenario: As a positive result of payment, the assessment detail, about installment with balance information from assessment registry, is created
    Given a simple debt position of type FEATURE_TEST_2 created by organization interacting with GPD
    When the citizen pays the installment of payment option 1
    Then the receipt is processed correctly
    And the debt position is in status paid
    And the installment has balance fields populated
    And the assessment is in status closed
    And the assessment detail is created correctly
