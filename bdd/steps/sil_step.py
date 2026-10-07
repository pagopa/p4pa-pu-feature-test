import base64
import pymupdf
import re
import xmltodict
from api.debt_positions import get_debt_position_by_iud
from api.fileshare import get_ingestion_flow_file
from api.soap.sil import post_sil_invia_carrello_dovuti, post_sil_chiedi_esito_carrello_dovuti, checkout_url_pattern, \
    post_sil_invia_carrello_dovuti_enti_secondari, post_sil_invia_dovuti, post_sil_chiedi_pagati, \
    post_sil_chiedi_pagati_con_ricevuta, post_sil_importa_dovuto, post_sil_verifica_avviso, \
    get_sil_print_payment_notice
from bdd.steps.utils.assertions import assert_response_ok
from bdd.steps.utils.debt_position_utility import \
    find_installment_by_seq_num_and_po_index, get_installment_paid, \
    retrieve_dp_type_org_by_code, retrieve_taxonomy_code_by_dp_type_org, \
    build_feature_test_iud
from bdd.steps.utils.utility import xml_elements_equal
from behave import when, then
from datetime import datetime, timedelta
from model.debt_position import DebtPosition, DebtPositionOrigin, Installment, \
    Debtor, SilDebtPositionAction

_RESPONSE_INFO_BY_SOAP_ACTION = {
    'InviaCarrelloDovuti': {
        'tag': 'ns3:paaSILInviaCarrelloDovutiRisposta',
        'session_field': 'idSessionCarrello',
    },
    'InviaDovuti': {
        'tag': 'ns3:paaSILInviaDovutiRisposta',
        'session_field': 'idSession',
    },
    'VerificaAvviso': {
        'tag': 'ns3:paaSILVerificaAvvisoRisposta',
        'session_field': 'idSession',
    },
    'ImportaDovuto': {
        'tag': 'ns3:paaSILImportaDovutoRisposta',
    },
}


def _get_response_body(res, soap_action):
    response_tag = _RESPONSE_INFO_BY_SOAP_ACTION[soap_action]['tag']

    res_parsed = xmltodict.parse(res.content.decode('utf-8'))
    assert_response_ok(res, f"SIL {soap_action}")
    return res_parsed['SOAP-ENV:Envelope']['SOAP-ENV:Body'][response_tag]


def _get_ok_response_body(res, soap_action):
    res_body = _get_response_body(res, soap_action)
    assert res_body.get('esito') == 'OK', f"'{soap_action}' did not return OK: {res_body.get('fault')}"
    return res_body


def _check_checkout_session(soap_action, res_body, org_info, installment):
    session_field = _RESPONSE_INFO_BY_SOAP_ACTION[soap_action]['session_field']
    assert res_body.get(session_field) is not None, f"No {session_field} returned by '{soap_action}'"

    expected_pattern = checkout_url_pattern(org_info.fiscal_code)
    assert re.match(expected_pattern, res_body['url']), (
        f"Checkout URL does not match with expected: {res_body['url']}"
    )

    installment.installment_id = res_body[session_field]


def _load_debt_position(context, org_info, installment, debt_position_origin: DebtPositionOrigin):
    debt_position_res = get_debt_position_by_iud(
        token=context.token,
        traceparent=context.traceparent,
        organization_id=org_info.id,
        iud=installment.iud,
        debt_position_origin=debt_position_origin.value,
    )
    assert_response_ok(debt_position_res, "Get debt position by installment id")
    context.debt_position = DebtPosition.from_dict(debt_position_res.json()[0])


def _process_response(context, soap_action, res, org_info, installment):
    res_body = _get_ok_response_body(res, soap_action)
    _check_checkout_session(soap_action, res_body, org_info, installment)
    _load_debt_position(context, org_info, installment, DebtPositionOrigin.SPONTANEOUS_SIL)


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
    res_body = _chiedi_pagati(context)
    assert res_body['fault']['faultCode'] == status


def _chiedi_pagati(context):
  res = post_sil_chiedi_pagati(
    token=context.token,
    traceparent=context.traceparent,
    installment_id=context.installment.installment_id,
    ipa_code=context.org_info.ipa_code,
  )

  res_parsed = xmltodict.parse(res.content.decode('utf-8'))
  assert_response_ok(res, "SIL chiedi pagati")
  return res_parsed['SOAP-ENV:Envelope']['SOAP-ENV:Body'][
    'ns3:paaSILChiediPagatiRisposta']


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


def _importa_dovuto(context, action: SilDebtPositionAction):
    res = post_sil_importa_dovuto(
      token=context.token,
      traceparent=context.traceparent,
      installment=context.installment,
      debt_position_type_org_code=context.debt_position_type_org_code,
      ipa_code=context.org_info.ipa_code,
      action=action,
    )

    res_body = _get_ok_response_body(res, 'ImportaDovuto')
    assert res_body.get('identificativoUnivocoVersamento'), "No IUV returned by 'ImportaDovuto'"
    return res_body


