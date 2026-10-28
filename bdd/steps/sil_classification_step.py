import io
import os
from datetime import datetime, timedelta

from bdd.steps.utils.date_utils import today

from collections import Counter
from datetime import datetime, timedelta
from decimal import Decimal

import pandas
from behave import given, when, then

from behave import when, then

from api.fileshare import get_export_file, post_upload_file_to_url
from api.soap.sil import post_sil_prenota_export_flusso, \
    post_sil_prenota_export_flusso_incrementale_con_ricevuta, \
    post_sil_autorizza_import_flusso_tesoreria, post_sil_prenota_export_flusso_riconciliazione, \
    post_sil_chiedi_accertamento_per_iuf, post_sil_chiedi_accertamento_per_bolletta
from bdd.steps.authentication_step import step_get_token_sil
from bdd.steps.treasury_step import format_ingestion_flow_file, create_files, IUF_NOT_FOUND
from bdd.steps.utils.assertions import assert_response_ok
from bdd.steps.utils.debt_position_utils import get_installment_paid
from bdd.steps.utils.soap_utils import check_res_ok_and_get_body
from bdd.steps.utils.polling_utils import retry_get_export_status, \
    retry_get_import_treasury_status, \
    retry_get_reconciliation_export_status
from config.configuration import settings

DEBT_POSITION_TYPE_ORG_CODE = settings.debt_position_type_org_code.feature_test


@when("SIL requests the export of paid notices with version {version}")
def step_sil_prenota_export_flusso(context, version):
    """Requests a paid-notices export through SIL (`paaSILPrenotaExportFlusso`)

    - requests the export for a date window around today, filtered by the debt position type org"""
    step_get_token_sil(context=context, pagopa_interaction=context.org_info.pagopa_interaction)

    date_from = today()
    date_to = today()

    res = post_sil_prenota_export_flusso(token=context.token, traceparent=context.traceparent,
                                         ipa_code=context.org_info.ipa_code, date_from=date_from, date_to=date_to,
                                         debt_position_type_org_code=DEBT_POSITION_TYPE_ORG_CODE, version=version)
    _store_export_request_token(context, res, 'paaSILPrenotaExportFlussoRisposta', "SIL prenota export flusso")


@when("SIL requests the incremental export of paid notices with receipt and version {version}")
def step_sil_prenota_export_flusso_incrementale(context, version):
    """Requests an incremental paid-notices export with receipt through SIL (`paaSILPrenotaExportFlussoIncrementaleConRicevuta`)

    - requests the export for a `dateTime` window around today, filtered by the debt position type org"""
    step_get_token_sil(context=context, pagopa_interaction=context.org_info.pagopa_interaction)

    date_from = (datetime.now() - timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M:%S')
    date_to = (datetime.now() + timedelta(hours=2)).strftime('%Y-%m-%dT%H:%M:%S')

    res = post_sil_prenota_export_flusso_incrementale_con_ricevuta(
        token=context.token, traceparent=context.traceparent, ipa_code=context.org_info.ipa_code,
        date_from=date_from, date_to=date_to, debt_position_type_org_code=DEBT_POSITION_TYPE_ORG_CODE, receipt=True,
        incremental=True, version=version)
    _store_export_request_token(context, res, 'paaSILPrenotaExportFlussoIncrementaleConRicevutaRisposta',
                                "SIL prenota export flusso incrementale con ricevuta")
        date_from=date_from, date_to=date_to, debt_position_type_org_code=DEBT_POSITION_TYPE_ORG_CODE, receipt=True,
        incremental=True, version=version)
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
    retry_get_import_treasury_status(token=context.token, traceparent=context.traceparent,
                                     ipa_code=context.org_info.ipa_code,
                                     request_token=context.import_request_token)


