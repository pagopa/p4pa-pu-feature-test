@receipts_file
Feature: An organizations creates receipts by importing file

  @gpd
  Scenario: As a positive result of importing a receipts file by an organization interacting with GPD, missing debt positions are created
    Given organization interacting with GPD
    And receipts of non-existent debt positions inserted into an ingestion flow file with version 1_3
    When the organization uploads the receipts file
    Then the receipts file is processed correctly
    And the debt positions are created correctly with origin receipt_file
    And the receipts are created correctly with origin receipt_file

  @aca
  Scenario: As a positive result of importing a receipts file by an organization interacting with ACA, missing debt positions are created
    Given organization interacting with ACA
    And receipts of non-existent debt positions inserted into an ingestion flow file with version 1_3
    When the organization uploads the receipts file
    Then the receipts file is processed correctly
    And the debt positions are created correctly with origin receipt_file
    And the receipts are created correctly with origin receipt_file

  @gpd
  Scenario: As a positive result of importing a receipts file by an organization interacting with GPD, a debt position is updated
    Given a simple debt position created by organization interacting with GPD
    And a receipt of a debt position inserted into an ingestion flow file with version 1_3
    When the organization uploads the receipts file
    Then the receipts file is processed correctly
    And the receipt is created correctly with origin receipt_file
    And the installment of payment option 1 is in status paid
    And the debt position is in status paid

  @aca
  Scenario: As a positive result of importing a receipts file by an organization interacting with ACA, a debt position is updated
    Given a simple debt position created by organization interacting with ACA
    And a receipt of a debt position inserted into an ingestion flow file with version 1_3
    When the organization uploads the receipts file
    Then the receipts file is processed correctly
    And the receipt is created correctly with origin receipt_file
    And the installment of payment option 1 is in status paid
    And the debt position is in status paid
