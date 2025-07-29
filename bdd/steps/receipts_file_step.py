import os
import random
import uuid
from datetime import datetime, timedelta

import pandas
from behave import given, when, then

from api.fileshare import post_upload_file
from bdd.steps.utils.debt_position_utility import generate_iuv
from bdd.steps.utils.utility import retry_get_process_file_status, retrieve_org_id_by_ipa_code
from bdd.steps.workflow_step import check_workflow_status
from config.configuration import secrets, settings
from model.csv_file_receipts import CSVRow, EntityIdType, PersonEntityType, to_csv_lines, CSVVersion
from model.file import IngestionFlowFileType, FileOrigin, FilePathName, FileStatus
from model.workflow_hub import WorkflowStatus, WorkflowType


@given("receipts of non-existent debt positions inserted into an ingestion flow file with version {csv_version}")
def step_create_ingestion_flow_file(context, csv_version: str):
    csv_version = CSVVersion(csv_version)
    context.csv_version = csv_version

    csv_rows = create_receipts_rows(context)
    context.receipts_rows_len = len(csv_rows)

    csv_lines = to_csv_lines(csv_rows=csv_rows, csv_version=csv_version)

    dataset_dataframe = pandas.DataFrame(data=csv_lines)

    filename = f'FeatureTestImportPagati_{csv_version.value}_{datetime.now().strftime("%Y%m%d%H%M%S")}'
    zip_file_path = f'{filename}.zip'
    dataset_dataframe.to_csv(zip_file_path, index=False, header=False,
                             compression=dict(method='zip', archive_name=f'{filename}.csv'))

    context.receipts_file_name = zip_file_path


@when("the organization uploads the receipts file")
def step_uploads_debt_positions_file(context):
    token = context.token

    organization_id = retrieve_org_id_by_ipa_code(token=token, ipa_code=context.org_info.ipa_code)
    context.org_info['id'] = organization_id

    zip_file_path = context.receipts_file_name

    res = post_upload_file(token=token, organization_id=organization_id,
                           ingestion_flow_file_type=IngestionFlowFileType.RECEIPT,
                           file_origin=FileOrigin.PORTAL, file_name=zip_file_path)

    assert res.status_code == 200
    assert res.json()['ingestionFlowFileId'] is not None

    context.receipts_file_id = res.json()['ingestionFlowFileId']

    os.remove(zip_file_path)


@then("the receipts file is processed correctly")
def step_receipts_file_processed(context):
    organization_id = context.org_info.id

    file_path_name = FilePathName.RECEIPT
    file_name = context.receipts_file_name

    res = retry_get_process_file_status(token=context.token, organization_id=organization_id,
                                        file_path_name=file_path_name, file_name=file_name,
                                        status=FileStatus.COMPLETED, delay=10)

    assert res['numTotalRows'] == context.receipts_rows_len
    assert res['numTotalRows'] == res['numCorrectlyImportedRows']

    check_workflow_status(context=context, workflow_type=WorkflowType.RECEIPT_INGESTION_FLOW,
                          entity_id=context.receipts_file_id, status=WorkflowStatus.COMPLETED)


def create_receipts_rows(context, receipts_size: int = 3, debt_position=None) -> list:
    csv_version = context.csv_version
    date_time = (datetime.now() - timedelta(days=1))
    context.iuvs = []

    org_info = context.org_info
    receipts_rows = []

    for i in range(receipts_size):
        iud = f'FeatureTest_{i + 1}_{date_time.strftime("%Y%m%d%H%M%S%f")[:15]}_{uuid.uuid4().hex[:5]}' if debt_position is None else "dp"  # TODO P4ADEV-3349 with DP
        amount = "{:.2f}".format(
            random.randint(1, 200)) if debt_position is None else "100.00"  # TODO P4ADEV-3349 with DP
        iuv = generate_iuv()
        context.iuvs.append(iuv)

        row = CSVRow()
        row.sourceFlowName = "FeatureTestImportReceipts"
        row.flowRowNumber = 1
        row.iud = iud
        row.noticeNumber = iuv if debt_position is None else "iuv"  # TODO P4ADEV-3349 with DP
        row.objectVersion = csv_version.object_version
        row.orgFiscalCode = org_info.fiscal_code
        row.requestingStationId = "12345"
        row.paymentReceiptId = str(random.randint(5000, 10000))
        row.paymentDateTime = date_time.isoformat(timespec="seconds")
        row.requestMessageReference = "requestMessageReference"
        row.requestDateReference = date_time.date().isoformat()
        row.uniqueIdType = "B"
        row.idPsp = secrets.payment_info.psp['id']
        row.pspCompanyName = secrets.payment_info.psp['name']
        row.certifierOperationalUnitCode = "certifierOperationalUnitCode"
        row.certifierOperationalUnitName = "certifierOperationalUnitName"
        row.certifierAddress = "Via del Corso"
        row.certifierCivicNumber = "1"
        row.certifierPostalCode = "00186"
        row.certifierLocation = "Roma"
        row.certifierProvince = "RM"
        row.certifierNation = "IT"
        row.beneficiaryEntityIdType = EntityIdType.G.value
        row.beneficiaryEntityIdCode = org_info.fiscal_code
        row.beneficiaryCompanyName = org_info.name
        row.beneficiaryOperationalUnitCode = "beneficiaryOperationalUnitCode"
        row.beneficiaryOperationalUnitName = "beneficiaryOperationalUnitName"
        row.beneficiaryAddress = "Via dei Gerolami"
        row.beneficiaryCivic = "110"
        row.beneficiaryPostalCode = "00102"
        row.beneficiaryCity = "Milano"
        row.beneficiaryProvince = "MI"
        row.beneficiaryNation = "IT"
        row.payerEntityType = PersonEntityType.F.value
        row.payerFiscalCode = secrets.citizen_info['fiscal_code']
        row.payerFullName = secrets.citizen_info['name']
        row.payerAddress = "Via del Test"
        row.payerCivic = "1"
        row.payerPostalCode = "00100"
        row.payerLocation = "Roma"
        row.payerProvince = "RM"
        row.payerNation = "IT"
        row.payerEmail = secrets.citizen_info['email']
        row.debtorEntityType = PersonEntityType.F.value
        row.debtorFiscalCode = secrets.citizen_info['fiscal_code']
        row.debtorFullName = secrets.citizen_info['name']
        row.debtorAddress = "Via del Test"
        row.debtorCivic = "1"
        row.debtorPostalCode = "00100"
        row.debtorLocation = "Roma"
        row.debtorProvince = "RM"
        row.debtorNation = "IT"
        row.debtorEmail = secrets.citizen_info['email']
        row.outcome = "0"
        row.paymentAmountCents = amount
        row.creditorReferenceId = iuv
        row.paymentContextCode = "paymentContextCode"
        row.singlePaymentAmount = amount
        row.singlePaymentOutcome = "0"
        row.singlePaymentOutcomeDate = date_time.date().isoformat()
        row.uniqueCollectionId = "TRN"
        row.remittanceInformation = "Feature Test Import Receipts File"
        row.paymentNote = "0301109AP/"
        row.debtPositionTypeOrgCode = settings.debt_position_type_org_code
        row.signatureType = "0"
        row.rt = "RT"
        row.idTransfer = 1
        row.feeCents = "1"
        row.receiptAttachmentTypeCode = "100"
        row.mbdAttachment = "<xml></xml>"
        row.balance = "<xml></xml>"
        row.fiscalCodePA = org_info.fiscal_code
        row.companyName = org_info.name
        row.transferCategory = "9/0301109AP/"

        receipts_rows.append(row)

    return receipts_rows
