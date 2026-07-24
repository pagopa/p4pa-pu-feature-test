from datetime import datetime

from behave import then

from api.classifications import get_assessment, get_assessment_details, get_assessment_registry, \
    get_assessment_details_by_iud_and_iuv, get_classification
from api.debt_position_type import get_debt_position_type_org_by_code, get_dpto_balance_cost_by_id
from api.debt_positions import get_installment
from bdd.steps.utils.balance_utility import extract_balance_from_xml, extract_sections, build_section
from bdd.steps.workflow_step import check_workflow_status
from model.classification import Balance, AssessmentRegistry, AssessmentDetailClassificationLabel, Section
from model.debt_position import DebtPositionTypeOrgBalanceCostType
from model.workflow_hub import WorkflowType, WorkflowStatus

default_send_dptobc_code = 'SEND'


@then("the assessment is in status {status}")
@then("the assessment related to debt position {dp_identifier} is in status {status}")
def step_check_assessment(context, status: str, dp_identifier: str = None):
    org_info = context.org_info
    installment_paid = context.installment_paid if dp_identifier is None else context.installment_paid.get(
        dp_identifier)
    context.installment_paid = installment_paid

    res = get_installment(token=context.token, traceparent=context.traceparent,
                          installment_id=installment_paid.installment_id)

    assert res.status_code == 200
    assert res.json()["sourceFlowName"] is not None
    installment_paid.source_flow_name = res.json()["sourceFlowName"]

    res = get_assessment(token=context.token, traceparent=context.traceparent, organization_id=org_info.id,
                         debt_position_type_org_code=context.debt_position_type_org_code,
                         assessment_name=installment_paid.source_flow_name)

    assert res.status_code == 200
    assert res.json()["assessmentId"] is not None
    assert res.json()["status"] == status.upper()

    context.assessment_id = int(res.json()["assessmentId"])

    check_workflow_status(context=context, workflow_type=WorkflowType.CREATE_ASSESSMENT,
                          entity_id=installment_paid.receipt_id, status=WorkflowStatus.COMPLETED)


def check_dp_with_dpto_mixed_not_classified(context, installment_paid):
    res = get_assessment_details_by_iud_and_iuv(token=context.token, traceparent=context.traceparent,
                                                organization_id=context.org_info.id,
                                                iud=installment_paid.iud, iuv=installment_paid.iuv)
    assert res.status_code == 200
    assert len(res.json()["_embedded"]["assessmentsDetails"]) == 0

    date_now = datetime.now().strftime('%Y-%m-%d')
    res = get_classification(token=context.token, traceparent=context.traceparent, organization_id=context.org_info.id,
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
                              entity_id=str(
                                  context.org_info.id) + '-' + installment_paid.iuv + '-' + transfer_mixed.iud,
                              status=WorkflowStatus.COMPLETED)

        res = get_assessment_details_by_iud_and_iuv(token=context.token, traceparent=context.traceparent,
                                                    organization_id=context.org_info.id,
                                                    iud=transfer_mixed.iud, iuv=installment_paid.iuv)

        assert res.status_code == 200
        assessment_details = res.json()["_embedded"]["assessmentsDetails"]

        balance = retrieve_balance(context=context, installment_paid=transfer_mixed,
                                   debt_position_type_org_code=transfer_mixed.debt_position_type_org_code)
        assert len(assessment_details) == len(balance.sections), \
            f"Expected {len(balance.sections)} assessmentDetails (one for each section) for IUD {transfer_mixed.iud}, got {len(assessment_details)}"

        for section in balance.sections:
            assessment_detail = _find_matching_assessment_detail(assessment_details, section)
            assert assessment_detail is not None, \
                f"No assessmentDetail matches {section.assessment_registry} for IUD {transfer_mixed.iud}"

            assert assessment_detail["iur"] == installment_paid.iur
            assert assessment_detail["debtPositionTypeOrgCode"] == transfer_mixed.debt_position_type_org_code
            assert assessment_detail['classificationLabel'] == label


