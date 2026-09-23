import time
import xml.etree.ElementTree as ET
from secrets import token_hex
from typing import Optional

import xmltodict

from api.debt_positions import get_debt_position
from api.organization import get_org_by_ipa_code
from api.process_executions import get_by_org_and_file_path_and_file_name
from api.send import get_send_notification
from api.soap.sil import post_sil_chiedi_stato_export_flusso
from api.workflow_hub import get_workflow_status
from bdd.steps.utils.assertions import assert_response_ok
from model.file import FileStatus, FilePathName
from model.workflow_hub import WorkflowType, WorkflowStatus

EXPORT_STATUS_COMPLETED = 'EXPORT_ESEGUITO'
EXPORT_STATUS_NO_DATA = 'EXPORT_ESEGUITO_NESSUN_DOVUTO_TROVATO'
EXPORT_STATUS_IN_PROGRESS = ('LOAD_EXPORT', 'EXPORT_IN_ELAB')
EXPORT_STATUS_FAILED = ('ERROR_EXPORT', 'EXPORT_CANCELLATO')


def get_workflow_id(workflow_type: WorkflowType, entity_id: int) -> str:
    return workflow_type.value + "-" + str(entity_id)


def retry_get_workflow_status(token, traceparent: str, workflow_id: str, status: WorkflowStatus, tries=20, delay=4):
    count = 0

    res = get_workflow_status(token=token, traceparent=traceparent, workflow_id=workflow_id)

    success = (res.status_code == 200 and res.json()['status'] == status.value)

    while not success:
        count += 1
        if count == tries:
            break
        time.sleep(delay)
        res = get_workflow_status(token=token, traceparent=traceparent, workflow_id=workflow_id)
        success = (res.status_code == 200 and res.json()['status'] == status.value)

    assert success, \
        f"\nWorkflow {workflow_id} did not reach status {status.value} after {tries} tries: " \
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


def retry_get_valid_send_notification(token, traceparent: str, notification_id, tries=20, delay=4):
    count = 0

    res = get_send_notification(token=token, traceparent=traceparent, notification_id=notification_id)

    success = (res.status_code == 200 and res.json().get('iun') is not None)

    while not success:
        count += 1
        if count == tries:
            break
        time.sleep(delay)
        res = get_send_notification(token=token, traceparent=traceparent, notification_id=notification_id)
        success = (res.status_code == 200 and res.json().get('iun') is not None)

    return res


def retrieve_org_id_by_ipa_code(token: str, traceparent: str, ipa_code: str) -> int:
    res_org = get_org_by_ipa_code(token=token, traceparent=traceparent, ipa_code=ipa_code)

    assert_response_ok(res_org, "Get organization by IPA code")
    organization_id = res_org.json()['organizationId']
    assert organization_id is not None, \
        f"\nNo organization found with IPA code {ipa_code}\n"

    return organization_id


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


def generate_traceparent():
    trace_id = token_hex(16)
    span_id = token_hex(8)
    flags = "01"  # means sampled trace

    return f"00-{trace_id}-{span_id}-{flags}"


def check_res_ok_and_get_body(response_content, tag_name):
    res_parsed = xmltodict.parse(response_content.decode('utf-8'))
    res_body = res_parsed['SOAP-ENV:Envelope']['SOAP-ENV:Body'][f'ns3:{tag_name}']
    assert res_body.get(
        'fault') is None, f"SIL {tag_name} returned a fault: {res_body.get('fault')}"
    return res_body


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

        if status == EXPORT_STATUS_COMPLETED:
            return
        assert status not in EXPORT_STATUS_FAILED and status != EXPORT_STATUS_NO_DATA, \
            f"Export {request_token} reached unexpected terminal status: {status}"
        assert status in EXPORT_STATUS_IN_PROGRESS, f"Unexpected export status: {status}"
        time.sleep(delay)

    assert False, f"Export {request_token} did not complete after {tries} tries (last status: {status})"


def xml_elements_equal(
        xml_a: str,
        xml_b: str,
        xpath_a: Optional[str] = None,
        xpath_b: Optional[str] = None,
) -> bool:
    """
    Compare the children of two XML elements, ignoring the root tag name.

    xpath_a / xpath_b: optional ElementTree find() path to locate the element
    to compare within each document. If omitted, the document root is used.
    Namespace-agnostic matching is supported via '{*}' wildcards in the path.
    """
    element_a = _resolve_element(xml_a, xpath_a)
    element_b = _resolve_element(xml_b, xpath_b)

    children_a = sorted(element_a, key=lambda e: _local_name(e.tag))
    children_b = sorted(element_b, key=lambda e: _local_name(e.tag))

    canon_a = [ET.canonicalize(ET.tostring(c, encoding='unicode')) for c in children_a]
    canon_b = [ET.canonicalize(ET.tostring(c, encoding='unicode')) for c in children_b]

    return canon_a == canon_b


def _resolve_element(xml_str: str, xpath: Optional[str]) -> ET.Element:
    root = ET.fromstring(xml_str)
    if xpath is None:
        return root

    element = root.find(xpath)
    assert element is not None, f"Element not found for xpath '{xpath}'"
    return element


def _local_name(tag: str) -> str:
    return tag.split('}')[-1]
