import time

from behave import given, when, then

from api.auth import post_external_auth_token
from api.debt_positions import get_installment
from api.send import post_create_send_notification, post_upload_send_file, get_send_notification, \
    get_send_notification_fee
from bdd.steps.authentication_step import PagoPaInteractionModel
from bdd.steps.utils.assertions import assert_response_ok
from bdd.steps.utils.debt_position_utility import find_installment_by_seq_num_and_po_index, get_installment_paid, \
    seq_num_of, FEATURE_TEST_IUD_PREFIX, get_stored_debt_position
from bdd.steps.utils.utility import retry_get_workflow_status, retry_get_valid_send_notification
from config.configuration import secrets
from model.send_notification import SendStatus, SendPdfDigest, NotificationRequest, PaymentData, Recipient, Payment, \
    Document
from model.workflow_hub import WorkflowStatus


def step_send_token(pagopa_interaction: PagoPaInteractionModel, traceparent: str) -> str:
    client = None
    match pagopa_interaction:
        case PagoPaInteractionModel.ACA.value:
            client = secrets.send_info.aca
        case PagoPaInteractionModel.GPD.value:
            client = secrets.send_info.gpd

    res = post_external_auth_token(client_id=client.client_id, client_secret=client.client_secret,
                                   traceparent=traceparent)

    assert_response_ok(res, "Post external auth token")
    assert res.json()['access_token'] is not None

    return res.json()['access_token']


@given("a notification created for the single installment of debt position {dp_identifiers}")
@given("a notification created for the single installment of debt positions {dp_identifiers}")
@given("a notification created for the {installments_size} installments of debt positions {dp_identifiers}")
def step_create_send_notification(context, dp_identifiers, installments_size=1):
    """Creates a SEND notification for the selected installments. It:

    - builds the notification request (recipients and pagoPA payments) for the given debt positions;
    - gets a SEND token and posts the notification;
    - asserts the call succeeds and the notification is created in status `WAITING`.
    """
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
        for seq_num in range(1, int(installments_size) + 1):
            installment = find_installment_by_seq_num_and_po_index(debt_position=get_stored_debt_position(context, dp_identifier),
                                                                   po_index=1, seq_num=seq_num)
            installments_notified.append(installment)

    recipients = []
    i = 1
    for installment in installments_notified:
        document = Document(file_name=f'payment_{i}.pdf', content_type='application/pdf',
                            digest=SendPdfDigest.payment_pdf_digest)
        payment_data = PaymentData(notice_code=installment.nav, creditor_tax_id=org_info.fiscal_code,
                                   attachment=document)
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

    send_token = step_send_token(pagopa_interaction=org_info.pagopa_interaction, traceparent=context.traceparent)
    context.send_token = send_token

    res = post_create_send_notification(token=send_token, traceparent=context.traceparent,
                                        payload=notification_request.to_json())

    assert_response_ok(res, "Create SEND notification")
    assert res.json()['sendNotificationId'] is not None
    assert res.json()['status'] == SendStatus.WAITING.value

    context.send_notification_id = res.json()['sendNotificationId']
    context.installments_notified = installments_notified


