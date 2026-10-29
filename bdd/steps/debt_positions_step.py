import json
import uuid
from datetime import datetime, timedelta
from pathlib import Path

from behave import given, when, then

from api.debt_position_type import get_debt_position_type_org_by_id
from api.debt_positions import post_create_debt_position, \
    get_debt_position_by_organization_id_and_installment_nav, get_installment, \
    get_debt_position_by_iuv, \
    get_debt_position, put_manage_debt_position_installments
from api.gpd_aca import get_debt_position_on_aca_or_gpd
from api.pagopa_payments import post_create_debt_position_on_gpd
from bdd.steps.authentication_step import step_get_token_org, \
    get_org_token_by_name
from bdd.steps.gpd_aca_step import \
    step_verify_presence_debt_position_in_gpd_or_aca
from bdd.steps.utils.assertions import assert_response_ok
from bdd.steps.utils.date_utils import unique_timestamp
from bdd.steps.utils.debt_position_utils import calculate_po_total_amount, \
    calculate_amount_first_transfer, \
    find_payment_option_by_po_index, find_installment_by_seq_num_and_po_index, \
    create_debt_position, create_installment, \
    create_payment_option, create_transfer, generate_iuv, fetch_debt_position, \
    get_installment_paid, \
    set_installment_paid, get_stored_debt_position, store_debt_position_by_id, \
    retrieve_dp_type_org_by_code, \
    retrieve_taxonomy_code_by_dp_type_org, build_feature_test_iud, \
    find_installment_by_iud
from bdd.steps.utils.generic_utils import get_workflow_run_id
from bdd.steps.utils.polling_utils import retry_get_dp_status
from bdd.steps.workflow_step import check_workflow_status, \
    step_debt_position_workflow_check_expiration
from config.configuration import settings
from model.classification import AssessmentRegistry
from model.csv_file_debt_positions import CSVVersion, Action
from model.debt_position import DebtPosition, Installment, Status, \
    PaymentOptionType, \
    PAYMENTS_REPORTING_OUTCOME_9_REMITTANCE, ANONYMOUS_DEBTOR_FISCAL_CODE, Debtor, \
    Stamp, NAV_PREFIX
from model.debt_position import DebtPositionOrigin
from model.workflow_hub import WorkflowStatus


@given("a new debt position of type {debt_position_type_org_code}")
def step_create_dp_entity(context, debt_position_type_org_code=settings.debt_position_type_org_code.feature_test):
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

    res = post_create_debt_position(token=context.token, traceparent=context.traceparent,
                                    debt_position=debt_position.to_json())

    assert_response_ok(res, "Create debt position")

    validate_debt_position_created(org_info=context.org_info, debt_position_request=debt_position,
                                   debt_position_response=res.json(),
                                   status=Status.TO_SYNC)

    context.debt_position = DebtPosition.from_dict(res.json())

    check_workflow_status(context=context, workflow_type=context.org_info.workflow_type,
                          entity_id=context.debt_position.debt_position_id, status=WorkflowStatus.COMPLETED)


@then("the debt position is in status {status}")
@then("the debt position {dp_identifier} is in status {status}")
def step_check_dp_status(context, status, debt_position_id=None, dp_identifier=None):
    if dp_identifier is not None:
        debt_position_id = get_stored_debt_position(context, dp_identifier).debt_position_id
    debt_position_id = debt_position_id if debt_position_id is not None else context.debt_position.debt_position_id

    retry_get_dp_status(token=context.token, traceparent=context.traceparent, debt_position_id=debt_position_id,
                        status=status.upper())


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
@given(
    "a simple debt position of type {dp_type_org_code} created by organization interacting with {pagopa_interaction}")
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
    step_verify_presence_debt_position_in_gpd_or_aca(context=context, pagopa_interaction=pagopa_interaction,
                                                     status='valid')

    step_debt_position_workflow_check_expiration(context=context, status="scheduled")

    if dp_identifier is not None:
        store_debt_position_by_id(context, dp_identifier)