@then("the assessment detail is created correctly based on balance")
@then("the assessment detail is created correctly based on balance including {dptobc_type} section")
def step_check_assessment_detail(context, dptobc_type=None):
    assessment_id = context.assessment_id
    installment_paid = context.installment_paid
    dptobc_type = dptobc_type.upper().replace(" ", "_") if dptobc_type is not None else None

    balance = retrieve_balance(context=context, installment_paid=installment_paid,
                               debt_position_type_org_code=context.debt_position_type_org_code, dptobc_type=dptobc_type)

    check_workflow_status(context=context, workflow_type=WorkflowType.CLASSIFY_ASSESSMENT,
                          entity_id=str(context.org_info.id) + '-' + installment_paid.iuv + '-' + installment_paid.iud,
                          status=WorkflowStatus.COMPLETED)

    res = get_assessment_details(token=context.token, traceparent=context.traceparent,
                                 assessment_id=assessment_id, iud=installment_paid.iud,
                                 iuv=installment_paid.iuv)

    assert res.status_code == 200
    assessment_details = res.json()["_embedded"]["assessmentsDetails"]
    assert len(assessment_details) == len(balance.sections)

    for section in balance.sections:
        assessment_detail = _find_matching_assessment_detail(assessment_details, section)
        assert assessment_detail is not None, f"No assessmentDetail matches {section.assessment_registry}"

        assert installment_paid.iur == assessment_detail["iur"]
        assert assessment_detail['classificationLabel'] == AssessmentDetailClassificationLabel.PAID.value
        assert int(section.amount_cents) == assessment_detail["amountCents"]
        assert (assessment_detail["sectionCode"] is not None and
                section.assessment_registry.section_code == assessment_detail["sectionCode"])
        assert section.assessment_registry.office_code == assessment_detail["officeCode"]
        assert section.assessment_registry.assessment_code == assessment_detail["assessmentCode"]


def _find_matching_assessment_detail(assessment_details, section):
    for detail in assessment_details:
        if (detail.get("sectionCode") == section.assessment_registry.section_code and
                detail.get("officeCode") == section.assessment_registry.office_code and
                detail.get("assessmentCode") == section.assessment_registry.assessment_code):
            return detail
    return None


def retrieve_balance(context, installment_paid, debt_position_type_org_code, dptobc_type=None) -> Balance:
    if installment_paid.balance is not None:
        balance_xml = installment_paid.balance
    else:
        res_dp_type_org = get_debt_position_type_org_by_code(token=context.token, traceparent=context.traceparent,
                                                             organization_id=context.org_info.id,
                                                             code=debt_position_type_org_code)
        assert res_dp_type_org.status_code == 200
        balance_xml = res_dp_type_org.json().get('balance')

    sections = []
    if balance_xml is not None:
        balance_dict = extract_balance_from_xml(balance_xml=balance_xml)
        raw_sections = extract_sections(balance_dict=balance_dict)

        sections.extend(
            build_section(section=raw_section, installment_amount=installment_paid.amount_cents)
            for raw_section in raw_sections
        )
    else:
        res = get_assessment_registry(token=context.token, traceparent=context.traceparent,
                                      organization_id=context.org_info.id,
                                      debt_position_type_org_code=debt_position_type_org_code)
        assert res.status_code == 200
        assert len(res.json()["_embedded"]["assessmentsRegistries"]) == 1
        ass_reg = res.json()["_embedded"]["assessmentsRegistries"][0]

        assessment_registry = AssessmentRegistry(section_code=ass_reg['sectionCode'],
                                                 office_code=ass_reg['officeCode'],
                                                 assessment_code=ass_reg['assessmentCode'])
        sections.append(Section(amount_cents=installment_paid.amount_cents, assessment_registry=assessment_registry))

    if dptobc_type == DebtPositionTypeOrgBalanceCostType.NOTIFICATION_COST.value:
        notification_registry = retrieve_dpto_balance_cost_of_notification(context=context)
        sections.append(Section(amount_cents=context.notification_fee, assessment_registry=notification_registry))

    return Balance(sections=sections)


def retrieve_dpto_balance_cost_of_notification(context) -> AssessmentRegistry:
    year = str(datetime.now().year)
    dpto_id = context.debt_position.debt_position_type_org_id
    dptobc_id = str(dpto_id) + '-' + DebtPositionTypeOrgBalanceCostType.NOTIFICATION_COST.value + '-' + year

    res_dptobc_by_id = get_dpto_balance_cost_by_id(token=context.token, traceparent=context.traceparent,
                                                   dptobc_id=dptobc_id)

    if res_dptobc_by_id.status_code == 404:
        return AssessmentRegistry(section_code=default_send_dptobc_code, office_code=default_send_dptobc_code,
                                  assessment_code=default_send_dptobc_code)
    else:
        assert res_dptobc_by_id.status_code == 200
        dptobc = res_dptobc_by_id.json()
        return AssessmentRegistry(section_code=dptobc.get('sectionCode'), office_code=dptobc.get('officeCode'),
                                  assessment_code=dptobc.get('assessmentCode'))
