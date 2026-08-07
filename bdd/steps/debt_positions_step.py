import json
import uuid
from datetime import datetime
from pathlib import Path

from behave import given, when, then

from api.debt_positions import post_create_debt_position, \
    get_debt_position_by_organization_id_and_installment_nav, get_installment
from api.pagopa_payments import post_create_debt_position_on_gpd
from bdd.steps.authentication_step import step_get_token_org
from bdd.steps.gpd_aca_step import step_verify_presence_debt_position_in_gpd_or_aca
from bdd.steps.utils.assertions import assert_response_ok
from bdd.steps.utils.debt_position_utility import calculate_po_total_amount, calculate_amount_first_transfer, \
    find_payment_option_by_po_index, find_installment_by_seq_num_and_po_index, create_debt_position, create_installment, \
    create_payment_option, create_transfer, generate_iuv, fetch_debt_position, get_installment_paid, \
    set_installment_paid, get_stored_debt_position, store_debt_position_by_id
from bdd.steps.utils.utility import retry_get_dp_status
from bdd.steps.workflow_step import check_workflow_status, step_debt_position_workflow_check_expiration
from config.configuration import settings
from model.classification import AssessmentRegistry
from model.csv_file_debt_positions import CSVVersion
from model.debt_position import DebtPosition, Installment, Status, PaymentOptionType, \
    PAYMENTS_REPORTING_OUTCOME_9_REMITTANCE, ANONYMOUS_DEBTOR_FISCAL_CODE
from model.debt_position import DebtPositionOrigin
from model.workflow_hub import WorkflowStatus


@given("a new debt position of type {debt_position_type_org_code}")
def step_create_dp_entity(context, debt_position_type_org_code = settings.debt_position_type_org_code.feature_test):
    debt_position = create_debt_position(token=context.token, traceparent=context.traceparent,
                                         organization_id=context.org_info.id,
                                         debt_position_type_org_code=debt_position_type_org_code)

    context.debt_position = debt_position
    context.debt_position_type_org_code = debt_position_type_org_code


@given(
    "payment option {po_index} with single installment of {amount} euros with due date set in {expiration_days} days")
def step_create_po_and_single_inst_entities(context, po_index, amount, expiration_days, balance=False,
                                            citizen_identifier=None, status=None):
    payment_option = create_payment_option(po_index=int(po_index),
                                           payment_option_type=PaymentOptionType.SINGLE_INSTALLMENT)

    amount_cents = int(amount) * 100
    assessment_registry = AssessmentRegistry()
    balance_str = None
    if balance:
        balance_template = Path('./bdd/steps/file_template/balance.xml').read_text()
        balance_str = (balance_template.format(section_code=assessment_registry.section_code,
                                               office_code=assessment_registry.office_code,
                                               assessment_code=assessment_registry.assessment_code,
                                               amount="{:.2f}".format(int(amount)))
                       .replace('\n', '')).replace(' ', '')

    installment = create_installment(amount_cents=amount_cents, expiration_days=int(expiration_days), seq_num=1,
                                     balance=balance_str, citizen_identifier=citizen_identifier, status=status)
    payment_option.installments.append(installment)

    context.debt_position.payment_options.append(payment_option)


@given(
    "payment option {po_index} with {installments_size} installments with due date set in {expiration_days} days")
def step_create_po_and_inst_entities(context, po_index, installments_size, expiration_days):
    payment_option = create_payment_option(po_index=int(po_index), payment_option_type=PaymentOptionType.INSTALLMENTS)

    for i in range(int(installments_size)):
        installment = create_installment(expiration_days=int(expiration_days), seq_num=i + 1)
        payment_option.installments.append(installment)

    context.debt_position.payment_options.append(payment_option)


@when("the organization creates the debt position")
def step_create_dp(context):
    """Creates the debt position and validates the outcome. It:

    - posts the debt position and asserts the call succeeds;
    - validates the whole created structure (payment options, installments, first transfer) in `TO_SYNC`;
    - checks the organization's sync workflow (ACA/GPD) completes.
    """
    debt_position = context.debt_position

    res = post_create_debt_position(token=context.token, traceparent=context.traceparent, debt_position=debt_position.to_json())

    assert_response_ok(res, "Create debt position")

    validate_debt_position_created(org_info=context.org_info, debt_position_request=debt_position,
                                   debt_position_response=res.json(),
                                   status=Status.TO_SYNC)

    context.debt_position = DebtPosition.from_dict(res.json())

    check_workflow_status(context=context, workflow_type=context.org_info.workflow_type,
                          entity_id=context.debt_position.debt_position_id, status=WorkflowStatus.COMPLETED)