@when("the organization requires the notification to be uploaded to SEND")
def step_upload_notification_file(context):
    """Uploads the notification and payment PDFs to SEND. It:

    - uploads the notification file and one payment file per notified installment;
    - reads the workflow id from the last upload;
    - checks the notification moves to `IN_VALIDATION` with no IUN yet;
    - waits for the upload workflow to complete.
    """
    send_token = context.send_token
    org_id = context.org_info.id
    notification_id = context.send_notification_id
    installments_notified = context.installments_notified

    notification_file_path = './bdd/steps/file_template/notification.pdf'

    res_notification_file = post_upload_send_file(token=send_token, traceparent=context.traceparent,
                                                  org_id=org_id, notification_id=notification_id,
                                                  file_path=notification_file_path,
                                                  digest=SendPdfDigest.notification_pdf_digest)

    assert_response_ok(res_notification_file, "Upload notification file to SEND", expected_status=202)

    workflow_id = ''
    for i in range(1, len(installments_notified) + 1):
        payment_file_path = f'./bdd/steps/file_template/payment_{i}.pdf'
        res_payment_file = post_upload_send_file(token=send_token, traceparent=context.traceparent,
                                                 org_id=org_id, notification_id=notification_id,
                                                 file_path=payment_file_path, digest=SendPdfDigest.payment_pdf_digest)

        if i == len(installments_notified):
            assert_response_ok(res_payment_file, "Upload last payment file to SEND")
            assert res_payment_file.json()['workflowId'] is not None
            workflow_id = res_payment_file.json()['workflowId']
        else:
            assert_response_ok(res_payment_file, "Upload payment file to SEND", expected_status=202)

    time.sleep(5)
    res_status = get_send_notification(token=send_token, traceparent=context.traceparent,
                                       notification_id=notification_id)

    assert_response_ok(res_status, "Get SEND notification")
    assert res_status.json()['status'] == SendStatus.IN_VALIDATION.value
    assert res_status.json().get('iun') is None

    retry_get_workflow_status(token=context.token, traceparent=context.traceparent, workflow_id=workflow_id,
                              status=WorkflowStatus.COMPLETED)


@then("the notification is in status {status} and the IUN is assigned to the installment")
@then("the notification is in status {status} and the IUN is assigned to all installments")
def step_check_iun(context, status):
    """Checks that the notification is valid and the IUN is assigned. It:

    - polls SEND until the notification is valid and asserts it has an IUN;
    - verifies that every notified installment carries that same IUN.
    """
    notification_id = context.send_notification_id
    installments_notified = context.installments_notified

    res_status = retry_get_valid_send_notification(token=context.send_token, traceparent=context.traceparent,
                                                   notification_id=notification_id, tries=10, delay=60)

    assert_response_ok(res_status, "Get valid SEND notification")
    assert res_status.json()['iun'] is not None

    for installment in installments_notified:
        res = get_installment(token=context.token, traceparent=context.traceparent,
                              installment_id=installment.installment_id)

        assert_response_ok(res, "Get installment by id")
        assert res.json()['iun'] == res_status.json()['iun']


@then("SEND has set a notification fee")
def step_check_notification_fee(context):
    """Checks that SEND set a notification fee:
    - reads the fee for each notified installment;
    - asserts it is present and that all installments share the same fee."""
    installments_notified = context.installments_notified

    notification_fee = {}
    i = 1
    for installment in installments_notified:
        res_fee = get_send_notification_fee(token=context.send_token, traceparent=context.traceparent,
                                            nav=installment.nav, org_id=context.org_info.id)

        assert_response_ok(res_fee, "Get SEND notification fee")
        assert res_fee.json()['totalPrice'] is not None
        notification_fee[i] = res_fee.json()['totalPrice']
        if i != 1:
            assert notification_fee[i] == notification_fee[i - 1]
        i += 1

    context.notification_fee = notification_fee[1]


@then("the amount of installment of debt position {dp_identifier} is increased by the notification fee")
@then("the amount of installment {seq_num} of debt position {dp_identifier} is increased by the notification fee")
def step_check_installment_amount_with_fee(context, dp_identifier, seq_num='1'):
    """Checks that the notified installment's amount was increased by the notification fee (both `notificationFeeCents` and `amountCents`)."""
    installments_notified = context.installments_notified
    installment_paid = get_installment_paid(context, dp_identifier)

    for installment in installments_notified:
        if (installment_paid.installment_id == installment.installment_id and
                installment.iud.startswith(FEATURE_TEST_IUD_PREFIX) and seq_num_of(installment.iud) == int(seq_num)):
            previous_amount = installment.amount_cents
            expected_amount = previous_amount + context.notification_fee

            res = get_installment(token=context.token, traceparent=context.traceparent,
                                  installment_id=installment.installment_id)

            assert_response_ok(res, "Get installment by id")
            assert res.json()['notificationFeeCents'] == context.notification_fee
            assert res.json()['amountCents'] == expected_amount