@when("SIL requests the reconciliation export for classification label {classification_labels} with version {version}")
def step_sil_prenota_reconciliation_export(context, classification_labels, version):
    """Requests a reconciliation export through SIL (`pivotSILPrenotaExportFlussoRiconciliazione`)

    - requests the export filtered by the paid notice IUV and the given classification"""
    installment = get_installment_paid(context)

    classification_labels = classification_labels.replace(" ", "")

    res = post_sil_prenota_export_flusso_riconciliazione(token=context.token, traceparent=context.traceparent,
                                                         ipa_code=context.org_info.ipa_code, iuv=installment.iuv,
                                                         classification_labels=classification_labels, version=version)
    _store_export_request_token(context, res, 'pivotSILPrenotaExportFlussoRiconciliazioneRisposta',
                                "SIL prenota export flusso riconciliazione")


@then("the reconciliation export completes successfully")
def step_check_reconciliation_export_status(context):
    """Polls the reconciliation export status (`pivotSILChiediStatoExportFlussoRiconciliazione`) until `EXPORT_ESEGUITO`"""
    retry_get_reconciliation_export_status(token=context.token, traceparent=context.traceparent,
                                           ipa_code=context.org_info.ipa_code,
                                           request_token=context.export_request_token)


@then(
    "the paid notice appears in the reconciliation export with classification label {classification_labels} without iur and iuf")
def step_check_notice_in_reconciliation_export_without_iur_iuf(context, classification_labels):
    """Downloads the reconciliation export CSV and verifies the paid notice row

                  - fetches the export file from the fileshare service using the export request token
                  - locates the row matching the paid installment IUV/IUD
                  - asserts that the classification label of that row matches the expected value"""
    check_notice_in_reconciliation_export(context, classification_labels, has_iur_and_iuf=False)


@then("the paid notice appears in the reconciliation export with classification label {classification_labels}")
def step_check_notice_in_reconciliation_export_with_iur_iuf(context, classification_labels):
    """Downloads the reconciliation export CSV and verifies the paid notice row

                    - fetches the export file from the fileshare service using the export request token
                    - locates the row matching the paid installment IUV/IUD
                    - asserts that the IUR, IUF and classification label of that row matches the expected values"""
    check_notice_in_reconciliation_export(context, classification_labels, has_iur_and_iuf=True)


def check_notice_in_reconciliation_export(context, classification_labels: str, has_iur_and_iuf: bool):
    installment = get_installment_paid(context)
    expected_labels = sorted(l.strip() for l in classification_labels.split(",") if l.strip())

    res = get_export_file(token=context.token,
                          traceparent=context.traceparent,
                          organization_id=context.org_info.id,
                          export_file_id=context.export_request_token)
    assert_response_ok(res, "Download reconciliation export file")

    export_rows = pandas.read_csv(io.BytesIO(res.content), compression='zip',
                                  sep=';', dtype=str, keep_default_na=False)

    matching = export_rows[(export_rows['cod_rp_silinviarp_id_univoco_versamento_e'] == installment.iuv) &
                           (export_rows['cod_iud_e'] == installment.iud)]

    actual_labels = sorted(matching['classificazione_completezza'])
    assert actual_labels == expected_labels, \
        f"classification labels mismatch for IUV {installment.iuv} / IUD {installment.iud}: " \
        f"expected {expected_labels}, got {actual_labels}"

    if has_iur_and_iuf:
        expected_iur = installment.iur or ''
        expected_iuf = installment.iuf or ''
        for _, row in matching.iterrows():
            label = row['classificazione_completezza']
            assert row['cod_e_id_messaggio_ricevuta_e'] == expected_iur, \
                f"[{label}] iur mismatch: expected '{expected_iur}', " \
                f"got '{row['cod_e_id_messaggio_ricevuta_e']}'"
            assert row['cod_identificativo_flusso_r'] == expected_iuf, \
                f"[{label}] iuf mismatch: expected '{expected_iuf}', got '{row['cod_identificativo_flusso_r']}'"


@given("the paid notice is classified as {classification_labels} according to the reconciliation export {version}")
@then("the paid notice is classified as {classification_labels} according to the reconciliation export {version}")
def step_check_classification_labels(context, classification_labels, version):
    step_sil_prenota_reconciliation_export(context=context, classification_labels=classification_labels,
                                           version=version)
    step_check_reconciliation_export_status(context=context)
    step_check_notice_in_reconciliation_export_with_iur_iuf(context=context, classification_labels=classification_labels)
