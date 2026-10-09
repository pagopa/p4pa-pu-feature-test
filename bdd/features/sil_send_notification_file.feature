@sil_send_notification
Feature: SEND notification import from a file by SIL

  Scenario: SEND notifications related to a campaign are created from a file, by a SIL interacting with GPD
    Given simple debt positions 1 2 3 created by organization interacting with GPD
    And a SEND campaign file prepared to notify the single installment of debt positions 1 2 3
    When SIL uploads the SEND campaign file
    Then the SEND campaign file is processed correctly
    And the campaign has each notifications in status in progress
    And each notifications are in status delivered and the IUN is assigned to the related installments

