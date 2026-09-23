import io
import pandas
import time
import xmltodict
from api.fileshare import get_export_file
from api.soap.sil import post_sil_prenota_export_flusso, \
    post_sil_prenota_export_flusso_incrementale_con_ricevuta, post_sil_chiedi_stato_export_flusso
from bdd.steps.authentication_step import step_get_token_sil
from bdd.steps.utils.assertions import assert_response_ok
from bdd.steps.utils.debt_position_utility import get_installment_paid
from behave import when, then
from config.configuration import settings
from datetime import datetime, timedelta

EXPORT_STATUS_COMPLETED = 'EXPORT_ESEGUITO'
EXPORT_STATUS_NO_DATA = 'EXPORT_ESEGUITO_NESSUN_DOVUTO_TROVATO'
EXPORT_STATUS_IN_PROGRESS = ('LOAD_EXPORT', 'EXPORT_IN_ELAB')
EXPORT_STATUS_FAILED = ('ERROR_EXPORT', 'EXPORT_CANCELLATO')

DEBT_POSITION_TYPE_ORG_CODE = settings.debt_position_type_org_code.feature_test


def check_res_ok_and_get_body(response_content, tag_name):
    res_parsed = xmltodict.parse(response_content.decode('utf-8'))
    res_body = res_parsed['SOAP-ENV:Envelope']['SOAP-ENV:Body'][f'ns3:{tag_name}']
    assert res_body.get('fault') is None, f"SIL {tag_name} returned a fault: {res_body.get('fault')}"
    return res_body


@when("SIL requests the export of paid notices")
def step_sil_prenota_export_flusso(context):
    """Requests a paid-notices export through SIL (`paaSILPrenotaExportFlusso`)

    - requests the export for a date window around today, filtered by the debt position type org"""
    step_get_token_sil(context=context, pagopa_interaction=context.org_info.pagopa_interaction)

    date_from = (datetime.now()).strftime('%Y-%m-%d')
    date_to = (datetime.now()).strftime('%Y-%m-%d')

    res = post_sil_prenota_export_flusso(token=context.token, traceparent=context.traceparent,
                                         ipa_code=context.org_info.ipa_code, date_from=date_from, date_to=date_to,
                                         debt_position_type_org_code=DEBT_POSITION_TYPE_ORG_CODE)
    assert_response_ok(res, "SIL prenota export flusso")
    res_body = check_res_ok_and_get_body(res.content, 'paaSILPrenotaExportFlussoRisposta')

    context.export_request_token = res_body['requestToken']
    assert context.export_request_token is not None, "No requestToken returned by the export reservation"


@when("SIL requests the incremental export of paid notices with receipt")
def step_sil_prenota_export_flusso_incrementale(context):
    """Requests an incremental paid-notices export with receipt through SIL (`paaSILPrenotaExportFlussoIncrementaleConRicevuta`)

    - requests the export for a `dateTime` window around today, filtered by the debt position type org"""
    step_get_token_sil(context=context, pagopa_interaction=context.org_info.pagopa_interaction)

    date_from = (datetime.now() - timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M:%S')
    date_to = (datetime.now() + timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M:%S')

    res = post_sil_prenota_export_flusso_incrementale_con_ricevuta(
        token=context.token, traceparent=context.traceparent, ipa_code=context.org_info.ipa_code,
        date_from=date_from, date_to=date_to, debt_position_type_org_code=DEBT_POSITION_TYPE_ORG_CODE, receipt=True, incremental=True)
    assert_response_ok(res, "SIL prenota export flusso incrementale con ricevuta")
    res_body = check_res_ok_and_get_body(res.content, 'paaSILPrenotaExportFlussoIncrementaleConRicevutaRisposta')

    context.export_request_token = res_body['requestToken']
    assert context.export_request_token is not None, "No requestToken returned by the export reservation"


@then("the paid notices export completes successfully")
def step_check_export_status(context, tries=20, delay=4):
    """Polls the export status (`paaSILChiediStatoExportFlusso`) until it reaches `EXPORT_ESEGUITO`

    - retries while the export is `LOAD_EXPORT` / `EXPORT_IN_ELAB`
    - fails on an error/cancelled/no-data terminal status"""
    status = None
    count = 0
    while count < tries:
        count += 1
        res = post_sil_chiedi_stato_export_flusso(token=context.token, traceparent=context.traceparent,
                                                  ipa_code=context.org_info.ipa_code,
                                                  request_token=context.export_request_token)
        assert_response_ok(res, "SIL chiedi stato export flusso")
        res_body = check_res_ok_and_get_body(res.content, 'paaSILChiediStatoExportFlussoRisposta')
        status = res_body['stato']

        if status == EXPORT_STATUS_COMPLETED:
            return
        assert status not in EXPORT_STATUS_FAILED and status != EXPORT_STATUS_NO_DATA, \
            f"Export {context.export_request_token} reached unexpected terminal status: {status}"
        assert status in EXPORT_STATUS_IN_PROGRESS, f"Unexpected export status: {status}"
        time.sleep(delay)

    assert False, f"Export {context.export_request_token} did not complete after {tries} tries (last status: {status})"


@then("the paid notice appears in the export with the correct data")
def step_check_paid_notice_in_export(context):
    """Downloads the exported CSV and verifies the paid installment row

    - fetches the export file from the fileshare service using the export request token
    - locates the row matching the paid installment IUV/IUD
    - asserts that the amount, debt position type org, IUR, IUV and IUD of that row matches the expected values"""
    installment = get_installment_paid(context)

    res = get_export_file(token=context.token, traceparent=context.traceparent,
                          organization_id=context.org_info.id, export_file_id=context.export_request_token)
    assert_response_ok(res, "Download export file")

    export_rows = pandas.read_csv(io.BytesIO(res.content), compression='zip', sep=';', dtype=str, keep_default_na=False)

    matching = export_rows[(export_rows['codIuv'] == installment.iuv) & (export_rows['codIud'] == installment.iud)]
    assert len(matching) == 1, \
        f"Expected exactly 1 export row for IUV {installment.iuv} / IUD {installment.iud}, got {len(matching)}"
    row = matching.iloc[0]

    expected_amount = float(installment.amount_cents) / 100
    assert float(row['singoloImportoPagato']) == expected_amount, \
        f"Amount mismatch: expected {expected_amount}, got {row['singoloImportoPagato']}"
    assert row['tipoDovuto'] == DEBT_POSITION_TYPE_ORG_CODE, \
        f"debtPositionTypeOrgCode mismatch: expected {DEBT_POSITION_TYPE_ORG_CODE}, got {row['tipoDovuto']}"
    assert row['identificativoUnivocoRiscoss'] == installment.iur, \
        f"iuv mismatch: expected {installment.iur}, got {row['identificativoUnivocoRiscoss']}"
    assert row['codIuv'] == installment.iuv, \
        f"iuv mismatch: expected {installment.iuv}, got {row['codIuv']}"
    assert row['codIud'] == installment.iud, \
        f"iud mismatch: expected {installment.iud}, got {row['codIud']}"