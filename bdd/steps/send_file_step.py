import os
import zipfile
from datetime import datetime

from behave import given, when, then

from api.fileshare import post_upload_file_to_url
from api.send_campaign import get_send_campaigns, get_send_campaign_notifications
from api.sil_rest import post_authorize_import_massive_file
from bdd.steps.authentication_step import step_get_token_sil
from bdd.steps.send_step import get_valid_send_notification, assert_installment_iun
from bdd.steps.utils.assertions import assert_response_ok
from bdd.steps.utils.utility import retry_get_process_file_status
from bdd.steps.workflow_step import check_workflow_status
from model.csv_file_send_notification import CSVRow, to_csv_lines
from model.file import IngestionFlowFileType, FileStatus, FilePathName
from model.send_notification import get_pagopa_int_mode, SEND_TEMPLATE_DIR, SendCampaignNotificationStatus
from model.workflow_hub import WorkflowStatus, WorkflowType


def create_send_notification_rows(installments: list, org_info, external_campaign_id: str) -> list[CSVRow]:
    pagopa_int_mode = get_pagopa_int_mode(org_info.pagopa_interaction)
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")[:15]

    send_notification_rows = []

    for index, inst in enumerate(installments, start=1):
        row = CSVRow(organizationId=org_info.id,
                     paProtocolNumber=f'PROT_FT_{timestamp}_{index}',
                     externalCampaignId=external_campaign_id)
        row.senderDenomination = org_info.name
        row.senderTaxId = org_info.fiscal_code
        row.amount = inst.amount_cents
        row.paymentExpirationDate = inst.due_date
        row.pagoPaIntMode = pagopa_int_mode
        row.paymentNoticeCode_1 = inst.nav
        row.paymentCreditorTaxId_1 = inst.transfers[0].org_fiscal_code
        row.attachmentFileName_1 = f'payment_{index}.pdf'
        row.documentFileName_1 = f'notification_{index}.pdf'

        send_notification_rows.append(row)

    return send_notification_rows


def create_send_zip(zip_path: str, csv_name: str, installments: list, org_info,
                    external_campaign_id: str) -> int:
    rows = create_send_notification_rows(installments=installments,
                                         org_info=org_info,
                                         external_campaign_id=external_campaign_id)

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(csv_name, '\n'.join(to_csv_lines(rows)))

        for index in range(1, len(rows) + 1):
            for prefix in ('payment', 'notification'):
                file_name = f'{prefix}_{index}.pdf'
                zf.write(SEND_TEMPLATE_DIR / file_name, arcname=f'{index}/{file_name}')

    return len(rows)


@given("a SEND campaign file prepared to notify the single installment of debt positions {identifiers}")
def step_prepare_campaign_file(context, identifiers):
    """Prepares the zip file of a SEND campaign. It:

    - generates the campaign id shared by all the notifications;
    - builds a CSV row for the single installment of each debt position;
    - zips the CSV together with the payment and notification PDFs of each debt position.
    """
    installments_notified = [inst
                             for identifier in identifiers.split()
                             for po in context.debt_positions[identifier].payment_options
                             for inst in po.installments]

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    context.external_campaign_id = f'FEATURE_TEST_{timestamp}'

    filename = f'SendCampaignFeatureTest_{timestamp}-1_0'
    zip_file_path = f'{filename}.zip'
    rows_len = create_send_zip(zip_path=zip_file_path,
                               csv_name=f'{filename}.csv',
                               installments=installments_notified,
                               org_info=context.org_info,
                               external_campaign_id=context.external_campaign_id)

    context.file_name = zip_file_path
    context.notifications_rows_len = rows_len
    context.installments_notified = installments_notified


@when("SIL uploads the SEND campaign file")
def step_upload_send_notifications(context):
    step_get_token_sil(context=context, pagopa_interaction=context.org_info.pagopa_interaction)

    res_file_auth = post_authorize_import_massive_file(token=context.token, traceparent=context.traceparent,
                                                       org_fiscal_code=context.org_info.fiscal_code,
                                                       ingestion_flow_file_type=IngestionFlowFileType.SEND_NOTIFICATION)

    assert_response_ok(res_file_auth, "SIL authorization to upload SEND campaign file")
    assert res_file_auth.json()[
               'uploadUrl'] is not None, "No uploadUrl returned by the send notification import authorization"
    assert res_file_auth.json()[
               'importId'] is not None, "No importId returned by the send notification import authorization"

    context.send_notification_file_id = res_file_auth.json()['importId']

    res_upload = post_upload_file_to_url(token=context.token, traceparent=context.traceparent,
                                         url=res_file_auth.json()['uploadUrl'],
                                         file_name=context.file_name)

    assert_response_ok(res_upload, "SIL upload SEND campaign file")

    os.remove(context.file_name)


