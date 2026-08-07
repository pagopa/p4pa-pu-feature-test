import xmltodict
from behave import given, when, then

from api.debt_positions import get_installment, get_receipt, get_receipt_by_iur
from api.soap.nodo import verify_payment_notice, activate_payment_notice, send_payment_outcome, PSP
from bdd.steps.debt_positions_step import step_check_dp_status
from bdd.steps.utils.assertions import assert_response_ok
from bdd.steps.utils.debt_position_utility import find_installment_by_seq_num_and_po_index, find_mixed_installment, \
    get_installment_paid, set_installment_paid, get_stored_debt_position
from bdd.steps.utils.utility import retry_get_process_file_status
from bdd.steps.workflow_step import check_workflow_status
from config.configuration import secrets
from model.debt_position import Status
from model.file import FilePathName, FileStatus, ReceiptOriginType
from model.workflow_hub import WorkflowType, WorkflowStatus

psp_info = secrets.payment_info.psp


def check_res_ok_and_get_body(response_content, tag_name):
    res_parsed = xmltodict.parse(response_content.decode('utf-8'))
    res_body = res_parsed['soapenv:Envelope']['soapenv:Body'][f'nfp:{tag_name}']
    assert res_body['outcome'] == 'OK'
    return res_body


@when("the citizen pays the installment of payment option {po_index}")
@when("the citizen pays the installment {seq_num} of payment option {po_index}")
@when("the citizen {citizen_identifier} pays the installment of debt position {dp_identifier}")
@when("the citizen pays the installment {seq_num} of debt position {dp_identifier}")
def step_installment_payment(context, po_index='1', seq_num='1', citizen_identifier='X', dp_identifier=None,
                             installment_to_paid=None):
    """Simulates the citizen paying the installment through the pagoPA node. It:

    - verifies the payment notice (`verifyPaymentNotice`) and reads amount/due date;
    - activates the payment notice (`activatePaymentNotice`) and gets a payment token;
    - sends the payment outcome (`sendPaymentOutcome`), each call expected to return `OK`"""
    citizen_info = secrets.citizen_info.get(citizen_identifier)
    psp = PSP(id=psp_info.id, id_broker=psp_info.id_broker, id_channel=psp_info.id_channel, password=psp_info.password)

    org_fiscal_code = context.org_info.fiscal_code
    debt_position = get_stored_debt_position(context, dp_identifier)
    installment = installment_to_paid if installment_to_paid is not None else (find_installment_by_seq_num_and_po_index(
        debt_position=debt_position,
        po_index=int(po_index), seq_num=int(seq_num)))

    res_verify_payment = verify_payment_notice(psp=psp, org_fiscal_code=org_fiscal_code, nav=installment.nav)

    assert_response_ok(res_verify_payment, "Verify payment notice")
    res_verify_payment_body = check_res_ok_and_get_body(res_verify_payment.content, tag_name='verifyPaymentNoticeRes')

    amount = res_verify_payment_body["paymentList"]["paymentOptionDescription"]["amount"]
    due_date = res_verify_payment_body["paymentList"]["paymentOptionDescription"]["dueDate"]

    res_activate_payment = activate_payment_notice(psp=psp, org_fiscal_code=org_fiscal_code, nav=installment.nav,
                                                   amount=amount, due_date=due_date)
    assert_response_ok(res_activate_payment, "Activate payment notice")
    res_activate_payment_body = check_res_ok_and_get_body(response_content=res_activate_payment.content,
                                                          tag_name='activatePaymentNoticeV2Response')

    payment_token = res_activate_payment_body["paymentToken"]

    res_send_outcome = send_payment_outcome(psp=psp, payment_token=payment_token,
                                            citizen_fiscal_code=citizen_info.fiscal_code,
                                            citizen_name=citizen_info.name,
                                            citizen_email=citizen_info.email)

    assert_response_ok(res_send_outcome, "Send payment outcome")
    check_res_ok_and_get_body(response_content=res_send_outcome.content, tag_name='sendPaymentOutcomeV2Response')

    set_installment_paid(context, installment, dp_identifier)


@when("the citizen pays the installment of mixed debt position")
def step_pay_mixed_installment(context):
    installment = find_mixed_installment(context.debt_position)
    step_installment_payment(context=context, installment_to_paid=installment)


