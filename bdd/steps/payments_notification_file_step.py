import os
from datetime import datetime

import pandas
from behave import when, then

from api.fileshare import post_upload_file_to_url
from api.soap.sil import post_sil_autorizza_import_flusso_notificati
from bdd.steps.authentication_step import step_get_token_sil
from bdd.steps.utils.assertions import assert_response_ok
from bdd.steps.utils.debt_position_utility import format_decimal_amount, get_installment_paid
from bdd.steps.utils.utility import check_res_ok_and_get_body, retry_get_import_payment_notification_status
from model.csv_file_payments_notification import CSVRow, to_csv_lines
from model.debt_position import Installment


def create_payments_notification_rows(installments: list[Installment]) -> list:
    payments_notification_rows = []
    today = datetime.now().strftime("%Y-%m-%d")

    for installment in installments:
        row = CSVRow()
        row.iud = installment.iud
        row.iuv = installment.iuv
        row.debtorUniqueIdentifierType = installment.debtor.entity_type.value
        row.debtorUniqueIdentifierCode = installment.debtor.fiscal_code
        row.debtorFullName = installment.debtor.full_name
        row.paymentExecutionDate = today
        row.amountPaid = format_decimal_amount(installment.amount_cents)
        row.remittanceInformation = installment.remittance_information
        row.transferCategory = installment.transfers[0].category
        row.debtorAddress = installment.debtor.address
        row.debtorCivic = installment.debtor.civic
        row.debtorPostalCode = installment.debtor.postal_code
        row.debtorLocation = installment.debtor.location
        row.debtorProvince = installment.debtor.province
        row.debtorNation = installment.debtor.nation
        row.debtorEmail = installment.debtor.email

        payments_notification_rows.append(row)

    return payments_notification_rows


def create_payment_notification_zip(installments: list) -> str:
    csv_rows = create_payments_notification_rows(installments=installments)

    csv_lines = to_csv_lines(csv_rows=csv_rows)
    dataset_dataframe = pandas.DataFrame(data=csv_lines)

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    filename = f'PaymentNotificationFeatureTest_{timestamp}-1_0'
    zip_file_path = f'{filename}.zip'

    dataset_dataframe.to_csv(zip_file_path, index=False, header=False,
                             compression=dict(method='zip', archive_name=f'{filename}.csv'))

    return zip_file_path


@when("SIL imports the payment notification related to the installment")
def step_sil_import_payment_notification_file(context):
    """Imports a payment notification file through SIL (`pivotSILAutorizzaImportFlusso`)

        - authorizes the import and reads the upload URL and request token
        - builds the payment notification zip and uploads it to the returned URL"""

    context.org_token = context.token
    step_get_token_sil(context=context, pagopa_interaction=context.org_info.pagopa_interaction)

    res = post_sil_autorizza_import_flusso_notificati(token=context.token, traceparent=context.traceparent,
                                                      ipa_code=context.org_info.ipa_code)
    assert_response_ok(res, "SIL authorize import payment notification file")
    res_body = check_res_ok_and_get_body(res.content, 'pivotSILAutorizzaImportFlussoRisposta')

    context.import_pn_req_token = res_body['requestToken']
    upload_url = res_body['uploadUrl']
    assert context.import_pn_req_token is not None, "No requestToken returned by the payment notification import authorization"
    assert upload_url is not None, "No uploadUrl returned by the payment notification import authorization"

    installment = get_installment_paid(context)

    zip_file_path = create_payment_notification_zip([installment])

    res_upload = post_upload_file_to_url(url=upload_url, token=context.token, traceparent=context.traceparent,
                                         file_name=zip_file_path)
    assert_response_ok(res_upload, "Upload payment notification file to authorized URL")

    os.remove(zip_file_path)


@then("the payment notification import completes successfully")
def step_check_payment_notification_import_status(context):
    """Polls the payment notification import status (`pivotSILChiediStatoImportFlusso`) until it reaches `FILE_CARICATO`"""
    retry_get_import_payment_notification_status(token=context.token, traceparent=context.traceparent,
                                                 ipa_code=context.org_info.ipa_code,
                                                 request_token=context.import_pn_req_token)
