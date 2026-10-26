import copy
import os
import random
import string
import uuid
from api.debt_positions import get_receipt, get_receipt_by_id, get_debt_position_by_organization_id_and_installment_nav, \
    get_installment, get_receipt_by_iur
from api.fileshare import post_upload_file
from bdd.steps.assessments_step import step_check_assessment, step_check_assessment_detail
from bdd.steps.debt_positions_step import step_check_dp_status, step_check_debt_positions_created, \
    step_check_installment_status
from bdd.steps.payments_step import step_check_receipt_created
from bdd.steps.utils.assertions import assert_response_ok
from bdd.steps.utils.balance_utility import build_balance_xml, extract_balance_from_xml
from bdd.steps.utils.csv_utils import to_csv_lines, write_csv_zip
from bdd.steps.utils.debt_position_utility import generate_iuv, set_installment_paid, FEATURE_TEST_IUD_PREFIX, \
    get_installment_paid, fetch_debt_position
from bdd.steps.utils.utility import retry_get_process_file_status, get_workflow_run_id
from bdd.steps.workflow_step import check_workflow_status
from behave import given, when, then
from config.configuration import secrets, settings
from datetime import datetime, timedelta
from model.classification import AssessmentRegistry, Section
from model.csv_file_receipts import CSVRow, EntityIdType, PersonEntityType, CSVVersion
from model.debt_position import DebtPosition, DebtPositionOrigin, Status, NAV_PREFIX
from model.file import IngestionFlowFileType, FileOrigin, FilePathName, FileStatus, ReceiptOriginType
from model.workflow_hub import WorkflowStatus, WorkflowType


@given("receipts of non-existent debt positions inserted into an ingestion flow file with version {csv_version}")
def step_create_receipts_file_for_non_existent_dp(context, csv_version: str):
    csv_version = CSVVersion(csv_version)
    context.csv_version = csv_version

    csv_rows = create_receipts_rows(context)

    _write_receipts_file(context, csv_rows)

def _write_receipts_file(context, csv_rows: list):
      csv_version = context.csv_version
      csv_lines = to_csv_lines(csv_rows=csv_rows, csv_version=csv_version)
      filename = f'FeatureTestImportPagati_{datetime.now().strftime("%Y%m%d%H%M%S")}-{csv_version.value}'

      context.receipts_rows = csv_rows
      context.receipts_rows_len = len(csv_rows)
      context.receipts_file_name = write_csv_zip(csv_lines=csv_lines, filename=filename)



@given("a receipt of a debt position inserted into an ingestion flow file with version {csv_version}")
def step_create_receipts_file_for_existing_dp(context, csv_version: str):
    csv_version = CSVVersion(csv_version)
    context.csv_version = csv_version

    csv_rows = create_receipts_rows(context, receipts_size=1, debt_position=context.debt_position)

    _write_receipts_file(context, csv_rows)
    set_installment_paid(context, context.debt_position.first_installment)


@when("the organization uploads the receipts file")
def step_uploads_receipts_file(context):
    zip_file_path = context.receipts_file_name

    res = post_upload_file(token=context.token, traceparent=context.traceparent, organization_id=context.org_info.id,
                           ingestion_flow_file_type=IngestionFlowFileType.RECEIPT,
                           file_origin=FileOrigin.PORTAL, file_name=zip_file_path)

    assert_response_ok(res, "Upload receipts file")
    assert res.json()['ingestionFlowFileId'] is not None

    context.receipts_file_id = res.json()['ingestionFlowFileId']

    os.remove(zip_file_path)


@then("the receipts file is processed correctly")
def step_receipts_file_processed(context):
    """Checks that the receipts file was processed correctly. It verifies that:

    - the file reaches status `COMPLETED`;
    - the number of imported rows equals the rows sent and all were imported successfully;
    - the `RECEIPT_INGESTION_FLOW` workflow completes.
    """
    file_path_name = FilePathName.RECEIPT
    file_name = context.receipts_file_name

    res = retry_get_process_file_status(token=context.token, traceparent=context.traceparent, organization_id=context.org_info.id,
                                        file_path_name=file_path_name, file_name=file_name,
                                        status=FileStatus.COMPLETED, delay=10)

    assert res['numTotalRows'] == context.receipts_rows_len
    assert res['numTotalRows'] == res['numCorrectlyImportedRows']

    check_workflow_status(context=context, workflow_type=WorkflowType.RECEIPT_INGESTION_FLOW,
                          entity_id=context.receipts_file_id, status=WorkflowStatus.COMPLETED)


