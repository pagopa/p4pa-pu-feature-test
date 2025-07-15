from behave import then

from api.classifications import get_assessment, get_assessment_details
from api.debt_positions import get_installment
from bdd.steps.workflow_step import check_workflow_status
from config.configuration import settings
from model.workflow_hub import WorkflowType, WorkflowStatus


@then("the assessment is in status {status}")
def step_check_assessment(context, status: str):
    org_info = context.org_info
    installment_paid = context.installment_paid

    res = get_installment(token=context.token, installment_id=installment_paid.installment_id)

    assert res.status_code == 200
    assert res.json()["sourceFlowName"] is not None
    installment_paid.source_flow_name = res.json()["sourceFlowName"]

    res = get_assessment(token=context.token, organization_id=org_info.id, debt_position_type_org_code=settings.debt_position_type_org_code,
                   assessment_name=installment_paid.source_flow_name)

    assert res.status_code == 200
    assert res.json()["assessmentId"] is not None
    assert res.json()["status"] == status.upper()

    context.assessment_id = int(res.json()["assessmentId"])

    check_workflow_status(context=context, workflow_type=WorkflowType.CREATE_ASSESSMENT,
                          entity_id=installment_paid.receipt_id, status=WorkflowStatus.COMPLETED)


@then("the assessment detail is created correctly")
def step_check_assessment_detail(context):
    assessment_id = context.assessment_id
    installment_paid = context.installment_paid

    res = get_assessment_details(context.token, assessment_id=assessment_id, iud=installment_paid.iud, iuv=installment_paid.iuv)

    assert res.status_code == 200
    assert len(res.json()["_embedded"]["assessmentsDetails"]) == 1
    assessment_detail = res.json()["_embedded"]["assessmentsDetails"][0]

    assert installment_paid.iur == assessment_detail["iur"]
    assert installment_paid.amount_cents == assessment_detail["amountCents"]
    assert assessment_detail["sectionCode"] is not None and context.balance_section_code == assessment_detail["sectionCode"]
    assert context.balance_office_code == assessment_detail["officeCode"]
    assert context.balance_assessment_code == assessment_detail["assessmentCode"]

