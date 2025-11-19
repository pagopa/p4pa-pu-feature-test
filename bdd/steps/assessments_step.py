from datetime import datetime

from behave import then

from api.classifications import get_assessment, get_assessment_details, get_assessment_registry, \
    get_assessment_details_by_iud_and_iuv, get_classification
from api.debt_position_type import get_debt_position_type_org_by_code
from api.debt_positions import get_installment
from bdd.steps.utils.balance_utility import extract_assessment_registry_from_balance_dict, \
    calculate_amount_from_balance, extract_balance_from_xml
from bdd.steps.workflow_step import check_workflow_status
from model.classification import Balance, AssessmentRegistry, AssessmentDetailClassificationLabel
from model.workflow_hub import WorkflowType, WorkflowStatus


@then("the assessment is in status {status}")
def step_check_assessment(context, status: str):
    org_info = context.org_info
    installment_paid = context.installment_paid

    res = get_installment(token=context.token, installment_id=installment_paid.installment_id)

    assert res.status_code == 200
    assert res.json()["sourceFlowName"] is not None
    installment_paid.source_flow_name = res.json()["sourceFlowName"]

    res = get_assessment(token=context.token, organization_id=org_info.id,
                         debt_position_type_org_code=context.debt_position_type_org_code,
                         assessment_name=installment_paid.source_flow_name)

    assert res.status_code == 200
    assert res.json()["assessmentId"] is not None
    assert res.json()["status"] == status.upper()

    context.assessment_id = int(res.json()["assessmentId"])

    check_workflow_status(context=context, workflow_type=WorkflowType.CREATE_ASSESSMENT,
                          entity_id=installment_paid.receipt_id, status=WorkflowStatus.COMPLETED)


def check_dp_with_dpto_mixed_not_classified(context, installment_paid):
    res = get_assessment_details_by_iud_and_iuv(token=context.token, organization_id=context.org_info.id,
                                                iud=installment_paid.iud, iuv=installment_paid.iuv)
    assert res.status_code == 200
    assert len(res.json()["_embedded"]["assessmentsDetails"]) == 0

    date_now = datetime.now().strftime('%Y-%m-%d')
    res = get_classification(token=context.token, organization_id=context.org_info.id,
                             last_classification_date_from=date_now, last_classification_date_to=date_now,
                             iuv=installment_paid.iuv, iud=installment_paid.iud)

    assert res.status_code == 200
    assert len(res.json()['content']) == 0


@then("the assessment classification label for each IUD is {label}")
def step_check_assessment_detail_classification_label(context, label):
    installment_paid = context.installment_paid

    check_dp_with_dpto_mixed_not_classified(context=context, installment_paid=installment_paid)

    for transfer_mixed in context.debt_position_mixed.transfers:

        check_workflow_status(context=context, workflow_type=WorkflowType.CLASSIFY_ASSESSMENT,
                              entity_id=str(context.org_info.id) + '-' + installment_paid.iuv + '-' + transfer_mixed.iud,
                              status=WorkflowStatus.COMPLETED)

        res = get_assessment_details_by_iud_and_iuv(token=context.token, organization_id=context.org_info.id,
                                                    iud=transfer_mixed.iud, iuv=installment_paid.iuv)

        assert res.status_code == 200
        assert len(res.json()["_embedded"]["assessmentsDetails"]) == 1
        assessment_detail = res.json()["_embedded"]["assessmentsDetails"][0]

        assert assessment_detail["iur"] == installment_paid.iur
        assert assessment_detail["debtPositionTypeOrgCode"] == transfer_mixed.debt_position_type_org_code
        assert assessment_detail['classificationLabel'] == label


@then("the assessment detail is created correctly")
def step_check_assessment_detail(context):
    assessment_id = context.assessment_id
    installment_paid = context.installment_paid

    balance = retrieve_balance(context=context, installment_paid=installment_paid)

    check_workflow_status(context=context, workflow_type=WorkflowType.CLASSIFY_ASSESSMENT,
                          entity_id=str(context.org_info.id) + '-' + installment_paid.iuv + '-' + installment_paid.iud,
                          status=WorkflowStatus.COMPLETED)

    res = get_assessment_details(context.token, assessment_id=assessment_id, iud=installment_paid.iud,
                                 iuv=installment_paid.iuv)

    assert res.status_code == 200
    assert len(res.json()["_embedded"]["assessmentsDetails"]) == 1
    assessment_detail = res.json()["_embedded"]["assessmentsDetails"][0]

    assert installment_paid.iur == assessment_detail["iur"]
    assert assessment_detail['classificationLabel'] == AssessmentDetailClassificationLabel.PAID.value
    assert int(balance.amount) == assessment_detail["amountCents"]
    assert (assessment_detail["sectionCode"] is not None and
            balance.assessment_registry.section_code == assessment_detail["sectionCode"])
    assert balance.assessment_registry.office_code == assessment_detail["officeCode"]
    assert balance.assessment_registry.assessment_code == assessment_detail["assessmentCode"]


def retrieve_balance(context, installment_paid) -> Balance:
    if installment_paid.balance is not None:
        balance_xml = installment_paid.balance
    else:
        res_dp_type_org = get_debt_position_type_org_by_code(token=context.token, organization_id=context.org_info.id,
                                                             code=context.debt_position_type_org_code)
        assert res_dp_type_org.status_code == 200
        balance_xml = res_dp_type_org.json().get('balance')

    if balance_xml is not None:
        balance_dict = extract_balance_from_xml(balance_xml=balance_xml)
        assessment_registry = extract_assessment_registry_from_balance_dict(balance_dict=balance_dict)
        amount_cents = calculate_amount_from_balance(balance_dict=balance_dict,
                                                     installment_amount=installment_paid.amount_cents)

        balance = Balance(amount=amount_cents, assessment_registry=assessment_registry)
    else:
        res = get_assessment_registry(token=context.token, organization_id=context.org_info.id,
                                      debt_position_type_org_code=context.debt_position_type_org_code)
        assert res.status_code == 200
        assert len(res.json()["_embedded"]["assessmentsRegistries"]) == 1
        ass_reg = res.json()["_embedded"]["assessmentsRegistries"][0]

        assessment_registry = AssessmentRegistry(section_code=ass_reg['sectionCode'],
                                                 office_code=ass_reg['officeCode'],
                                                 assessment_code=ass_reg['assessmentCode'])
        balance = Balance(amount=installment_paid.amount_cents, assessment_registry=assessment_registry)

    return balance
