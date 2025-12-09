import json
import uuid
from collections import defaultdict
from datetime import datetime, timedelta

import xmltodict
from behave import given, when, then

from api.debt_positions import get_debt_position_by_iud, get_debt_position_by_iuv, get_debt_position
from api.soap.sil import post_sil_invia_dovuto
from bdd.steps.authentication_step import get_token_sil
from bdd.steps.debt_positions_step import step_check_dp_status
from bdd.steps.gpd_aca_step import check_aca_or_gpd_notice_presence
from bdd.steps.utils.debt_position_utility import retrieve_taxonomy_code_by_dp_type_org, retrieve_dp_type_org_by_code
from bdd.steps.workflow_step import step_debt_position_workflow_check_expiration, check_workflow_does_not_exist
from model.debt_position import DebtPositionOrigin, PaymentOptionType, DebtPosition, Status
from model.debt_position_mixed import TransferMixed, DebtPositionMixed
from model.workflow_hub import WorkflowType


@given("a new mixed debt position configured as follows")
def step_create_dp_mixed_entity(context):
    org_id = context.org_info.id

    transfers_mixed = []
    for row in context.table:
        transfer_index = row['transfer index']
        iud = f'Mixed_{transfer_index}_{datetime.now().strftime("%Y%m%d%H%M%S%f")[:15]}_{uuid.uuid4().hex[:5]}'
        remittance_information = 'Test ' + iud
        dp_type_org_code = row['type org']

        debt_position_type_org = retrieve_dp_type_org_by_code(token=context.token, organization_id=org_id,
                                                              debt_position_type_org_code=dp_type_org_code)
        taxonomy_code = retrieve_taxonomy_code_by_dp_type_org(token=context.token,
                                                              debt_position_type_id=debt_position_type_org[
                                                                  'debtPositionTypeId'])

        transfer = TransferMixed(iud=iud,
                                 remittance_information=remittance_information,
                                 amount=row["amount"],
                                 debt_position_type_org_code=dp_type_org_code,
                                 legacy_payment_metadata=taxonomy_code,
                                 debt_position_type_org_id=debt_position_type_org['debtPositionTypeOrgId'],
                                 transfer_index=int(transfer_index))

        transfers_mixed.append(transfer)

    debt_position_mixed = DebtPositionMixed(organization_id=org_id,
                                            transfers=transfers_mixed)

    context.debt_position_mixed = debt_position_mixed


@when("SIL creates the mixed debt position")
def step_sil_invia_dovuto_mixed(context):
    res = post_sil_invia_dovuto(token=context.token,
                                debt_position_mixed=context.debt_position_mixed,
                                ipa_code=context.org_info.ipa_code)

    res_parsed = xmltodict.parse(res.content.decode('utf-8'))
    assert res.status_code == 200
    res_body = res_parsed['SOAP-ENV:Envelope']['SOAP-ENV:Body']['ns3:paaSILInviaDovutiRisposta']
    assert res_body['esito'] == 'OK'
    assert res_body['url'] is not None


@then("3 debt positions having installments with same IUV are in status {status} configured as follows")
def step_check_debt_positions_mixed_created(context, status):
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
            res_dp_by_iud = get_debt_position_by_iud(token=token, organization_id=org_info.id,
                                                     iud=transfer_mixed.iud,
                                                     debt_position_origin=dp_origin)
            assert res_dp_by_iud.status_code == 200
            assert len(res_dp_by_iud.json()) == 1
            res_dp = res_dp_by_iud.json()[0]

            iuv = _validate_dp_spontaneous_mixed_and_retrieve_iuv(res_dp, transfer_mixed, dp_mixed, org_info,
                                                                  row, transfers_index, transfer_index_map, status)

        elif dp_origin == DebtPositionOrigin.SPONTANEOUS_SIL.value:
            res_dp_by_iuv = get_debt_position_by_iuv(token=token, organization_id=org_info.id,
                                                     iuv=iuv,
                                                     debt_position_origin=dp_origin)
            assert res_dp_by_iuv.status_code == 200
            assert len(res_dp_by_iuv.json()) == 1
            res_dp = res_dp_by_iuv.json()[0]

            debt_position_type_org = retrieve_dp_type_org_by_code(token=context.token, organization_id=org_info.id,
                                                                  debt_position_type_org_code=row['type org'])

            _validate_dp_spontaneous_sil(res_dp, debt_position_type_org['debtPositionTypeOrgId'], dp_mixed, org_info,
                                         row, transfers_index, transfer_index_map, status)

            context.debt_position = DebtPosition.from_dict(res_dp)


