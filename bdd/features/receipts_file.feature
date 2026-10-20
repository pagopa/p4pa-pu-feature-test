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
    Then the receipt is imported correctly and the debt position is paid

    @gpd
    Examples:
      | interaction |
      | GPD         |

    @aca
    Examples:
      | interaction |
      | ACA         |

  @receipts_file_update
  Scenario: A receipt imported from a file for a debt position in PU is updated by importing it again with modified data and balance
    Given a simple debt position created by organization interacting with GPD
    And a receipt successfully imported from a receipts file with version 1_3
    When the same receipt with amount increased by 20 euros, modified remittance information and balance is inserted into an ingestion flow file with version 1_3
    And the organization uploads the receipts file
    Then the receipt is imported correctly and the debt position is paid
    And the receipt is updated
    And the installment keeps its original amount
    And the assessment details are recalculated
    And the assessment detail is created correctly based on balance

  @receipts_file_update
  Scenario: A technical debt position created by importing a receipts file is updated by importing the same receipt again with modified data and balance
    Given organization interacting with GPD
    And a receipt with balance of a non-existent debt position successfully imported from a receipts file with version 1_3
    When the same receipt with amount increased by 10 euros, modified remittance information and balance is inserted into an ingestion flow file with version 1_3
    And the organization uploads the receipts file
    Then the receipt is imported correctly and the debt position is paid
    And the receipt is updated
    And the assessment details are recalculated
    And the assessment detail is created correctly based on balance
    And the technical debt position is updated

  @receipts_file_update
  Scenario: An installment paid by a receipt imported from a file is updated with the data of the receipt sent by pagoPA node
    Given a simple debt position created by organization interacting with GPD
    And a receipt successfully imported from a receipts file with version 1_3
    When the citizen pays the installment
    Then the receipt is processed correctly
    And the receipt is created correctly with origin receipt_pagopa
    And the installment is updated with the data of the pagoPA receipt
