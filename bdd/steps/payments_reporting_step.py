import os
import random
import string
import uuid
import zipfile
from datetime import datetime
from zipfile import ZipFile

from behave import when, then

from api.debt_positions import get_debt_position, get_installment
from api.fileshare import post_upload_file
from bdd.steps.utils.debt_position_utility import find_installment_by_seq_num_and_po_index
from bdd.steps.utils.utility import retry_get_process_file_status
from bdd.steps.workflow_step import check_workflow_status
from config.configuration import secrets
from model.debt_position import DebtPosition
from model.file import IngestionFlowFileType, FileOrigin, FilePathName, FileStatus
from model.workflow_hub import WorkflowType, WorkflowStatus

psp_info = secrets.payment_info.psp


@when("the organization uploads the payment reporting file about installment of payment option {po_index}")
@when("the organization uploads the payment reporting file about installment {seq_num} of payment option {po_index}")
@when("the organization uploads the payment reporting file about installment of payment option {po_index} with outcome code {outcome_code}")
def step_upload_payment_reporting_file(context, po_index, seq_num='1', outcome_code='0'):
    token = context.token
    org_info = context.org_info

    res = get_debt_position(token=token, debt_position_id=context.debt_position.debt_position_id)

    debt_position = DebtPosition.from_dict(res.json())

    installment = find_installment_by_seq_num_and_po_index(debt_position=debt_position,
                                                           po_index=int(po_index), seq_num=int(seq_num))
    installment.iur = installment.iur if int(outcome_code) != 9 else uuid.uuid4().hex

    with open('./bdd/steps/file_template/payment_reporting.xml', 'r') as file:
        ingestion_flow_file = file.read()

    date = datetime.now().strftime('%Y-%m-%d')
    date_time = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
    iuf = date + '-' + psp_info.id + '-' + ''.join(random.choices(string.digits + string.ascii_letters, k=14))
    regulation_unique_identifier = ''.join(random.choices(string.digits, k=20))

    amount = int(installment.amount_cents) / 100

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
                                                     total_amount_cents=amount,
                                                     iuv=installment.iuv,
                                                     iur=installment.iur,
                                                     transfer_index=1,
                                                     amount_paid_cents=amount,
                                                     payment_outcome_code=int(outcome_code),
                                                     payment_date=date)

    xml_file_path = f'{iuf}.xml'
    with open(xml_file_path, 'w') as file:
        file.write(ingestion_flow_file)

    zip_file_path = f'{iuf}.zip'
    with ZipFile(zip_file_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        zip_file.write(xml_file_path)

    res = post_upload_file(token=token, organization_id=org_info.id,
                           ingestion_flow_file_type=IngestionFlowFileType.PAYMENTS_REPORTING,
                           file_origin=FileOrigin.PORTAL, file_name=zip_file_path)

    context.payment_reporting_file_name = zip_file_path
    context.installment_paid = installment

    assert res.status_code == 200
    assert res.json()['ingestionFlowFileId'] is not None

    os.remove(zip_file_path)
    os.remove(xml_file_path)


@then("the payment reporting is processed correctly")
@then("the payment reporting with outcome code 9 is processed correctly")
def step_check_payment_reporting_processed(context):
    installment_paid = context.installment_paid
    organization_id = context.org_info.id

    file_path_name = FilePathName.PAYMENTS_REPORTING
    file_name = context.payment_reporting_file_name

    payment_reporting_file_id = retry_get_process_file_status(token=context.token, organization_id=organization_id,
                                                              file_path_name=file_path_name, file_name=file_name,
                                                              status=FileStatus.COMPLETED)

    check_workflow_status(context=context, workflow_type=WorkflowType.PAYMENTS_REPORTING_INGESTION,
                          entity_id=payment_reporting_file_id, status=WorkflowStatus.COMPLETED)

    check_workflow_status(context=context, workflow_type=WorkflowType.TRANSFER_CLASSIFICATION,
                          entity_id=str(organization_id) + '-' + installment_paid.iuv + '-' + installment_paid.iur + '-1',
                          status=WorkflowStatus.COMPLETED)

    res = get_installment(token=context.token, installment_id=installment_paid.installment_id)

    assert res.status_code == 200
    assert res.json()['iuf'] is not None

    context.iuf = (res.json()['iuf'])