@given(
    "a mixed debt position created by SIL for organization interacting with {pagopa_interaction} configured as follows")
def step_sil_create_mixed_dp(context, pagopa_interaction):
    get_token_sil(context=context, pagopa_interaction=pagopa_interaction)
    token = context.token
    org_id = context.org_info.id
    step_create_dp_mixed_entity(context=context)
    step_sil_invia_dovuto_mixed(context=context)

    iuv = _extract_iuv_from_dp_found_by_iud(token=token, org_id=org_id,
                                            iud=context.debt_position_mixed.transfers[0].iud)

    res_dp_by_iuv = get_debt_position_by_iuv(token=token, organization_id=org_id, iuv=iuv)
    assert res_dp_by_iuv.status_code == 200
    res_dp_list = res_dp_by_iuv.json()

    _quick_validate_all_dp(context=context, res_dp_list=res_dp_list, org_id=org_id)

    check_aca_or_gpd_notice_presence(context=context, pagopa_interaction=pagopa_interaction)


@then("the mixed debt position and technical ones are in status {status}")
def step_check_mixed_and_tech_dp_status(context, status):
    step_check_dp_status(context=context, status=status)

    res_dp_by_iuv = get_debt_position_by_iuv(token=context.token, organization_id=context.org_info.id,
                                             iuv=context.iuv_mixed, debt_position_origin=DebtPositionOrigin.SPONTANEOUS_MIXED.value)
    assert res_dp_by_iuv.status_code == 200
    for dp_sp_mixed in res_dp_by_iuv.json():
        step_check_dp_status(context=context, status=status, debt_position_id=dp_sp_mixed['debtPositionId'])


def _quick_validate_all_dp(context, res_dp_list, org_id):
    dp_mixed_request = context.debt_position_mixed

    amount_by_type_org_id = defaultdict(int)
    for transfer in dp_mixed_request.transfers:
        dp_type_org_id = transfer.debt_position_type_org_id
        amount_by_type_org_id[dp_type_org_id] += int(float(transfer.amount) * 100)

    assert len(res_dp_list) == len(amount_by_type_org_id) + 1
    for dp in res_dp_list:
        assert dp['status'] == Status.UNPAID.value
        if dp['debtPositionOrigin'] == DebtPositionOrigin.SPONTANEOUS_MIXED.value:
            assert dp['paymentOptions'][0]['totalAmountCents'] == amount_by_type_org_id[dp['debtPositionTypeOrgId']]
            check_workflow_does_not_exist(context=context, workflow_type=WorkflowType.EXPIRATION_DP,
                                          entity_id=dp['debtPositionId'])
        else:
            assert dp['debtPositionOrigin'] == DebtPositionOrigin.SPONTANEOUS_SIL.value
            debt_position_type_org_id = retrieve_dp_type_org_by_code(token=context.token, organization_id=org_id,
                                                                     debt_position_type_org_code='MIXED')[
                'debtPositionTypeOrgId']
            assert dp['debtPositionTypeOrgId'] == debt_position_type_org_id
            assert dp['paymentOptions'][0]['totalAmountCents'] == sum(amount_by_type_org_id.values())

            context.iuv_mixed = dp['paymentOptions'][0]['installments'][0]['iuv']
            context.debt_position = DebtPosition.from_dict(dp)

            step_debt_position_workflow_check_expiration(context=context, status="scheduled")


def _extract_iuv_from_dp_found_by_iud(token, org_id, iud):
    res_dp_by_iud = get_debt_position_by_iud(token=token, organization_id=org_id, iud=iud,
                                             debt_position_origin=DebtPositionOrigin.SPONTANEOUS_MIXED.value)
    assert res_dp_by_iud.status_code == 200
    assert res_dp_by_iud.json() != []

    return res_dp_by_iud.json()[0]['paymentOptions'][0]['installments'][0]['iuv']