@when("SIL creates a debt position of type {debt_position_type_org_code} with single installment of {amount} euros "
      "through SIL 'ImportaDovuto'")
def step_sil_importa_dovuto(context, debt_position_type_org_code, amount):
    """Creates the debt position through SIL (`paaSILImportaDovuto`)"""

    org_info = context.org_info
    debt_position_type_org = retrieve_dp_type_org_by_code(token=context.token,
                                                          traceparent=context.traceparent,
                                                          organization_id=context.org_info.id,
                                                          debt_position_type_org_code=debt_position_type_org_code)
    taxonomy_code = retrieve_taxonomy_code_by_dp_type_org(token=context.token,
                                                          traceparent=context.traceparent,
                                                          debt_position_type_id=
                                                          debt_position_type_org['debtPositionTypeId'])

    iud = build_feature_test_iud(seq_num=1)
    installment = Installment(iud=iud, amount_cents=(int(amount) * 100),
                              remittance_information='Test ' + iud,
                              debtor=Debtor(),
                              legacy_payment_metadata=taxonomy_code,
                              due_date=(datetime.now() + timedelta(days=3)).strftime('%Y-%m-%d')
                              )

    context.installment = installment
    context.debt_position_type_org_code = debt_position_type_org_code

    res_body = _importa_dovuto(context, SilDebtPositionAction.INSERT)
    assert res_body.get('urlFileAvviso'), "No payment notice URL returned by 'ImportaDovuto'"

    installment.iuv = res_body['identificativoUnivocoVersamento']
    context.payment_notice_url = res_body['urlFileAvviso']

    _load_debt_position(context, org_info, installment, DebtPositionOrigin.ORDINARY_SIL)


def _extract_notice_data(pdf_bytes: bytes) -> dict:
    with pymupdf.open(stream=pdf_bytes, filetype='pdf') as document:
        lines = [line.strip() for page in document for line in page.get_text().splitlines() if line.strip()]

    def after(label: str, offset: int = 1) -> str:
        return lines[lines.index(label) + offset]

    return {
        'subject': after('AVVISO DI PAGAMENTO'),
        'creditor_fiscal_code': after('ENTE CREDITORE'),
        'creditor_name': after('ENTE CREDITORE', 2),
        'debtor_name': after('DESTINATARIO'),
        'amount': after('Importo').removesuffix(' Euro'),
        'due_date': after('entro il') + after('entro il', 2),
        'notice_number': after('Cod. Avviso').replace(' ', ''),
        'cbill_code': after('Cod. CBILL'),
    }


@then("the payment notice PDF returned by 'ImportaDovuto' contains the debt position data")
def step_check_payment_notice_pdf(context):
    """Downloads the payment notice from the URL returned by 'ImportaDovuto'.

    It verifies that:
    - the downloaded file is a PDF;
    - the PDF reports the remittance information, the creditor organization fiscal code and name, the debtor name,
      the amount, the due date and the NAV of the installment, and a valid CBILL code."""

    res = get_sil_print_payment_notice(token=context.token, traceparent=context.traceparent,
                                       url=context.payment_notice_url)
    assert_response_ok(res, "Download payment notice")
    assert res.content.startswith(b'%PDF'), "The payment notice returned by 'ImportaDovuto' is not a PDF"

    installment = find_installment_by_seq_num_and_po_index(debt_position=context.debt_position, po_index=1, seq_num=1)
    expected = {
        'subject': installment.remittance_information,
        'creditor_fiscal_code': context.org_info.fiscal_code,
        'creditor_name': context.org_info.name,
        'debtor_name': installment.debtor.full_name,
        'amount': f"{installment.amount_cents / 100:.2f}".replace('.', ','),
        'due_date': installment.due_date,
        'notice_number': installment.nav,
    }

    actual = _extract_notice_data(res.content)
    cbill_code = actual.pop('cbill_code')

    assert actual == expected, f"expected {expected}, got {actual}"
    assert re.fullmatch(r'[A-Z0-9]{5}', cbill_code), f"invalid CBILL code: {cbill_code!r}"


@then("'VerificaAvviso' returns the checkout URL to start the payment")
def step_sil_verifica_avviso(context):
    """Verifies the payment notice through SIL (`paaSILVerificaAvviso`)"""

    res_body = _get_ok_response_body(post_sil_verifica_avviso(
      token=context.token,
      traceparent=context.traceparent,
      iuv=context.installment.iuv,
      ipa_code=context.org_info.ipa_code,
    ), 'VerificaAvviso')
    _check_checkout_session('VerificaAvviso', res_body, context.org_info, context.installment)