@then("the debt position is in status {status}")
def step_check_dp_status(context, status, debt_position_id=None):
    debt_position_id = debt_position_id if debt_position_id is not None else context.debt_position.debt_position_id

    retry_get_dp_status(token=context.token, traceparent=context.traceparent, debt_position_id=debt_position_id, status=status.upper())


@then("the payment option {po_index} is in status {status}")
def step_check_po_status(context, po_index, status):
    debt_position = fetch_debt_position(context)

    payment_option = find_payment_option_by_po_index(debt_position=debt_position, po_index=int(po_index))

    assert payment_option.status.value == status.upper(), \
        f"Payment option {po_index} status mismatch: expected {status.upper()}, got {payment_option.status.value}"


@then("the installment of payment option {po_index} is in status {status}")
@then("the installment {installment_seq_num} of payment option {po_index} is in status {status}")
def step_check_installment_status(context, po_index, status, installment_seq_num='1'):
    debt_position = fetch_debt_position(context)

    installment = find_installment_by_seq_num_and_po_index(debt_position=debt_position, po_index=int(po_index),
                                                           seq_num=int(installment_seq_num))

    assert installment.status.value == status.upper(), \
        f"Installment status mismatch: expected {status.upper()}, got {installment.status.value}"


@then("the installment of the created debt position is in status {status}")
def step_check_outcome9_installment_status(context, status):
    debt_position = fetch_debt_position(context)
    installment = debt_position.payment_options[0].installments[0]

    assert installment.status.value == status.upper(), \
        f"Installment status mismatch: expected {status.upper()}, got {installment.status.value}"


@given("a simple debt position created by organization interacting with {pagopa_interaction}")
@given("a simple debt position of type {dp_type_org_code} created by organization interacting with {pagopa_interaction}")
@given(
    "a simple debt position {dp_identifier} for citizen {citizen_identifier} created by organization interacting with {pagopa_interaction}")
def step_create_simple_debt_position(context, pagopa_interaction, dp_identifier=None, citizen_identifier=None,
                                     dp_type_org_code=settings.debt_position_type_org_code.feature_test):
    """Creates a simple, single-installment debt position in one step. It:

    - gets the organization token and builds the debt position entity;
    - creates it and checks it becomes `UNPAID`;
    - verifies the notice is present as `valid` in the GPD/ACA archive;
    - checks the expiration workflow is scheduled.
    """
    step_get_token_org(context=context, pagopa_interaction=pagopa_interaction)
    step_create_dp_entity(context=context, debt_position_type_org_code=dp_type_org_code)
    step_create_po_and_single_inst_entities(context=context, po_index=1, amount=100,
                                            expiration_days=3, citizen_identifier=citizen_identifier)
    step_create_dp(context=context)
    step_check_dp_status(context=context, status=Status.UNPAID.value)
    step_verify_presence_debt_position_in_gpd_or_aca(context=context, pagopa_interaction=pagopa_interaction, status='valid')

    step_debt_position_workflow_check_expiration(context=context, status="scheduled")

    if dp_identifier is not None:
        store_debt_position_by_id(context, dp_identifier)


@given("a simple debt position with balance created by organization interacting with {pagopa_interaction}")
def step_create_simple_debt_position_with_balance(context, pagopa_interaction):
    """Like `a simple debt position created by organization...`, but with a balance set to the installment. It:

    - creates the debt position and checks it become `UNPAID`;
    - verifies the notice is present as `valid` in the GPD/ACA archive;
    - checks the expiration workflow is scheduled."""
    step_get_token_org(context=context, pagopa_interaction=pagopa_interaction)
    step_create_dp_entity(context=context)
    step_create_po_and_single_inst_entities(context=context, po_index=1, amount=100, expiration_days=3, balance=True)
    step_create_dp(context=context)
    step_check_dp_status(context=context, status=Status.UNPAID.value)
    step_verify_presence_debt_position_in_gpd_or_aca(context=context, pagopa_interaction=pagopa_interaction, status='valid')
    step_debt_position_workflow_check_expiration(context=context, status="scheduled")


@given(
    "a complex debt position with {po_size} payment options created by organization interacting with {pagopa_interaction}")
@given(
    "a debt position {dp_identifier} with {po_size} payment option and {installments_size} installments created by organization interacting with {pagopa_interaction}")