@then("the receipt is processed correctly")
@then("the receipt of debt position {dp_identifier} is processed correctly")
def step_check_receipt_processed(context, dp_identifier=None, organization_id=None):
    """Checks that the pagoPA receipt has been fully processed. It verifies that:

    - the receipt file `RT_<nav>.xml` reaches status `COMPLETED`;
    - the paid installment now has both `IUR` and `receiptId` set;
    - the async `TRANSFER_CLASSIFICATION` workflow completes;
    - the async `IUD_CLASSIFICATION` workflow completes."""

    installment_paid = get_installment_paid(context, dp_identifier)
    org_id = organization_id if organization_id is not None else context.org_info.id

    file_path_name = FilePathName.RECEIPT_PAGOPA
    file_name = 'RT_' + installment_paid.nav + '.xml'

    retry_get_process_file_status(token=context.token, traceparent=context.traceparent, organization_id=org_id,
                                  file_path_name=file_path_name, file_name=file_name, status=FileStatus.COMPLETED)

    res = get_installment(token=context.token, traceparent=context.traceparent,
                          installment_id=installment_paid.installment_id)

    assert_response_ok(res, "Get installment by id")
    assert res.json()['iur'] is not None and res.json()['receiptId'] is not None
    installment_paid.iur = res.json()['iur']
    installment_paid.receipt_id = res.json()['receiptId']

    set_installment_paid(context, installment_paid, dp_identifier)

    check_workflow_status(context=context, workflow_type=WorkflowType.TRANSFER_CLASSIFICATION,
                          entity_id=str(org_id) + '-' + installment_paid.iuv + '-' + installment_paid.iur + '-1',
                          status=WorkflowStatus.COMPLETED)

    check_workflow_status(context=context, workflow_type=WorkflowType.IUD_CLASSIFICATION,
                          entity_id=str(org_id) + '-' + installment_paid.iud, status=WorkflowStatus.COMPLETED)


@then("the receipts are created correctly with origin {receipt_origin}")
def step_check_receipts_created(context, receipt_origin: str = ReceiptOriginType.PAYMENTS_REPORTING.value):
    """Runs the `the receipt is created correctly` checks for every receipt imported from the file."""
    for i in range(context.receipts_rows_len):
        step_check_receipt_created(context=context, receipt_origin=receipt_origin,
                                   installment_paid=context.imported_installments[i])


@then("the receipt is created correctly with origin {receipt_origin}")
def step_check_receipt_created(context, receipt_origin: str = ReceiptOriginType.PAYMENTS_REPORTING.value,
                               installment_paid=None, is_duplicate: bool = False):
    """Checks that the receipt for the paid installment was created with the expected origin. It verifies that:

    - the receipt exists (looked up by IUV/IUR, or by IUR when it is a duplicate);
    - its `receiptOrigin` matches the expected one and it is linked to the installment (`receiptId`);
    - the `TRANSFER_CLASSIFICATION` workflow completes for each transfer;
    - the `IUD_CLASSIFICATION` workflow completes."""

    installment_paid = installment_paid if installment_paid else get_installment_paid(context)
    receipt_origin = ReceiptOriginType[receipt_origin.upper()].value
    org_info = context.org_info

    res = get_installment(token=context.token, traceparent=context.traceparent,
                          installment_id=installment_paid.installment_id)
    assert_response_ok(res, "Get installment by id")
    installment = res.json()

    if is_duplicate:
        res = get_receipt_by_iur(token=context.token, traceparent=context.traceparent, iur=installment_paid.iur)
        assert_response_ok(res, "Get receipt by IUR")
        receipt = res.json()
        assert receipt['receiptOrigin'] == receipt_origin
        assert installment['iur'] != installment_paid.iur
    else:
        res = get_receipt(token=context.token, traceparent=context.traceparent, organization_id=org_info.id,
                          receipt_origin=receipt_origin, iuv=installment_paid.iuv,
                          iur=installment_paid.iur)
        assert_response_ok(res, "Get receipt by IUV and IUR")
        assert len(res.json()['content']) == 1, \
            f"Expected exactly 1 receipt for IUV {installment_paid.iuv} / IUR {installment_paid.iur}, got {len(res.json()['content'])}"
        receipt = res.json()['content'][0]
        assert receipt['receiptOrigin'] == receipt_origin
        assert installment_paid.iuv == receipt['iuv']
        assert installment['iur'] is not None and installment['receiptId'] is not None \
               and receipt['receiptId'] == installment['receiptId']
        installment_paid.iur = installment['iur']

    for transfer in installment_paid.transfers:
        check_workflow_status(context=context, workflow_type=WorkflowType.TRANSFER_CLASSIFICATION,
                              entity_id=str(
                                  org_info.id) + '-' + installment_paid.iuv + '-' + installment_paid.iur + '-' + str(
                                  transfer.transfer_index),
                              status=WorkflowStatus.COMPLETED)

    check_workflow_status(context=context, workflow_type=WorkflowType.IUD_CLASSIFICATION,
                          entity_id=str(org_info.id) + '-' + installment_paid.iud, status=WorkflowStatus.COMPLETED)


@given("the successful payment of the installment")
def step_successful_installment_payment(context):
    """Performs a full successful payment in one step:

    - pays the installment,
    - checks the debt position becomes `PAID`
    - checks the receipt is processed correctly."""
    step_installment_payment(context=context)
    step_check_dp_status(context=context, status=Status.PAID.value)
    step_check_receipt_processed(context=context)


@given("the successful payment of the installment created outside PU")
def step_successful_installment_payment_outside_pu(context):
    """Like `the successful payment of the installment`, but pays the first installment of a debt
    position created outside PU, then checks the `PAID` status and that the receipt is processed."""
    step_installment_payment(context=context, installment_to_paid=context.debt_position.payment_options[0].installments[0])
    step_check_dp_status(context=context, status=Status.PAID.value)
    step_check_receipt_processed(context=context)