@given("simple debt positions {identifiers} created by organization interacting with {pagopa_interaction}")
def step_create_multiple_debt_positions(context, identifiers, pagopa_interaction,
                                        dp_type_org_code=settings.debt_position_type_org_code.feature_test):
    """Creates multiple simple, single-installment debt positions in one step, one for each identifier. It:

    - gets the organization token;
    - for each debt position builds the entity, creates it and checks it becomes `UNPAID`;
    - verifies the notices are present as `valid` in the GPD/ACA archive;
    - checks the expiration workflows are scheduled.
    """
    step_get_token_org(context=context, pagopa_interaction=pagopa_interaction)

    for dp_identifier in identifiers.split():
        dp_identifier = dp_identifier.strip()
        step_create_dp_entity(context=context, debt_position_type_org_code=dp_type_org_code)
        step_create_po_and_single_inst_entities(context=context, po_index=1, amount=100,
                                                expiration_days=3)
        step_create_dp(context=context)
        step_check_dp_status(context=context, status=Status.UNPAID.value)
        step_verify_presence_debt_position_in_gpd_or_aca(context=context, pagopa_interaction=pagopa_interaction,
                                                         status='valid')
        step_debt_position_workflow_check_expiration(context=context, status="scheduled")

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
    step_verify_presence_debt_position_in_gpd_or_aca(context=context, pagopa_interaction=pagopa_interaction,
                                                     status='valid')
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
        step_create_po_and_inst_entities(context=context, po_index=i + 1, installments_size=installments_size,
                                         expiration_days=3)
    step_create_dp(context=context)
    step_check_dp_status(context=context, status=Status.UNPAID.value)
    step_verify_presence_debt_position_in_gpd_or_aca(context=context, pagopa_interaction=pagopa_interaction,
                                                     status='valid')

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

    nav = NAV_PREFIX + iuv
    res = get_debt_position_by_organization_id_and_installment_nav(token, context.traceparent,
                                                                   organization_id=org_info.id, nav=nav)

    assert_response_ok(res, "Get debt position by NAV")
    assert len(res.json()) == 1, \
        f"Expected exactly 1 debt position for NAV {nav}, got {len(res.json())}"

    res_debt_position = res.json()[0]
    assert res_debt_position.get('debtPositionId') is not None, f"No debtPositionId returned for NAV {nav}"

    debt_position = fetch_debt_position(context, debt_position_id=res_debt_position['debtPositionId'])
    assert DebtPositionOrigin[debt_position_origin.upper()] == debt_position.debt_position_origin, \
        f"Expected debtPositionOrigin {debt_position_origin.upper()}, got {debt_position.debt_position_origin}"
    if DebtPositionOrigin.RECEIPT_FILE.value == debt_position_origin.upper():
        assert Status.PAID == debt_position.status, \
            f"Expected debt position status PAID, got {debt_position.status}"

    installment = debt_position.payment_options[0].installments[0]
    assert iuv == installment.iuv, f"Expected installment IUV {iuv}, got {installment.iuv}"
    if DebtPositionOrigin.REPORTING_PAGOPA.value == debt_position_origin.upper():
        assert PAYMENTS_REPORTING_OUTCOME_9_REMITTANCE == installment.remittance_information, \
            f"Expected remittanceInformation {PAYMENTS_REPORTING_OUTCOME_9_REMITTANCE}, got {installment.remittance_information}"
        assert ANONYMOUS_DEBTOR_FISCAL_CODE == installment.debtor.fiscal_code, \
            f"Expected debtor fiscal code {ANONYMOUS_DEBTOR_FISCAL_CODE}, got {installment.debtor.fiscal_code}"

    context.debt_position = debt_position
    set_installment_paid(context, installment)


