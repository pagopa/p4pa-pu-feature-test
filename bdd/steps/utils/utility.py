import time

from api.debt_positions import get_debt_position
from api.organization import get_org_by_ipa_code
from api.process_executions import get_by_org_and_file_path_and_file_name
from api.send import get_send_notification
from api.workflow_hub import get_workflow_status
from model.file import FileStatus, FilePathName
from model.workflow_hub import WorkflowType, WorkflowStatus

from secrets import token_hex

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

    assert success

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
        res = get_by_org_and_file_path_and_file_name(token=token, traceparent=traceparent, organization_id=organization_id,
                                                     file_path_name=file_path_name.value, file_name=file_name)
        file = get_latest_file(res) if res.status_code == 200 else None
        success = (res.status_code == 200 and file is not None and file['status'] == status.value)

    assert success
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

    assert res_org.status_code == 200
    organization_id = res_org.json()['organizationId']
    assert organization_id is not None

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

    assert success

def generate_traceparent():
    trace_id = token_hex(16)
    span_id = token_hex(8)
    flags = "01" # means sampled trace

    return f"00-{trace_id}-{span_id}-{flags}"