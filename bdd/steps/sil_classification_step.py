import io
import os
import pandas
from api.fileshare import get_export_file, post_upload_file_to_url
from api.soap.sil import post_sil_prenota_export_flusso, \
    post_sil_prenota_export_flusso_incrementale_con_ricevuta, \
    post_sil_autorizza_import_flusso_tesoreria, post_sil_prenota_export_flusso_riconciliazione
from bdd.steps.authentication_step import step_get_token_sil
from bdd.steps.treasury_step import format_ingestion_flow_file, create_files
from bdd.steps.utils.assertions import assert_response_ok
from bdd.steps.utils.debt_position_utility import get_installment_paid
from bdd.steps.utils.utility import check_res_ok_and_get_body, retry_get_export_status, retry_get_import_status, \
    retry_get_reconciliation_export_status
from behave import when, then
from config.configuration import settings
from datetime import datetime, timedelta

DEBT_POSITION_TYPE_ORG_CODE = settings.debt_position_type_org_code.feature_test


@when("SIL requests the export of paid notices with version {version}")
def step_sil_prenota_export_flusso(context, version):
    """Requests a paid-notices export through SIL (`paaSILPrenotaExportFlusso`)

    - requests the export for a date window around today, filtered by the debt position type org"""
    step_get_token_sil(context=context, pagopa_interaction=context.org_info.pagopa_interaction)

    date_from = (datetime.now()).strftime('%Y-%m-%d')
    date_to = (datetime.now()).strftime('%Y-%m-%d')

    res = post_sil_prenota_export_flusso(token=context.token, traceparent=context.traceparent,
                                         ipa_code=context.org_info.ipa_code, date_from=date_from, date_to=date_to,
                                         debt_position_type_org_code=DEBT_POSITION_TYPE_ORG_CODE, version=version)
    assert_response_ok(res, "SIL prenota export flusso")
    res_body = check_res_ok_and_get_body(res.content, 'paaSILPrenotaExportFlussoRisposta')

    context.export_request_token = res_body['requestToken']
    assert context.export_request_token is not None, "No requestToken returned by the export reservation"


