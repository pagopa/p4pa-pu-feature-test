import time
from dataclasses import dataclass
from enum import Enum

from behave import given, when, then

from api.auth import post_send_auth_token
from api.debt_positions import get_installment
from api.send import post_create_send_notification, post_upload_send_file, get_send_notification_status
from bdd.steps.authentication_step import PagoPaInteractionModel
from bdd.steps.utils.debt_position_utility import find_installment_by_seq_num_and_po_index
from bdd.steps.utils.utility import retry_get_workflow_status
from bdd.steps.workflow_step import check_workflow_status
from config.configuration import secrets
from model.workflow_hub import WorkflowStatus, WorkflowType


@dataclass
class SendStatus(Enum):
    WAITING = 'WAITING_FILE'
    SENDING = 'SENDING'
    REGISTERED = 'REGISTERED'
    COMPLETE = 'COMPLETE'
    ACCEPTED = 'ACCEPTED'


notification_pdf_digest = "YSxsCpvZHvwL8IIosWJBUDjgUwa01sBHu6Cj4laQRLA="
payment_pdf_digest = "45Iba3tn9Dfm7TX+AbtWDR1csMuHgEbrHi/zZr6DjHU="


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


@given("a notification created for the installment {seq_num} of payment option {po_index}")
def step_create_send_notification(context, seq_num, po_index):
    debt_position = context.debt_position
    installment = find_installment_by_seq_num_and_po_index(debt_position=debt_position,
                                                           po_index=int(po_index), seq_num=int(seq_num))
    context.installment = installment

    org_info = context.org_info

    pagopa_int_mode = None
    match org_info.pagopa_interaction:
        case PagoPaInteractionModel.GPD.value:
            pagopa_int_mode = 'ASYNC'
        case PagoPaInteractionModel.ACA.value:
            pagopa_int_mode = 'SYNC'


    payload = {
        "organizationId": org_info.id,
        "paProtocolNumber": "Prot_001",
        "recipient": {
            "recipientType": "PF",
            "taxId": secrets.send_info.citizen.fiscal_code,
            "denomination": "Michelangelo Buonarroti",
            "physicalAddress": {
                "address": "Via Larga 10",
                "zip": "00186",
                "municipality": "Roma",
                "province": "RM"
            },
            "payments": [{
                "pagoPa": {
                    "noticeCode": installment.nav,
                    "creditorTaxId": org_info.fiscal_code,
                    "applyCost": True,
                    "attachment": {
                        "fileName": "payment.pdf",
                        "contentType": "application/pdf",
                        "digest": payment_pdf_digest
                    }
                }
            }]
        },
        "documents": [{
            "fileName": "notification.pdf",
            "contentType": "application/pdf",
            "digest": notification_pdf_digest
        }],
        "notificationFeePolicy": "DELIVERY_MODE",
        "physicalCommunicationType": "AR_REGISTERED_LETTER",
        "senderDenomination": "Ente Intermediario 2",
        "senderTaxId": "00000000018",
        "amount": 0,
        "paymentExpirationDate": str(installment.due_date),
        "taxonomyCode": "010101P",
        "paFee": 100,
        "vat": 22,
        "pagoPaIntMode": pagopa_int_mode
    }

    send_token = step_send_token(pagopa_interaction=org_info.pagopa_interaction)
    context.send_token = send_token

    res = post_create_send_notification(token=send_token, payload=payload)

    assert res.status_code == 200
    assert res.json()['sendNotificationId'] is not None
    assert res.json()['status'] == SendStatus.WAITING.value

    context.send_notification_id = res.json()['sendNotificationId']


@when("the organization requires the notification to be uploaded to SEND")
def step_upload_notification_file(context):
    send_token = context.send_token
    org_id = context.org_info.id
    notification_id = context.send_notification_id

    notification_file_path = './bdd/steps/file_template/notification.pdf'

    res_notification_file = post_upload_send_file(token=send_token, org_id=org_id, notification_id=notification_id,
                                                  file_path=notification_file_path, digest=notification_pdf_digest)

    assert res_notification_file.status_code == 202

    payment_file_path = './bdd/steps/file_template/payment.pdf'

    res_payment_file = post_upload_send_file(token=send_token, org_id=org_id, notification_id=notification_id,
                                             file_path=payment_file_path, digest=payment_pdf_digest)

    assert res_payment_file.status_code == 200
    assert res_payment_file.json()['workflowId'] is not None

    time.sleep(5)
    res_status = get_send_notification_status(token=send_token, notification_id=notification_id)

    assert res_status.status_code == 200
    assert res_status.json()['status'] == SendStatus.COMPLETE.value
    assert res_status.json().get('iun') is None

    retry_get_workflow_status(token=send_token, workflow_id=res_payment_file.json()['workflowId'],
                              status=WorkflowStatus.COMPLETED,
                              tries=12, delay=30)


@then("the notification is in status {status} and the IUN is assigned to the installment")
def step_impl(context, status):
    send_token = context.send_token
    notification_id = context.send_notification_id

    res_status = get_send_notification_status(token=send_token, notification_id=notification_id)

    assert res_status.status_code == 200
    assert res_status.json()['status'] == SendStatus.ACCEPTED.value
    assert res_status.json()['iun'] is not None

    res = get_installment(token=context.token, installment_id=context.installment.installment_id)

    assert res.status_code == 200
    assert res.json()['iun'] == res_status.json()['iun']

    check_workflow_status(context=context, workflow_type=WorkflowType.SEND_NOTIFICATION_DATE_RETRIEVE,
                          entity_id=notification_id, status=WorkflowStatus.RUNNING)
