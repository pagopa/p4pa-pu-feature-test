import time

from api.debt_positions import get_debt_position
from api.process_executions import get_by_org_and_file_path_and_file_name
from api.send import get_send_notification
from api.send_campaign import get_send_campaign_detail
from api.soap.sil import post_sil_chiedi_stato_export_flusso, post_sil_chiedi_stato_import_flusso_tesoreria, \
    post_sil_chiedi_stato_export_flusso_riconciliazione, post_sil_chiedi_stato_import_flusso_notificati, \
    post_sil_chiedi_stato_import_flusso_posizioni_debitorie
from api.workflow_hub import get_workflow_status
from bdd.steps.utils.assertions import assert_response_ok
from bdd.steps.utils.soap_utils import check_res_ok_and_get_body
from model.file import FileStatus, FilePathName, SilExportStatus, SilImportStatus
from model.send_campaign import SendCampaignCounter
from model.workflow_hub import WorkflowStatus


def retry_get_workflow_status(token, traceparent: str, workflow_id: str, status: WorkflowStatus, tries=20, delay=4,
                              previous_run_id: str = None):
    count = 0

    def is_expected_run(response):
        return (response.status_code == 200 and response.json()['status'] == status.value
                and (previous_run_id is None or response.json()['runId'] != previous_run_id))

    res = get_workflow_status(token=token, traceparent=traceparent, workflow_id=workflow_id)

    success = is_expected_run(res)

    while not success:
        count += 1
        if count == tries:
            break
        time.sleep(delay)
        res = get_workflow_status(token=token, traceparent=traceparent, workflow_id=workflow_id)
        success = is_expected_run(res)

    assert success, \
        f"\nWorkflow {workflow_id} did not reach status {status.value} after {tries} tries" \
        f"{f' with a run other than {previous_run_id}' if previous_run_id else ''}: " \
        f"Last response HTTP {res.status_code} - {res.content}\n"


def retry_get_process_file_status(token, traceparent: str, organization_id: int, file_path_name: FilePathName,
                                  file_name: str, status: FileStatus, tries=20, delay=4) -> dict:
    count = 0

    def get_latest_file(response):
        files = response.json()['_embedded']['ingestionFlowFiles']
        if not files:
            return None
        return max(files, key=lambda f: f['ingestionFlowFileId'])

    res = get_by_org_and_file_path_and_file_name(token=token, traceparent=traceparent, organization_id=organization_id,
                                                 file_path_name=file_path_name.value, file_name=file_name)

    file = get_latest_file(res) if res.status_code == 200 else None
    success = (res.status_code == 200 and file is not None and file['status'] == status.value)

    while not success:
        count += 1
        if count == tries:
            break
        time.sleep(delay)
        res = get_by_org_and_file_path_and_file_name(token=token, traceparent=traceparent,
                                                     organization_id=organization_id,
                                                     file_path_name=file_path_name.value, file_name=file_name)
        file = get_latest_file(res) if res.status_code == 200 else None
        success = (res.status_code == 200 and file is not None and file['status'] == status.value)

    assert success, \
        f"\nFile '{file_name}' ({file_path_name.value}) did not reach status {status.value} after {tries} tries: " \
        f"last response HTTP {res.status_code} - {res.content}\n"
    return file


def retry_get_valid_send_notification(token, traceparent: str, notification_id, statuses: list = None,
                                      tries=20, delay=4):
    count = 0

    res = get_send_notification(token=token, traceparent=traceparent, notification_id=notification_id)

    success = (res.status_code == 200 and res.json().get('iun') is not None
               and (statuses is None or res.json().get('status') in statuses))

    while not success:
        count += 1
        if count == tries:
            break
        time.sleep(delay)
        res = get_send_notification(token=token, traceparent=traceparent, notification_id=notification_id)
        success = (res.status_code == 200 and res.json().get('iun') is not None
                   and (statuses is None or res.json().get('status') in statuses))

    return res


def retry_get_dp_status(token, traceparent: str, debt_position_id: int, status: str, tries=10, delay=2):
    count = 0

    res = get_debt_position(token=token, traceparent=traceparent, debt_position_id=debt_position_id)

    success = (res.status_code == 200 and res.json()['status'] == status)

    while not success:
        count += 1
        if count == tries:
            break
        time.sleep(delay)
        res = get_debt_position(token=token, traceparent=traceparent, debt_position_id=debt_position_id)
        success = (res.status_code == 200 and res.json()['status'] == status)

    assert success, \
        f"\nDebt position {debt_position_id} did not reach status {status} after {tries} tries: " \
        f"last response HTTP {res.status_code} - {res.content}\n"