@then("'VerificaAvviso' reports the outcome as '{status}'")
def step_sil_verifica_avviso_fault(context, status):
    """Verifies that SIL (`paaSILVerificaAvviso`) returns the expected status as fault code"""

    res_body = _get_response_body(post_sil_verifica_avviso(
      token=context.token,
      traceparent=context.traceparent,
      iuv=context.installment.iuv,
      ipa_code=context.org_info.ipa_code,
    ), 'VerificaAvviso')
    assert res_body.get('fault') is not None, f"'VerificaAvviso' did not return a fault: {res_body}"
    assert res_body['fault']['faultCode'] == status, \
        f"'VerificaAvviso' fault code mismatch: expected {status}, got {res_body['fault']['faultCode']}"


@then("the payment notice PDF returned by 'ImportaDovuto' is no longer available")
def step_check_payment_notice_not_available(context):
    """Verifies that the payment notice download is no longer available through the URL returned by 'ImportaDovuto'"""

    res = get_sil_print_payment_notice(token=context.token, traceparent=context.traceparent,
                                       url=context.payment_notice_url)
    assert_response_ok(res, "Download payment notice", expected_status=404)


@then("'ChiediPagati' reports the installment as paid")
def step_sil_chiedi_pagati(context):
    """Checks the payment through SIL (`paaSILChiediPagati`)"""

    res_body = _chiedi_pagati(context)
    assert res_body.get('fault') is None, f"'ChiediPagati' returned a fault: {res_body.get('fault')}"
    assert res_body.get('pagati'), "Field 'pagati' is missing in the 'ChiediPagati' response"

    payment = xmltodict.parse(base64.b64decode(res_body['pagati']), process_namespaces=True,
                                   namespaces={'http://www.regione.veneto.it/schemas/2012/Pagamenti/Ente/': None},
                                   force_list=('datiSingoloPagamento',))['Pagati']
    payment_data = payment['datiPagamento']
    single_payment_data = payment_data['datiSingoloPagamento'][0]
    installment = get_installment_paid(context)
    expected_amount = "{:.2f}".format(installment.amount_cents / 100)

    assert payment_data['identificativoUnivocoVersamento'] == installment.iuv, \
        f"iuv mismatch: expected {installment.iuv}, got {payment_data['identificativoUnivocoVersamento']}"
    assert payment_data['codiceEsitoPagamento'] == '0', \
        f"payment outcome code mismatch: expected 0, got {payment_data['codiceEsitoPagamento']}"
    assert single_payment_data['identificativoUnivocoDovuto'] == installment.iud, \
        f"iud mismatch: expected {installment.iud}, got {single_payment_data['identificativoUnivocoDovuto']}"
    assert single_payment_data['singoloImportoPagato'] == expected_amount, \
        f"amount mismatch: expected {expected_amount}, got {single_payment_data['singoloImportoPagato']}"


@when("SIL updates the installment amount to {amount} euros through SIL 'ImportaDovuto'")
def step_sil_importa_dovuto_update(context, amount):
    """Updates the installment amount through SIL (`paaSILImportaDovuto` with action `M`).

    - asserts the SOAP outcome is `OK` with the same IUV and the URL of the updated payment notice PDF;
    - checks the debt position has been updated with the new amount."""

    installment = context.installment
    iuv = installment.iuv
    installment.amount_cents = int(amount) * 100

    res_body = _importa_dovuto(context, SilDebtPositionAction.UPDATE)
    assert res_body['identificativoUnivocoVersamento'] == iuv, \
        f"iuv mismatch: expected {iuv}, got {res_body['identificativoUnivocoVersamento']}"
    assert res_body.get('urlFileAvviso'), "No payment notice URL returned by 'ImportaDovuto'"

    context.payment_notice_url = res_body['urlFileAvviso']

    _load_debt_position(context, context.org_info, installment, DebtPositionOrigin.ORDINARY_SIL)
    updated_installment = find_installment_by_seq_num_and_po_index(debt_position=context.debt_position, po_index=1,
                                                                   seq_num=1)
    assert updated_installment.amount_cents == installment.amount_cents, \
        f"amount mismatch: expected {installment.amount_cents}, got {updated_installment.amount_cents}"


@when("SIL cancels the debt position through SIL 'ImportaDovuto'")
def step_sil_importa_dovuto_cancel(context):
    """Cancels the debt position through SIL (`paaSILImportaDovuto` with action `A`) and asserts the SOAP outcome is
    `OK` with the same IUV and no payment notice URL."""

    iuv = context.installment.iuv

    res_body = _importa_dovuto(context, SilDebtPositionAction.CANCEL)
    assert res_body['identificativoUnivocoVersamento'] == iuv, \
        f"iuv mismatch: expected {iuv}, got {res_body['identificativoUnivocoVersamento']}"
    assert res_body.get('urlFileAvviso') is None, \
        f"Unexpected payment notice URL returned for a cancelled debt position: {res_body.get('urlFileAvviso')}"