from datetime import datetime, timedelta

from behave import given, when, then

from api.arpu import get_broker_info, get_orgs_info_for_spontaneous, get_debt_position_type_orgs_for_spontaneous, \
    post_create_spontaneous
from api.auth import post_auth_token
from api.cie import get_cie_organizations, get_cie_amount
from api.debt_positions import get_debt_position, get_receipt_by_id
from bdd.steps.payments_step import step_installment_payment, step_check_receipt_processed
from config.configuration import secrets
from model.debt_position import DebtPosition, DebtPositionOrigin
from model.debt_position_cie import get_debt_position_type_org_code_by_reason, DebtPositionSpontaneous, FieldValues, \
    PaymentOptionSpontaneous, InstallmentSpontaneous, DebtorSpontaneous


def get_admin_ipzs_token() -> str:
    user_id = secrets.user_info.admin_org_ipzs.user_id
    res = post_auth_token(user_id=user_id)

    assert res.status_code == 200
    assert res.json()['access_token'] is not None

    return res.json()['access_token']

@given("the broker with code \'{external_id}\' delegate for the issuance of CIE")
def step_get_broker_and_org_delegate_for_cie(context, external_id: str):
    res_broker = get_broker_info(external_id=external_id)

    assert res_broker.status_code == 200
    assert res_broker.json()['brokerId'] is not None

    broker_id = res_broker.json()['brokerId']

    res_orgs = get_orgs_info_for_spontaneous(broker_id=broker_id)

    assert res_orgs.status_code == 200
    assert len(res_orgs.json()) == 1
    assert res_orgs.json()[0]['organizationId'] is not None
    assert res_orgs.json()[0]['orgFiscalCode'] == "00399810589"
    assert res_orgs.json()[0]['orgName'] == "Ministero dell'Interno"

    context.broker_id = broker_id
    context.organization_id = res_orgs.json()[0]['organizationId']
    context.organization_fiscal_code = res_orgs.json()[0]['orgFiscalCode']

    context.token = get_admin_ipzs_token()


def get_cie_org_fiscal_code(cie_orgs_list: list[dict], org_name: str):
    for cie_org in cie_orgs_list:
        if org_name in cie_org['label']:
            return cie_org['value']
    return None


@given("a citizen who requests the CIE to the organization {organization_name} due to '{reason_of_request}'")
def step_create_dp_cie_entity(context, organization_name: str, reason_of_request: str):
    res_cie_organizations = get_cie_organizations()

    assert res_cie_organizations.status_code == 200
    assert len(res_cie_organizations.json()['result']) > 0

    cie_org_fiscal_code = get_cie_org_fiscal_code(res_cie_organizations.json()['result'], organization_name)

    dp_type_org_code = get_debt_position_type_org_code_by_reason(reason_of_request)

    res_dp_type_orgs = get_debt_position_type_orgs_for_spontaneous(broker_id=context.broker_id,
                                                                   organization_id=context.organization_id)

    assert res_dp_type_orgs.status_code == 200
    assert len(res_dp_type_orgs.json()) > 0

    dp_type_org = next(
        (dp_type_org for dp_type_org in res_dp_type_orgs.json() if dp_type_org["code"] == dp_type_org_code), None)
    assert dp_type_org is not None

    dp_type_org_id = dp_type_org['debtPositionTypeOrgId']
    dp_type_org_desc = dp_type_org['description']
    remittance_information = "Carta d'Identità Elettronica - " + dp_type_org_desc

    res_cie_amount = get_cie_amount(org_fiscal_code=cie_org_fiscal_code, debt_position_type_org_code=dp_type_org_code)

    assert res_cie_amount.status_code == 200
    assert res_cie_amount.json()['result'] is not None

    cie_amount_cents = res_cie_amount.json()['result']

    spontaneous_request = DebtPositionSpontaneous(organization_id=context.organization_id,
                                                  debt_position_type_org_id=dp_type_org_id,
                                                  payment_options=[
                                                      PaymentOptionSpontaneous(
                                                          total_amount_cents=cie_amount_cents,
                                                          installments=[
                                                              InstallmentSpontaneous(
                                                                  amount_cents=cie_amount_cents,
                                                                  remittance_information=remittance_information,
                                                                  user_remittance_information=remittance_information,
                                                                  debtor=DebtorSpontaneous())
                                                          ])
                                                  ],
                                                  field_values=FieldValues(org_fiscal_code=cie_org_fiscal_code))

    context.spontaneous_request = spontaneous_request