@then("the installment has {installment_field} field populated")
@then("the installment of debt position {dp_identifier} has {installment_field} field populated")
def step_check_installment_fields(context, installment_field: str, dp_identifier: str = None):
    debt_position = get_stored_debt_position(context, dp_identifier)
    installment = debt_position.payment_options[0].installments[0]

    res = get_installment(token=context.token, traceparent=context.traceparent,
                          installment_id=installment.installment_id)

    assert_response_ok(res, "Get installment by id")
    assert installment_field in res.json(), \
        f"Field '{installment_field}' is missing in the installment response"


def validate_debt_position_created(org_info, debt_position_request: DebtPosition, debt_position_response: dict,
                                   status: Status, csv_version: str = None):
    _validate_debt_position_fields(org_info, debt_position_request, debt_position_response, status, csv_version)
    _validate_payment_options(org_info, debt_position_request, debt_position_response['paymentOptions'], status,
                              csv_version)


def _validate_debt_position_fields(org_info, request, response, status, csv_version):
    assert response.get('status') == status.value, \
        f"Expected debt position status {status.value}, got {response.get('status')}"
    assert response.get('debtPositionTypeOrgId') == request.debt_position_type_org_id, \
        f"Expected debtPositionTypeOrgId {request.debt_position_type_org_id}, got {response.get('debtPositionTypeOrgId')}"

    if request.iupd_org is None or not CSVVersion.is_v2(csv_version):
        assert (response.get('iupdOrg') or '').startswith(org_info.fiscal_code), \
            f"Expected iupdOrg to start with {org_info.fiscal_code}, got {response.get('iupdOrg')}"
    else:
        assert response.get('iupdOrg') == request.iupd_org, \
            f"Expected iupdOrg {request.iupd_org}, got {response.get('iupdOrg')}"

    if csv_version:
        csv_version = CSVVersion(csv_version)
        if not CSVVersion.is_v2(csv_version):
            assert f"DebtPosition with code {settings.debt_position_type_org_code.feature_test} was created" in \
                   (response.get('description') or ''), \
                f"Unexpected debt position description: {response.get('description')}"
        if csv_version <= CSVVersion.V1_4:
            assert len(response.get('paymentOptions') or []) == 1, \
                f"Expected exactly 1 payment option, got {len(response.get('paymentOptions') or [])}"
            assert len(response['paymentOptions'][0].get('installments') or []) == 1, \
                f"Expected exactly 1 installment, got {len(response['paymentOptions'][0].get('installments') or [])}"
        if csv_version <= CSVVersion.V1_2:
            assert response.get('flagPuPagoPaPayment') is True, \
                f"Expected flagPuPagoPaPayment True, got {response.get('flagPuPagoPaPayment')}"


def _validate_payment_options(org_info, request, response_options, status, csv_version):
    assert len(response_options) == len(request.payment_options), \
        f"Expected {len(request.payment_options)} payment options, got {len(response_options)}"

    map_po_request = {po.payment_option_index: po for po in request.payment_options}
    for po_response in response_options:
        if csv_version and CSVVersion(csv_version) < CSVVersion.V1_4:
            assert po_response.get('paymentOptionIndex') == 1, \
                f"Expected paymentOptionIndex 1, got {po_response.get('paymentOptionIndex')}"

        po_request = map_po_request.get(po_response['paymentOptionIndex'])
        _validate_payment_option(po_response, po_request, status, csv_version)

        map_inst_request = {inst.iud: inst for inst in po_request.installments}
        _validate_installments(org_info, map_inst_request, po_response['installments'], status)


