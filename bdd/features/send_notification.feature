@send
Feature: Management of debt position notified by SEND

  @gpd
  Scenario: A simple debt position is notified by SEND and when it is paid the amount is updated
    Given a simple debt position A for citizen X created by organization interacting with GPD
    And a notification created for the single installment of debt position A
    When the organization requires the notification to be uploaded to SEND
    Then the notification is in status accepted and the IUN is assigned to the installment
    And SEND has set a notification fee
    When the citizen X pays the installment of debt position A
    Then the receipt of debt position A is processed correctly
    And the amount of installment of debt position A is increased by the notification fee

  @gpd
  Scenario: Two simple debt position with two different debtor are notified by SEND and when they are paid the amount is updated
    Given a simple debt position A for citizen X created by organization interacting with GPD
    And a simple debt position B for citizen Y created by organization interacting with GPD
    And a notification created for the single installment of debt positions A B
    When the organization requires the notification to be uploaded to SEND
    Then the notification is in status accepted and the IUN is assigned to all installments
    And SEND has set a notification fee
    When the citizen X pays the installment of debt position A
    Then the receipt of debt position A is processed correctly
    And the amount of installment of debt position A is increased by the notification fee
    When the citizen Y pays the installment of debt position B
    Then the receipt of debt position B is processed correctly
    And the amount of installment of debt position B is increased by the notification fee

  @gpd
  Scenario: A debt position with 2 installments is notified by SEND and when it is paid the amount is updated for all installments
    Given a debt position A with 1 payment option and 2 installments created by organization interacting with GPD
    And a notification created for the 2 installments of debt positions A
    When the organization requires the notification to be uploaded to SEND
    Then the notification is in status accepted and the IUN is assigned to all installments
    And SEND has set a notification fee
    When the citizen pays the installment 1 of debt position A
    Then the receipt of debt position A is processed correctly
    And the amount of installment 1 of debt position A is increased by the notification fee
    When the citizen pays the installment 2 of debt position A
    Then the receipt of debt position A is processed correctly
    And the amount of installment 2 of debt position A is increased by the notification fee