def retry_get_export_status(token, traceparent: str, ipa_code: str,
                            request_token: str, tries=20, delay=4):
    status = None
    count = 0
    while count < tries:
        count += 1
        res = post_sil_chiedi_stato_export_flusso(token=token,
                                                  traceparent=traceparent,
                                                  ipa_code=ipa_code,
                                                  request_token=request_token)
        assert_response_ok(res, "SIL chiedi stato export flusso")
        res_body = check_res_ok_and_get_body(res.content,
                                             'paaSILChiediStatoExportFlussoRisposta')
        status = res_body['stato']

        if status == SilExportStatus.EXPORT_STATUS_COMPLETED:
            return
        assert status not in SilExportStatus.EXPORT_STATUS_FAILED and status != SilExportStatus.EXPORT_STATUS_NO_DATA, \
            f"Export {request_token} reached unexpected terminal status: {status}"
        assert status in SilExportStatus.EXPORT_STATUS_IN_PROGRESS, f"Unexpected export status: {status}"
        time.sleep(delay)

    assert False, f"Export {request_token} did not complete after {tries} tries (last status: {status})"


def retry_get_sil_import_status(post_fn, operation_name: str, response_root: str,
                                token, traceparent: str, ipa_code: str, request_token: str,
                                tries=20, delay=4):
    status = None
    count = 0
    while count < tries:
        count += 1
        res = post_fn(token=token, traceparent=traceparent, ipa_code=ipa_code, request_token=request_token)
        assert_response_ok(res, operation_name)
        res_body = check_res_ok_and_get_body(res.content, response_root)
        status = res_body['stato']

        if status == SilImportStatus.IMPORT_STATUS_COMPLETED:
            return res_body
        assert status != SilImportStatus.IMPORT_STATUS_FAILED, \
            f"{operation_name}: import {request_token} reached unexpected terminal status: {status}"
        assert status in SilImportStatus.IMPORT_STATUS_IN_PROGRESS, \
            f"{operation_name}: unexpected import status: {status}"
        time.sleep(delay)

    assert False, f"{operation_name}: import {request_token} did not complete after {tries} tries (last status: {status})"


def retry_get_import_treasury_status(token, traceparent: str, ipa_code: str, request_token: str, tries=20, delay=4):
    retry_get_sil_import_status(post_sil_chiedi_stato_import_flusso_tesoreria,
                                "SIL chiedi stato import flusso tesoreria",
                                'pivotSILChiediStatoImportFlussoTesoreriaRisposta',
                                token, traceparent, ipa_code, request_token, tries, delay)


def retry_get_import_payment_notification_status(token, traceparent: str, ipa_code: str, request_token: str, tries=20,
                                                 delay=4):
    retry_get_sil_import_status(post_sil_chiedi_stato_import_flusso_notificati,
                                "SIL chiedi stato import notificati",
                                'pivotSILChiediStatoImportFlussoRisposta',
                                token, traceparent, ipa_code, request_token, tries, delay)


def retry_get_import_debt_positions_status(token, traceparent: str, ipa_code: str, request_token: str, tries=20,
                                           delay=4):
    return retry_get_sil_import_status(post_sil_chiedi_stato_import_flusso_posizioni_debitorie,
                                       "SIL chiedi stato import posizioni debitorie",
                                       'paaSILChiediStatoImportFlussoRisposta',
                                       token, traceparent, ipa_code, request_token, tries, delay)


def retry_get_reconciliation_export_status(token, traceparent: str, ipa_code: str, request_token: str, tries=20,
                                           delay=4):
    status = None
    count = 0
    while count < tries:
        count += 1
        res = post_sil_chiedi_stato_export_flusso_riconciliazione(token=token, traceparent=traceparent,
                                                                  ipa_code=ipa_code,
                                                                  request_token=request_token)
        assert_response_ok(res, "SIL chiedi stato export flusso riconciliazione")
        res_body = check_res_ok_and_get_body(res.content, 'pivotSILChiediStatoExportFlussoRiconciliazioneRisposta')
        status = res_body['stato']

        if status == SilExportStatus.EXPORT_STATUS_COMPLETED:
            return
        assert status not in SilExportStatus.EXPORT_STATUS_FAILED and status != SilExportStatus.EXPORT_STATUS_NO_DATA, \
            f"Reconciliation export {request_token} reached unexpected terminal status: {status}"
        assert status in SilExportStatus.EXPORT_STATUS_IN_PROGRESS, f"Unexpected reconciliation export status: {status}"
        time.sleep(delay)

    assert False, f"Reconciliation export {request_token} did not complete after {tries} tries (last status: {status})"


def retry_get_send_campaign_detail(token, traceparent: str, organization_id: int, campaign_id,
                                   counter_name: SendCampaignCounter, expected_value: int, tries=5, delay=4):
    res_campaign_detail = None
    count = 0

    while count < tries:
        count += 1
        res_campaign_detail = get_send_campaign_detail(token=token, traceparent=traceparent,
                                                       organization_id=organization_id, campaign_id=campaign_id)
        counters = res_campaign_detail.json().get('counters')
        if counters is not None and counters.get(counter_name.value) == expected_value:
            return res_campaign_detail

        if count < tries:
            time.sleep(delay)

    return res_campaign_detail