@when("the citizen confirms the request for creation of the spontaneous")
def step_citizen_create_cie_spontaneous(context):
    spontaneous_request = context.spontaneous_request

    res = post_create_spontaneous(broker_id=context.broker_id, debt_position_spontaneous=spontaneous_request.to_json())

    assert res.status_code == 200
    assert res.json() is not None
    assert res.json()['debtPositionId'] is not None

    context.debt_position_id = res.json()['debtPositionId']

    res = get_debt_position(token=context.token, debt_position_id=res.json()['debtPositionId'])
    assert res.status_code == 200
    assert res.json() is not None
    context.debt_position = DebtPosition.from_dict(res.json())


@then("it has only one installment with 2 transfers: the owner beneficiary is {organization_name} and the other is MEF")
def step_check_cie_spontaneous_data(context, organization_name: str):
    spontaneous_request = context.spontaneous_request
    debt_position_created = context.debt_position

    assert debt_position_created.debt_position_origin.value == DebtPositionOrigin.SPONTANEOUS.value
    assert debt_position_created.organization_id == spontaneous_request.organization_id
    assert debt_position_created.iupd_org.startswith(context.organization_fiscal_code)
    assert debt_position_created.debt_position_type_org_id == spontaneous_request.debt_position_type_org_id

    assert len(debt_position_created.payment_options) == 1
    assert debt_position_created.payment_options[0].total_amount_cents == spontaneous_request.payment_options[0].total_amount_cents

    assert len(debt_position_created.payment_options[0].installments) == 1
    installment_created = debt_position_created.payment_options[0].installments[0]
    installment_request = spontaneous_request.payment_options[0].installments[0]
    assert installment_created.iupd_pagopa.startswith(context.organization_fiscal_code)
    assert installment_created.amount_cents == installment_request.amount_cents
    assert installment_created.due_date == (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d")
    assert installment_created.remittance_information == installment_request.remittance_information

    assert len(installment_created.transfers) == 2
    transfer_owner = next(transfer for transfer in installment_created.transfers if transfer.flag_owner == True)
    assert transfer_owner.org_fiscal_code == spontaneous_request.field_values.org_fiscal_code
    assert transfer_owner.org_name == organization_name

    other_transfer = installment_created.transfers[0] if installment_created.transfers[1] == transfer_owner else installment_created.transfers[1]
    assert other_transfer.flag_owner == False
    assert other_transfer.org_name == "Ministero dell'Economia e delle Finanze"
    assert other_transfer.org_fiscal_code == "80415740580"


@when("the citizen pays the spontaneous")
def step_citizen_pays_spontaneous(context):
    debt_position = context.debt_position
    installment_to_paid = debt_position.payment_options[0].installments[0]

    step_installment_payment(context=context, installment_to_paid=installment_to_paid,
                             org_fiscal_code_owner=context.spontaneous_request.field_values.org_fiscal_code)


@then("the receipt is processed correctly for {organization_name} with classification disabled")
def step_check_receipt_processed_without_classification(context, organization_name: str):
    spontaneous = context.spontaneous_request
    org_id = spontaneous.organization_id
    step_check_receipt_processed(context=context, classification=False, organization_id=org_id)

    installment_paid = context.installment_paid

    res = get_receipt_by_id(token=context.token, receipt_id=installment_paid.receipt_id)

    assert res.status_code == 200
    assert res.json() is not None
    receipt = res.json()
    assert receipt['orgFiscalCode'] == spontaneous.field_values.org_fiscal_code
    assert receipt['companyName'] == organization_name
    assert receipt['paymentAmountCents'] == spontaneous.payment_options[0].total_amount_cents
