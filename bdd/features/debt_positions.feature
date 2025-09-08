@debt_positions
Feature: An organization creates a debt position

  @aca
  Scenario: Organization interacting with ACA creates a simple debt position
    Given organization interacting with ACA
    And a new debt position of type FEATURE_TEST
    And payment option 1 with single installment of 100 euros with due date set in 2 days
    When the organization creates the debt position
    Then the debt position is in status unpaid
    And the notice is present in ACA archive in status valid
    And the check of debt position expiration is scheduled

  @aca
  Scenario: Organization interacting with ACA creates a complex debt position
    Given organization interacting with ACA
    And a new debt position of type FEATURE_TEST
    And payment option 1 with 2 installments with due date set in 2 days
    And payment option 2 with 2 installments with due date set in 2 days
    When the organization creates the debt position
    Then the debt position is in status unpaid
    And the notices are present in ACA archive in status valid
    And the check of debt position expiration is scheduled

  @gpd
  Scenario: Organization interacting with GPD creates a simple debt position
    Given organization interacting with GPD
    And a new debt position of type FEATURE_TEST
    And payment option 1 with single installment of 100 euros with due date set in 2 days
    When the organization creates the debt position
    Then the debt position is in status unpaid
    And the notice is present in GPD archive in status valid
    And the check of debt position expiration is scheduled
