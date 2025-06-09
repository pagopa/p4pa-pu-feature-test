import os
import random
import string
import zipfile
from datetime import datetime
from zipfile import ZipFile

from behave import when, then

from api.fileshare import post_upload_file
from bdd.steps.utils.utility import retry_get_process_file_status
from bdd.steps.workflow_step import check_workflow_status
from config.configuration import secrets
from model.file import IngestionFlowFileType, FileOrigin, FilePathName, FileStatus
from model.workflow_hub import WorkflowType, WorkflowStatus

psp_info = secrets.payment_info.psp

def format_ingestion_flow_file(context, amount, file, org_info):
    try:
        iuf = context.iuf
    except AttributeError:
        iuf = 'IUF_NOT_FOUND'

    date = datetime.now().strftime('%Y-%m-%d')
    date_time = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
    year = datetime.now().year
    remittance_description = '/PUR/LGPE-RIVERSAMENTO/URI/' + iuf + ' .PUR.LGPE-RIVERSAMENTO.URI.2025-05- TRXID: ' + ''.join(
        random.choices(string.digits, k=17))

    file = file.format(flow_date_time=date_time,
                       org_code='XX00YY',
                       org_name=org_info.name,
                       org_fiscal_code=org_info.fiscal_code,
                       bt_flow_id='GDC-' + ''.join(
                           random.choices(string.digits, k=36)) + '#001#001',
                       bill_year=year,
                       date=date,
                       flow_account_id=''.join(random.choices(string.digits, k=17)),
                       account_movement_number=''.join(
                           random.choices(string.digits, k=7)),
                       document_code=''.join(random.choices(string.digits, k=7)),
                       actual_suspension_date=date,
                       management_provisional_code=''.join(
                           random.choices(string.digits, k=10)),
                       bill_amount=amount,
                       bill_code=''.join(random.choices(string.digits, k=7)),
                       bill_date=date,
                       region_value_date=date,
                       psp_last_name=psp_info.name,
                       remittance_description=remittance_description,
                       end_to_end_id='RF' + ''.join(random.choices(string.digits, k=24))
                       )

    context.iuf = iuf

    return file


def create_files(context, ingestion_flow_file):
    now = datetime.now().strftime('%Y%m%dT%H%M%S')

    xml_file_path = f'GDC-{now}.xml'
    with open(xml_file_path, 'w') as file:
        file.write(ingestion_flow_file)

    zip_file_path = f'GDC-{now}.zip'
    with ZipFile(zip_file_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        zip_file.write(xml_file_path)

    context.treasury_file_name = zip_file_path

    return xml_file_path, zip_file_path


@when("the organization uploads the treasury file with amount of {amount} euros")
def step_upload_payment_reporting_file_with_amount(context, amount):
    token = context.token
    org_info = context.org_info


    with open('./bdd/steps/file_template/treasury_opi.xml', 'r') as file:
        ingestion_flow_file = file.read()

    ingestion_flow_file = format_ingestion_flow_file(context, amount, ingestion_flow_file, org_info)

    xml_file_path, zip_file_path = create_files(context, ingestion_flow_file)

    res = post_upload_file(token=token, organization_id=org_info.id,
                           ingestion_flow_file_type=IngestionFlowFileType.TREASURY_OPI,
                           file_origin=FileOrigin.PORTAL, file_name=zip_file_path)

    assert res.status_code == 200
    assert res.json()['ingestionFlowFileId'] is not None

    os.remove(zip_file_path)
    os.remove(xml_file_path)

@when("the organization uploads the treasury file with amount of installment {installment_seq_num} of payment option {po_index}")
def step_upload_payment_reporting_file(context, po_index, installment_seq_num):
    token = context.token
    org_info = context.org_info
    amount = int(context.installment_paid.amount_cents / 100)

    with open('./bdd/steps/file_template/treasury_opi.xml', 'r') as file:
        ingestion_flow_file = file.read()

    ingestion_flow_file = format_ingestion_flow_file(context, amount, ingestion_flow_file, org_info)

    xml_file_path, zip_file_path = create_files(context, ingestion_flow_file)

    res = post_upload_file(token=token, organization_id=org_info.id,
                           ingestion_flow_file_type=IngestionFlowFileType.TREASURY_OPI,
                           file_origin=FileOrigin.PORTAL, file_name=zip_file_path)

    assert res.status_code == 200
    assert res.json()['ingestionFlowFileId'] is not None

    os.remove(zip_file_path)
    os.remove(xml_file_path)


@then("the treasury is processed correctly")
def step_check_payment_reporting_processed(context):
    organization_id = context.org_info.id
    installment_paid = context.installment_paid

    file_path_name = FilePathName.TREASURY_OPI
    file_name = context.treasury_file_name

    treasury_file_id = retry_get_process_file_status(token=context.token, organization_id=organization_id,
                                                     file_path_name=file_path_name, file_name=file_name,
                                                     status=FileStatus.COMPLETED)

    check_workflow_status(context=context, workflow_type=WorkflowType.TREASURY_OPI_INGESTION,
                          entity_id=treasury_file_id, status=WorkflowStatus.COMPLETED)

    check_workflow_status(context=context, workflow_type=WorkflowType.TRANSFER_CLASSIFICATION,
                          entity_id=str(organization_id) + '-' + installment_paid.iuv + '-' + installment_paid.iur + '-1',
                          status=WorkflowStatus.COMPLETED)

    check_workflow_status(context=context, workflow_type=WorkflowType.IUF_CLASSIFICATION,
                          entity_id=str(organization_id) + '-' + context.iuf,
                          status=WorkflowStatus.COMPLETED)