def _validate_payment_option(po_response, po_request, status, csv_version):
    assert po_response.get('status') == status.value, \
        f"Expected payment option status {status.value}, got {po_response.get('status')}"
    assert po_response.get('paymentOptionType') == po_request.payment_option_type.value, \
        f"Expected paymentOptionType {po_request.payment_option_type.value}, got {po_response.get('paymentOptionType')}"
    assert po_response.get('totalAmountCents') == calculate_po_total_amount(po_request), \
        f"Expected totalAmountCents {calculate_po_total_amount(po_request)}, got {po_response.get('totalAmountCents')}"
    assert len(po_response.get('installments') or []) == len(po_request.installments), \
        f"Expected {len(po_request.installments)} installments, got {len(po_response.get('installments') or [])}"

    if csv_version and not CSVVersion.is_v2(csv_version):
        assert po_response.get('description') == 'Pagamento Singolo Avviso', \
            f"Expected payment option description 'Pagamento Singolo Avviso', got {po_response.get('description')}"


def _validate_installments(org_info, inst_request_map, inst_responses, status):
    for inst_response in inst_responses:
        inst_request = inst_request_map.get(inst_response.get('iud'))

        assert inst_response.get('status') == status.value, \
            f"Expected installment status {status.value}, got {inst_response.get('status')}"
        if status == Status.TO_SYNC:
            assert (inst_response.get('syncStatus') or {}).get('syncStatusFrom') == Status.DRAFT.value, \
                f"Expected syncStatusFrom DRAFT, got {(inst_response.get('syncStatus') or {}).get('syncStatusFrom')}"
            assert (inst_response.get('syncStatus') or {}).get('syncStatusTo') == Status.UNPAID.value, \
                f"Expected syncStatusTo UNPAID, got {(inst_response.get('syncStatus') or {}).get('syncStatusTo')}"

        assert (inst_response.get('iupdPagopa') or '').startswith(org_info.fiscal_code), \
            f"Expected iupdPagopa to start with {org_info.fiscal_code}, got {inst_response.get('iupdPagopa')}"
        assert len(inst_response.get('iuv') or '') == 17, \
            f"Expected IUV of length 17, got {len(inst_response.get('iuv') or '')} ({inst_response.get('iuv')})"
        assert len(inst_response.get('nav') or '') == 18 and inst_response.get('nav') == NAV_PREFIX + (inst_response.get('iuv') or ''), \
            f"Unexpected NAV {inst_response.get('nav')} (expected {NAV_PREFIX + (inst_response.get('iuv') or '')})"
        assert inst_response.get('dueDate') == inst_request.due_date, \
            f"Expected dueDate {inst_request.due_date}, got {inst_response.get('dueDate')}"
        assert inst_response.get('amountCents') == inst_request.amount_cents, \
            f"Expected amountCents {inst_request.amount_cents}, got {inst_response.get('amountCents')}"
        assert inst_response.get('debtor') == json.loads(inst_request.debtor.to_json()), \
            f"Installment debtor does not match: got {inst_response.get('debtor')}"
        assert len(inst_response.get('transfers') or []) == len(inst_request.transfers) + 1, \
            f"Expected {len(inst_request.transfers) + 1} transfers, got {len(inst_response.get('transfers') or [])}"

        _validate_first_transfer(org_info, inst_response, inst_request)


def _validate_first_transfer(org_info, inst_response, inst_request):
    first_transfer = next(transfer for transfer in inst_response['transfers'] if transfer['transferIndex'] == 1)

    assert first_transfer.get('orgFiscalCode') == org_info.fiscal_code, \
        f"Expected orgFiscalCode {org_info.fiscal_code}, got {first_transfer.get('orgFiscalCode')}"
    assert first_transfer.get('orgName') == org_info.name, \
        f"Expected orgName {org_info.name}, got {first_transfer.get('orgName')}"
    assert first_transfer.get('iban') == org_info.iban, \
        f"Expected iban {org_info.iban}, got {first_transfer.get('iban')}"
    assert first_transfer.get('category') is not None, "First transfer has no category"
    assert first_transfer.get('remittanceInformation') == inst_request.remittance_information, \
        f"Expected remittanceInformation {inst_request.remittance_information}, got {first_transfer.get('remittanceInformation')}"
    assert first_transfer.get('amountCents') == calculate_amount_first_transfer(
        installment=Installment.from_dict(inst_request)), \
        f"Expected first transfer amountCents {calculate_amount_first_transfer(installment=Installment.from_dict(inst_request))}, " \
        f"got {first_transfer.get('amountCents')}"


