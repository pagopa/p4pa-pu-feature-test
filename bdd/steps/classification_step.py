from behave import then

from bdd.steps.workflow_step import check_workflow_status
from model.workflow_hub import WorkflowType, WorkflowStatus


@then("the classification is {label}")
def step_check_classification(context, label):
    org_info = context.org_info

    if label == 'RT_NO_IUF':
        installment = context.installment_paid

        check_workflow_status(context=context, workflow_type=WorkflowType.IUD_CLASSIFICATION,
                              entity_id=str(org_info.id) + '-' + installment.iud, status=WorkflowStatus.COMPLETED)

        check_workflow_status(context=context, workflow_type=WorkflowType.TRANSFER_CLASSIFICATION,
                              entity_id=str(org_info.id) + '-' + installment.iuv + '-' + installment.iur + '-1',
                              status=WorkflowStatus.COMPLETED)
        #TODO check classification label
