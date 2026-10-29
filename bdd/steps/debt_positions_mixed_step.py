import json
import re
import uuid
from collections import defaultdict
from datetime import datetime, timedelta

from behave import given, when, then

from api.debt_positions import get_debt_position_by_iud, get_debt_position_by_iuv
from api.soap.sil import post_sil_invia_dovuto_eterogeneo, checkout_url_pattern
from bdd.steps.authentication_step import step_get_token_sil
from bdd.steps.debt_positions_step import step_check_dp_status
from bdd.steps.gpd_aca_step import step_verify_presence_debt_position_in_gpd_or_aca
from bdd.steps.utils.assertions import assert_response_ok
from bdd.steps.utils.date_utils import unique_timestamp
from bdd.steps.utils.debt_position_utils import retrieve_taxonomy_code_by_dp_type_org, retrieve_dp_type_org_by_code
from bdd.steps.utils.soap_utils import extract_soap_body
from bdd.steps.workflow_step import step_debt_position_workflow_check_expiration, check_workflow_does_not_exist
from model.debt_position import DebtPositionOrigin, PaymentOptionType, DebtPosition, Status
from model.debt_position_mixed import TransferMixed, DebtPositionMixed, MIXED_REMITTANCE
from model.workflow_hub import WorkflowType


@given("a new mixed debt position configured as follows")
def step_create_dp_mixed_entity(context):
    org_id = context.org_info.id

    transfers_mixed = []
    for row in context.table:
        transfer_index = row['transfer index']
        iud = f'Mixed_{transfer_index}_{unique_timestamp()}_{uuid.uuid4().hex[:5]}'
        remittance_information = 'Test ' + iud
        dp_type_org_code = row['type org']

        debt_position_type_org = retrieve_dp_type_org_by_code(token=context.token, traceparent=context.traceparent,
                                                              organization_id=org_id,
                                                              debt_position_type_org_code=dp_type_org_code)
        taxonomy_code = retrieve_taxonomy_code_by_dp_type_org(token=context.token, traceparent=context.traceparent,
                                                              debt_position_type_id=debt_position_type_org[
                                                                  'debtPositionTypeId'])

        transfer = TransferMixed(iud=iud,
                                 remittance_information=remittance_information,
                                 amount_cents=int(float(row["amount"]) * 100),
                                 debt_position_type_org_code=dp_type_org_code,
                                 legacy_payment_metadata=taxonomy_code,
                                 debt_position_type_org_id=debt_position_type_org['debtPositionTypeOrgId'],
                                 transfer_index=int(transfer_index))

        transfers_mixed.append(transfer)

    debt_position_mixed = DebtPositionMixed(organization_id=org_id,
                                            transfers=transfers_mixed)

    context.debt_position_mixed = debt_position_mixed


@when("SIL creates the mixed debt position via the 'InviaDovuti'")
def step_sil_invia_dovuto_mixed(context):
    """Creates the mixed debt position through SIL (`paaSILInviaDovuti`) and asserts the SOAP outcome is `OK` with a URL to proceed for payment."""
    res = post_sil_invia_dovuto_eterogeneo(token=context.token,
                                           traceparent=context.traceparent,
                                           debt_position_mixed=context.debt_position_mixed,
                                           ipa_code=context.org_info.ipa_code)

    assert_response_ok(res, "SIL invia dovuto")
    res_body = extract_soap_body(res.content, 'paaSILInviaDovutiRisposta')
    assert res_body.get('esito') == 'OK', f"Expected 'paaSILInviaDovuti' esito OK, got {res_body.get('esito')}"

    expected_pattern = checkout_url_pattern(context.org_info.fiscal_code)
    assert re.match(expected_pattern, res_body.get('url') or ''), (
        f"Checkout URL does not match with expected: {res_body.get('url')}"
    )


