import copy
import os
import uuid
from api.debt_positions import get_debt_positions_by_ingestion_flow_id, \
    get_debt_position_by_iud
from api.fileshare import post_upload_file
from api.gpd_aca import get_debt_position_on_aca_or_gpd
from bdd.steps.debt_positions_step import validate_debt_position_created
from bdd.steps.gpd_aca_step import step_verify_presence_debt_positions_in_gpd
from bdd.steps.utils.assertions import assert_response_ok
from bdd.steps.utils.csv_utils import to_csv_lines, write_csv_zip
from bdd.steps.utils.debt_position_utils import create_debt_position, \
    create_payment_option, create_installment, \
    get_stored_debt_position, fetch_debt_position, \
    find_payment_option_by_po_index, \
    find_installment_by_seq_num_and_po_index, seq_num_of
from bdd.steps.utils.amount_utils import cents_to_euro_str
from bdd.steps.utils.polling_utils import retry_get_process_file_status
from bdd.steps.workflow_step import check_workflow_status, \
    step_debt_positions_workflow_check_expiration
from behave import given, when, then
from config.configuration import settings
from datetime import datetime, timedelta
from model.csv_file_debt_positions import CSVRow, CSVVersion, Action
from model.debt_position import Status, PaymentOptionType, DebtPosition
from model.file import FileOrigin, IngestionFlowFileType, FilePathName, \
    FileStatus
from model.workflow_hub import WorkflowType, WorkflowStatus


@given("debt positions {identifiers} with the installments configured as follows")
def step_configure_debt_positions_for_file(context, identifiers):
    debt_positions = {}

    for row in context.table:
        debt_position_identifier = row['identifier']
        payment_option_index = int(row['po index'])
        payment_option_type = row['po type']
        installment_seq = int(row['installment seq'])
        action = row['action']

        if debt_position_identifier not in debt_positions:
            debt_position = create_debt_position(token=context.token, traceparent=context.traceparent,
                                                 organization_id=context.org_info.id,
                                                 debt_position_type_org_code=settings.debt_position_type_org_code.feature_test,
                                                 iupd_org=f'Feature-test-{uuid.uuid4().hex[:10]}',
                                                 identifier=debt_position_identifier)
            debt_positions[debt_position_identifier] = debt_position
        else:
            debt_position = debt_positions[debt_position_identifier]

        payment_option = next(
            (po for po in debt_position.payment_options if po.payment_option_index == payment_option_index), None)

        if payment_option is None:
            payment_option = create_payment_option(po_index=payment_option_index,
                                                   payment_option_type=PaymentOptionType(payment_option_type))
            debt_position.payment_options.append(payment_option)

        installment = create_installment(expiration_days=1, seq_num=installment_seq, ingestion_flow_file_action=action)
        payment_option.installments.append(installment)

    context.debt_positions = debt_positions
    context.debt_positions_identifiers = identifiers.split()
    context.total_installments = len(context.table.rows)


@given("debt positions {identifiers} inserted into an ingestion flow file with version {csv_version}")
def step_create_debt_positions_file(context, identifiers, csv_version):
    debt_positions = context.debt_positions
    identifiers = identifiers.split()

    installments_rows = create_installments_rows(identifiers=identifiers, debt_positions=debt_positions)

    _write_debt_positions_file(context=context, installments_rows=installments_rows, csv_version=csv_version)


def _write_debt_positions_file(context, installments_rows: list, csv_version: str):
    csv_lines = to_csv_lines(csv_rows=installments_rows, csv_version=csv_version)
    filename = f'ImportFeatureTest_{datetime.now().strftime("%Y%m%d%H%M%S")}-{csv_version}'

    context.debt_positions_file_name = write_csv_zip(csv_lines=csv_lines, filename=filename)
    context.csv_version = csv_version


def create_installments_rows(identifiers: list, debt_positions: dict) -> list:
    installments_rows = []

    for identifier in identifiers:
        dp = debt_positions.get(identifier)
        for po in dp.payment_options:
            for inst in po.installments:
                installments_rows.append(_create_installment_row(debt_position=dp, payment_option=po, installment=inst,
                                                                 action=inst.ingestion_flow_file_action))

    return installments_rows


