@receipts_file
Feature: An organization creates receipts by importing a file

  Scenario Outline: As a positive result of importing a receipts file by an organization interacting with <interaction>, missing debt positions are created
    Given organization interacting with <interaction>
    And receipts of non-existent debt positions inserted into an ingestion flow file with version 1_3
    When the organization uploads the receipts file
    Then the receipts file is processed correctly
    And the debt positions are created correctly with origin receipt_file
    And the receipts are created correctly with origin receipt_file

    @gpd
    Examples:
      | interaction |
      | GPD         |

    @aca
    Examples:
      | interaction |
      | ACA         |

  Scenario Outline: As a positive result of importing a receipts file by an organization interacting with <interaction>, a debt position is updated
    Given a simple debt position created by organization interacting with <interaction>
    And a receipt of a debt position inserted into an ingestion flow file with version 1_3
    When the organization uploads the receipts file
    Then the receipts file is processed correctly
    And the receipt is created correctly with origin receipt_file
    And the installment of payment option 1 is in status paid
    And the debt position is in status paid

    @gpd
    Examples:
      | interaction |
      | GPD         |

    @aca
    Examples:
      | interaction |
      | ACA         |
