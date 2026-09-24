import base64
import re

import xmltodict
from behave import when, then

from api.debt_positions import get_debt_position_by_iud
from api.fileshare import get_ingestion_flow_file
from api.soap.sil import post_sil_invia_carrello_dovuti, post_sil_chiedi_esito_carrello_dovuti, checkout_url_pattern, \
    post_sil_invia_carrello_dovuti_enti_secondari
from bdd.steps.utils.assertions import assert_response_ok
from bdd.steps.utils.utility import xml_elements_equal
from model.debt_position import DebtPosition, DebtPositionOrigin


def _process_invia_carrello_response(context, res, org_info, installment):
    """Shared logic for parsing an InviaCarrello SOAP response, asserting the
    outcome/checkout URL, and fetching the resulting debt position."""

    res_parsed = xmltodict.parse(res.content.decode('utf-8'))
    assert_response_ok(res, "SIL invia carrello dovuti")
    res_body = res_parsed['SOAP-ENV:Envelope']['SOAP-ENV:Body']['ns3:paaSILInviaCarrelloDovutiRisposta']
    assert res_body['esito'] == 'OK'
    assert res_body['idSessionCarrello'] is not None

    expected_pattern = checkout_url_pattern(org_info.fiscal_code)
    assert re.match(expected_pattern, res_body['url']), (
        f"Checkout URL does not match with expected: {res_body['url']}"
    )

    installment.installment_id = res_body['idSessionCarrello']

    debt_position_res = get_debt_position_by_iud(
        token=context.token,
        traceparent=context.traceparent,
        organization_id=org_info.id,
        iud=installment.iud,
        debt_position_origin=DebtPositionOrigin.SPONTANEOUS_SIL.value,
    )
    assert_response_ok(debt_position_res, "Get debt position by installment id")
    context.debt_position = DebtPosition.from_dict(debt_position_res.json()[0])


@when("SIL creates the spontaneous debt position via the 'InviaCarrello'")
def step_sil_invia_carrello(context):
    """Creates the spontaneous debt position through SIL (`paaSILInviaCarrello`) and
    asserts the SOAP outcome is `OK` with a URL to proceed for payment."""

    installment = context.installment
    org_info = context.org_info

    res = post_sil_invia_carrello_dovuti(
        token=context.token,
        traceparent=context.traceparent,
        installment=installment,
        debt_position_type_org_code=context.debt_position_type_org_code,
        ipa_code=org_info.ipa_code,
    )

    _process_invia_carrello_response(context, res, org_info, installment)


@when("SIL creates the spontaneous multi-beneficiary debt position via the 'InviaCarrello'")
def step_sil_invia_carrello_multi_beneficiary(context):
    """Creates the spontaneous multi-beneficiary debt position through SIL (`paaSILInviaCarrello`) and
    asserts the SOAP outcome is `OK` with a URL to proceed for payment."""

    installment = context.installment
    org_info = context.org_info

    res = post_sil_invia_carrello_dovuti_enti_secondari(
        token=context.token,
        traceparent=context.traceparent,
        installment=installment,
        second_transfer=context.second_transfer,
        debt_position_type_org_code=context.debt_position_type_org_code,
        ipa_code=org_info.ipa_code,
    )

    _process_invia_carrello_response(context, res, org_info, installment)


@then("'ChiediEsitoCarrello' reports the outcome as '{status}'")
@then("'ChiediEsitoCarrello' reports the outcome as '{status}' and the {data} data")
def step_sil_chiedi_esito_carrello(context, status):
    res = post_sil_chiedi_esito_carrello_dovuti(token=context.token,
                                                traceparent=context.traceparent,
                                                installment_id=context.installment.installment_id,
                                                ipa_code=context.org_info.ipa_code)

    res_parsed = xmltodict.parse(res.content.decode('utf-8'))
    assert_response_ok(res, "SIL invia chiedi esito carrello")
    res_body = \
        res_parsed['SOAP-ENV:Envelope']['SOAP-ENV:Body']['ns3:paaSILChiediEsitoCarrelloDovutiRisposta'][
            'listaCarrelli'][
            'rispostaCarrello']
    assert res_body['esito'] == status

    context.chiedi_esito_carrello_response = res_body


@then("the RT returned by 'ChiediEsitoCarrello' matches the expected data")
def step_chiedi_esito_carrello_rt_matches(context):
    """Checks if the RT returned by 'ChiediEsitoCarrello' matches the same RT ingested by PU from PagoPA"""
    res_body = context.chiedi_esito_carrello_response

    rt_b64 = res_body.get('rt')
    assert rt_b64, "Field 'rt' is missing in the ChiediEsitoCarrello response with outcome PAGATO"

    actual_rt_xml = base64.b64decode(rt_b64).decode('utf-8')

    res = get_ingestion_flow_file(
        token=context.token,
        traceparent=context.traceparent,
        organization_id=context.org_info.id,
        ingestion_flow_file_id=context.ingestion_flow_file_id,
    )
    assert_response_ok(res, "Get ingestion flow file by id")

    expected_rt_xml = res.content.decode('utf-8')

    assert xml_elements_equal(
        xml_a=actual_rt_xml,
        xml_b=expected_rt_xml,
        xpath_b='.//{*}receipt',
    ), "The RT returned by 'ChiediEsitoCarrello' does not match the expected RT ingested from PagoPA"
