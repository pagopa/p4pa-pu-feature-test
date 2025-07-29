@rt_file
Feature: An organizations creates debt positions by importing receipts file


  @wip
  @gpd
  Scenario: Organization interacting with GPD creates debt position by receipt file
    Given organization interacting with GPD
    And receipts of non-existent debt positions inserted into an ingestion flow file with version 1_3
    When the organization uploads the receipts file
    Then the receipts file is processed correctly
    And the debt positions are created correctly with origin receipt_file
    And the receipts are created correctly with origin receipt_file