def _create_installment_row(debt_position, payment_option, installment, action: Action) -> CSVRow:
    row = CSVRow()
    row.action = action
    row.iupdOrg = debt_position.iupd_org
    row.description = debt_position.description
    row.paymentOptionIndex = payment_option.payment_option_index
    row.paymentOptionType = payment_option.payment_option_type
    row.paymentOptionDescription = payment_option.description
    row.entityType = installment.debtor.entity_type
    row.fiscalCode = installment.debtor.fiscal_code
    row.fullName = installment.debtor.full_name
    row.address = installment.debtor.address
    row.civic = installment.debtor.civic
    row.postalCode = installment.debtor.postal_code
    row.location = installment.debtor.location
    row.province = installment.debtor.province
    row.nation = installment.debtor.nation
    row.email = installment.debtor.email
    row.iud = installment.iud
    row.dueDate = installment.due_date
    row.amount = cents_to_euro_str(installment.amount_cents)
    row.remittanceInformation = installment.remittance_information
    row.iuv = installment.iuv

    return row


@when("the organization uploads the debt positions file")
def step_uploads_debt_positions_file(context):
    token = context.token
    org_info = context.org_info

    zip_file_path = context.debt_positions_file_name

    res = post_upload_file(token=token, traceparent=context.traceparent, organization_id=org_info.id,
                           ingestion_flow_file_type=IngestionFlowFileType.DP_INSTALLMENTS,
                           file_origin=FileOrigin.PORTAL, file_name=zip_file_path)

    assert_response_ok(res, "Upload debt positions file")
    assert res.json().get('ingestionFlowFileId') is not None, "No ingestionFlowFileId returned by the debt positions file upload"

    context.debt_positions_file_id = res.json()['ingestionFlowFileId']

    os.remove(zip_file_path)


@then("the ingestion file is processed correctly")
def step_debt_position_file_processed(context):
    """Checks that the debt positions ingestion file was processed correctly. It verifies that:

    - the file reaches `COMPLETED` (or `WARNING` when the organization has no generate-notice API key);
    - the number of imported rows equals the rows sent and all were imported successfully;
    - the `DEBT_POSITION_INGESTION_FLOW` workflow completes.
    """
    organization_id = context.org_info.id
    org_has_generate_notice_api_key: bool = context.org_info.has_generate_notice_api_key

    file_path_name = FilePathName.INSTALLMENT
    file_name = context.debt_positions_file_name
    status = FileStatus.COMPLETED if org_has_generate_notice_api_key else FileStatus.WARNING

    res = retry_get_process_file_status(token=context.token, traceparent=context.traceparent, organization_id=organization_id,
                                        file_path_name=file_path_name, file_name=file_name,
                                        status=status, delay=10)

    assert res.get('numTotalRows') == context.total_installments, \
        f"Expected numTotalRows {context.total_installments}, got {res.get('numTotalRows')}"
    assert res.get('numTotalRows') == res.get('numCorrectlyImportedRows'), \
        f"Expected all {res.get('numTotalRows')} rows imported correctly, got {res.get('numCorrectlyImportedRows')}"

    check_workflow_status(context=context, workflow_type=WorkflowType.DEBT_POSITION_INGESTION_FLOW,
                          entity_id=context.debt_positions_file_id, status=WorkflowStatus.COMPLETED)


def search_dp_by_iupd_org(list_debt_positions: list[dict], iupd_org: str) -> dict:
    return dict(next(dp for dp in list_debt_positions if dp['iupdOrg'] == iupd_org))


def search_dp_by_inst_iud(list_debt_positions: list[dict], inst_iud: str) -> dict:
    return dict(next(dp for dp in list_debt_positions if dp['paymentOptions'][0]['installments'][0]['iud'] == inst_iud))


@then("the debt positions {identifiers} are created in status {status}")
def step_check_debt_positions_created_from_file(context, identifiers, status):
    """Checks that the debt positions imported from the file were created in the expected status:

    - fetches the debt positions by ingestion flow id and asserts the count matches the identifiers;
    - validates each created debt position against its request (fields, payment options, installments).
    """
    identifiers = identifiers.split()

    res = get_debt_positions_by_ingestion_flow_id(token=context.token, traceparent=context.traceparent, ingestion_flow_id=context.debt_positions_file_id)

    assert_response_ok(res, "Get debt positions by ingestion flow id")

    debt_positions_created = check_debt_positions_created(context=context, identifiers=identifiers, status=status, debt_position_by_ingestion_flow_id=res.json())

    context.debt_positions_created = debt_positions_created