@when("SIL requests the incremental export of paid notices with receipt and version {version}")
def step_sil_prenota_export_flusso_incrementale(context, version):
    """Requests an incremental paid-notices export with receipt through SIL (`paaSILPrenotaExportFlussoIncrementaleConRicevuta`)

    - requests the export for a `dateTime` window around today, filtered by the debt position type org"""
    step_get_token_sil(context=context, pagopa_interaction=context.org_info.pagopa_interaction)

    date_from = (datetime.now() - timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M:%S')
    date_to = (datetime.now() + timedelta(hours=2)).strftime('%Y-%m-%dT%H:%M:%S')

    res = post_sil_prenota_export_flusso_incrementale_con_ricevuta(
        token=context.token, traceparent=context.traceparent, ipa_code=context.org_info.ipa_code,
        date_from=date_from, date_to=date_to, debt_position_type_org_code=DEBT_POSITION_TYPE_ORG_CODE, receipt=True, incremental=True, version=version)
    assert_response_ok(res, "SIL prenota export flusso incrementale con ricevuta")
    res_body = check_res_ok_and_get_body(res.content, 'paaSILPrenotaExportFlussoIncrementaleConRicevutaRisposta')

    context.export_request_token = res_body['requestToken']
    assert context.export_request_token is not None, "No requestToken returned by the export reservation"


@then("the paid notices export completes successfully")
def step_check_export_status(context):
    """Polls the export status (`paaSILChiediStatoExportFlusso`) until it reaches `EXPORT_ESEGUITO`

    - retries while the export is `LOAD_EXPORT` / `EXPORT_IN_ELAB`
    - fails on an error/cancelled/no-data terminal status"""
    retry_get_export_status(token=context.token, traceparent=context.traceparent,
                            ipa_code=context.org_info.ipa_code, request_token=context.export_request_token)


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
        f"iur mismatch: expected {installment.iur}, got {row['identificativoUnivocoRiscoss']}"
    assert row['codIuv'] == installment.iuv, \
        f"iuv mismatch: expected {installment.iuv}, got {row['codIuv']}"
    assert row['codIud'] == installment.iud, \
        f"iud mismatch: expected {installment.iud}, got {row['codIud']}"



@when("SIL imports the treasury flow of type {flow_type}")
def step_sil_import_treasury_flow(context, flow_type):
    """Imports a treasury flow through SIL (`pivotSILAutorizzaImportFlussoTesoreria`)

    - authorizes the import and reads the upload URL and request token
    - builds the treasury OPI zip and uploads it to the returned URL"""
    step_get_token_sil(context=context, pagopa_interaction=context.org_info.pagopa_interaction)

    res = post_sil_autorizza_import_flusso_tesoreria(token=context.token, traceparent=context.traceparent,
                                                     ipa_code=context.org_info.ipa_code, flow_type=flow_type)
    assert_response_ok(res, "SIL autorizza import flusso tesoreria")
    res_body = check_res_ok_and_get_body(res.content, 'pivotSILAutorizzaImportFlussoTesoreriaRisposta')

    context.import_request_token = res_body['requestToken']
    upload_url = res_body['uploadUrl']
    assert context.import_request_token is not None, "No requestToken returned by the treasury import authorization"
    assert upload_url is not None, "No uploadUrl returned by the treasury import authorization"

    amount = int(get_installment_paid(context).amount_cents / 100)
    with open('./bdd/steps/file_template/treasury_opi.xml', 'r') as file:
        ingestion_flow_file = file.read()
    ingestion_flow_file = format_ingestion_flow_file(context, amount, ingestion_flow_file, context.org_info)
    xml_file_path, zip_file_path = create_files(context, ingestion_flow_file)

    res_upload = post_upload_file_to_url(url=upload_url, token=context.token, traceparent=context.traceparent,
                                         file_name=zip_file_path)
    assert_response_ok(res_upload, "Upload treasury flow to authorized URL")

    os.remove(zip_file_path)
    os.remove(xml_file_path)


@then("the treasury import completes successfully")
def step_check_treasury_import_status(context):
    """Polls the treasury import status (`pivotSILChiediStatoImportFlussoTesoreria`) until it reaches `FILE_CARICATO`"""
    retry_get_import_status(token=context.token, traceparent=context.traceparent, ipa_code=context.org_info.ipa_code,
                            request_token=context.import_request_token)


@when("SIL requests the reconciliation export for classification label {classification_label} with version {version}")
def step_sil_prenota_reconciliation_export(context, classification_label, version):
    """Requests a reconciliation export through SIL (`pivotSILPrenotaExportFlussoRiconciliazione`)

    - requests the export filtered by the paid notice IUV and the given classification"""
    installment = get_installment_paid(context)

    res = post_sil_prenota_export_flusso_riconciliazione(token=context.token, traceparent=context.traceparent,
                                                         ipa_code=context.org_info.ipa_code, iuv=installment.iuv,
                                                         classification_label=classification_label, version=version)
    assert_response_ok(res, "SIL prenota export flusso riconciliazione")
    res_body = check_res_ok_and_get_body(res.content, 'pivotSILPrenotaExportFlussoRiconciliazioneRisposta')

    context.export_request_token = res_body['requestToken']
    assert context.export_request_token is not None, "No requestToken returned by the reconciliation export reservation"


@then("the reconciliation export completes successfully")
def step_check_reconciliation_export_status(context):
    """Polls the reconciliation export status (`pivotSILChiediStatoExportFlussoRiconciliazione`) until `EXPORT_ESEGUITO`"""
    retry_get_reconciliation_export_status(token=context.token, traceparent=context.traceparent,
                                           ipa_code=context.org_info.ipa_code,
                                           request_token=context.export_request_token)


@then("the paid notice appears in the reconciliation export with classification label {classification_label} without iur and iuf")
def step_check_notice_in_reconciliation_export(context, classification_label):
    """Downloads the reconciliation export CSV and verifies the paid notice row

                  - fetches the export file from the fileshare service using the export request token
                  - locates the row matching the paid installment IUV/IUD
                  - asserts that the classification label of that row matches the expected value"""
    check_notice_in_reconciliation_export(context, classification_label, has_iur_and_iuf=False)


@then("the paid notice appears in the reconciliation export with classification label {classification_label}")
def step_check_notice_in_reconciliation_export(context, classification_label):
    """Downloads the reconciliation export CSV and verifies the paid notice row

                    - fetches the export file from the fileshare service using the export request token
                    - locates the row matching the paid installment IUV/IUD
                    - asserts that the IUR, IUF and classification label of that row matches the expected values"""
    check_notice_in_reconciliation_export(context, classification_label, has_iur_and_iuf=True)


def check_notice_in_reconciliation_export(context, classification_label, has_iur_and_iuf: bool):
    installment = get_installment_paid(context)

    res = get_export_file(token=context.token,
                          traceparent=context.traceparent,
                          organization_id=context.org_info.id,
                          export_file_id=context.export_request_token)
    assert_response_ok(res, "Download reconciliation export file")

    export_rows = pandas.read_csv(io.BytesIO(res.content), compression='zip',
                                  sep=';', dtype=str, keep_default_na=False)

    matching = export_rows[(export_rows[
                              'cod_rp_silinviarp_id_univoco_versamento_e'] == installment.iuv) & (
                                 export_rows['cod_iud_e'] == installment.iud)]
    assert len(matching) == 1, \
      f"Expected exactly 1 reconciliation row for IUV {installment.iuv} / IUD {installment.iud}, got {len(matching)}"
    row = matching.iloc[0]

    if has_iur_and_iuf:
      assert row[
               'cod_dati_sing_pagam_identificativo_univoco_riscossione_r'] == installment.iur, \
        f"iur mismatch: expected {installment.iur}, got {row['cod_dati_sing_pagam_identificativo_univoco_riscossione_r']}"
      assert row['cod_identificativo_flusso_r'] == installment.iuf, \
        f"iuf mismatch: expected {installment.iuf}, got {row['cod_identificativo_flusso_r']}"
    assert row['classificazione_completezza'] == classification_label, \
      f"classification label mismatch: expected {classification_label}, got {row['classificazione_completezza']}"