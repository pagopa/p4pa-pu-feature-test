@classification
Feature: Classification process starting from an installment payment

  @aca
  Scenario: As a positive result of payment, payment reporting and treasury a debt position on ACA is reported
    Given a simple debt position created by organization interacting with ACA
    When the citizen pays the installment of payment option 1
    Then the receipt is processed correctly
    And the debt position is in status paid
    And the check of debt position expiration is canceled
    And the classification labels are RT_NO_IUF, RT_NO_IUD
    When the organization uploads the payment reporting file about installment of payment option 1
    Then the payment reporting is processed correctly
    And the debt position is in status reported
    And the classification labels are RT_IUF, IUF_NO_TES, RT_NO_IUD
    When the organization uploads the treasury file with amount of 100 euros
    Then the treasury is processed correctly
    And the debt position is in status reported
    And the classification labels are RT_IUF, RT_IUF_TES, RT_NO_IUD


  @gpd
  Scenario: As a positive result of payment, payment reporting and treasury a debt position on GPD is reported
    Given a simple debt position created by organization interacting with GPD
    When the citizen pays the installment of payment option 1
    Then the receipt is processed correctly
    And the debt position is in status paid
    And the check of debt position expiration is canceled
    And the classification labels are RT_NO_IUF, RT_NO_IUD
    When the organization uploads the payment reporting file about installment of payment option 1
    Then the payment reporting is processed correctly
    And the debt position is in status reported
    And the classification labels are RT_IUF, IUF_NO_TES, RT_NO_IUD
    When the organization uploads the treasury file with amount of 100 euros
    Then the treasury is processed correctly
    And the debt position is in status reported
    And the classification labels are RT_IUF, RT_IUF_TES, RT_NO_IUD