def check_debt_positions_created(context, identifiers, status, debt_position_by_ingestion_flow_id) -> list[DebtPosition]:
    assert len(identifiers) == debt_position_by_ingestion_flow_id.get('totalElements'), \
        f"Expected {len(identifiers)} debt positions, got {debt_position_by_ingestion_flow_id.get('totalElements')}"

    debt_positions_response = debt_position_by_ingestion_flow_id['content']

    debt_positions_created = []

    for identifier in identifiers:
        debt_position_request = context.debt_positions.get(identifier)

        if CSVVersion.is_v2(csv_version=context.csv_version):
            debt_position_response = search_dp_by_iupd_org(list_debt_positions=debt_positions_response,
                                                           iupd_org=debt_position_request.iupd_org)
        else:
            installment_iud = debt_position_request.payment_options[0].installments[0].iud
            debt_position_response = search_dp_by_inst_iud(list_debt_positions=debt_positions_response,
                                                           inst_iud=installment_iud)

        validate_debt_position_created(org_info=context.org_info, csv_version=context.csv_version, debt_position_request=debt_position_request,
                                       debt_position_response=debt_position_response, status=Status(status))

        debt_positions_created.append(DebtPosition.from_dict(debt_position_response))

    return debt_positions_created


@given("debt positions {identifiers} with the installments configured as follows are successfully imported from an "
       "ingestion flow file with version {csv_version}")
def step_debt_positions_imported_from_file(context, identifiers, csv_version):
    """Imports the debt positions configured in the table from a file and checks they are created.

    - builds the debt positions file and uploads it
    - checks that the file is processed and the debt positions are created in status `UNPAID`
    - checks that the notices are present in the GPD archive in status `valid`
    - checks that the expiration checks are scheduled"""
    step_configure_debt_positions_for_file(context=context, identifiers=identifiers)
    step_create_debt_positions_file(context=context, identifiers=identifiers, csv_version=csv_version)
    step_uploads_debt_positions_file(context=context)
    step_debt_position_file_processed(context=context)
    step_check_debt_positions_created_from_file(context=context, identifiers=identifiers, status=Status.UNPAID.value)
    step_verify_presence_debt_positions_in_gpd(context=context, status='valid')
    step_debt_positions_workflow_check_expiration(context=context, status='scheduled')

    for identifier, debt_position in zip(identifiers.split(), context.debt_positions_created):
        context.debt_positions[identifier] = debt_position


@when("the changes configured as follows are inserted into an ingestion flow file with version {csv_version}")
def step_create_debt_positions_changes_file(context, csv_version):
    """Builds a file with the changes configured in the table. For each row:

    - `I`: inserts a new installment in the given payment option
    - `M`: updates the installment with new remittance information, amount increased by 10 euros and due date
      postponed by 5 days
    - `A`: deletes the installment"""
    installments_rows = []
    requested_installments = {}

    for table_row in context.table:
        debt_position = get_stored_debt_position(context, table_row['identifier'])
        po_index = int(table_row['po index'])
        seq_num = int(table_row['installment seq'])
        action = Action(table_row['action'])
        payment_option = find_payment_option_by_po_index(debt_position=debt_position, po_index=po_index)

        if action == Action.I:
            installment = create_installment(expiration_days=1, seq_num=seq_num)
            requested_installments[installment.iud] = installment
        else:
            installment = find_installment_by_seq_num_and_po_index(debt_position=debt_position, po_index=po_index,
                                                                   seq_num=seq_num)
            if action == Action.M:
                installment = copy.deepcopy(installment)
                installment.remittance_information = f'Feature test installment {seq_num} updated'
                installment.amount_cents += 1000
                installment.due_date = (datetime.strptime(installment.due_date, '%Y-%m-%d')
                                        + timedelta(days=5)).strftime('%Y-%m-%d')
                requested_installments[installment.iud] = installment

        installments_rows.append(_create_installment_row(debt_position=debt_position, payment_option=payment_option,
                                                         installment=installment, action=action))

    _write_debt_positions_file(context=context, installments_rows=installments_rows, csv_version=csv_version)
    context.requested_installments = requested_installments
    context.total_installments = len(installments_rows)