def create_receipts_rows(context, receipts_size: int = 3, debt_position: DebtPosition = None) -> list:
    csv_version = context.csv_version
    date_time = (datetime.now() - timedelta(days=1))
    context.iuvs = []
    context.debt_position_type_org_code = settings.debt_position_type_org_code.feature_test

    org_info = context.org_info
    receipts_rows = []

    for i in range(receipts_size):
        iud = f'{FEATURE_TEST_IUD_PREFIX}{i + 1}_{date_time.strftime("%Y%m%d%H%M%S%f")[:15]}_{uuid.uuid4().hex[:5]}' if debt_position is None else debt_position.first_installment.iud
        amount = "{:.2f}".format(
            random.randint(1, 200)) if debt_position is None else (float(debt_position.first_installment.amount_cents) / 100)
        iuv = generate_iuv() if debt_position is None else debt_position.first_installment.iuv
        context.iuvs.append(iuv)

        row = CSVRow()
        row.sourceFlowName = "FeatureTestImportReceipts"
        row.flowRowNumber = 1
        row.iud = iud
        row.noticeNumber = iuv
        row.objectVersion = csv_version.object_version
        row.orgFiscalCode = org_info.fiscal_code
        row.requestingStationId = "12345"
        row.paymentReceiptId = ''.join(random.choices(string.digits + string.ascii_letters, k=32))
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
        row.beneficiaryEntityIdType = EntityIdType.G
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
        row.payerEntityType = PersonEntityType.F
        row.payerFiscalCode = secrets.citizen_info.X.fiscal_code
        row.payerFullName = secrets.citizen_info.X.name
        row.payerAddress = "Via del Test"
        row.payerCivic = "1"
        row.payerPostalCode = "00100"
        row.payerLocation = "Roma"
        row.payerProvince = "RM"
        row.payerNation = "IT"
        row.payerEmail = secrets.citizen_info.X.email
        row.debtorEntityType = PersonEntityType.F
        row.debtorFiscalCode = secrets.citizen_info.X.fiscal_code
        row.debtorFullName = secrets.citizen_info.X.name
        row.debtorAddress = "Via del Test"
        row.debtorCivic = "1"
        row.debtorPostalCode = "00100"
        row.debtorLocation = "Roma"
        row.debtorProvince = "RM"
        row.debtorNation = "IT"
        row.debtorEmail = secrets.citizen_info.X.email
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
        row.debtPositionTypeOrgCode = settings.debt_position_type_org_code.feature_test
        row.signatureType = "0"
        row.rt = "RT"
        row.idTransfer = 1
        row.feeCents = "1"
        row.receiptAttachmentTypeCode = "100"
        row.mbdAttachment = "<xml></xml>"
        row.fiscalCodePA = org_info.fiscal_code
        row.companyName = org_info.name
        row.transferCategory = "9/0301109AP/"

        receipts_rows.append(row)

    return receipts_rows


def _to_cents(amount: str) -> int:
    return round(float(amount) * 100)


@given("a receipt with balance of a non-existent debt position inserted into an ingestion flow file with version {csv_version}")
def step_create_receipts_file_with_balance_for_non_existent_dp(context, csv_version: str):
    context.csv_version = CSVVersion(csv_version)

    csv_rows = create_receipts_rows(context, receipts_size=1)
    row = csv_rows[0]
    row.balance = build_balance_xml([Section(amount_cents=_to_cents(row.paymentAmountCents),
                                             assessment_registry=AssessmentRegistry())])

    _write_receipts_file(context, csv_rows)


@given("a receipt with balance of the paid installment inserted into an ingestion flow file with version {csv_version}")
def step_create_receipts_file_with_balance_for_paid_installment(context, csv_version: str):
    context.csv_version = CSVVersion(csv_version)

    csv_rows = create_receipts_rows(context, receipts_size=1, debt_position=context.debt_position)
    row = csv_rows[0]
    row.balance = build_balance_xml([Section(amount_cents=_to_cents(row.paymentAmountCents),
                                             assessment_registry=AssessmentRegistry())])

    _write_receipts_file(context, csv_rows)


@when("the same receipt with amount increased by {amount_increase} euros, modified remittance information and balance "
      "is inserted into an ingestion flow file with version {csv_version}")