@given("a simple debt position created on {pagopa_interaction}")
def step_create_dp_on_gpd(context, pagopa_interaction):
    """Creates a simple debt position directly on GPD/ACA (bypassing PU creation):

    - builds the entity and its transfer, generating IUV/NAV/IUPD;
    - posts it to GPD/ACA and asserts the call succeeds;
    - verifies the notice is present as `VALID` in the GPD/ACA archive.
    """
    step_get_token_org(context=context, pagopa_interaction=pagopa_interaction)
    step_create_dp_entity(context=context,
                          debt_position_type_org_code=settings.debt_position_type_org_code.feature_test)
    step_create_po_and_single_inst_entities(context=context, po_index=1, amount=100, expiration_days=3,
                                            status=Status.TO_SYNC.value)
    debt_position = context.debt_position
    installment = debt_position.payment_options[0].installments[0]

    transfer = create_transfer(token=context.token, traceparent=context.traceparent, org_info=context.org_info,
                               debt_position_type_org_code=settings.debt_position_type_org_code.feature_test,
                               remittance_information=installment.remittance_information,
                               amount_cents=installment.amount_cents)

    installment.transfers.append(transfer)
    installment.iuv = generate_iuv()
    installment.nav = NAV_PREFIX + installment.iuv
    installment.iupd_pagopa = f'{context.org_info.fiscal_code}_{unique_timestamp()}_{uuid.uuid4().hex[:5]}'
    context.debt_position.payment_options[0].installments[0] = installment

    res = post_create_debt_position_on_gpd(token=context.token, traceparent=context.traceparent,
                                           debt_position=debt_position.to_json(), iud=installment.iud)

    assert_response_ok(res, "Create debt position on GPD")

    step_verify_presence_debt_position_in_gpd_or_aca(context=context, pagopa_interaction=pagopa_interaction,
                                                     status='VALID')


@given(
    "a citizen requests a spontaneous debt position of type {debt_position_type_org_code} with single installment of {amount} euros")
def step_create_installment_entity_of_spontaneous_dp(context, debt_position_type_org_code, amount):
    debt_position_type_org = retrieve_dp_type_org_by_code(token=context.token, traceparent=context.traceparent,
                                                          organization_id=context.org_info.id,
                                                          debt_position_type_org_code=debt_position_type_org_code)
    taxonomy_code = retrieve_taxonomy_code_by_dp_type_org(token=context.token, traceparent=context.traceparent,
                                                          debt_position_type_id=debt_position_type_org[
                                                              'debtPositionTypeId'])

    iud = build_feature_test_iud(seq_num=1)
    installment = Installment(iud=iud, amount_cents=(int(amount) * 100), remittance_information='Test ' + iud,
                              debtor=Debtor(), legacy_payment_metadata=taxonomy_code)

    context.debt_position_type_org_code = debt_position_type_org_code
    context.installment = installment

    if debt_position_type_org_code == settings.debt_position_type_org_code.feature_test_bollo:
        context.stamp = Stamp()


@given("a second beneficiary '{org_name}' is added to the installment with an amount of {amount} euros")
def step_create_second_transfer_entity(context, org_name, amount):
    org, token = get_org_token_by_name(context=context, org_name=org_name)

    transfer = create_transfer(token=token, traceparent=context.traceparent, org_info=org,
                               debt_position_type_org_code=settings.debt_position_type_org_code.feature_test,
                               remittance_information="Test second beneficiary",
                               amount_cents=(int(amount) * 100))

    context.second_transfer = transfer


