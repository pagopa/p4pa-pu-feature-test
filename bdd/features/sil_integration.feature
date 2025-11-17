@sil
Feature: SIL management of debt positions

  @mixed
  Scenario: Organization interacting with GPD creates a mixed debt position
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