def step_create_receipts_file_with_modified_receipt(context, csv_version: str, amount_increase: str):
    """Builds a receipts file containing the receipt already imported, with modified data. It:

    - keeps the same receipt identifier, IUV and IUD, so that the existing receipt is updated
    - changes the remittance information, increases the amount by the given value and changes the balance using different assessment codes so that the recalculated
      assessment details differ from the previous ones"""
    context.csv_version = CSVVersion(csv_version)
    installment_paid = get_installment_paid(context)

    row = copy.deepcopy(context.receipts_rows[0])
    row.remittanceInformation = 'Feature Test Import Receipts File updated'
    amount_cents = _to_cents(row.paymentAmountCents) + int(amount_increase) * 100
    row.paymentAmountCents = "{:.2f}".format(amount_cents / 100)
    row.singlePaymentAmount = row.paymentAmountCents

    row.balance = build_balance_xml([
        Section(amount_cents=_to_cents(row.paymentAmountCents),
                assessment_registry=AssessmentRegistry(section_code='FTCAP_02', office_code='FTUFF_02',
                                                       assessment_code='FTACC_02')),
    ])
    installment_paid.balance = row.balance

    context.create_assessment_run_id = get_workflow_run_id(
        token=context.token, traceparent=context.traceparent, workflow_type=WorkflowType.CREATE_ASSESSMENT,
        entity_id=installment_paid.receipt_id)
    context.classify_assessment_run_id = get_workflow_run_id(
        token=context.token, traceparent=context.traceparent, workflow_type=WorkflowType.CLASSIFY_ASSESSMENT,
        entity_id=str(context.org_info.id) + '-' + installment_paid.iuv + '-' + installment_paid.iud)

    _write_receipts_file(context, [row])


@then("the receipt is updated")
def step_check_receipt_updated(context):
    """Checks that the receipt already imported has been updated by the last receipts file. It verifies that:

    - there is still exactly one receipt linked to the installment for the IUV and IUR
    - the receipt refers to the last ingestion flow file and has the modified remittance information and amount"""
    installment_paid = get_installment_paid(context)
    row = context.receipts_rows[0]

    res = get_receipt(token=context.token, traceparent=context.traceparent, organization_id=context.org_info.id,
                      receipt_origin=ReceiptOriginType.RECEIPT_FILE.value, iuv=installment_paid.iuv,
                      iur=installment_paid.iur)
    assert_response_ok(res, "Get receipt by IUV and IUR")
    assert len(res.json()['content']) == 1, \
        f"Expected exactly 1 receipt for IUV {installment_paid.iuv} / IUR {installment_paid.iur}, got {len(res.json()['content'])}"
    receipt_id = res.json()['content'][0]['receiptId']
    assert receipt_id == installment_paid.receipt_id, \
        f"receiptId mismatch: expected {installment_paid.receipt_id}, got {receipt_id}"

    res = get_receipt_by_id(token=context.token, traceparent=context.traceparent, receipt_id=receipt_id)
    assert_response_ok(res, "Get receipt by id")
    receipt = res.json()

    expected_amount_cents = _to_cents(row.paymentAmountCents)
    assert receipt['ingestionFlowFileId'] == context.receipts_file_id, \
        f"ingestionFlowFileId mismatch: expected {context.receipts_file_id}, got {receipt['ingestionFlowFileId']}"
    assert receipt['description'] == row.remittanceInformation, \
        f"description mismatch: expected {row.remittanceInformation}, got {receipt['description']}"
    assert receipt['paymentAmountCents'] == expected_amount_cents, \
        f"paymentAmountCents mismatch: expected {expected_amount_cents}, got {receipt['paymentAmountCents']}"


