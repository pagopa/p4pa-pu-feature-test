import time

from api.workflow_hub import get_workflow_status
from model.workflow_hub import WorkflowType, WorkflowStatus


def get_workflow_id(workflow_type: WorkflowType, entity_id: int) -> str:
    print(workflow_type.value + "-" + str(entity_id))
    return workflow_type.value + "-" + str(entity_id)


def retry_get_workflow_status(token, workflow_id, status, tries=15, delay=3):
    count = 0

    res = get_workflow_status(token=token, workflow_id=workflow_id)

    success = (res.status_code == 200 and res.json()['status'] == status)

    while not success:
        count += 1
        if count == tries:
            break
        time.sleep(delay)
        res = get_workflow_status(token=token, workflow_id=workflow_id)
        success = (res.status_code == 200 and res.json()['status'] == status)

    assert success