@then("the installment {seq_num} of payment option {po_index} of debt position {dp_identifier} is cancelled and its notice is removed from GPD")
def step_check_installment_cancelled(context, seq_num, po_index, dp_identifier):
    debt_position = fetch_debt_position(context, get_stored_debt_position(context, dp_identifier).debt_position_id)
    installment = find_installment_by_seq_num_and_po_index(debt_position=debt_position, po_index=int(po_index),
                                                           seq_num=int(seq_num))

    assert installment.status == Status.CANCELLED, \
        f"status mismatch: expected {Status.CANCELLED.value}, got {installment.status}"

    res = get_debt_position_on_aca_or_gpd(org_fiscal_code=context.org_info.fiscal_code,
                                          iupd_pagopa=installment.iupd_pagopa)
    assert_response_ok(res, "Get cancelled debt position on GPD", expected_status=404)


@then("the installment {seq_num} of payment option {po_index} of debt position {dp_identifier} is created in a new debt position")
def step_check_installment_created_in_new_debt_position(context, seq_num, po_index, dp_identifier):
    stored_debt_position = get_stored_debt_position(context, dp_identifier)
    requested_installment = next(inst for inst in context.requested_installments.values()
                                 if seq_num_of(inst.iud) == int(seq_num))

    res = get_debt_position_by_iud(token=context.token, traceparent=context.traceparent,
                                   organization_id=context.org_info.id, iud=requested_installment.iud)
    assert_response_ok(res, "Get debt position by iud")
    assert len(res.json()) == 1, f"Expected exactly 1 debt position for iud {requested_installment.iud}, " \
                                 f"got {len(res.json())}"

    new_debt_position = DebtPosition.from_dict(res.json()[0])
    installment = find_installment_by_seq_num_and_po_index(debt_position=new_debt_position, po_index=int(po_index),
                                                           seq_num=int(seq_num))

    assert new_debt_position.debt_position_id != stored_debt_position.debt_position_id, \
        f"Expected a new debt position, got the debt position {dp_identifier} " \
        f"({stored_debt_position.debt_position_id})"
    assert new_debt_position.status == Status.UNPAID, \
        f"status mismatch: expected {Status.UNPAID.value}, got {new_debt_position.status}"
    assert installment.amount_cents == requested_installment.amount_cents, \
        f"amountCents mismatch: expected {requested_installment.amount_cents}, got {installment.amount_cents}"
    assert installment.due_date == requested_installment.due_date, \
        f"dueDate mismatch: expected {requested_installment.due_date}, got {installment.due_date}"
    assert installment.remittance_information == requested_installment.remittance_information, \
        f"remittanceInformation mismatch: expected {requested_installment.remittance_information}, " \
        f"got {installment.remittance_information}"


@then("the debt position {dp_identifier} is unchanged")
def step_check_debt_position_unchanged(context, dp_identifier):
    stored_debt_position = get_stored_debt_position(context, dp_identifier)
    stored_installment = stored_debt_position.payment_options[0].installments[0]
    debt_position = fetch_debt_position(context, stored_debt_position.debt_position_id)

    assert len(debt_position.payment_options) == 1, \
        f"Expected 1 payment option, got {len(debt_position.payment_options)}"
    assert len(debt_position.payment_options[0].installments) == 1, \
        f"Expected 1 installment, got {len(debt_position.payment_options[0].installments)}"

    installment = debt_position.payment_options[0].installments[0]
    assert installment.iud == stored_installment.iud, \
        f"iud mismatch: expected {stored_installment.iud}, got {installment.iud}"
    assert installment.iuv == stored_installment.iuv, \
        f"iuv mismatch: expected {stored_installment.iuv}, got {installment.iuv}"
    assert installment.amount_cents == stored_installment.amount_cents, \
        f"amountCents mismatch: expected {stored_installment.amount_cents}, got {installment.amount_cents}"
    assert installment.due_date == stored_installment.due_date, \
        f"dueDate mismatch: expected {stored_installment.due_date}, got {installment.due_date}"
    assert installment.remittance_information == stored_installment.remittance_information, \
        f"remittanceInformation mismatch: expected {stored_installment.remittance_information}, " \
        f"got {installment.remittance_information}"
    assert installment.status == Status.UNPAID, \
        f"status mismatch: expected {Status.UNPAID.value}, got {installment.status}"
