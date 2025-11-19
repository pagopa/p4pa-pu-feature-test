@sil_debt_positions
Feature: SIL management of debt positions

  @debt_position_mixed
  Scenario: A SIL creates a mixed debt position for organization interacting with GPD
    Given a SIL acting on behalf of an organization interacting with GPD
    And a new mixed debt position configured as follows:
      | transfer index | type org       | amount |
      | 1              | FEATURE_TEST   | 34.00  |
      | 2              | FEATURE_TEST_2 | 48.00  |
      | 3              | FEATURE_TEST   | 68.00  |
    When SIL creates the mixed debt position
    Then 3 debt positions having installments with same IUV are in status unpaid configured as follows:
      | origin            | type org       | total installments | total amount | transfers index |
      | SPONTANEOUS_MIXED | FEATURE_TEST   | 2                  | 102.00       | 1 3             |
      | SPONTANEOUS_MIXED | FEATURE_TEST_2 | 1                  | 48.00        | 2               |
      | SPONTANEOUS_SIL   | MIXED          | 1                  | 150.00       | 1 2 3           |
    And the notice is present in GPD archive in status valid
    And the check of debt position expiration is scheduled

  @debt_position_mixed_classification
  Scenario: As a positive result of payment, payment reporting and treasury a mixed debt position, created by SIL on GPD, is reported
    Given a mixed debt position created by SIL for organization interacting with GPD configured as follows:
      | transfer index | type org       | amount |
      | 1              | FEATURE_TEST   | 43.00  |
      | 2              | FEATURE_TEST_2 | 30.00  |
      | 3              | FEATURE_TEST   | 77.00  |
    When the citizen pays the installment of mixed debt position
    Then the receipt is processed correctly
    And the mixed debt position and technical ones are in status paid
    And the check of mixed debt position expiration is canceled
    And the classification labels for each transfer are RT_NO_IUF, RT_NO_IUD
    And the assessment classification label for each IUD is PAID
    When the organization uploads the payment reporting file about installment paid
    Then the payment reporting is processed correctly
    And the mixed debt position and technical ones are in status reported
    And the classification labels are RT_IUF, IUF_NO_TES, RT_NO_IUD
    And the assessment classification label for each IUD is REPORTED
    When the organization uploads the treasury file with amount of 150 euros
    Then the treasury is processed correctly
    And the mixed debt position and technical ones are in status reported
    And the classification labels are RT_IUF, RT_IUF_TES, RT_NO_IUD
    And the assessment classification label for each IUD is CASHED