def step_create_complex_debt_position(context, po_size, pagopa_interaction, dp_identifier=None, installments_size=2):
    """Creates a complex debt position (more than 1 payment options with installments) in one step. It:

    - gets the organization token and builds the payment options;
    - creates the debt position and checks it becomes `UNPAID`;
    - verifies presence in the GPD/ACA archive and the scheduled expiration workflow.
    """
    step_get_token_org(context=context, pagopa_interaction=pagopa_interaction)
    step_create_dp_entity(context=context)
    for i in range(int(po_size)):
        step_create_po_and_inst_entities(context=context, po_index=i + 1, installments_size=installments_size, expiration_days=3)
    step_create_dp(context=context)
    step_check_dp_status(context=context, status=Status.UNPAID.value)
    step_verify_presence_debt_position_in_gpd_or_aca(context=context, pagopa_interaction=pagopa_interaction, status='valid')

    step_debt_position_workflow_check_expiration(context=context, status="scheduled")

    if dp_identifier is not None:
        store_debt_position_by_id(context, dp_identifier)


@then("the debt positions are created correctly with origin {debt_position_origin}")
def step_check_debt_positions_created(context, debt_position_origin: str = DebtPositionOrigin.REPORTING_PAGOPA.value):
    """Runs the `the debt position is created correctly` checks for every debt position imported from file."""
    context.imported_installments = []
    for i in range(context.receipts_rows_len):
        step_check_debt_position_created(context=context, debt_position_origin=debt_position_origin,
                                         iuv=context.iuvs[i])
        context.imported_installments.append(get_installment_paid(context))


@then("the debt position is created correctly")
def step_check_debt_position_created(context, debt_position_origin: str = DebtPositionOrigin.REPORTING_PAGOPA.value,
                                     iuv: str = None):
    """Checks that the debt position was created correctly. It:

    - looks it up by NAV and asserts exactly one is found;
    - verifies its origin and, for `RECEIPT_FILE` origin, that it is `PAID`;
    - checks the installment IUV and, for `REPORTING_PAGOPA` origin, the outcome-9 remittance and anonymous debtor.
    """
    token = context.token
    org_info = context.org_info
    iuv = iuv if iuv else context.iuv

    nav = '3' + iuv
    res = get_debt_position_by_organization_id_and_installment_nav(token, context.traceparent, organization_id=org_info.id, nav=nav)

    assert_response_ok(res, "Get debt position by NAV")
    assert len(res.json()) == 1, \
        f"Expected exactly 1 debt position for NAV {nav}, got {len(res.json())}"

    res_debt_position = res.json()[0]
    assert res_debt_position['debtPositionId'] is not None

    debt_position = fetch_debt_position(context, debt_position_id=res_debt_position['debtPositionId'])
    assert DebtPositionOrigin[debt_position_origin.upper()] == debt_position.debt_position_origin
    if DebtPositionOrigin.RECEIPT_FILE.value == debt_position_origin.upper():
        assert Status.PAID == debt_position.status

    installment = debt_position.payment_options[0].installments[0]
    assert iuv == installment.iuv
    if DebtPositionOrigin.REPORTING_PAGOPA.value == debt_position_origin.upper():
        assert PAYMENTS_REPORTING_OUTCOME_9_REMITTANCE == installment.remittance_information
        assert ANONYMOUS_DEBTOR_FISCAL_CODE == installment.debtor.fiscal_code

    context.debt_position = debt_position
    set_installment_paid(context, installment)


@then("the installment has {installment_field} field populated")
@then("the installment of debt position {dp_identifier} has {installment_field} field populated")
def step_check_installment_fields(context, installment_field: str, dp_identifier: str = None):
    debt_position = get_stored_debt_position(context, dp_identifier)
    installment = debt_position.payment_options[0].installments[0]

    res = get_installment(token=context.token, traceparent=context.traceparent, installment_id=installment.installment_id)

    assert_response_ok(res, "Get installment by id")
    assert installment_field in res.json()


def validate_debt_position_created(org_info, debt_position_request: DebtPosition, debt_position_response: dict,
                                   status: Status, csv_version: str = None):
    _validate_debt_position_fields(org_info, debt_position_request, debt_position_response, status, csv_version)
    _validate_payment_options(org_info, debt_position_request, debt_position_response['paymentOptions'], status,
                              csv_version)


def _validate_debt_position_fields(org_info, request, response, status, csv_version):
    assert response['status'] == status.value
    assert response['debtPositionTypeOrgId'] == request.debt_position_type_org_id

    if request.iupd_org is None or not CSVVersion.is_v2(csv_version):
        assert response['iupdOrg'].startswith(org_info.fiscal_code)
    else:
        assert response['iupdOrg'] == request.iupd_org

    if csv_version:
        csv_version = CSVVersion(csv_version)
        if not CSVVersion.is_v2(csv_version):
            assert f"DebtPosition with code {settings.debt_position_type_org_code.feature_test} was created" in response[
                'description']
        if csv_version <= CSVVersion.V1_4:
            assert len(response['paymentOptions']) == 1
            assert len(response['paymentOptions'][0]['installments']) == 1
        if csv_version <= CSVVersion.V1_2:
            assert response['flagPuPagoPaPayment'] is True


