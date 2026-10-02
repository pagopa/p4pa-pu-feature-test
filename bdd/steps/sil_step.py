import base64
import re

import xmltodict
from behave import when, then

from api.debt_positions import get_debt_position_by_iud
from api.fileshare import get_ingestion_flow_file
from api.soap.sil import post_sil_invia_carrello_dovuti, post_sil_chiedi_esito_carrello_dovuti, checkout_url_pattern, \
    post_sil_invia_carrello_dovuti_enti_secondari, post_sil_invia_dovuti, post_sil_chiedi_pagati, \
    post_sil_chiedi_pagati_con_ricevuta
from bdd.steps.utils.assertions import assert_response_ok
from bdd.steps.utils.utility import xml_elements_equal
from model.debt_position import DebtPosition, DebtPositionOrigin

_RESPONSE_INFO_BY_SOAP_ACTION = {
    'InviaCarrelloDovuti': {
        'tag': 'ns3:paaSILInviaCarrelloDovutiRisposta',
        'session_field': 'idSessionCarrello',
    },
    'InviaDovuti': {
        'tag': 'ns3:paaSILInviaDovutiRisposta',
        'session_field': 'idSession',
    },
}


def _process_response(context, soap_action, res, org_info, installment):
    response_info = _RESPONSE_INFO_BY_SOAP_ACTION[soap_action]
    response_tag = response_info['tag']
    session_field = response_info['session_field']

    res_parsed = xmltodict.parse(res.content.decode('utf-8'))
    assert_response_ok(res, f"SIL {soap_action}")
    res_body = res_parsed['SOAP-ENV:Envelope']['SOAP-ENV:Body'][response_tag]
    assert res_body['esito'] == 'OK'
    assert res_body[session_field] is not None

    expected_pattern = checkout_url_pattern(org_info.fiscal_code)
    assert re.match(expected_pattern, res_body['url']), (
        f"Checkout URL does not match with expected: {res_body['url']}"
    )

    installment.installment_id = res_body[session_field]

    debt_position_res = get_debt_position_by_iud(
        token=context.token,
        traceparent=context.traceparent,
        organization_id=org_info.id,
        iud=installment.iud,
        debt_position_origin=DebtPositionOrigin.SPONTANEOUS_SIL.value,
    )
    assert_response_ok(debt_position_res, "Get debt position by installment id")
    context.debt_position = DebtPosition.from_dict(debt_position_res.json()[0])


def _assert_rt_matches_expected(context, rt_b64, source_label: str):
    """Shared logic: decode a base64 RT, fetch the expected RT ingested from PagoPA,
    and compare their content."""

    assert rt_b64, f"Field 'rt' is missing in the {source_label} response"

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
    ), f"The RT returned by '{source_label}' does not match the expected RT ingested from PagoPA"


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

    _process_response(context, 'InviaCarrelloDovuti', res, org_info, installment)


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

    _process_response(context, 'InviaCarrelloDovuti', res, org_info, installment)


@when("SIL creates the spontaneous debt position via the 'InviaDovuti'")
def step_sil_invia_dovuti(context):
    """Creates the spontaneous debt position through SIL (`paaSILInviaDovuti`) and
    asserts the SOAP outcome is `OK` with a URL to proceed for payment."""

    installment = context.installment
    org_info = context.org_info

    res = post_sil_invia_dovuti(
        token=context.token,
        traceparent=context.traceparent,
        installment=installment,
        debt_position_type_org_code=context.debt_position_type_org_code,
        ipa_code=org_info.ipa_code,
        marca_bollo=getattr(context, 'stamp', None)
    )

    _process_response(context, 'InviaDovuti', res, org_info, installment)


@then("'ChiediEsitoCarrello' reports the outcome as '{status}'")
def step_sil_chiedi_esito_carrello(context, status):
    res = post_sil_chiedi_esito_carrello_dovuti(
        token=context.token,
        traceparent=context.traceparent,
        installment_id=context.installment.installment_id,
        ipa_code=context.org_info.ipa_code,
    )

    res_parsed = xmltodict.parse(res.content.decode('utf-8'))
    assert_response_ok(res, "SIL chiedi esito carrello")
    res_body = res_parsed['SOAP-ENV:Envelope']['SOAP-ENV:Body'] \
        ['ns3:paaSILChiediEsitoCarrelloDovutiRisposta']['listaCarrelli']['rispostaCarrello']
    assert res_body['esito'] == status

    context.chiedi_esito_carrello_response = res_body


@then("the RT returned by 'ChiediEsitoCarrello' matches the expected data")
def step_chiedi_esito_carrello_rt_matches(context):
    """Checks if the RT returned by 'ChiediEsitoCarrello' matches the same RT ingested by PU from PagoPA"""
    rt_b64 = context.chiedi_esito_carrello_response.get('rt')
    _assert_rt_matches_expected(context, rt_b64, source_label='ChiediEsitoCarrello')


@then("'ChiediPagati' reports the outcome as '{status}'")
def step_sil_chiedi_pagati(context, status):
    res = post_sil_chiedi_pagati(
        token=context.token,
        traceparent=context.traceparent,
        installment_id=context.installment.installment_id,
        ipa_code=context.org_info.ipa_code,
    )

    res_parsed = xmltodict.parse(res.content.decode('utf-8'))
    assert_response_ok(res, "SIL chiedi pagati")
    res_body = res_parsed['SOAP-ENV:Envelope']['SOAP-ENV:Body']['ns3:paaSILChiediPagatiRisposta']
    assert res_body['fault']['faultCode'] == status


@then("the RT returned by 'ChiediPagatiConRicevuta' matches the expected data")
def step_chiedi_pagati_rt_matches(context):
    """Checks if the RT returned by 'ChiediPagatiConRicevuta' matches the same RT ingested by PU from PagoPA"""

    res = post_sil_chiedi_pagati_con_ricevuta(
        token=context.token,
        traceparent=context.traceparent,
        installment_id=context.installment.installment_id,
        ipa_code=context.org_info.ipa_code,
    )

    res_parsed = xmltodict.parse(res.content.decode('utf-8'))
    assert_response_ok(res, "SIL chiedi pagati con ricevuta")
    res_body = res_parsed['SOAP-ENV:Envelope']['SOAP-ENV:Body']['ns3:paaSILChiediPagatiConRicevutaRisposta']
    rt_b64 = res_body.get('rt')
    _assert_rt_matches_expected(context, rt_b64, source_label='ChiediPagatiConRicevuta')