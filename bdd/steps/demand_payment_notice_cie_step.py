import sys

import xmltodict
from behave import given, when

from api.arpu import get_debt_position_type_orgs_for_spontaneous
from api.broker import get_broker_by_broker_id
from api.cie import get_cie_organizations, get_cie_amount
from api.debt_positions import \
  get_debt_position_by_organization_id_and_installment_nav
from api.soap.payments import post_demand_payment_notice
from bdd.steps.debt_position_cie_step import get_cie_org_fiscal_code
from config.configuration import secrets, settings
from model.debt_position import DebtPositionOrigin, DebtPosition
from model.debt_position_cie import get_debt_position_type_org_code_by_reason
from model.demand_payment_notice_cie import DemandPaymentNotice, RequestData


@given("The payment node requests the CIE to the organization {organization_name} due to '{reason_of_request}' for a citizen")
def step_demand_payment_notice_cie_entity(context, organization_name: str, reason_of_request: str):
    res_cie_organizations = get_cie_organizations()

    assert res_cie_organizations.status_code == 200
    assert len(res_cie_organizations.json()['result']) > 0

    cie_org_fiscal_code = get_cie_org_fiscal_code(res_cie_organizations.json()['result'], organization_name)
    context.cie_org_fiscal_code = cie_org_fiscal_code

    dp_type_org_code = get_debt_position_type_org_code_by_reason(reason_of_request)

    res_dp_type_orgs = get_debt_position_type_orgs_for_spontaneous(broker_id=context.broker_id,
                                                                   organization_id=context.organization_id)

    assert res_dp_type_orgs.status_code == 200
    assert len(res_dp_type_orgs.json()) > 0

    dp_type_org = next(
        (dp_type_org for dp_type_org in res_dp_type_orgs.json() if dp_type_org["code"] == dp_type_org_code), None)
    assert dp_type_org is not None
    context.debt_position_type_org_id = dp_type_org["debtPositionTypeOrgId"]

    res_broker = get_broker_by_broker_id(token=context.token, broker_id = context.broker_id)
    assert res_broker.status_code == 200
    station_id = res_broker.json()['stationId']


    demand_payment_notice_request = DemandPaymentNotice(delegate_org_fiscal_code=context.organization_fiscal_code,
                                                        broker_fiscal_code=context.broker_fiscal_code,
                                                        service_id=settings.demand_payment_notice.service_id,
                                                        station_id=station_id,
                                                        service_subject_id=secrets.demand_payment_notice_info.cie.service_subject_id,
                                                        request_data=RequestData(debt_position_type_org_code=dp_type_org_code,
                                                                                 cie_org_fiscal_code=cie_org_fiscal_code,
                                                                                 debtor_fiscal_code=secrets.citizen_info.X.fiscal_code,
                                                                                 debtor_full_name=secrets.citizen_info.X.name))

    res_cie_amount = get_cie_amount(org_fiscal_code=demand_payment_notice_request.request_data.cie_org_fiscal_code, debt_position_type_org_code=demand_payment_notice_request.request_data.debt_position_type_org_code)
    assert res_cie_amount.status_code == 200
    assert res_cie_amount.json()['result'] is not None

    cie_amount_cents = res_cie_amount.json()['result']
    context.total_amount_cents = cie_amount_cents
    context.debt_position_type_org_code = dp_type_org_code
    context.debt_position_origin = DebtPositionOrigin.SPONTANEOUS_PSP.value
    context.demand_payment_notice_request = demand_payment_notice_request


@when("the payment node confirms the request for creation of the spontaneous")
def step_create_cie_spontaneous_debt_position_with_demand_payment_notice(context):
    res = post_demand_payment_notice(token=context.token, demand_payment_notice=context.demand_payment_notice_request)
    print(res)
    res_parsed = xmltodict.parse(res.content.decode('utf-8'))
    assert res.status_code == 200
    res_body = res_parsed['SOAP-ENV:Envelope']['SOAP-ENV:Body']['ns3:paDemandPaymentNoticeResponse']
    assert res_body['outcome'] == 'OK'
    assert res_body['qrCode'] is not None
    assert res_body['qrCode']['noticeNumber'] is not None
    nav = res_body['qrCode']['noticeNumber']

    res = get_debt_position_by_organization_id_and_installment_nav(token=context.token,organization_id=context.organization_id,nav=nav)
    assert res.status_code == 200
    assert len(res.json()) == 1

    res_debt_position = res.json()[0]
    context.debt_position_id = res_debt_position['debtPositionId']
    context.debt_position = DebtPosition.from_dict(res_debt_position)
