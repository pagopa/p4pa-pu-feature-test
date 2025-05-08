from behave import then

from api.gpd_aca import get_debt_position_on_aca
from bdd.steps.utils.debt_position_utility import retrieve_iuv_list, calculate_amount_first_transfer
from config.configuration import secrets
from model.debt_position import Transfer, Installment


@then("the notice is present in ACA archive in status {status}")
@then("the notices are present in ACA archive in status {status}")
def step_verify_presence_debt_position_in_aca(context, status):
    org_fiscal_code = secrets.organization.aca.fiscal_code

    iuv_list = retrieve_iuv_list(debt_position=context.debt_position)

    for iuv in iuv_list:
        res = get_debt_position_on_aca(org_fiscal_code=org_fiscal_code, iuv=iuv)
        assert res.status_code == 200
        assert res.json()['status'] == status.upper()
