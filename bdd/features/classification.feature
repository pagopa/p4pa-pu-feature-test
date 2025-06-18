@classification
Feature: Classification process starting from an installment payment

  @aca
  Scenario: As a positive result of payment, payment reporting and treasury a simple debt position, created on ACA, is reported
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
  Scenario: As a positive result of payment, payment reporting and treasury a simple debt position, created on GPD, is reported
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


  @gpd
  Scenario: As a positive result of payment, payment reporting and treasury of an installment, a complex debt position, created on GPD, is partially paid
    Given a complex debt position with 2 payment options created by organization interacting with GPD
    When the citizen pays the installment 1 of payment option 1
    Then the receipt is processed correctly
    And the installment 1 of payment option 1 is in status paid
    And the payment option 1 is in status partially_paid
    And the debt position is in status partially_paid
    And the payment option 2 is in status invalid
    And the classification labels are RT_NO_IUF, RT_NO_IUD
    When the organization uploads the payment reporting file about installment 1 of payment option 1
    Then the payment reporting is processed correctly
    And the installment 1 of payment option 1 is in status reported
    And the payment option 1 is in status partially_paid
    And the debt position is in status partially_paid
    And the classification labels are RT_NO_IUD, RT_IUF, IUF_NO_TES
    When the organization uploads the treasury file with amount of installment 1 of payment option 1
    Then the treasury is processed correctly
    And the payment option 1 is in status partially_paid
    And the debt position is in status partially_paid
    And the classification labels are RT_NO_IUD, RT_IUF, RT_IUF_TES


  @gpd
  Scenario: As a positive result of payment, payment reporting and treasury of all installments, a complex debt position, created on GPD, is reported
    Given a complex debt position with 2 payment options created by organization interacting with GPD
    And the previous payment of installment 1 of payment option 1
    When the citizen pays the installment 2 of payment option 1
    Then the receipt is processed correctly
    And the installment 2 of payment option 1 is in status paid
    And the payment option 1 is in status paid
    And the debt position is in status paid
    And the classification labels are RT_NO_IUF, RT_NO_IUD
    When the organization uploads the payment reporting file about installment 2 of payment option 1
    Then the payment reporting is processed correctly
    And the installment 2 of payment option 1 is in status reported
    And the payment option 1 is in status reported
    And the debt position is in status reported
    And the classification labels are RT_NO_IUD, RT_IUF, IUF_NO_TES
    When the organization uploads the treasury file with amount of installment 2 of payment option 1
    Then the treasury is processed correctly
    And the payment option 1 is in status reported
    And the debt position is in status reported
    And the classification labels are RT_NO_IUD, RT_IUF, RT_IUF_TES


  @gpd
  Scenario: As a positive result of payment reporting of a paid debt position without receipt, created with GPD, a receipt is created and the debt position is reported
    Given a simple debt position created by organization interacting with GPD
    When the organization uploads the payment reporting file about installment of payment option 1 with outcome code 9
    Then the payment reporting with outcome code 9 is processed correctly
    And the receipt is created correctly
    And the installment of payment option 1 is in status reported
    And the debt position is in status reported
    And the classification labels are RT_IUF, RT_IUF_TES, RT_NO_IUD