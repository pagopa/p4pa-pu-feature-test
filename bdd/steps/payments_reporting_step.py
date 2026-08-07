import os
import random
import string
import uuid
import zipfile
from datetime import datetime
from zipfile import ZipFile

from behave import given, when, then

from api.debt_positions import get_installment
from api.fileshare import post_upload_file
from bdd.steps.debt_positions_step import step_check_dp_status, step_check_debt_position_created
from bdd.steps.payments_step import step_check_receipt_created
from bdd.steps.utils.assertions import assert_response_ok
from bdd.steps.utils.debt_position_utility import find_installment_by_seq_num_and_po_index, find_installment_by_iuv, \
    generate_iuv, get_installment_paid, set_installment_paid, fetch_debt_position, find_mixed_installment
from bdd.steps.utils.utility import retry_get_process_file_status
from bdd.steps.workflow_step import check_workflow_status
from config.configuration import secrets, settings
from model.debt_position import Status, Installment
from model.file import IngestionFlowFileType, FileOrigin, FileStatus, FilePathName, ReceiptOriginType
from model.workflow_hub import WorkflowType, WorkflowStatus

psp_info = secrets.payment_info.psp


def _register_payment_reporting_flow(context, outcome_code, iuf, iur, installment):
    if installment is None:
        return
    context.payment_reporting_flows[str(outcome_code)] = {'iuf': iuf, 'iur': iur, 'installment': installment}


def get_payment_reporting_flow(context, outcome_code):
    flows = getattr(context, 'payment_reporting_flows', {})
    key = str(outcome_code)
    assert key in flows, (
        f"No payment reporting flow registered with outcome code {key}. "
        f"Available flows: {sorted(flows)}"
    )
    return flows[key]


@when("the organization uploads the payment reporting file about installment of payment option {po_index}")
@when("the organization uploads the payment reporting file about installment {seq_num} of payment option {po_index}")
@when(
    "the organization uploads the payment reporting file about installment of payment option {po_index} with outcome code {outcome_code}")
