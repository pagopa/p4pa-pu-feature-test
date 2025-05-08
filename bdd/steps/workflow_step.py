from behave import then

from bdd.steps.utils.utility import get_workflow_id
from bdd.steps.utils.utility import retry_get_workflow_status
from model.workflow_hub import WorkflowType, WorkflowStatus


def check_workflow_status(context, workflow_type: WorkflowType, entity_id: int, status: WorkflowStatus):
    workflow_id = get_workflow_id(workflow_type=workflow_type,
                                  entity_id=entity_id)

    retry_get_workflow_status(token=context.token, workflow_id=workflow_id, status=status.value)


@then("the check of debt position expiration is scheduled")
def step_workflow_check_expiration_scheduled(context):
    check_workflow_status(context=context, workflow_type=WorkflowType.EXPIRATION_DP,
                          entity_id=context.debt_position.debt_position_id, status=WorkflowStatus.RUNNING)