@then("3 debt positions having installments with same IUV are in status {status} configured as follows")
def step_check_debt_positions_mixed_created(context, status):
    """Checks the debt positions generated from a mixed SIL flow (sharing the same IUV). For each configured row it:

    - looks up the `SPONTANEOUS_MIXED` or `SPONTANEOUS_SIL` debt position and asserts they exist as configured;
    - validates their status, amounts, payment option and installments/transfers against the request.
    """
    token = context.token
    org_info = context.org_info
    dp_mixed = context.debt_position_mixed

    transfer_index_map = {transfer.transfer_index: transfer for transfer in dp_mixed.transfers}
    iuv = ''

    for row in context.table:
        dp_origin = row['origin']
        transfers_index = row['transfers index'].split()
        if dp_origin == DebtPositionOrigin.SPONTANEOUS_MIXED.value:
            transfer_mixed = transfer_index_map[int(transfers_index[0])]
            res_dp_by_iud = get_debt_position_by_iud(token=token, traceparent=context.traceparent,
                                                     organization_id=org_info.id,
                                                     iud=transfer_mixed.iud,
                                                     debt_position_origin=dp_origin)
            assert_response_ok(res_dp_by_iud, "Get debt position by IUD")
            assert len(res_dp_by_iud.json()) == 1, \
                f"Expected exactly 1 debt position for IUD {transfer_mixed.iud}, got {len(res_dp_by_iud.json())}"
            res_dp = res_dp_by_iud.json()[0]

            iuv = _validate_dp_spontaneous_mixed_and_retrieve_iuv(res_dp, transfer_mixed, dp_mixed, org_info,
                                                                  row, transfers_index, transfer_index_map, status)

        elif dp_origin == DebtPositionOrigin.SPONTANEOUS_SIL.value:
            res_dp_by_iuv = get_debt_position_by_iuv(token=token, traceparent=context.traceparent,
                                                     organization_id=org_info.id,
                                                     iuv=iuv,
                                                     debt_position_origin=dp_origin)
            assert_response_ok(res_dp_by_iuv, "Get debt position by IUV")
            assert len(res_dp_by_iuv.json()) == 1, \
                f"Expected exactly 1 debt position for IUV {iuv}, got {len(res_dp_by_iuv.json())}"
            res_dp = res_dp_by_iuv.json()[0]

            debt_position_type_org = retrieve_dp_type_org_by_code(token=context.token, traceparent=context.traceparent,
                                                                  organization_id=org_info.id,
                                                                  debt_position_type_org_code=row['type org'])

            _validate_dp_spontaneous_sil(res_dp, debt_position_type_org['debtPositionTypeOrgId'], dp_mixed, org_info,
                                         row, transfers_index, transfer_index_map, status)

            context.debt_position = DebtPosition.from_dict(res_dp)


@given(
    "a mixed debt position created by SIL for organization interacting with {pagopa_interaction} configured as follows")
def step_sil_create_mixed_dp(context, pagopa_interaction):
    """Creates a mixed debt position via SIL in one step. It:

    - gets the SIL token and builds the mixed entity;
    - sends it through SIL and retrieves the resulting debt positions by IUV;
    - validates all data of generated debt positions (status, amounts, expiration workflow, ecc);
    - verifies presence as `valid` in the GPD/ACA archive.
    """
    step_get_token_sil(context=context, pagopa_interaction=pagopa_interaction)
    token = context.token
    org_id = context.org_info.id
    step_create_dp_mixed_entity(context=context)
    step_sil_invia_dovuto_mixed(context=context)

    iuv = _extract_iuv_from_dp_found_by_iud(token=token, traceparent=context.traceparent, org_id=org_id,
                                            iud=context.debt_position_mixed.transfers[0].iud)

    res_dp_by_iuv = get_debt_position_by_iuv(token=token, traceparent=context.traceparent, organization_id=org_id,
                                             iuv=iuv)
    assert_response_ok(res_dp_by_iuv, "Get debt position by IUV")
    res_dp_list = res_dp_by_iuv.json()

    _quick_validate_all_dp(context=context, res_dp_list=res_dp_list, org_id=org_id)

    step_verify_presence_debt_position_in_gpd_or_aca(context=context, pagopa_interaction=pagopa_interaction,
                                                     status='valid')


@then("the mixed debt position and technical ones are in status {status}")
def step_check_mixed_and_tech_dp_status(context, status):
    """Checks that the mixed debt position and its technical (`SPONTANEOUS_MIXED`) ones are all in the expected status."""
    step_check_dp_status(context=context, status=status)

    res_dp_by_iuv = get_debt_position_by_iuv(token=context.token, traceparent=context.traceparent,
                                             organization_id=context.org_info.id,
                                             iuv=context.iuv_mixed,
                                             debt_position_origin=DebtPositionOrigin.SPONTANEOUS_MIXED.value)
    assert_response_ok(res_dp_by_iuv, "Get debt position by IUV")
    for dp_sp_mixed in res_dp_by_iuv.json():
        step_check_dp_status(context=context, status=status, debt_position_id=dp_sp_mixed['debtPositionId'])