def _validate_dp_spontaneous_mixed_and_retrieve_iuv(res_dp, transfer_mixed, dp_mixed, org_info, row,
                                                    transfers_index, transfer_index_map, status):
    assert res_dp['status'] == status.upper()
    assert res_dp['debtPositionTypeOrgId'] == transfer_mixed.debt_position_type_org_id
    assert len(res_dp['paymentOptions']) == 1
    assert res_dp['paymentOptions'][0]['totalAmountCents'] == int(float(row['total amount']) * 100)
    assert res_dp['paymentOptions'][0]['status'] == status.upper()
    if int(row['total installments']) > 1:
        assert res_dp['paymentOptions'][0]['paymentOptionType'] == PaymentOptionType.INSTALLMENTS.value
    else:
        assert res_dp['paymentOptions'][0]['paymentOptionType'] == PaymentOptionType.SINGLE_INSTALLMENT.value
    assert len(res_dp['paymentOptions'][0]['installments']) == int(row['total installments'])

    res_installments = res_dp['paymentOptions'][0]['installments']
    res_inst_map = {installment['iud']: installment for installment in res_installments}
    for transfer_index in transfers_index:
        transfer_mixed = transfer_index_map[int(transfer_index)]
        res_installment = res_inst_map[transfer_mixed.iud]
        assert res_installment['status'] == status.upper()
        assert res_installment['amountCents'] == int(float(transfer_mixed.amount) * 100)
        assert res_installment['dueDate'] == (datetime.now() + timedelta(minutes=120)).strftime("%Y-%m-%d")
        assert res_installment['remittanceInformation'] == transfer_mixed.remittance_information
        assert res_installment['legacyPaymentMetadata'] == transfer_mixed.legacy_payment_metadata
        assert res_installment['debtor'] == json.loads(dp_mixed.debtor.to_json())
        assert len(res_installment['transfers']) == 1
        first_transfer = res_installment['transfers'][0]
        assert first_transfer['transferIndex'] == int(transfer_index)
        assert first_transfer['orgFiscalCode'] == org_info.fiscal_code
        assert first_transfer['orgName'] == org_info.name
        assert first_transfer['iban'] == org_info.iban
        assert (first_transfer['category'] == str(transfer_mixed.legacy_payment_metadata).replace('9/', '')
                .replace('/', ''))
        assert first_transfer['remittanceInformation'] == transfer_mixed.remittance_information
        assert first_transfer['amountCents'] == int(float(transfer_mixed.amount) * 100)

    return res_installments[0]['iuv']


def _validate_dp_spontaneous_sil(res_dp, debt_position_type_org_id, dp_mixed, org_info, row, transfers_index,
                                 transfer_index_map, status):
    assert res_dp['status'] == status.upper()
    assert res_dp['description'] == 'MIXED'
    assert res_dp['debtPositionTypeOrgId'] == debt_position_type_org_id
    assert len(res_dp['paymentOptions']) == 1
    assert res_dp['paymentOptions'][0]['totalAmountCents'] == int(float(row['total amount']) * 100)
    assert res_dp['paymentOptions'][0]['status'] == status.upper()
    assert res_dp['paymentOptions'][0]['paymentOptionType'] == PaymentOptionType.SINGLE_INSTALLMENT.value
    assert len(res_dp['paymentOptions'][0]['installments']) == int(row['total installments']) == 1

    res_installment = res_dp['paymentOptions'][0]['installments'][0]
    assert res_installment['iud'] is not None
    assert res_installment['status'] == status.upper()
    assert res_installment['amountCents'] == int(float(row['total amount']) * 100)
    assert res_installment['dueDate'] == (datetime.now() + timedelta(minutes=120)).strftime("%Y-%m-%d")
    assert res_installment['remittanceInformation'] == 'Causali multiple'
    assert res_installment['debtor'] == json.loads(dp_mixed.debtor.to_json())

    assert len(res_installment['transfers']) == len(transfers_index)
    res_transfers_map = {transfer['transferIndex']: transfer for transfer in res_installment['transfers']}
    for transfer_index in transfers_index:
        transfer_mixed = transfer_index_map[int(transfer_index)]
        res_transfer = res_transfers_map[int(transfer_index)]
        assert res_transfer['transferIndex'] == int(transfer_index)
        assert res_transfer['orgFiscalCode'] == org_info.fiscal_code
        assert res_transfer['orgName'] == org_info.name
        assert res_transfer['iban'] == org_info.iban
        assert (res_transfer['category'] == str(transfer_mixed.legacy_payment_metadata).replace('9/', '')
                .replace('/', ''))
        assert res_transfer['remittanceInformation'] == transfer_mixed.remittance_information
        assert res_transfer['amountCents'] == int(float(transfer_mixed.amount) * 100)
