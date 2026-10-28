@debt_positions_file
Feature: Debt positions import from a file

  @<csv_version> @eng
  @gpd
  Scenario Outline: Debt positions are created from an ingestion flow file version <csv_version>, by an organization interacting with GPD
    Given organization interacting with GPD
    And debt positions <identifiers> with the installments configured as follows:
      | identifier | po index | po type            | installment seq | action |
      | A          | 1        | INSTALLMENTS       | 1               | I      |
      | A          | 1        | INSTALLMENTS       | 2               | I      |
      | A          | 2        | SINGLE_INSTALLMENT | 1               | I      |
      | B          | 1        | INSTALLMENTS       | 1               | I      |
      | B          | 1        | INSTALLMENTS       | 2               | I      |
      | C          | 1        | SINGLE_INSTALLMENT | 1               | I      |
    And debt positions <identifiers> inserted into an ingestion flow file with version <csv_version>
    When the organization uploads the debt positions file
    Then the ingestion file is processed correctly
    And the debt positions <identifiers> are created in status UNPAID
    And the notices of each debt positions are present in GPD archive in status valid
    And the checks of debt positions expiration are scheduled

    Examples:
      | identifiers | csv_version |
      | A B C       | 2_0-eng     |
      | A B C       | 2_0         |

  @<csv_version> @it
  @gpd
  Scenario Outline: Debt positions are created from an ingestion flow file version <csv_version>, by an organization interacting with GPD
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

  @debt_positions_file_update
  @gpd
  Scenario: Debt positions imported from a file version 2_0 are updated by a second file that cancels, modifies and adds installments, by an organization interacting with GPD
    Given organization interacting with GPD
    And debt positions A B C with the installments configured as follows are successfully imported from an ingestion flow file with version 2_0:
      | identifier | po index | po type            | installment seq | action |
      | A          | 1        | INSTALLMENTS       | 1               | I      |
      | A          | 1        | INSTALLMENTS       | 2               | I      |
      | A          | 1        | INSTALLMENTS       | 3               | I      |
      | A          | 2        | SINGLE_INSTALLMENT | 1               | I      |
      | B          | 1        | INSTALLMENTS       | 1               | I      |
      | B          | 1        | INSTALLMENTS       | 2               | I      |
      | B          | 1        | INSTALLMENTS       | 3               | I      |
      | B          | 2        | SINGLE_INSTALLMENT | 1               | I      |
      | C          | 1        | INSTALLMENTS       | 1               | I      |
      | C          | 1        | INSTALLMENTS       | 2               | I      |
      | C          | 1        | INSTALLMENTS       | 3               | I      |
      | C          | 2        | SINGLE_INSTALLMENT | 1               | I      |
    When the changes configured as follows are inserted into an ingestion flow file with version 2_0:
      | identifier | po index | installment seq | action |
      | A          | 1        | 3               | A      |
      | B          | 1        | 1               | M      |
      | C          | 2        | 2               | I      |
    And the organization uploads the debt positions file
    Then the ingestion file is processed correctly
    And the installment 3 of payment option 1 of debt position A is cancelled and its notice is removed from GPD
    And the installment 1 of payment option 1 of debt position B is saved with the requested data
    And the installment 1 of payment option 1 of debt position B matches its notice on GPD
    And the installment 2 of payment option 2 of debt position C is saved with the requested data
    And the installment 2 of payment option 2 of debt position C matches its notice on GPD

  @debt_positions_file_update
  @gpd
  Scenario: A debt position imported from a file version 2_0 is updated by a second file that adds, modifies and cancels its installments, by an organization interacting with GPD
    Given organization interacting with GPD
    And debt positions A with the installments configured as follows are successfully imported from an ingestion flow file with version 2_0:
      | identifier | po index | po type            | installment seq | action |
      | A          | 1        | INSTALLMENTS       | 1               | I      |
      | A          | 1        | INSTALLMENTS       | 2               | I      |
      | A          | 1        | INSTALLMENTS       | 3               | I      |
      | A          | 2        | SINGLE_INSTALLMENT | 1               | I      |
    When the changes configured as follows are inserted into an ingestion flow file with version 2_0:
      | identifier | po index | installment seq | action |
      | A          | 2        | 2               | I      |
      | A          | 1        | 1               | M      |
      | A          | 1        | 3               | A      |
    And the organization uploads the debt positions file
    Then the ingestion file is processed correctly
    And the installment 3 of payment option 1 of debt position A is cancelled and its notice is removed from GPD
    And the installment 1 of payment option 1 of debt position A is saved with the requested data
    And the installment 1 of payment option 1 of debt position A matches its notice on GPD
    And the installment 2 of payment option 2 of debt position A is saved with the requested data
    And the installment 2 of payment option 2 of debt position A matches its notice on GPD

  @debt_positions_file_update
  @gpd
  Scenario: Debt positions imported from a file version 1_4 are cancelled and modified by a second file, whose new installment creates a new debt position, by an organization interacting with GPD
    Given organization interacting with GPD
    And debt positions A B C with the installments configured as follows are successfully imported from an ingestion flow file with version 1_4:
      | identifier | po index | po type            | installment seq | action |
      | A          | 1        | SINGLE_INSTALLMENT | 1               | I      |
      | B          | 1        | SINGLE_INSTALLMENT | 1               | I      |
      | C          | 1        | SINGLE_INSTALLMENT | 1               | I      |
    When the changes configured as follows are inserted into an ingestion flow file with version 1_4:
      | identifier | po index | installment seq | action |
      | A          | 1        | 1               | A      |
      | B          | 1        | 1               | M      |
      | C          | 1        | 2               | I      |
    And the organization uploads the debt positions file
    Then the ingestion file is processed correctly
    And the installment 1 of payment option 1 of debt position A is cancelled and its notice is removed from GPD
    And the debt position A is in status cancelled
    And the installment 1 of payment option 1 of debt position B is saved with the requested data
    And the installment 1 of payment option 1 of debt position B matches its notice on GPD
    And the installment 2 of payment option 1 of debt position C is created in a new debt position
    And the debt position C is unchanged