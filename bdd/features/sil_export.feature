@sil_export
Feature: Export requested by SIL

  @sil_export_paid
  Scenario: SIL requests the export of paid notices
    Given a simple debt position created by organization interacting with GPD
    When the citizen pays the installment of payment option 1
    Then the receipt is processed correctly
    And the debt position is in status paid
    When SIL requests the export of paid notices with version v1.4
    Then the paid notices export completes successfully
    And the paid notice appears in the export with the correct data

  @sil_export_paid
  Scenario: SIL requests the incremental export of paid notices with receipts
    Given a simple debt position created by organization interacting with GPD
    When the citizen pays the installment of payment option 1
    Then the receipt is processed correctly
    And the debt position is in status paid
    When SIL requests the incremental export of paid notices with receipt and version v1.4
    Then the paid notices export completes successfully
    And the paid notice appears in the export with the correct data