@then("the technical debt position is updated")
def step_check_technical_debt_position_updated(context):
    """Checks that the technical debt position has been updated by the last receipts file. It verifies that:

    - there is still exactly one debt position for the notice, the same created by the first import
    - it has origin `RECEIPT_FILE`, it is `PAID` and its installment has the modified amount and remittance
      information"""
    installment_paid = get_installment_paid(context)
    row = context.receipts_rows[0]
    debt_position_id = context.debt_position.debt_position_id

    nav = NAV_PREFIX + installment_paid.iuv
    res = get_debt_position_by_organization_id_and_installment_nav(context.token, context.traceparent,
                                                                   organization_id=context.org_info.id, nav=nav)
    assert_response_ok(res, "Get debt position by NAV")
    assert len(res.json()) == 1, f"Expected exactly 1 debt position for NAV {nav}, got {len(res.json())}"
    assert res.json()[0]['debtPositionId'] == debt_position_id, \
        f"debtPositionId mismatch: expected {debt_position_id}, got {res.json()[0]['debtPositionId']}"

    debt_position = fetch_debt_position(context, debt_position_id=debt_position_id)
    installment = debt_position.payment_options[0].installments[0]
    expected_amount_cents = _to_cents(row.paymentAmountCents)

    assert debt_position.debt_position_origin == DebtPositionOrigin.RECEIPT_FILE, \
        f"debtPositionOrigin mismatch: expected {DebtPositionOrigin.RECEIPT_FILE}, got {debt_position.debt_position_origin}"
    assert debt_position.status == Status.PAID, \
        f"status mismatch: expected {Status.PAID}, got {debt_position.status}"
    assert installment.amount_cents == expected_amount_cents, \
        f"amountCents mismatch: expected {expected_amount_cents}, got {installment.amount_cents}"
    assert installment.remittance_information == row.remittanceInformation, \
        f"remittanceInformation mismatch: expected {row.remittanceInformation}, got {installment.remittance_information}"


@then("the assessment details are recalculated")
def step_check_assessment_details_recalculated(context):
    """Checks that the assessment workflows ran again after the last receipts file. It verifies that a new run of the
    `CREATE_ASSESSMENT` and of the `CLASSIFY_ASSESSMENT` workflows completes"""
    installment_paid = get_installment_paid(context)

    check_workflow_status(context=context, workflow_type=WorkflowType.CREATE_ASSESSMENT,
                          entity_id=installment_paid.receipt_id, status=WorkflowStatus.COMPLETED,
                          previous_run_id=context.create_assessment_run_id)
    check_workflow_status(context=context, workflow_type=WorkflowType.CLASSIFY_ASSESSMENT,
                          entity_id=str(context.org_info.id) + '-' + installment_paid.iuv + '-' + installment_paid.iud,
                          status=WorkflowStatus.COMPLETED, previous_run_id=context.classify_assessment_run_id)


@then("the installment keeps its original amount")
def step_check_installment_amount_unchanged(context):
    installment_paid = get_installment_paid(context)

    res = get_installment(token=context.token, traceparent=context.traceparent,
                          installment_id=installment_paid.installment_id)
    assert_response_ok(res, "Get installment by id")
    assert res.json()['amountCents'] == installment_paid.amount_cents, \
        f"amountCents mismatch: expected {installment_paid.amount_cents}, got {res.json()['amountCents']}"


@given("a receipt successfully imported from a receipts file with version {csv_version}")
def step_receipt_of_existing_dp_imported(context, csv_version: str):
    """Imports a receipt from a receipts file and checks it is processed:

    - builds the receipts file and uploads it
    - checks that the receipts file is processed
    - checks that the receipt is created with origin `RECEIPT_FILE`
    - checks that the installment of payment option 1 and the debt position are `PAID`
    - checks that the assessment is `CLOSED` and its details match the balance"""
    step_create_receipts_file_for_existing_dp(context=context, csv_version=csv_version)
    step_uploads_receipts_file(context=context)
    step_check_receipt_imported_and_dp_paid(context=context)
    step_check_assessment(context=context, status='closed')
    step_check_assessment_detail(context=context)

@given("a receipt of the installment created outside PU successfully imported from a receipts file with version {csv_version}")
def step_receipt_of_installment_outside_pu_imported(context, csv_version: str):
    """Imports a receipt of an installment created outside PU and checks it is processed:

    - builds the receipts file and uploads it
    - checks that the file is processed and the technical debt position is created with origin `RECEIPT_FILE`
    - checks that the receipt is created with origin `RECEIPT_FILE`
    - checks that the installment of payment option 1 and the debt position are `PAID`"""
    step_create_receipts_file_for_existing_dp(context=context, csv_version=csv_version)
    step_uploads_receipts_file(context=context)
    step_receipts_file_processed(context=context)
    step_check_debt_positions_created(context=context, debt_position_origin=DebtPositionOrigin.RECEIPT_FILE.value)
    step_check_receipt_imported_and_dp_paid(context=context)

