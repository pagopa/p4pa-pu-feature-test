@debt_positions
Feature: An organization creates a debt position

  @aca
  Scenario: Organization interacting with ACA creates a simple debt position
    Given organization interacting with ACA
    And a new debt position of type TEST
    And payment option 1 with single installment of 100 euros with due date set in 2 days
    When the organization creates the debt position
    Then the debt position is in status unpaid
    And the notice is present in ACA archive in status valid
    And the check of debt position expiration is scheduled
    When the citizen pays the installment of payment option 1
    Then the receipt is processed correctly
    And the debt position is in status paid
    And the check of debt position expiration is canceled
    And the classification labels are RT_NO_IUF, RT_NO_IUD
    When the organization uploads the payment reporting file about installment of payment option 1
    Then the payment reporting is processed correctly
    And the debt position is in status reported
    And the classification labels are RT_IUF, IUF_NO_TES, RT_NO_IUD
