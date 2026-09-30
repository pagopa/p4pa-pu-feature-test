@sil_classification
Feature: Export requested by SIL

  @sil_export_paid
  Scenario: SIL requests the export of paid notices
    Given a simple debt position created by organization interacting with GPD
    and the successful payment of the installment
    When SIL requests the export of paid notices with version v1.4
    Then the paid notices export completes successfully
    And the paid notice appears in the export with the correct data

  @sil_export_paid
  Scenario: SIL requests the incremental export of paid notices with receipts
    Given a simple debt position created by organization interacting with GPD
    and the successful payment of the installment
    When SIL requests the incremental export of paid notices with receipt and version v1.4
    Then the paid notices export completes successfully
    And the paid notice appears in the export with the correct data

  @sil_export_reconciliation
  Scenario: SIL imports a treasury flow and the paid notice is correctly reconciled
    Given a simple debt position created by organization interacting with GPD
    And the successful payment of the installment
    And a payment reporting with outcome code 0 has been successfully processed for the installment
    When SIL imports the treasury flow of type O
    Then the treasury import completes successfully
    When SIL requests the reconciliation export for classification label RT_IUF_TES with version v1.4
    Then the reconciliation export completes successfully
    And the paid notice appears in the reconciliation export with classification label RT_IUF_TES