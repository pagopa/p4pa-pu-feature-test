import time

from behave import given, when, then

from api.auth import post_send_auth_token
from api.debt_positions import get_installment
from api.send import post_create_send_notification, post_upload_send_file, get_send_notification_status, \
    get_send_notification_fee
from bdd.steps.authentication_step import PagoPaInteractionModel
from bdd.steps.utils.debt_position_utility import find_installment_by_seq_num_and_po_index
from bdd.steps.utils.utility import retry_get_workflow_status
from bdd.steps.workflow_step import check_workflow_status
from config.configuration import secrets
from model.send_notification import SendStatus, SendPdfDigest, NotificationRequest, PaymentData, Recipient, Payment, \
    Document
from model.workflow_hub import WorkflowStatus, WorkflowType


def step_send_token(pagopa_interaction: PagoPaInteractionModel) -> str:
    client = None
    match pagopa_interaction:
        case PagoPaInteractionModel.ACA.value:
            client = secrets.send_info.aca
        case PagoPaInteractionModel.GPD.value:
            client = secrets.send_info.gpd

    res = post_send_auth_token(client_id=client.client_id, client_secret=client.client_secret)

    assert res.status_code == 200
    assert res.json()['access_token'] is not None

    return res.json()['access_token']


@given("a notification created for the single installment of debt position {dp_identifiers}")
@given("a notification created for the single installment of debt positions {dp_identifiers}")
def step_create_send_notification(context, dp_identifiers):
    org_info = context.org_info

    pagopa_int_mode = None
    match org_info.pagopa_interaction:
        case PagoPaInteractionModel.GPD.value:
            pagopa_int_mode = 'ASYNC'
        case PagoPaInteractionModel.ACA.value:
            pagopa_int_mode = 'SYNC'

    installments_notified = []

    dp_identifiers = dp_identifiers.split()
    for dp_identifier in dp_identifiers:
        installment = find_installment_by_seq_num_and_po_index(debt_position=context.debt_positions[dp_identifier],
                                                               po_index=1, seq_num=1)
        installments_notified.append(installment)

    recipients = []
    i = 1
    for installment in installments_notified:
        document = Document(file_name=f'payment_{i}.pdf', content_type='application/pdf',
                            digest=SendPdfDigest.payment_pdf_digest)
        payment_data = PaymentData(notice_code=installment.nav, creditor_tax_id=org_info.fiscal_code, attachment=document)
        payment = Payment(pago_pa=payment_data)

        recipient = next((recipient for recipient in recipients if recipient.tax_id == installment.debtor.fiscal_code),
                         None)
        if recipient is None:
            recipient = Recipient(tax_id=installment.debtor.fiscal_code, denomination=installment.debtor.full_name,
                                  payments=[payment])
            recipients.append(recipient)
        else:
            recipient.payments.append(payment)

        i += 1

    notification_request = NotificationRequest(organization_id=org_info.id, pago_pa_int_mode=pagopa_int_mode,
                                               sender_denomination=org_info.name, recipients=recipients)

    send_token = step_send_token(pagopa_interaction=org_info.pagopa_interaction)
    context.send_token = send_token

    res = post_create_send_notification(token=send_token, payload=notification_request.to_json())

    print(notification_request.to_json())
    print(res.json())
    assert res.status_code == 200
    assert res.json()['sendNotificationId'] is not None
    assert res.json()['status'] == SendStatus.WAITING.value

    context.send_notification_id = res.json()['sendNotificationId']
    context.installments_notified = installments_notified


@when("the organization requires the notification to be uploaded to SEND")
def step_upload_notification_file(context):
    send_token = context.send_token
    org_id = context.org_info.id
    notification_id = context.send_notification_id
    installments_notified = context.installments_notified

    notification_file_path = './bdd/steps/file_template/notification.pdf'

    res_notification_file = post_upload_send_file(token=send_token, org_id=org_id, notification_id=notification_id,
                                                  file_path=notification_file_path,
                                                  digest=SendPdfDigest.notification_pdf_digest)

    assert res_notification_file.status_code == 202



    workflow_id = ''
    for i in range(1, len(installments_notified) + 1):
        payment_file_path = f'./bdd/steps/file_template/payment_{i}.pdf'
        res_payment_file = post_upload_send_file(token=send_token, org_id=org_id, notification_id=notification_id,
                                                 file_path=payment_file_path, digest=SendPdfDigest.payment_pdf_digest)

        if i == len(installments_notified):
            assert res_payment_file.status_code == 200
            assert res_payment_file.json()['workflowId'] is not None
            workflow_id = res_payment_file.json()['workflowId']
        else:
            assert res_payment_file.status_code == 202

    time.sleep(5)
    res_status = get_send_notification_status(token=send_token, notification_id=notification_id)

    assert res_status.status_code == 200
    assert res_status.json()['status'] == SendStatus.COMPLETE.value
    assert res_status.json().get('iun') is None

    retry_get_workflow_status(token=context.token, workflow_id=workflow_id,
                              status=WorkflowStatus.COMPLETED,
                              tries=16, delay=30)


@then("the notification is in status {status} and the IUN is assigned to the installment")
@then("the notification is in status {status} and the IUN is assigned to all installments")
def step_check_iun(context, status):
    notification_id = context.send_notification_id
    installments_notified = context.installments_notified

    res_status = get_send_notification_status(token=context.send_token, notification_id=notification_id)

    assert res_status.status_code == 200
    assert res_status.json()['status'] == status.upper()
    assert res_status.json()['iun'] is not None

    for installment in installments_notified:
        res = get_installment(token=context.token, installment_id=installment.installment_id)

        assert res.status_code == 200
        assert res.json()['iun'] == res_status.json()['iun']

    check_workflow_status(context=context, workflow_type=WorkflowType.SEND_NOTIFICATION_DATE_RETRIEVE,
                          entity_id=notification_id, status=WorkflowStatus.RUNNING)


@then("SEND has set a notification fee")
def step_check_notification_fee(context):
    installments_notified = context.installments_notified

    res_fee = get_send_notification_fee(token=context.send_token, nav=installments_notified[0].nav,
                                        org_id=context.org_info.id)

    assert res_fee.status_code == 200
    assert res_fee.json()['totalPrice'] is not None

    context.notification_fee = res_fee.json()['totalPrice']


@then("the amount of installment is increased by the notification fee")
def step_check_installment_amount_with_fee(context):
    installments_notified = context.installments_notified
    installment_paid = context.installment_paid

    for installment in installments_notified:
        if installment_paid.installment_id == installment.installment_id:
            previous_amount = installment.amount_cents
            expected_amount = previous_amount + context.notification_fee

            res = get_installment(token=context.token, installment_id=installment.installment_id)

            assert res.status_code == 200
            assert res.json()['notificationFeeCents'] == context.notification_fee
            assert res.json()['amountCents'] == expected_amount
