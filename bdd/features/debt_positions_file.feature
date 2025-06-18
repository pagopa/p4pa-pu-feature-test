@debt_positions_file
Feature: An organizations creates debt positions by importing file

  @test
  Scenario Outline: Organization interacting with GPD creates 3 debt positions by ingestion flow file
    Given organization interacting with GPD
    And debt positions <identifiers> configured as follows:
      | identifier | po index | installments size | action |
      | A          | 1        | 2                 | I      |
      | A          | 2        | 1                 | I      |
      | B          | 1        | 2                 | I      |
      | C          | 1        | 1                 | I      |
    And debt positions <identifiers> inserted into an ingestion flow file with version 2_0-eng
    When the organization uploads the debt positions file
    Then the debt positions ingestion file is processed correctly

    Examples:
      | identifiers |
      | A B C       |