@when("the organization uploads a second payment reporting for the installment with outcome code {outcome_code}")
def step_upload_payment_reporting_file(context, po_index='1', seq_num='1', outcome_code='0', installment=None):
    token = context.token
    org_info = context.org_info

    if installment is None:
        debt_position = fetch_debt_position(context)
        installment = find_installment_by_seq_num_and_po_index(debt_position=debt_position,
                                                               po_index=int(po_index), seq_num=int(seq_num))

    installment.iur = installment.iur if int(outcome_code) != 9 else uuid.uuid4().hex

    date = datetime.now().strftime('%Y-%m-%d')
    date_time = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
    iuf = date + '-' + psp_info.id + '-' + ''.join(random.choices(string.digits + string.ascii_letters, k=14))
    regulation_unique_identifier = ''.join(random.choices(string.digits, k=20))

    amount = "{:.2f}".format(int(installment.amount_cents) / 100)

    with open('./bdd/steps/file_template/data_single_payment.xml', 'r') as file:
        data_single_payment_file = file.read()

    data_payments = ""
    for transfer in installment.transfers:
        data_payments += data_single_payment_file.format(iuv=installment.iuv,
                                                         iur=installment.iur,
                                                         transfer_index=transfer.transfer_index,
                                                         amount_paid="{:.2f}".format(int(transfer.amount_cents) / 100),
                                                         payment_outcome_code=int(outcome_code),
                                                         payment_date=date)

    with open('./bdd/steps/file_template/payment_reporting.xml', 'r') as file:
        ingestion_flow_file = file.read()

    ingestion_flow_file = ingestion_flow_file.format(iuf=iuf,
                                                     flow_date_time=date_time,
                                                     regulation_unique_identifier=regulation_unique_identifier,
                                                     regulation_date=date,
                                                     sender_psp_type='G',
                                                     sender_psp_code=psp_info.id,
                                                     sender_psp_name=psp_info.name,
                                                     receiver_organization_type='G',
                                                     receiver_organization_code=org_info.fiscal_code,
                                                     receiver_organization_name=org_info.name,
                                                     total_payments=1,
                                                     total_amount=amount,
                                                     data_payments=data_payments)

    file_version = settings.ingestion_flow_file.base_version
    xml_file_path = f'{iuf}_{file_version}.xml'
    with open(xml_file_path, 'w') as file:
        file.write(ingestion_flow_file)

    zip_file_path = f'{iuf}_{file_version}.zip'
    with ZipFile(zip_file_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        zip_file.write(xml_file_path)

    res = post_upload_file(token=token, traceparent=context.traceparent, organization_id=org_info.id,
                           ingestion_flow_file_type=IngestionFlowFileType.PAYMENTS_REPORTING,
                           file_origin=FileOrigin.PORTAL, file_name=zip_file_path)

    assert_response_ok(res, "Upload payment reporting file")
    assert res.json()['ingestionFlowFileId'] is not None

    context.payment_reporting_file_id = res.json()['ingestionFlowFileId']
    context.payment_reporting_file_name = zip_file_path
    set_installment_paid(context, installment)
    context.iuv = installment.iuv
    context.iur = installment.iur

    _register_payment_reporting_flow(context, outcome_code, iuf, installment.iur, installment)

    os.remove(zip_file_path)
    os.remove(xml_file_path)


@when("the organization uploads the payment reporting file about mixed installment")
def step_upload_payment_reporting_for_mixed_dp(context):
    debt_position = fetch_debt_position(context)
    installment = find_mixed_installment(debt_position=debt_position)
    step_upload_payment_reporting_file(context=context, installment=installment)


@when(
    "the organization uploads the payment reporting file with outcome code {outcome_code} about a debt position created outside PU")
def step_upload_payment_reporting_file_no_debt_position(context, outcome_code='9', installment: Installment = None):
    token = context.token
    org_info = context.org_info

    with open('./bdd/steps/file_template/payment_reporting.xml', 'r') as file:
        ingestion_flow_file = file.read()

    date = datetime.now().strftime('%Y-%m-%d')
    date_time = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
    iuf = date + '-' + psp_info.id + '-' + ''.join(random.choices(string.digits + string.ascii_letters, k=14))
    regulation_unique_identifier = ''.join(random.choices(string.digits, k=20))
    amount = "{:.2f}".format(random.randint(1, 200)) if installment is None else "{:.2f}".format(int(installment.amount_cents) / 100)
    iuv = generate_iuv() if installment is None else installment.iuv
    iur = uuid.uuid4().hex

    with open('./bdd/steps/file_template/data_single_payment.xml', 'r') as file:
        data_single_payment_file = file.read()
        data_single_payment = data_single_payment_file.format(iuv=iuv,
                                                              iur=iur,
                                                              transfer_index=1,
                                                              amount_paid=amount,
                                                              payment_outcome_code=int(outcome_code),
                                                              payment_date=date)

    data_payments = data_single_payment

    ingestion_flow_file = ingestion_flow_file.format(iuf=iuf,
                                                     flow_date_time=date_time,
                                                     regulation_unique_identifier=regulation_unique_identifier,
                                                     regulation_date=date,
                                                     sender_psp_type='G',
                                                     sender_psp_code=psp_info.id,
                                                     sender_psp_name=psp_info.name,
                                                     receiver_organization_type='G',
                                                     receiver_organization_code=org_info.fiscal_code,
                                                     receiver_organization_name=org_info.name,
                                                     total_payments=1,
                                                     total_amount=amount,
                                                     data_payments=data_payments)

    file_version = settings.ingestion_flow_file.base_version
    xml_file_path = f'{iuf}_{file_version}.xml'
    with open(xml_file_path, 'w') as file:
        file.write(ingestion_flow_file)

    zip_file_path = f'{iuf}_{file_version}.zip'
    with ZipFile(zip_file_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        zip_file.write(xml_file_path)

    res = post_upload_file(token=token, traceparent=context.traceparent, organization_id=context.org_info.id,
                           ingestion_flow_file_type=IngestionFlowFileType.PAYMENTS_REPORTING,
                           file_origin=FileOrigin.PORTAL, file_name=zip_file_path)

    assert_response_ok(res, "Upload payment reporting file")
    assert res.json()['ingestionFlowFileId'] is not None

    context.payment_reporting_file_id = res.json()['ingestionFlowFileId']
    context.payment_reporting_file_name = zip_file_path
    context.iuv = iuv
    context.iur = iur

    _register_payment_reporting_flow(context, outcome_code, iuf, iur, installment)

    os.remove(zip_file_path)
    os.remove(xml_file_path)


@then("the payment reporting is processed correctly")
def step_check_payment_reporting_processed(context):
    """Checks that the payment reporting file was processed correctly. It verifies that:

    - the file reaches status `COMPLETED`;
    - the `PAYMENTS_REPORTING_INGESTION` workflow completes;
    - the `TRANSFER_CLASSIFICATION` workflow completes for each transfer;
    - the installment now has its `IUF` set.
    """
    installment_paid = get_installment_paid(context)
    organization_id = context.org_info.id

    file_path_name = FilePathName.PAYMENTS_REPORTING
    file_name = context.payment_reporting_file_name

    retry_get_process_file_status(token=context.token, traceparent=context.traceparent, organization_id=organization_id,
                                  file_path_name=file_path_name, file_name=file_name,
                                  status=FileStatus.COMPLETED)

    check_workflow_status(context=context, workflow_type=WorkflowType.PAYMENTS_REPORTING_INGESTION,
                          entity_id=context.payment_reporting_file_id, status=WorkflowStatus.COMPLETED)

    for transfer in installment_paid.transfers:
        check_workflow_status(context=context, workflow_type=WorkflowType.TRANSFER_CLASSIFICATION,
                              entity_id=str(organization_id) + '-' + installment_paid.iuv + '-' +
                                        installment_paid.iur + '-' + str(transfer.transfer_index),
                              status=WorkflowStatus.COMPLETED)

    res = get_installment(token=context.token, traceparent=context.traceparent, installment_id=installment_paid.installment_id)

    assert_response_ok(res, "Get installment by id")
    assert res.json()['iuf'] is not None
    installment_paid.iuf = res.json()['iuf']


@then("the payment reporting with outcome code 9 is processed correctly")
def step_check_payment_reporting_outcome9_processed(context):
    """Checks that a payment reporting with outcome code 9 was processed correctly. It verifies that:

    - the file reaches status `COMPLETED`;
    - the `PAYMENTS_REPORTING_INGESTION` workflow completes;
    - the `TRANSFER_CLASSIFICATION` workflow completes.
    """
    organization_id = context.org_info.id

    file_path_name = FilePathName.PAYMENTS_REPORTING
    file_name = context.payment_reporting_file_name

    retry_get_process_file_status(token=context.token, traceparent=context.traceparent, organization_id=organization_id,
                                  file_path_name=file_path_name, file_name=file_name,
                                  status=FileStatus.COMPLETED)

    check_workflow_status(context=context, workflow_type=WorkflowType.PAYMENTS_REPORTING_INGESTION,
                          entity_id=context.payment_reporting_file_id, status=WorkflowStatus.COMPLETED)

    check_workflow_status(context=context, workflow_type=WorkflowType.TRANSFER_CLASSIFICATION,
                          entity_id=str(organization_id) + '-' + context.iuv + '-' + context.iur + '-1',
                          status=WorkflowStatus.COMPLETED)


@given("a payment reporting with outcome code {outcome_code} has been successfully processed for the installment")
def step_successful_payment_reporting_uploading(context, outcome_code='0'):
    """Uploads a payment reporting and checks it is processed:

    - uploads the file;
    - checks the debt position becomes `REPORTED`;
    - checks processing and (for outcome 9) that the receipt is created."""
    step_upload_payment_reporting_file(context=context, outcome_code=outcome_code)
    step_check_dp_status(context=context, status=Status.REPORTED.value)
    step_check_payment_reporting_processed(context=context)
    if int(outcome_code) == 9:
        step_check_receipt_created(context=context, installment_paid=get_installment_paid(context))


@given("a payment reporting with outcome code 9 has been successfully processed for the installment created outside PU")
def step_successful_payment_reporting_uploading_outside_pu(context):
    """Uploads a payment reporting for an installment created outside PU and checks it is processed:

    - uploads the file;
    - checks the debt position becomes `REPORTED`;
    - checks processing and that the debt position is created in PU with origin `REPORTING_PAGOPA`."""
    installment = context.debt_position.payment_options[0].installments[0]
    step_upload_payment_reporting_file_no_debt_position(context=context, outcome_code='9', installment=installment)
    step_check_payment_reporting_outcome9_processed(context=context)
    step_check_debt_position_created(context=context)


@when("the organization uploads a second payment reporting for the installment created outside PU with outcome code {outcome_code}")
def step_upload_payment_reporting_file_outside_pu(context, outcome_code='0'):
    debt_position = fetch_debt_position(context)
    installment = find_installment_by_iuv(debt_position=debt_position, iuv=context.iuv)
    step_upload_payment_reporting_file(context=context, outcome_code=outcome_code, installment=installment)


@then("the duplicate receipt for the payment reporting with outcome code {outcome_code} is created correctly with origin {receipt_origin}")
def step_check_duplicate_receipt_created_for_flow(context, outcome_code,
                                                  receipt_origin: str = ReceiptOriginType.PAYMENTS_REPORTING.value):
    """Checks that the duplicate receipt for the given payment reporting flow (by outcome code) is created with the expected origin."""
    flow = get_payment_reporting_flow(context, outcome_code)
    step_check_receipt_created(context=context, receipt_origin=receipt_origin,
                               installment_paid=flow['installment'], is_duplicate=True)