@then("the SEND campaign file is processed correctly")
def step_check_send_file_processed(context):
    """Checks that the SEND campaign file was processed correctly. It verifies that:

        - the file reaches status `COMPLETED`;
        - the number of imported rows equals the rows sent and all were imported successfully;
        - the `SEND_NOTIFICATION_INGESTION_FLOW` workflow completes.
        """

    file_path_name = FilePathName.SEND_NOTIFICATION
    file_name = context.file_name

    res = retry_get_process_file_status(token=context.token, traceparent=context.traceparent,
                                        organization_id=context.org_info.id,
                                        file_path_name=file_path_name, file_name=file_name,
                                        status=FileStatus.COMPLETED, delay=10)

    assert res['numTotalRows'] == context.notifications_rows_len
    assert res['numTotalRows'] == res['numCorrectlyImportedRows']

    check_workflow_status(context=context, workflow_type=WorkflowType.SEND_NOTIFICATION_INGESTION_FLOW,
                          entity_id=context.send_notification_file_id, status=WorkflowStatus.COMPLETED)


@then("the campaign has each notifications in status in progress")
def step_check_campaign_notifications_status(context):
    external_campaign_id = context.external_campaign_id
    org_id = context.org_info.id
    total_notifications = context.notifications_rows_len

    res_campaign_detail = get_send_campaigns(token=context.token, traceparent=context.traceparent,
                                             organization_id=org_id, external_campaign_id=external_campaign_id)

    assert_response_ok(res_campaign_detail, "Get campaign detail")
    assert len(res_campaign_detail.json()['content']) == 1
    campaign_detail = res_campaign_detail.json()['content'][0]

    assert campaign_detail['campaignId'] is not None
    assert campaign_detail['counters'] is not None
    assert campaign_detail['counters']['total'] == total_notifications
    assert campaign_detail['startDate'] == datetime.now().strftime("%Y-%m-%d")

    context.campaign_id = campaign_detail['campaignId']

    res_campaign_notifications = get_send_campaign_notifications(token=context.token, traceparent=context.traceparent,
                                                                 organization_id=org_id, campaign_id=context.campaign_id)

    assert_response_ok(res_campaign_notifications, "Get campaign notifications")
    campaign_notifications = res_campaign_notifications.json()

    assert campaign_notifications['totalElements'] == total_notifications
    notifications = campaign_notifications['content']
    assert len(notifications) == total_notifications

    for notification in notifications:
        assert notification['sendNotificationId'] is not None
        assert notification['status'] == SendCampaignNotificationStatus.IN_PROGRESS.value, \
            f"Notification {notification['sendNotificationId']} in status {notification['status']}"
        assert notification.get('iun') is None, \
            f"Notification {notification['sendNotificationId']} has already the IUN {notification['iun']}"

    context.send_notification_ids = [notification['sendNotificationId'] for notification in notifications]


@then("each notifications are in status {status} and the IUN is assigned to the related installments")
def step_check_campaign_iun(context, status):
    """Checks that each notification of the campaign is in the expected status and the IUN is assigned. It:

    - polls SEND until each notification is in the expected status and asserts it has an IUN;
    - matches each notification to its installment through the NAV;
    - verifies that every notified installment carries the IUN of its own notification.
    """
    installments_by_nav = {inst.nav: inst for inst in context.installments_notified}
    checked_navs = set()

    for notification_id in context.send_notification_ids:
        notification = get_valid_send_notification(context=context, notification_id=notification_id,
                                                   status=status)

        navs = [nav for payment in notification['payments'] for nav in payment['navList']]
        assert len(navs) == 1, f"Notification {notification_id} has NAVs {navs}"
        nav = navs[0]
        assert nav in installments_by_nav, f"Notification {notification_id} has unexpected NAV {nav}"
        assert nav not in checked_navs, f"NAV {nav} is notified more than once"
        checked_navs.add(nav)

        assert_installment_iun(context=context, installment=installments_by_nav[nav], iun=notification['iun'])

    assert checked_navs == set(installments_by_nav), \
        f"Installments not notified: {set(installments_by_nav) - checked_navs}"
