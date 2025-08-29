import os
import uuid
from datetime import datetime

import pandas
from behave import given, when, then

from api.debt_positions import get_debt_positions_by_ingestion_flow_id
from api.fileshare import post_upload_file
from bdd.steps.debt_positions_step import validate_debt_position_created
from bdd.steps.utils.debt_position_utility import create_debt_position, create_payment_option, create_installment
from bdd.steps.utils.utility import retrieve_org_id_by_ipa_code, retry_get_process_file_status
from bdd.steps.workflow_step import check_workflow_status
from config.configuration import settings
from model.csv_file_debt_positions import CSVRow, to_csv_lines, CSVVersion
from model.debt_position import Status, PaymentOptionType, DebtPosition
from model.file import FileOrigin, IngestionFlowFileType, FilePathName, FileStatus
from model.workflow_hub import WorkflowType, WorkflowStatus


@given("debt positions {identifiers} with the installments configured as follows")
def step_configure_debt_positions_for_file(context, identifiers):
    token = context.token

    organization_id = retrieve_org_id_by_ipa_code(token=token, ipa_code=context.org_info.ipa_code)
    context.org_info['id'] = organization_id

    debt_positions = {}

    for row in context.table:
        debt_position_identifier = row['identifier']
        payment_option_index = int(row['po index'])
        payment_option_type = row['po type']
        installment_seq = int(row['installment seq'])
        action = row['action']

        if debt_position_identifier not in debt_positions:
            debt_position = create_debt_position(token=token, organization_id=organization_id,
                                                 debt_position_type_org_code=settings.debt_position_type_org_code,
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
def step_create_ingestion_flow_file(context, identifiers, csv_version):
    debt_positions = context.debt_positions
    identifiers = identifiers.split()

    installments_rows = create_installments_rows(identifiers=identifiers, debt_positions=debt_positions)

    csv_lines = to_csv_lines(csv_rows=installments_rows, csv_version=csv_version)

    dataset_dataframe = pandas.DataFrame(data=csv_lines)

    filename = f'ImportFeatureTest_{datetime.now().strftime("%Y%m%d%H%M%S")}_{csv_version}'
    zip_file_path = f'{filename}.zip'
    dataset_dataframe.to_csv(zip_file_path, index=False, header=False,
                             compression=dict(method='zip', archive_name=f'{filename}.csv'))

    context.debt_positions_file_name = zip_file_path
    context.csv_version = csv_version


def create_installments_rows(identifiers: list, debt_positions: dict) -> list:
    installments_rows = []

    for identifier in identifiers:
        dp = debt_positions.get(identifier)
        for po in dp.payment_options:
            for inst in po.installments:
                row = CSVRow()
                row.action = inst.ingestion_flow_file_action
                row.iupdOrg = dp.iupd_org
                row.description = dp.description
                row.paymentOptionIndex = po.payment_option_index
                row.paymentOptionType = po.payment_option_type
                row.paymentOptionDescription = po.description
                row.entityType = inst.debtor.entity_type
                row.fiscalCode = inst.debtor.fiscal_code
                row.fullName = inst.debtor.full_name
                row.address = inst.debtor.address
                row.civic = inst.debtor.civic
                row.postalCode = inst.debtor.postal_code
                row.location = inst.debtor.location
                row.province = inst.debtor.province
                row.nation = inst.debtor.nation
                row.email = inst.debtor.email
                row.iud = inst.iud
                row.dueDate = inst.due_date
                row.amount = str(inst.amount_cents / 100)
                row.remittanceInformation = inst.remittance_information

                installments_rows.append(row)

    return installments_rows


@when("the organization uploads the debt positions file")
def step_uploads_debt_positions_file(context):
    token = context.token
    org_info = context.org_info

    zip_file_path = context.debt_positions_file_name

    res = post_upload_file(token=token, organization_id=org_info.id,
                           ingestion_flow_file_type=IngestionFlowFileType.DP_INSTALLMENTS,
                           file_origin=FileOrigin.PORTAL, file_name=zip_file_path)

    assert res.status_code == 200
    assert res.json()['ingestionFlowFileId'] is not None

    context.debt_positions_file_id = res.json()['ingestionFlowFileId']

    os.remove(zip_file_path)


@then("the ingestion file is processed correctly")
def step_debt_position_file_processed(context):
    organization_id = context.org_info.id
    org_has_generate_notice_api_key: bool = context.org_info.has_generate_notice_api_key

    file_path_name = FilePathName.INSTALLMENT
    file_name = context.debt_positions_file_name
    status = FileStatus.COMPLETED if org_has_generate_notice_api_key == True else FileStatus.ERROR

    res = retry_get_process_file_status(token=context.token, organization_id=organization_id,
                                        file_path_name=file_path_name, file_name=file_name,
                                        status=status, delay=10)

    assert res['numTotalRows'] == context.total_installments
    assert res['numTotalRows'] == res['numCorrectlyImportedRows']

    check_workflow_status(context=context, workflow_type=WorkflowType.DEBT_POSITION_INGESTION_FLOW,
                          entity_id=context.debt_positions_file_id, status=WorkflowStatus.COMPLETED)


def search_dp_by_iupd_org(list_debt_positions: list[dict], iupd_org: str) -> dict:
    return dict(next(dp for dp in list_debt_positions if dp['iupdOrg'] == iupd_org))


def search_dp_by_inst_iud(list_debt_positions: list[dict], inst_iud: str) -> dict:
    return dict(next(dp for dp in list_debt_positions if dp['paymentOptions'][0]['installments'][0]['iud'] == inst_iud))


@then("the debt positions {identifiers} are created in status {status}")
def step_check_debt_positions_created(context, identifiers, status):
    identifiers = identifiers.split()

    res = get_debt_positions_by_ingestion_flow_id(token=context.token, ingestion_flow_id=context.debt_positions_file_id)

    assert res.status_code == 200

    debt_positions_created = check_debt_positions_created(context=context, identifiers=identifiers, status=status, debt_position_by_ingestion_flow_id=res.json())

    context.debt_positions_created = debt_positions_created


def check_debt_positions_created(context, identifiers, status, debt_position_by_ingestion_flow_id) -> list[DebtPosition]:
    assert len(identifiers) == debt_position_by_ingestion_flow_id['totalElements']

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