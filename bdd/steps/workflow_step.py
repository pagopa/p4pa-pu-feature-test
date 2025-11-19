from behave import then

from api.workflow_hub import get_workflow_status
from bdd.steps.utils.utility import get_workflow_id
from bdd.steps.utils.utility import retry_get_workflow_status
from model.workflow_hub import WorkflowType, WorkflowStatus


def check_workflow_status(context, workflow_type: WorkflowType, entity_id: int, status: WorkflowStatus):
    workflow_id = get_workflow_id(workflow_type=workflow_type,
                                  entity_id=entity_id)

    retry_get_workflow_status(token=context.token, workflow_id=workflow_id, status=status)


@then("the check of debt position expiration is {status}")
@then("the check of mixed debt position expiration is {status}")
def step_debt_position_workflow_check_expiration(context, status):
    debt_position = context.debt_position

    workflow_status = WorkflowStatus[status.upper()] if status != 'scheduled' else WorkflowStatus.RUNNING

    check_workflow_status(context=context, workflow_type=WorkflowType.EXPIRATION_DP,
                          entity_id=debt_position.debt_position_id, status=workflow_status)


@then("the checks of debt positions expiration are {status}")
def step_debt_positions_workflow_check_expiration(context, status):
    debt_positions = context.debt_positions_created

    workflow_status = WorkflowStatus[status.upper()] if status != 'scheduled' else WorkflowStatus.RUNNING

    for debt_position in debt_positions:
        check_workflow_status(context=context, workflow_type=WorkflowType.EXPIRATION_DP,
                              entity_id=debt_position.debt_position_id, status=workflow_status)


def check_workflow_does_not_exist(context, workflow_type: WorkflowType, entity_id: int):
    workflow_id = get_workflow_id(workflow_type=workflow_type,
                                  entity_id=entity_id)

    res = get_workflow_status(token=context.token, workflow_id=workflow_id)
    assert res.status_code == 404