def _quick_validate_all_dp(context, res_dp_list, org_id):
    dp_mixed_request = context.debt_position_mixed

    amount_by_type_org_id = defaultdict(int)
    for transfer in dp_mixed_request.transfers:
        dp_type_org_id = transfer.debt_position_type_org_id
        amount_by_type_org_id[dp_type_org_id] += transfer.amount_cents

    assert len(res_dp_list) == len(amount_by_type_org_id) + 1, \
        f"Expected {len(amount_by_type_org_id) + 1} debt positions, got {len(res_dp_list)}"
    for dp in res_dp_list:
        assert dp.get('status') == Status.UNPAID.value, \
            f"Expected debt position {dp.get('debtPositionId')} status UNPAID, got {dp.get('status')}"
        if dp.get('debtPositionOrigin') == DebtPositionOrigin.SPONTANEOUS_MIXED.value:
            assert dp['paymentOptions'][0].get('totalAmountCents') == amount_by_type_org_id[dp.get('debtPositionTypeOrgId')], \
                f"Expected totalAmountCents {amount_by_type_org_id[dp.get('debtPositionTypeOrgId')]} " \
                f"for type org {dp.get('debtPositionTypeOrgId')}, got {dp['paymentOptions'][0].get('totalAmountCents')}"
            check_workflow_does_not_exist(context=context, workflow_type=WorkflowType.EXPIRATION_DP,
                                          entity_id=dp['debtPositionId'])
        else:
            assert dp.get('debtPositionOrigin') == DebtPositionOrigin.SPONTANEOUS_SIL.value, \
                f"Expected debtPositionOrigin SPONTANEOUS_SIL, got {dp.get('debtPositionOrigin')}"
            debt_position_type_org_id = \
            retrieve_dp_type_org_by_code(token=context.token, traceparent=context.traceparent,
                                         organization_id=org_id, debt_position_type_org_code='MIXED')[
                'debtPositionTypeOrgId']
            assert dp.get('debtPositionTypeOrgId') == debt_position_type_org_id, \
                f"Expected debtPositionTypeOrgId {debt_position_type_org_id}, got {dp.get('debtPositionTypeOrgId')}"
            assert dp['paymentOptions'][0].get('totalAmountCents') == sum(amount_by_type_org_id.values()), \
                f"Expected totalAmountCents {sum(amount_by_type_org_id.values())}, " \
                f"got {dp['paymentOptions'][0].get('totalAmountCents')}"

            context.iuv_mixed = dp['paymentOptions'][0]['installments'][0]['iuv']
            context.debt_position = DebtPosition.from_dict(dp)

            step_debt_position_workflow_check_expiration(context=context, status="scheduled")


def _extract_iuv_from_dp_found_by_iud(token, traceparent, org_id, iud):
    res_dp_by_iud = get_debt_position_by_iud(token=token, traceparent=traceparent, organization_id=org_id, iud=iud,
                                             debt_position_origin=DebtPositionOrigin.SPONTANEOUS_MIXED.value)
    assert_response_ok(res_dp_by_iud, "Get debt position by IUD")
    assert res_dp_by_iud.json() != [], f"No SPONTANEOUS_MIXED debt position found for IUD {iud}"

    return res_dp_by_iud.json()[0]['paymentOptions'][0]['installments'][0]['iuv']


