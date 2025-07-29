import xmltodict
from behave import when, then

from api.debt_positions import get_installment, get_receipt
from api.soap.nodo import verify_payment_notice, activate_payment_notice, send_payment_outcome, PSP
from bdd.steps.utils.debt_position_utility import find_installment_by_seq_num_and_po_index
from bdd.steps.utils.utility import retry_get_process_file_status
from bdd.steps.workflow_step import check_workflow_status
from config.configuration import secrets
from model.file import FilePathName, FileStatus, ReceiptOriginType
from model.workflow_hub import WorkflowType, WorkflowStatus

psp_info = secrets.payment_info.psp


def check_res_ok_and_get_body(response_content, tag_name):
    res_parsed = xmltodict.parse(response_content.decode('utf-8'))
    res_body = res_parsed['soapenv:Envelope']['soapenv:Body'][f'nfp:{tag_name}']
    assert res_body['outcome'] == 'OK'
    return res_body


@when('the citizen pays the installment of payment option {po_index}')
@when('the citizen pays the installment {seq_num} of payment option {po_index}')
@when('the citizen pays the installment')
def step_installment_payment(context, po_index='1', seq_num='1'):
    citizen_info = secrets.citizen_info.X
    psp = PSP(id=psp_info.id, id_broker=psp_info.id_broker, id_channel=psp_info.id_channel, password=psp_info.password)

    org_info = context.org_info
    debt_position = context.debt_position
    installment = find_installment_by_seq_num_and_po_index(debt_position=debt_position,
                                                           po_index=int(po_index), seq_num=int(seq_num))

    res_verify_payment = verify_payment_notice(psp=psp, org_fiscal_code=org_info.fiscal_code, iuv=installment.iuv)
    assert res_verify_payment.status_code == 200
    res_verify_payment_body = check_res_ok_and_get_body(res_verify_payment.content, tag_name='verifyPaymentNoticeRes')

    amount = res_verify_payment_body["paymentList"]["paymentOptionDescription"]["amount"]
    due_date = res_verify_payment_body["paymentList"]["paymentOptionDescription"]["dueDate"]

    res_activate_payment = activate_payment_notice(psp=psp, org_fiscal_code=org_info.fiscal_code, iuv=installment.iuv,
                                                   amount=amount, due_date=due_date)
    assert res_activate_payment.status_code == 200
    res_activate_payment_body = check_res_ok_and_get_body(response_content=res_activate_payment.content,
                                                          tag_name='activatePaymentNoticeRes')

    payment_token = res_activate_payment_body["paymentToken"]

    res_send_outcome = send_payment_outcome(psp=psp, payment_token=payment_token,
                                            citizen_fiscal_code=citizen_info.fiscal_code,
                                            citizen_name=citizen_info.name,
                                            citizen_email=citizen_info.email)
    assert res_send_outcome.status_code == 200
    check_res_ok_and_get_body(response_content=res_send_outcome.content, tag_name='sendPaymentOutcomeRes')

    context.installment_paid = installment


@then("the receipt is processed correctly")
def step_check_receipt_processed(context):
    installment_paid = context.installment_paid
    org_info = context.org_info

    file_path_name = FilePathName.RECEIPT_PAGOPA
    file_name = 'RT_' + installment_paid.nav + '.xml'

    retry_get_process_file_status(token=context.token, organization_id=org_info.id,
                                  file_path_name=file_path_name, file_name=file_name, status=FileStatus.COMPLETED)

    res = get_installment(token=context.token, installment_id=installment_paid.installment_id)

    assert res.status_code == 200
    assert res.json()['iur'] is not None and res.json()['receiptId'] is not None
    installment_paid.iur = res.json()['iur']
    installment_paid.receipt_id = res.json()['receiptId']

    context.installment_paid = installment_paid

    check_workflow_status(context=context, workflow_type=WorkflowType.TRANSFER_CLASSIFICATION,
                          entity_id=str(org_info.id) + '-' + installment_paid.iuv + '-' + res.json()['iur'] + '-1',
                          status=WorkflowStatus.COMPLETED)

    check_workflow_status(context=context, workflow_type=WorkflowType.IUD_CLASSIFICATION,
                          entity_id=str(org_info.id) + '-' + installment_paid.iud, status=WorkflowStatus.COMPLETED)


@then("the receipt is created correctly")
def step_check_receipt_created(context):
    installment_paid = context.installment_paid
    org_info = context.org_info

    res = get_receipt(token=context.token, organization_id=org_info.id,
                      receipt_origin=ReceiptOriginType.PAYMENTS_REPORTING.value, iuv=installment_paid.iuv,
                      iur=installment_paid.iur)

    assert res.status_code == 200
    assert len(res.json()['content']) == 1
    receipt = res.json()['content'][0]
    assert receipt['receiptOrigin'] == ReceiptOriginType.PAYMENTS_REPORTING.value
    assert installment_paid.iuv == receipt['iuv']

    res = get_installment(token=context.token, installment_id=installment_paid.installment_id)

    assert res.status_code == 200
    assert res.json()['iur'] is not None and res.json()['receiptId'] is not None and receipt['receiptId'] == res.json()['receiptId']
    installment_paid.iur = res.json()['iur']

    check_workflow_status(context=context, workflow_type=WorkflowType.TRANSFER_CLASSIFICATION,
                          entity_id=str(org_info.id) + '-' + installment_paid.iuv + '-' + installment_paid.iur + '-1',
                          status=WorkflowStatus.COMPLETED)

    check_workflow_status(context=context, workflow_type=WorkflowType.IUD_CLASSIFICATION,
                          entity_id=str(org_info.id) + '-' + installment_paid.iud, status=WorkflowStatus.COMPLETED)
