@cie_debt_positions
Feature: Management of debt positions related to the issuance of the CIE

  Scenario Outline: A citizen creates a spontaneous debt position related to CIE issued by <organization_name>
    Given the broker with code 'cie' delegate for the issuance of CIE
    And a citizen who requests the CIE to the organization <organization_name> due to '<reason_of_request>'
    When the citizen confirms the request for creation of the spontaneous
    Then the debt position is in status unpaid
    And it has only one installment with 2 transfers: the owner beneficiary is <organization_name> and the other is MEF
    And the check of debt position expiration is scheduled
    When the citizen pays the spontaneous
    Then the receipt is processed correctly for <organization_name> with classification disabled
    And the debt position is in status paid
    And the check of debt position expiration is canceled

    Examples:
      | organization_name | reason_of_request    |
      | Milano            | renewal expired card |
      | Brescia           | first card issuance  |