@then("a debt position with origin secondary_org is created for organization '{org_name}' in status paid")
def step_check_secondary_org_dp(context, org_name):
    """Checks that the debt position of secondary organization was created correctly. It:

    - checks if it exists with origin `SECONDARY_ORG`
    - validates the structure data
    - checks if it has status `PAID` and debt position type org of type `UNKNOWN`
    """
    org, token = get_org_token_by_name(context=context, org_name=org_name)
    primary_installment = context.installment
    second_transfer_req = context.second_transfer

    iuv = find_installment_by_iud(debt_position=context.debt_position, iud=primary_installment.iud).iuv

    res = get_debt_position_by_iuv(token=token, traceparent=context.traceparent, organization_id=org.get('id'),
                                   iuv=iuv, debt_position_origin=DebtPositionOrigin.SECONDARY_ORG.value)

    assert_response_ok(res, "Get debt position for secondary org")

    assert res.json() is not None, "Failed to get debt position for secondary org"

    secondary_dp = DebtPosition.from_dict(res.json()[0])

    assert secondary_dp.status == Status.PAID, \
        f"Expected secondary debt position status PAID, got {secondary_dp.status}"
    assert len(secondary_dp.payment_options) == 1, \
        f"Expected exactly 1 payment option, got {len(secondary_dp.payment_options)}"
    assert len(secondary_dp.payment_options[0].installments) == 1, \
        f"Expected exactly 1 installment, got {len(secondary_dp.payment_options[0].installments)}"
    assert (secondary_dp.payment_options[0].installments[0].amount_cents ==
            primary_installment.amount_cents + second_transfer_req.amount_cents), \
        f"Expected installment amountCents {primary_installment.amount_cents + second_transfer_req.amount_cents}, " \
        f"got {secondary_dp.payment_options[0].installments[0].amount_cents}"
    assert len(secondary_dp.payment_options[0].installments[0].transfers) == 1, \
        f"Expected exactly 1 transfer, got {len(secondary_dp.payment_options[0].installments[0].transfers)}"

    transfer_res = secondary_dp.payment_options[0].installments[0].transfers[0]
    assert transfer_res.amount_cents == second_transfer_req.amount_cents, \
        f"Expected transfer amountCents {second_transfer_req.amount_cents}, got {transfer_res.amount_cents}"
    assert transfer_res.org_fiscal_code == second_transfer_req.org_fiscal_code, \
        f"Expected transfer orgFiscalCode {second_transfer_req.org_fiscal_code}, got {transfer_res.org_fiscal_code}"
    assert transfer_res.iban == second_transfer_req.iban, \
        f"Expected transfer iban {second_transfer_req.iban}, got {transfer_res.iban}"
    # assert transfer_res.category == second_transfer_req.category #TODO check correctness of taxonomy category mapping, see P4ADEV-4530
    assert transfer_res.transfer_index == 2, \
        f"Expected transferIndex 2, got {transfer_res.transfer_index}"

    res_dpto = get_debt_position_type_org_by_id(token=context.token, traceparent=context.traceparent,
                                                debt_position_type_org_id=secondary_dp.debt_position_type_org_id)

    assert_response_ok(res_dpto, "Get debt position type org by id")
    assert res_dpto.json().get('debtPositionTypeId') == -1, \
        f"Expected debtPositionTypeId -1 (UNKNOWN), got {res_dpto.json().get('debtPositionTypeId')}"


@then('the transfer is created with stamp data instead of iban')
def step_check_transfer_data(context):
    debt_position = context.debt_position
    stamp_data = context.stamp

    transfer = debt_position.payment_options[0].installments[0].transfers[0]

    assert transfer.iban is None, f"Expected transfer iban to be None (stamp transfer), got {transfer.iban}"
    assert transfer.stamp_type == stamp_data.stamp_type, \
        f"Expected stamp_type {stamp_data.stamp_type}, got {transfer.stamp_type}"
    assert transfer.stamp_hash_document == stamp_data.stamp_hash_document, \
        f"Expected stamp_hash_document {stamp_data.stamp_hash_document}, got {transfer.stamp_hash_document}"
    assert transfer.stamp_provincial_residence == stamp_data.stamp_provincial_residence, \
        f"Expected stamp_provincial_residence {stamp_data.stamp_provincial_residence}, got {transfer.stamp_provincial_residence}"