def _validate_dp_spontaneous_mixed_and_retrieve_iuv(res_dp, transfer_mixed, dp_mixed, org_info, row,
                                                    transfers_index, transfer_index_map, status):
    assert res_dp.get('status') == status.upper(), \
        f"Expected debt position status {status.upper()}, got {res_dp.get('status')}"
    assert res_dp.get('debtPositionTypeOrgId') == transfer_mixed.debt_position_type_org_id, \
        f"Expected debtPositionTypeOrgId {transfer_mixed.debt_position_type_org_id}, got {res_dp.get('debtPositionTypeOrgId')}"
    assert len(res_dp.get('paymentOptions') or []) == 1, \
        f"Expected exactly 1 payment option, got {len(res_dp.get('paymentOptions') or [])}"
    assert res_dp['paymentOptions'][0].get('totalAmountCents') == int(float(row['total amount']) * 100), \
        f"Expected totalAmountCents {int(float(row['total amount']) * 100)}, got {res_dp['paymentOptions'][0].get('totalAmountCents')}"
    assert res_dp['paymentOptions'][0].get('status') == status.upper(), \
        f"Expected payment option status {status.upper()}, got {res_dp['paymentOptions'][0].get('status')}"
    if int(row['total installments']) > 1:
        assert res_dp['paymentOptions'][0].get('paymentOptionType') == PaymentOptionType.INSTALLMENTS.value, \
            f"Expected paymentOptionType INSTALLMENTS, got {res_dp['paymentOptions'][0].get('paymentOptionType')}"
    else:
        assert res_dp['paymentOptions'][0].get('paymentOptionType') == PaymentOptionType.SINGLE_INSTALLMENT.value, \
            f"Expected paymentOptionType SINGLE_INSTALLMENT, got {res_dp['paymentOptions'][0].get('paymentOptionType')}"
    assert len(res_dp['paymentOptions'][0].get('installments') or []) == int(row['total installments']), \
        f"Expected {int(row['total installments'])} installments, got {len(res_dp['paymentOptions'][0].get('installments') or [])}"

    res_installments = res_dp['paymentOptions'][0]['installments']
    res_inst_map = {installment['iud']: installment for installment in res_installments}
    for transfer_index in transfers_index:
        transfer_mixed = transfer_index_map[int(transfer_index)]
        res_installment = res_inst_map[transfer_mixed.iud]
        assert res_installment.get('status') == status.upper(), \
            f"Expected installment {transfer_mixed.iud} status {status.upper()}, got {res_installment.get('status')}"
        assert res_installment.get('amountCents') == transfer_mixed.amount_cents, \
            f"Expected installment amountCents {transfer_mixed.amount_cents}, got {res_installment.get('amountCents')}"
        assert res_installment.get('dueDate') == (datetime.now() + timedelta(minutes=120)).strftime("%Y-%m-%d"), \
            f"Expected dueDate {(datetime.now() + timedelta(minutes=120)).strftime('%Y-%m-%d')}, got {res_installment.get('dueDate')}"
        assert res_installment.get('remittanceInformation') == transfer_mixed.remittance_information, \
            f"Expected remittanceInformation {transfer_mixed.remittance_information}, got {res_installment.get('remittanceInformation')}"
        assert res_installment.get('legacyPaymentMetadata') == transfer_mixed.legacy_payment_metadata, \
            f"Expected legacyPaymentMetadata {transfer_mixed.legacy_payment_metadata}, got {res_installment.get('legacyPaymentMetadata')}"
        assert res_installment.get('debtor') == json.loads(dp_mixed.debtor.to_json()), \
            f"Installment debtor does not match: got {res_installment.get('debtor')}"
        assert len(res_installment.get('transfers') or []) == 1, \
            f"Expected exactly 1 transfer for installment {transfer_mixed.iud}, got {len(res_installment.get('transfers') or [])}"
        first_transfer = res_installment['transfers'][0]
        assert first_transfer.get('transferIndex') == int(transfer_index), \
            f"Expected transferIndex {int(transfer_index)}, got {first_transfer.get('transferIndex')}"
        assert first_transfer.get('orgFiscalCode') == org_info.fiscal_code, \
            f"Expected orgFiscalCode {org_info.fiscal_code}, got {first_transfer.get('orgFiscalCode')}"
        assert first_transfer.get('orgName') == org_info.name, \
            f"Expected orgName {org_info.name}, got {first_transfer.get('orgName')}"
        assert first_transfer.get('iban') == org_info.iban, \
            f"Expected iban {org_info.iban}, got {first_transfer.get('iban')}"
        assert first_transfer.get('category') == str(transfer_mixed.legacy_payment_metadata), \
            f"Expected category {str(transfer_mixed.legacy_payment_metadata)}, got {first_transfer.get('category')}"
        assert first_transfer.get('remittanceInformation') == transfer_mixed.remittance_information, \
            f"Expected transfer remittanceInformation {transfer_mixed.remittance_information}, got {first_transfer.get('remittanceInformation')}"
        assert first_transfer.get('amountCents') == transfer_mixed.amount_cents, \
            f"Expected transfer amountCents {transfer_mixed.amount_cents}, got {first_transfer.get('amountCents')}"

    return res_installments[0]['iuv']


