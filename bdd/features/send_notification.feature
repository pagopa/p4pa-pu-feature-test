@send
Feature: Management of debt position notified by SEND

  @gpd
  Scenario: A simple debt position is notified by SEND and when it is paid the amount is updated
    Given a simple debt position A for citizen X created by organization interacting with GPD
    And a notification created for the single installment of debt position A
    When the organization requires the notification to be uploaded to SEND
    Then the notification is in status accepted and the IUN is assigned to the installment
    And SEND has set a notification fee
    When the citizen pays the installment
    Then the receipt is processed correctly
    And the amount of installment is increased by the notification fee

  @gpd
  Scenario: Two simple debt position with two different debtor are notified by SEND
    Given a simple debt position A for citizen X created by organization interacting with GPD
    And a simple debt position B for citizen Y created by organization interacting with GPD
    And a notification created for the single installment of debt positions A B
    When the organization requires the notification to be uploaded to SEND
    Then the notification is in status accepted and the IUN is assigned to all installments
