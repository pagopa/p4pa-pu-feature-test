from datetime import datetime

from behave import given, then

from api.classifications import get_classification
from bdd.steps.debt_positions_step import step_check_po_status, step_check_installment_status, step_check_dp_status
from bdd.steps.payments_reporting_step import step_upload_payment_reporting_file, \
    step_check_payment_reporting_processed, get_payment_reporting_flow
from bdd.steps.payments_step import step_installment_payment, step_check_receipt_processed
from bdd.steps.treasury_step import step_upload_treasury_file, step_check_treasury_processed
from bdd.steps.utils.assertions import assert_response_ok
from bdd.steps.utils.debt_position_utility import get_installment_paid
from model.debt_position import Status


@then("the classification labels are {labels}")
@then("the classification labels for each transfer are {labels}")
@then("the classification labels related to payment reporting with outcome code {outcome_code} are {labels}")
def step_check_classification(context, labels: str, outcome_code: str = None):
    date_now = datetime.now().strftime('%Y-%m-%d')

    if outcome_code is not None:
        flow = get_payment_reporting_flow(context, outcome_code)
        installment = flow['installment']
        iuf = flow['iuf']
        iur = flow['iur']
    else:
        installment = get_installment_paid(context)
        iuf = None
        iur = None

    expected_labels = sorted(labels.split(sep=', '))

    res = get_classification(token=context.token, traceparent=context.traceparent,
                             last_classification_date_from=date_now, last_classification_date_to=date_now,
                             organization_id=context.org_info.id, iuv=installment.iuv, iuf=iuf, iur=iur)

    assert_response_ok(res, "Get classification by IUV, IUF and IUR")
    classifications = res.json()['content']
    assert len(classifications) != 0

    classification_transfer_map = {}
    for classification in classifications:
        classification_transfer_map.setdefault(classification['transferIndex'], []).append(classification)

    for transfer in installment.transfers:
        actual_labels = sorted(cl['label'] for cl in classification_transfer_map.get(transfer.transfer_index, []))
        assert actual_labels == expected_labels, (
            f"Transfer {transfer.transfer_index}"
            + (f", payment reporting outcome {outcome_code}" if outcome_code is not None else "")
            + f": Expected {expected_labels}, found {actual_labels}"
        )


@given(
    "the previous payment of installment {seq_num} of payment option {po_index}")
def step_pay_installment_and_verify(context, seq_num, po_index):
    step_installment_payment(context=context, po_index=po_index, seq_num=seq_num)

    step_check_receipt_processed(context=context)
    invalid_po_indexes = [po.payment_option_index for po in context.debt_position.payment_options if
                          po.payment_option_index != int(po_index)]
    for i in invalid_po_indexes:
        step_check_po_status(context=context, po_index=str(i), status=Status.INVALID.value)

    step_upload_payment_reporting_file(context=context, po_index=po_index, seq_num=seq_num)
    step_check_payment_reporting_processed(context=context)
    step_check_installment_status(context=context, installment_seq_num=seq_num, po_index=po_index,
                                  status=Status.REPORTED.value)

    step_upload_treasury_file(context=context, po_index=po_index, installment_seq_num=seq_num)
    step_check_treasury_processed(context=context)

    step_check_po_status(context=context, po_index=po_index, status=Status.PARTIALLY_PAID.value)
    step_check_dp_status(context=context, status=Status.PARTIALLY_PAID.value)
    step_check_classification(context=context, labels='RT_NO_IUD, RT_IUF, RT_IUF_TES')