def _validate_dp_spontaneous_sil(res_dp, debt_position_type_org_id, dp_mixed, org_info, row, transfers_index,
                                 transfer_index_map, status):
    assert res_dp.get('status') == status.upper(), \
        f"Expected debt position status {status.upper()}, got {res_dp.get('status')}"
    assert res_dp.get('description') == 'MIXED', f"Expected description MIXED, got {res_dp.get('description')}"
    assert res_dp.get('debtPositionTypeOrgId') == debt_position_type_org_id, \
        f"Expected debtPositionTypeOrgId {debt_position_type_org_id}, got {res_dp.get('debtPositionTypeOrgId')}"
    assert len(res_dp.get('paymentOptions') or []) == 1, \
        f"Expected exactly 1 payment option, got {len(res_dp.get('paymentOptions') or [])}"
    assert res_dp['paymentOptions'][0].get('totalAmountCents') == int(float(row['total amount']) * 100), \
        f"Expected totalAmountCents {int(float(row['total amount']) * 100)}, got {res_dp['paymentOptions'][0].get('totalAmountCents')}"
    assert res_dp['paymentOptions'][0].get('status') == status.upper(), \
        f"Expected payment option status {status.upper()}, got {res_dp['paymentOptions'][0].get('status')}"
    assert res_dp['paymentOptions'][0].get('paymentOptionType') == PaymentOptionType.SINGLE_INSTALLMENT.value, \
        f"Expected paymentOptionType SINGLE_INSTALLMENT, got {res_dp['paymentOptions'][0].get('paymentOptionType')}"
    assert len(res_dp['paymentOptions'][0].get('installments') or []) == int(row['total installments']) == 1, \
        f"Expected exactly 1 installment, got {len(res_dp['paymentOptions'][0].get('installments') or [])}"

    res_installment = res_dp['paymentOptions'][0]['installments'][0]
    assert res_installment.get('iud') is not None, "Installment has no iud"
    assert res_installment.get('status') == status.upper(), \
        f"Expected installment status {status.upper()}, got {res_installment.get('status')}"
    assert res_installment.get('amountCents') == int(float(row['total amount']) * 100), \
        f"Expected installment amountCents {int(float(row['total amount']) * 100)}, got {res_installment.get('amountCents')}"
    assert res_installment.get('dueDate') == (datetime.now() + timedelta(minutes=120)).strftime("%Y-%m-%d"), \
        f"Expected dueDate {(datetime.now() + timedelta(minutes=120)).strftime('%Y-%m-%d')}, got {res_installment.get('dueDate')}"
    assert res_installment.get('remittanceInformation') == MIXED_REMITTANCE, \
        f"Expected remittanceInformation {MIXED_REMITTANCE}, got {res_installment.get('remittanceInformation')}"
    assert res_installment.get('debtor') == json.loads(dp_mixed.debtor.to_json()), \
        f"Installment debtor does not match: got {res_installment.get('debtor')}"

    assert len(res_installment.get('transfers') or []) == len(transfers_index), \
        f"Expected {len(transfers_index)} transfers, got {len(res_installment.get('transfers') or [])}"
    res_transfers_map = {transfer['transferIndex']: transfer for transfer in res_installment['transfers']}
    for transfer_index in transfers_index:
        transfer_mixed = transfer_index_map[int(transfer_index)]
        res_transfer = res_transfers_map[int(transfer_index)]
        assert res_transfer.get('transferIndex') == int(transfer_index), \
            f"Expected transferIndex {int(transfer_index)}, got {res_transfer.get('transferIndex')}"
        assert res_transfer.get('orgFiscalCode') == org_info.fiscal_code, \
            f"Expected orgFiscalCode {org_info.fiscal_code}, got {res_transfer.get('orgFiscalCode')}"
        assert res_transfer.get('orgName') == org_info.name, \
            f"Expected orgName {org_info.name}, got {res_transfer.get('orgName')}"
        assert res_transfer.get('iban') == org_info.iban, \
            f"Expected iban {org_info.iban}, got {res_transfer.get('iban')}"
        assert res_transfer.get('category') == str(transfer_mixed.legacy_payment_metadata), \
            f"Expected category {str(transfer_mixed.legacy_payment_metadata)}, got {res_transfer.get('category')}"
        assert res_transfer.get('remittanceInformation') == transfer_mixed.remittance_information, \
            f"Expected transfer remittanceInformation {transfer_mixed.remittance_information}, got {res_transfer.get('remittanceInformation')}"
        assert res_transfer.get('amountCents') == transfer_mixed.amount_cents, \
            f"Expected transfer amountCents {transfer_mixed.amount_cents}, got {res_transfer.get('amountCents')}"