def _validate_payment_options(org_info, request, response_options, status, csv_version):
    assert len(response_options) == len(request.payment_options)

    map_po_request = {po.payment_option_index: po for po in request.payment_options}
    for po_response in response_options:
        if csv_version and CSVVersion(csv_version) < CSVVersion.V1_4:
            assert po_response['paymentOptionIndex'] == 1

        po_request = map_po_request.get(po_response['paymentOptionIndex'])
        _validate_payment_option(po_response, po_request, status, csv_version)

        map_inst_request = {inst.iud: inst for inst in po_request.installments}
        _validate_installments(org_info, map_inst_request, po_response['installments'], status)


def _validate_payment_option(po_response, po_request, status, csv_version):
    assert po_response['status'] == status.value
    assert po_response['paymentOptionType'] == po_request.payment_option_type.value
    assert po_response['totalAmountCents'] == calculate_po_total_amount(po_request)
    assert len(po_response['installments']) == len(po_request.installments)

    if csv_version and not CSVVersion.is_v2(csv_version):
        assert po_response['description'] == 'Pagamento Singolo Avviso'


def _validate_installments(org_info, inst_request_map, inst_responses, status):
    for inst_response in inst_responses:
        inst_request = inst_request_map.get(inst_response['iud'])

        assert inst_response['status'] == status.value
        if status == Status.TO_SYNC:
            assert inst_response['syncStatus']['syncStatusFrom'] == Status.DRAFT.value
            assert inst_response['syncStatus']['syncStatusTo'] == Status.UNPAID.value

        assert inst_response['iupdPagopa'].startswith(org_info.fiscal_code)
        assert len(inst_response['iuv']) == 17
        assert len(inst_response['nav']) == 18 and inst_response['nav'] == '3' + inst_response['iuv']
        assert inst_response['dueDate'] == inst_request.due_date
        assert inst_response['amountCents'] == inst_request.amount_cents
        assert inst_response['debtor'] == json.loads(inst_request.debtor.to_json())
        assert len(inst_response['transfers']) == len(inst_request.transfers) + 1

        _validate_first_transfer(org_info, inst_response, inst_request)


def _validate_first_transfer(org_info, inst_response, inst_request):
    first_transfer = next(transfer for transfer in inst_response['transfers'] if transfer['transferIndex'] == 1)

    assert first_transfer['orgFiscalCode'] == org_info.fiscal_code
    assert first_transfer['orgName'] == org_info.name
    assert first_transfer['iban'] == org_info.iban
    assert first_transfer['category'] is not None
    assert first_transfer['remittanceInformation'] == inst_request.remittance_information
    assert first_transfer['amountCents'] == calculate_amount_first_transfer(
        installment=Installment.from_dict(inst_request))


@given("a simple debt position created on {pagopa_interaction}")
def step_create_dp_on_gpd(context, pagopa_interaction):
    """Creates a simple debt position directly on GPD/ACA (bypassing PU creation):

    - builds the entity and its transfer, generating IUV/NAV/IUPD;
    - posts it to GPD/ACA and asserts the call succeeds;
    - verifies the notice is present as `VALID` in the GPD/ACA archive.
    """
    step_get_token_org(context=context, pagopa_interaction=pagopa_interaction)
    step_create_dp_entity(context=context, debt_position_type_org_code=settings.debt_position_type_org_code.feature_test)
    step_create_po_and_single_inst_entities(context=context, po_index=1, amount=100, expiration_days=3, status=Status.TO_SYNC.value)
    debt_position = context.debt_position
    installment = debt_position.payment_options[0].installments[0]

    transfer = create_transfer(token=context.token, traceparent=context.traceparent, org_info=context.org_info,
                               debt_position_type_org_code=settings.debt_position_type_org_code.feature_test,
                               remittance_information=installment.remittance_information, amount_cents=installment.amount_cents)

    installment.transfers.append(transfer)
    installment.iuv = generate_iuv()
    installment.nav = '3' + installment.iuv
    installment.iupd_pagopa = f'{context.org_info.fiscal_code}_{datetime.now().strftime("%Y%m%d%H%M%S%f")[:15]}_{uuid.uuid4().hex[:5]}'
    context.debt_position.payment_options[0].installments[0] = installment

    res = post_create_debt_position_on_gpd(token=context.token, traceparent=context.traceparent, debt_position=debt_position.to_json(), iud=installment.iud)

    assert_response_ok(res, "Create debt position on GPD")

    step_verify_presence_debt_position_in_gpd_or_aca(context=context, pagopa_interaction=pagopa_interaction,
                                                     status='VALID')
