@debt_positions
Feature: Debt positions management

  @aca
  Scenario: A simple debt position is created by an organization interacting with ACA
    Given organization interacting with ACA
    And a new debt position of type FEATURE_TEST
    And payment option 1 with single installment of 100 euros with due date set in 2 days
    When the organization creates the debt position
    Then the debt position is in status unpaid
    And the notice is present in ACA archive in status valid
    And the check of debt position expiration is scheduled

  @aca
  Scenario: A complex debt position is created by an organization interacting with ACA
    Given organization interacting with ACA
    And a new debt position of type FEATURE_TEST
    And payment option 1 with 2 installments with due date set in 2 days
    And payment option 2 with 2 installments with due date set in 2 days
    When the organization creates the debt position
    Then the debt position is in status unpaid
    And the notices are present in ACA archive in status valid
    And the check of debt position expiration is scheduled

  @gpd
  Scenario: A simple debt position is created by an organization interacting with GPD
    Given organization interacting with GPD
    And a new debt position of type FEATURE_TEST
    And payment option 1 with single installment of 100 euros with due date set in 2 days
    When the organization creates the debt position
    Then the debt position is in status unpaid
    And the notice is present in GPD archive in status valid
    And the check of debt position expiration is scheduled

  @debt_positions_update
  @gpd
  Scenario: A complex debt position created by an organization interacting with GPD is updated by adding an installment to a payment option and modifying an installment of another one
    Given a complex debt position with 2 payment options created by organization interacting with GPD
    When the organization adds the installment 3 to payment option 1 with an amount of 80 euros and due date set in 5 days
    Then the debt position update is synchronized
    And the installment 3 of payment option 1 is saved with the requested data
    And the installment 3 of payment option 1 matches its notice on GPD
    When the organization modifies the installment 1 of payment option 2 with new remittance information, amount increased by 20 euros and due date postponed by 7 days
    Then the debt position update is synchronized
    And the installment 1 of payment option 2 is saved with the requested data
    And the installment 1 of payment option 2 matches its notice on GPD
