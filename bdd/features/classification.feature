@classification
Feature: Classification process starting from an installment payment

  @payment
  Scenario Outline: A simple debt position created on <interaction> is paid after a citizen payment
    Given a simple debt position created by organization interacting with <interaction>
    When the citizen pays the installment of payment option 1
    Then the receipt is processed correctly
    And the debt position is in status paid
    And the check of debt position expiration is canceled

    @aca
    Examples:
      | interaction |
      | ACA         |

    @gpd
    Examples:
      | interaction |
      | GPD         |

  Scenario Outline: A simple debt position created on <interaction> is reported after payment, payment reporting and treasury
    Given a simple debt position created by organization interacting with <interaction>
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

    @aca
    Examples:
      | interaction |
      | ACA         |

    @gpd
    Examples:
      | interaction |
      | GPD         |

  @gpd
  Scenario: A complex debt position created on GPD is partially paid after payment, payment reporting and treasury of one installment
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
  Scenario: A complex debt position created on GPD is reported after payment, payment reporting and treasury of all installments
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

  @classification_outcome9
  @gpd
  Scenario: A debt position created on GPD gets a receipt and is reported after payment reporting with outcome code 9
    Given a simple debt position created by organization interacting with GPD
    When the organization uploads the payment reporting file about installment of payment option 1 with outcome code 9
    Then the payment reporting with outcome code 9 is processed correctly
    And the receipt is created correctly with origin payments_reporting
    And the installment of payment option 1 is in status reported
    And the debt position is in status reported
    And the classification labels are IUF_NO_TES, RT_IUF, RT_NO_IUD

  @classification_outcome9
  @gpd
  Scenario: A debt position created outside PU gets a receipt and is reported after payment reporting with outcome code 9
    Given organization interacting with GPD
    When the organization uploads the payment reporting file with outcome code 9 about a debt position created outside PU
    Then the payment reporting with outcome code 9 is processed correctly
    And the debt position is created correctly
    And the receipt is created correctly with origin payments_reporting
    And the installment of the created debt position is in status reported
    And the debt position is in status reported
    And the classification labels are IUF_NO_TES, RT_IUF, RT_NO_IUD

  @classification_duplicates
  @gpd
  Scenario: An installment already paid and reported is classified as duplicate (DOPPI) when a second payment reporting with outcome code 9 arrives
    Given a simple debt position created by organization interacting with GPD
    And the successful payment of the installment
    And a payment reporting with outcome code 0 has been successfully processed for the installment
    When the organization uploads a second payment reporting for the installment with outcome code 9
    Then the payment reporting with outcome code 9 is processed correctly
    And the duplicate receipt for the payment reporting with outcome code 9 is created correctly with origin payments_reporting
    And the debt position is in status reported
    And the classification labels related to payment reporting with outcome code 0 are IUF_NO_TES, RT_IUF, RT_NO_IUD, DOPPI
    And the classification labels related to payment reporting with outcome code 9 are IUF_NO_TES, IUV_NO_RT, DOPPI

  @classification_duplicates
  @gpd
  Scenario: An installment is classified as duplicate (DOPPI) when a payment reporting with outcome code 9 arrives before the payment and it is later reported
    Given a simple debt position created by organization interacting with GPD
    And a payment reporting with outcome code 9 has been successfully processed for the installment
    And the successful payment of the installment
    When the organization uploads a second payment reporting for the installment with outcome code 0
    Then the payment reporting is processed correctly
    And the debt position is in status reported
    And the classification labels related to payment reporting with outcome code 9 are IUF_NO_TES, RT_IUF, RT_NO_IUD, DOPPI
    And the classification labels related to payment reporting with outcome code 0 are IUF_NO_TES, RT_IUF, RT_NO_IUD, DOPPI

  @classification_duplicates
  @gpd
        @test
  Scenario: An installment, created outside PU, is classified as duplicate (DOPPI) when a payment reporting with outcome code 9 arrives before the payment and it is later reported
    Given a simple debt position created on GPD
    And a payment reporting with outcome code 9 has been successfully processed for the installment created outside PU
    And the successful payment of the installment created outside PU
    When the organization uploads a second payment reporting for the installment created outside PU with outcome code 0
    Then the payment reporting is processed correctly
    And the classification labels related to payment reporting with outcome code 9 are IUF_NO_TES, RT_IUF, RT_NO_IUD, DOPPI
    And the classification labels related to payment reporting with outcome code 0 are IUF_NO_TES, RT_IUF, RT_NO_IUD, DOPPI
