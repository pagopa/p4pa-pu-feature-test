from api.debt_positions import get_debt_position
from bdd.steps.utils.assertions import assert_response_ok
from model.debt_position import DebtPosition


def set_installment_paid(context, installment, dp_identifier=None):
    context.installments_paid_by_id[dp_identifier] = installment


def get_installment_paid(context, dp_identifier=None):
    return context.installments_paid_by_id[dp_identifier]


def fetch_debt_position(context, debt_position_id=None) -> DebtPosition:
    debt_position_id = debt_position_id if debt_position_id is not None else context.debt_position.debt_position_id
    res = get_debt_position(token=context.token, traceparent=context.traceparent, debt_position_id=debt_position_id)

    assert_response_ok(res, "Get debt position by id")
    return DebtPosition.from_dict(res.json())
