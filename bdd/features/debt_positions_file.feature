@debt_positions_file
Feature: An organizations creates debt positions by importing file

  @<csv_version> @eng
  @gpd
  Scenario Outline: Organization interacting with GPD creates 3 debt positions by ingestion flow file using version <csv_version>-eng
    Given organization interacting with GPD
    And debt positions <identifiers> with the installments configured as follows:
      | identifier | po index | po type            | installment seq | action |
      | A          | 1        | INSTALLMENTS       | 1               | I      |
      | A          | 1        | INSTALLMENTS       | 2               | I      |
      | A          | 2        | SINGLE_INSTALLMENT | 1               | I      |
      | B          | 1        | INSTALLMENTS       | 1               | I      |
      | B          | 1        | INSTALLMENTS       | 2               | I      |
      | C          | 1        | SINGLE_INSTALLMENT | 1               | I      |
    And debt positions <identifiers> inserted into an ingestion flow file with version <csv_version>-eng
    When the organization uploads the debt positions file
    Then the ingestion file is processed correctly
    And the debt positions <identifiers> are created in status UNPAID
    And the notices of each debt positions are present in GPD archive in status valid
    And the checks of debt positions expiration are scheduled

    Examples:
      | identifiers | csv_version |
      | A B C       | 2_0         |


  @<csv_version> @it
  @gpd
  Scenario Outline: Organization interacting with GPD creates 3 debt positions by ingestion flow file using version <csv_version>
    Given organization interacting with GPD
    And debt positions <identifiers> with the installments configured as follows:
      | identifier | po index | po type            | installment seq | action |
      | A          | 1        | SINGLE_INSTALLMENT | 1               | I      |
      | B          | 1        | SINGLE_INSTALLMENT | 1               | I      |
      | C          | 1        | SINGLE_INSTALLMENT | 1               | I      |
    And debt positions <identifiers> inserted into an ingestion flow file with version <csv_version>
    When the organization uploads the debt positions file
    Then the ingestion file is processed correctly
    And the debt positions <identifiers> are created in status UNPAID
    And the notices of each debt positions are present in GPD archive in status valid
    And the checks of debt positions expiration are scheduled

    Examples:
      | identifiers | csv_version |
      | A B C       | 1_4         |
      | A B C       | 1_3         |
      | A B C       | 1_2         |
      | A B C       | 1_1         |
      | A B C       | 1_0         |