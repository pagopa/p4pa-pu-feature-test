import os
import uuid
from datetime import datetime

import pandas
from behave import given, when, then

from api.fileshare import post_upload_file
from bdd.steps.utils.debt_position_utility import create_debt_position, create_payment_option
from bdd.steps.utils.utility import retrieve_org_id_by_ipa_code
from config.configuration import settings
from model.csv_file_debt_positions import CSVRow, Action, to_csv_lines
from model.file import FileOrigin, IngestionFlowFileType


@given("debt positions {identifiers} configured as follows")
def step_configure_debt_positions_for_file(context, identifiers):
    token = context.token

    organization_id = retrieve_org_id_by_ipa_code(token=token, ipa_code=context.org_info.ipa_code)
    context.org_info['id'] = organization_id

    debt_positions = {}

    for row in context.table:
        debt_position_identifier = row['identifier']
        payment_option_index = int(row['po index'])
        installments_size = int(row['installments size'])

        if debt_position_identifier not in debt_positions:
            debt_position = create_debt_position(token=token, organization_id=organization_id,
                                                 debt_position_type_org_code=settings.debt_position_type_org_code,
                                                 iupd_org=f'Feature-test-{uuid.uuid4().hex[:10]}',
                                                 identifier=debt_position_identifier)
        else:
            debt_position = debt_positions[debt_position_identifier]

        payment_option = create_payment_option(po_index=payment_option_index, installments_size=installments_size,
                                               expiration_days=2)

        debt_position.payment_options.append(payment_option)

        debt_positions[debt_position_identifier] = debt_position

    context.debt_positions = debt_positions


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


def create_installments_rows(identifiers: list, debt_positions: dict) -> list:
    installments_rows = []

    for identifier in identifiers:
        dp = debt_positions.get(identifier)
        for po in dp.payment_options:
            for inst in po.installments:
                row = CSVRow()
                row.action = Action.I.value
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

    context.payment_reporting_file_name = zip_file_path

    assert res.status_code == 200
    assert res.json()['ingestionFlowFileId'] is not None

    os.remove(zip_file_path)


@then("the debt positions ingestion file is processed correctly")
def step_debt_position_file_processed(context):
    pass