@when("the organization adds the installment {seq_num} to payment option {po_index} with an amount of {amount} euros "
      "and due date set in {expiration_days} days")
def step_add_installment(context, seq_num, po_index, amount, expiration_days):
    installment = create_installment(expiration_days=int(expiration_days), seq_num=int(seq_num),
                                     amount_cents=int(amount) * 100)

    _put_manage_installments(context=context, debt_position_dict=_get_debt_position_dict(context),
                             po_index=int(po_index), action=Action.I,
                             installment=json.loads(installment.to_json()))
    context.requested_installments = {installment.iud: installment}


@when("the organization modifies the installment {seq_num} of payment option {po_index} with new remittance "
      "information, amount increased by {amount_increase} euros and due date postponed by {due_date_delay} days")
def step_modify_installment(context, seq_num, po_index, amount_increase, due_date_delay):
    debt_position_dict = _get_debt_position_dict(context)
    stored_installment = find_installment_by_seq_num_and_po_index(debt_position=context.debt_position,
                                                                  po_index=int(po_index), seq_num=int(seq_num))
    payment_option_dict = next(
        po for po in debt_position_dict['paymentOptions'] if po['paymentOptionIndex'] == int(po_index))

    installment = next(inst for inst in payment_option_dict['installments'] if inst['iud'] == stored_installment.iud)
    installment['remittanceInformation'] = f'Feature test installment {seq_num} updated'
    installment['amountCents'] = installment['amountCents'] + int(amount_increase) * 100
    installment['dueDate'] = (datetime.strptime(installment['dueDate'], '%Y-%m-%d')
                              + timedelta(days=int(due_date_delay))).strftime('%Y-%m-%d')

    _put_manage_installments(context=context, debt_position_dict=debt_position_dict, po_index=int(po_index),
                             action=Action.M, installment=installment)
    context.requested_installments = {installment['iud']: Installment.from_dict(installment)}


@then("the debt position update is synchronized")
def step_check_debt_position_update_synchronized(context):
    """Checks that the update is synchronized.

    It:
    - waits for a new run of the organization's sync workflow to complete
    - checks that the debt position status is `UNPAID`"""
    check_workflow_status(context=context, workflow_type=context.org_info.workflow_type,
                          entity_id=context.debt_position.debt_position_id, status=WorkflowStatus.COMPLETED,
                          previous_run_id=context.sync_run_id)
    step_check_dp_status(context=context, status=Status.UNPAID.value)
    context.debt_position = fetch_debt_position(context)


@then("the installment {seq_num} of payment option {po_index} is saved with the requested data")
@then(
    "the installment {seq_num} of payment option {po_index} of debt position {dp_identifier} is saved with the requested data")
def step_check_installment_saved(context, seq_num, po_index, dp_identifier=None):
    debt_position = _get_updated_debt_position(context, dp_identifier)
    installment = find_installment_by_seq_num_and_po_index(debt_position=debt_position, po_index=int(po_index),
                                                           seq_num=int(seq_num))

    assert installment is not None, f"Installment {seq_num} of payment option {po_index} not found"
    requested_installment = context.requested_installments[installment.iud]
    assert installment.amount_cents == requested_installment.amount_cents, \
        f"amountCents mismatch: expected {requested_installment.amount_cents}, got {installment.amount_cents}"
    assert installment.due_date == requested_installment.due_date, \
        f"dueDate mismatch: expected {requested_installment.due_date}, got {installment.due_date}"
    assert installment.remittance_information == requested_installment.remittance_information, \
        f"remittanceInformation mismatch: expected {requested_installment.remittance_information}, " \
        f"got {installment.remittance_information}"
    assert installment.status == Status.UNPAID, \
        f"status mismatch: expected {Status.UNPAID.value}, got {installment.status}"
    assert installment.iuv is not None and len(installment.iuv) == 17, f"Unexpected iuv: {installment.iuv}"
    assert installment.nav == NAV_PREFIX + installment.iuv, \
        f"nav mismatch: expected {NAV_PREFIX + installment.iuv}, got {installment.nav}"


