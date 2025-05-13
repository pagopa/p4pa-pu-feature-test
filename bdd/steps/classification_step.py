from datetime import datetime

from behave import then

from api.classifications import get_classification
from bdd.steps.workflow_step import check_workflow_status
from model.workflow_hub import WorkflowType, WorkflowStatus


@then("the classification is {label}")
def step_check_classification(context, label):
    date_now = datetime.utcnow().strftime('%Y-%m-%d')

    org_info = context.org_info
    installment = context.installment_paid

    if label == 'RT_NO_IUF':
        check_workflow_status(context=context, workflow_type=WorkflowType.IUD_CLASSIFICATION,
                              entity_id=str(org_info.id) + '-' + installment.iud, status=WorkflowStatus.COMPLETED)

        check_workflow_status(context=context, workflow_type=WorkflowType.TRANSFER_CLASSIFICATION,
                              entity_id=str(org_info.id) + '-' + installment.iuv + '-' + installment.iur + '-1',
                              status=WorkflowStatus.COMPLETED)

    res = get_classification(token=context.token, organization_id=org_info.id,
                             last_classification_date_from=date_now, last_classification_date_to=date_now,
                             iuv=installment.iuv, iur=installment.iur)

    assert res.status_code == 200
    assert len(res.json()['content']) != 0

    classification = next(cl for cl in res.json()['content'] if cl['label'] == label)
    assert classification is not None