@given("a receipt with balance of a non-existent debt position successfully imported from a receipts file with version {csv_version}")
def step_receipt_with_balance_of_non_existent_dp_imported(context, csv_version: str):
    """Imports a receipt with balance of a debt position not present in PU from a receipts file and checks it is
    processed:

    - builds the receipts file and uploads it
    - checks that the file is processed and the technical debt position is created with origin `RECEIPT_FILE`
    - checks that the receipts file is processed
    - checks that the receipt is created with origin `RECEIPT_FILE`
    - checks that the installment of payment option 1 and the debt position are `PAID`
    - checks that the assessment is `CLOSED` and its details match the balance"""
    step_create_receipts_file_with_balance_for_non_existent_dp(context=context, csv_version=csv_version)
    step_uploads_receipts_file(context=context)
    step_receipts_file_processed(context=context)
    step_check_debt_positions_created(context=context, debt_position_origin=DebtPositionOrigin.RECEIPT_FILE.value)
    step_check_receipt_imported_and_dp_paid(context=context)
    step_check_assessment(context=context, status='closed')
    step_check_assessment_detail(context=context)


@then("the receipt is imported correctly and the debt position is paid")
def step_check_receipt_imported_and_dp_paid(context):
    """Checks that the uploaded receipt is imported for the debt position. It verifies that:

    - the receipts file is processed
    - the receipt is created with origin `RECEIPT_FILE`
    - the installment of payment option 1 and the debt position are `PAID`"""
    step_receipts_file_processed(context=context)
    step_check_receipt_created(context=context, receipt_origin=ReceiptOriginType.RECEIPT_FILE.value)
    step_check_installment_status(context=context, po_index='1', status=Status.PAID.value)
    step_check_dp_status(context=context, status=Status.PAID.value)


@then("the installment is linked to the pagoPA receipt")
def step_check_installment_linked_to_pagopa_receipt(context):
    """Checks that the installment is linked to the receipt sent by pagoPA instead of the one imported from file.
    It verifies that:

    - the installment IUR isn't the one imported from file
    - the receipt linked to the installment has origin `RECEIPT_PAGOPA` and the same IUR of the installment"""
    installment_paid = get_installment_paid(context)
    res = get_installment(token=context.token, traceparent=context.traceparent, installment_id=installment_paid.installment_id)
    assert_response_ok(res, "Get installment by id")
    installment = res.json()

    file_row = context.receipts_rows[0]

    assert installment['iur'] != file_row.paymentReceiptId, \
        f"iur is equal to the one imported from file: {file_row.paymentReceiptId}"

    res = get_receipt_by_id(token=context.token, traceparent=context.traceparent, receipt_id=installment['receiptId'])
    assert_response_ok(res, "Get receipt by id")
    receipt = res.json()
    assert receipt['receiptOrigin'] == ReceiptOriginType.RECEIPT_PAGOPA.value, \
        f"receiptOrigin mismatch: expected {ReceiptOriginType.RECEIPT_PAGOPA.value}, got {receipt['receiptOrigin']}"
    assert receipt['paymentReceiptId'] == installment['iur'], \
        f"paymentReceiptId mismatch: expected {installment['iur']}, got {receipt['paymentReceiptId']}"


@then("the receipt imported from file is created with origin receipt_file")
def step_check_file_receipt_created(context):
    """Checks that the receipt in the file is imported with origin `RECEIPT_FILE`."""
    row = context.receipts_rows[0]

    res = get_receipt_by_iur(token=context.token, traceparent=context.traceparent, iur=row.paymentReceiptId)
    assert_response_ok(res, "Get receipt by IUR")
    receipt = res.json()
    assert receipt['receiptOrigin'] == ReceiptOriginType.RECEIPT_FILE.value, \
        f"receiptOrigin mismatch: expected {ReceiptOriginType.RECEIPT_FILE.value}, got {receipt['receiptOrigin']}"
    assert receipt['ingestionFlowFileId'] == context.receipts_file_id, \
        f"ingestionFlowFileId mismatch: expected {context.receipts_file_id}, got {receipt['ingestionFlowFileId']}"


@then("the installment balance is updated by the receipts file")
def step_check_installment_balance_updated(context):
    """Checks that the balance of the paid installment has been replaced by the balance of the receipt in the file."""
    installment_paid = get_installment_paid(context)
    row = context.receipts_rows[0]

    res = get_installment(token=context.token, traceparent=context.traceparent, installment_id=installment_paid.installment_id)
    assert_response_ok(res, "Get installment by id")
    installment_balance = res.json()['balance']

    assert installment_balance is not None, "Installment balance not set"
    assert extract_balance_from_xml(installment_balance) == extract_balance_from_xml(row.balance), \
        f"balance mismatch: expected {row.balance}, got {installment_balance}"
