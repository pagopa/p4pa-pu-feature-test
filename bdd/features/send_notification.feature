@send
Feature: Management of debt position notified by SEND

  @gpd
  Scenario: A simple debt position is notified by SEND and when it is paid the amount is updated
    Given a simple debt position created by organization interacting with GPD
    And a notification created for the installment 1 of payment option 1
    When the organization requires the notification to be uploaded to SEND
    Then the notification is in status accepted and the IUN is assigned to the installment
    And SEND has set a notification fee
    When the citizen pays the installment 1 of payment option 1
    Then the receipt is processed correctly
    And the amount of installment is increased by the notification fee
