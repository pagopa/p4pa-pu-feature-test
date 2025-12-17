from behave import then

from api.gpd_aca import get_debt_position_on_aca, get_debt_position_on_gpd
from bdd.steps.authentication_step import PagoPaInteractionModel
from config.configuration import secrets


def check_presence_debt_position_in_gpd(org_fiscal_code, debt_position, status):
    for po in debt_position.payment_options:
        for installment in po.installments:
            res = get_debt_position_on_gpd(org_fiscal_code=org_fiscal_code, iupd_pagopa=installment.iupd_pagopa)
            assert res.status_code == 200
            assert res.json()['status'] == status.upper()


def check_presence_debt_position_in_aca(org_fiscal_code, debt_position, status):
    for po in debt_position.payment_options:
        for installment in po.installments:
            res = get_debt_position_on_aca(org_fiscal_code=org_fiscal_code, iupd_pagopa=installment.iupd_pagopa)
            assert res.status_code == 200
            assert res.json()['status'] == status.upper()


@then("the notice is present in {pagopa_interaction} archive in status {status}")
@then("the notices are present in {pagopa_interaction} archive in status {status}")
def step_verify_presence_debt_position_in_gpd_or_aca(context, pagopa_interaction, status):
    debt_position = context.debt_position

    if pagopa_interaction == PagoPaInteractionModel.ACA.value:
        check_presence_debt_position_in_aca(context.org_info.fiscal_code, debt_position, status)
    elif pagopa_interaction == PagoPaInteractionModel.GPD.value:
        check_presence_debt_position_in_gpd(context.org_info.fiscal_code, debt_position, status)


@then("the notices of each debt positions are present in GPD archive in status {status}")
def step_verify_presence_debt_positions_in_gpd(context, status):
    org_fiscal_code = secrets.organization.gpd.fiscal_code

    debt_positions = context.debt_positions_created

    for debt_position in debt_positions:
        check_presence_debt_position_in_gpd(org_fiscal_code=org_fiscal_code, debt_position=debt_position, status=status)