@then("the installment {seq_num} of payment option {po_index} matches its notice on GPD")
@then("the installment {seq_num} of payment option {po_index} of debt position {dp_identifier} matches its notice "
      "on GPD")
def step_check_installment_on_gpd(context, seq_num, po_index, dp_identifier=None):
    debt_position = _get_updated_debt_position(context, dp_identifier)
    installment = find_installment_by_seq_num_and_po_index(debt_position=debt_position, po_index=int(po_index),
                                                           seq_num=int(seq_num))

    res = get_debt_position_on_aca_or_gpd(org_fiscal_code=context.org_info.fiscal_code,
                                          iupd_pagopa=installment.iupd_pagopa)
    assert_response_ok(res, "Get debt position on GPD")
    gpd_position = res.json()
    gpd_installment = gpd_position['paymentOption'][0]['installments'][0]

    assert gpd_position.get('status') == 'VALID', f"GPD status mismatch: expected VALID, got {gpd_position.get('status')}"
    assert gpd_installment.get('iuv') == installment.iuv, \
        f"GPD iuv mismatch: expected {installment.iuv}, got {gpd_installment.get('iuv')}"
    assert gpd_installment.get('amount') == installment.amount_cents, \
        f"GPD amount mismatch: expected {installment.amount_cents}, got {gpd_installment.get('amount')}"
    assert (gpd_installment.get('dueDate') or '').startswith(installment.due_date), \
        f"GPD dueDate mismatch: expected {installment.due_date}, got {gpd_installment.get('dueDate')}"
    assert gpd_installment.get('description') == installment.remittance_information, \
        f"GPD description mismatch: expected {installment.remittance_information}, got {gpd_installment.get('description')}"


def _get_debt_position_dict(context) -> dict:
    res = get_debt_position(token=context.token, traceparent=context.traceparent,
                            debt_position_id=context.debt_position.debt_position_id)
    assert_response_ok(res, "Get debt position by id")
    return res.json()


def _put_manage_installments(context, debt_position_dict: dict, po_index: int, action: Action,
                             installment: dict):
    payment_option_dict = next(
        po for po in debt_position_dict['paymentOptions'] if po['paymentOptionIndex'] == po_index)
    manage_debt_position = {
        'debtPositionDescription': debt_position_dict['description'],
        'validityDate': debt_position_dict.get('validityDate'),
        'paymentOptionId': payment_option_dict['paymentOptionId'],
        'paymentOptionDescription': payment_option_dict['description'],
        'installments': [{'action': action.value, 'installment': installment}]
    }

    context.sync_run_id = get_workflow_run_id(token=context.token, traceparent=context.traceparent,
                                              workflow_type=context.org_info.workflow_type,
                                              entity_id=context.debt_position.debt_position_id)

    res = put_manage_debt_position_installments(token=context.token, traceparent=context.traceparent,
                                                debt_position_id=context.debt_position.debt_position_id,
                                                manage_debt_position=manage_debt_position)
    assert_response_ok(res, f"Manage installments of payment option {po_index} with action {action.value}")


def _get_updated_debt_position(context, dp_identifier=None) -> DebtPosition:
    if dp_identifier is None:
        return context.debt_position
    return fetch_debt_position(context, get_stored_debt_position(context, dp_identifier).debt_position_id)
