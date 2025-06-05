import time

from api.process_executions import get_by_org_and_file_path_and_file_name
from api.send import get_send_notification_status
from api.workflow_hub import get_workflow_status
from model.file import FileStatus, FilePathName
from model.workflow_hub import WorkflowType, WorkflowStatus


def get_workflow_id(workflow_type: WorkflowType, entity_id: int) -> str:
    return workflow_type.value + "-" + str(entity_id)


def retry_get_workflow_status(token, workflow_id: str, status: WorkflowStatus, tries=15, delay=3):
    count = 0

    res = get_workflow_status(token=token, workflow_id=workflow_id)

    success = (res.status_code == 200 and res.json()['status'] == status.value)

    while not success:
        count += 1
        if count == tries:
            break
        time.sleep(delay)
        res = get_workflow_status(token=token, workflow_id=workflow_id)
        success = (res.status_code == 200 and res.json()['status'] == status.value)

    assert success


def retry_get_process_file_status(token, organization_id: int, file_path_name: FilePathName,
                                  file_name: str, status: FileStatus, tries=15, delay=3) -> int:
    count = 0

    res = get_by_org_and_file_path_and_file_name(token=token, organization_id=organization_id,
                                                 file_path_name=file_path_name.value, file_name=file_name)

    success = (res.status_code == 200 and res.json()['status'] == status.value)

    while not success:
        count += 1
        if count == tries:
            break
        time.sleep(delay)
        res = get_by_org_and_file_path_and_file_name(token=token, organization_id=organization_id,
                                                     file_path_name=file_path_name.value, file_name=file_name)
        success = (res.status_code == 200 and res.json()['status'] == status.value)

    assert success
    return res.json()['ingestionFlowFileId']


def retry_get_status_send_notification(token, notification_id, status, tries=15, delay=3):
    count = 0

    res = get_send_notification_status(token=token, notification_id=notification_id)

    success = (res.status_code == 200 and status in res.json())

    while not success:
        count += 1
        if count == tries:
            break
        time.sleep(delay)
        res = get_send_notification_status(token=token, notification_id=notification_id)
        print(res.json())
        success = (res.status_code == 200 and status in res.json())

    assert success
