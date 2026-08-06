@receipts_file
Feature: Receipts import from a file

  Scenario Outline: Missing debt positions are created by importing a receipts file, with an organization interacting with <interaction>
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

  Scenario Outline: A debt position is updated by importing a receipts file, with an organization interacting with <interaction>
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
