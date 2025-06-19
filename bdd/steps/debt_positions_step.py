import json

from behave import given
from behave import then
from behave import when

from api.debt_positions import post_create_debt_position, get_debt_position
from bdd.steps.authentication_step import get_token_org, PagoPaInteractionModel
from bdd.steps.classification_step import step_check_classification
from bdd.steps.gpd_aca_step import step_verify_presence_debt_position_in_aca
from bdd.steps.payments_reporting_step import step_upload_payment_reporting_file, step_check_payment_reporting_processed
from bdd.steps.payments_step import step_installment_payment, step_check_receipt_processed
from bdd.steps.treasury_step import step_check_treasury_processed
from bdd.steps.treasury_step import step_upload_treasury_file
from bdd.steps.utils.debt_position_utility import calculate_po_total_amount, calculate_amount_first_transfer, \
    find_installment_by_seq_num_and_po_index, find_payment_option_by_po_index, create_debt_position, \
    create_payment_option, create_installment
from bdd.steps.utils.utility import retrieve_org_id_by_ipa_code
from bdd.steps.workflow_step import check_workflow_status, step_debt_position_workflow_check_expiration
from config.configuration import settings
from model.debt_position import DebtPosition, Installment, Status, PaymentOptionType
from model.workflow_hub import WorkflowStatus


@given("a new debt position of type TEST")
def step_create_dp_entity(context):
    token = context.token

    organization_id = retrieve_org_id_by_ipa_code(token=token, ipa_code=context.org_info.ipa_code)
    context.org_info['id'] = organization_id

    debt_position = create_debt_position(token=token, organization_id=organization_id,
                                         debt_position_type_org_code=settings.debt_position_type_org_code)

    context.debt_position = debt_position


@given(
    "payment option {po_index} with single installment of {amount} euros with due date set in {expiration_days} days")
def step_create_po_and_single_inst_entities(context, po_index, amount, expiration_days):
    payment_option = create_payment_option(po_index=int(po_index),
                                           payment_option_type=PaymentOptionType.SINGLE_INSTALLMENT)

    amount_cents = int(amount) * 100
    installment = create_installment(amount_cents=amount_cents, expiration_days=int(expiration_days), seq_num=1)
    payment_option.installments.append(installment)

    context.debt_position.payment_options.append(payment_option)


@given(
    "payment option {po_index} with {installments_size} installments with due date set in {expiration_days} days")
def step_create_po_and_inst_entities(context, po_index, installments_size, expiration_days):
    payment_option = create_payment_option(po_index=int(po_index), payment_option_type=PaymentOptionType.INSTALLMENTS)

    for i in range(int(installments_size)):
        installment = create_installment(expiration_days=int(expiration_days), seq_num=i + 1)
        payment_option.installments.append(installment)

    context.debt_position.payment_options.append(payment_option)


@when("the organization creates the debt position")
def step_create_dp(context):
    token = context.token
    debt_position = context.debt_position

    res = post_create_debt_position(token=token, debt_position=debt_position.to_json())

    assert res.status_code == 200

    validate_debt_position_created(org_info=context.org_info, debt_position_request=debt_position, debt_position_response=res.json(),
                                   status=Status.TO_SYNC)

    context.debt_position = DebtPosition.from_dict(res.json())

    check_workflow_status(context=context, workflow_type=context.org_info.workflow_type,
                          entity_id=context.debt_position.debt_position_id, status=WorkflowStatus.COMPLETED)


@then("the debt position is in status {status}")
def step_check_dp_status(context, status):
    token = context.token
    debt_position_id = context.debt_position.debt_position_id

    res = get_debt_position(token=token, debt_position_id=debt_position_id)

    assert res.status_code == 200
    assert res.json()['status'] == status.upper()


@then("the payment option {po_index} is in status {status}")
def step_check_po_status(context, po_index, status):
    token = context.token
    debt_position_id = context.debt_position.debt_position_id

    res = get_debt_position(token=token, debt_position_id=debt_position_id)
    assert res.status_code == 200

    debt_position = DebtPosition.from_dict(res.json())

    payment_option = find_payment_option_by_po_index(debt_position=debt_position, po_index=int(po_index))

    assert payment_option.status.value == status.upper()


@then("the installment of payment option {po_index} is in status {status}")
@then("the installment {installment_seq_num} of payment option {po_index} is in status {status}")
def step_check_installment_status(context, po_index, status, installment_seq_num='1'):
    token = context.token
    debt_position_id = context.debt_position.debt_position_id

    res = get_debt_position(token=token, debt_position_id=debt_position_id)

    assert res.status_code == 200

    debt_position = DebtPosition.from_dict(res.json())

    installment = find_installment_by_seq_num_and_po_index(debt_position=debt_position, po_index=int(po_index),
                                                           seq_num=installment_seq_num)

    assert installment.status.value == status.upper()


@given("a simple debt position created by organization interacting with {pagopa_interaction}")
def step_create_simple_debt_position(context, pagopa_interaction):
    get_token_org(context=context, pagopa_interaction=pagopa_interaction)
    step_create_dp_entity(context=context)
    step_create_po_and_single_inst_entities(context=context, po_index=1, amount=100, expiration_days=3)
    step_create_dp(context=context)
    step_check_dp_status(context=context, status=Status.UNPAID.value)

    if pagopa_interaction == PagoPaInteractionModel.ACA.value:
        step_verify_presence_debt_position_in_aca(context=context, status="valid")

    step_debt_position_workflow_check_expiration(context=context, status="scheduled")


@given(
    "a complex debt position with {po_size} payment options created by organization interacting with {pagopa_interaction}")
def step_create_simple_debt_position(context, po_size, pagopa_interaction):
    get_token_org(context=context, pagopa_interaction=pagopa_interaction)
    step_create_dp_entity(context=context)
    for i in range(int(po_size)):
        step_create_po_and_inst_entities(context=context, po_index=i + 1, installments_size=2, expiration_days=3)
    step_create_dp(context=context)
    step_check_dp_status(context=context, status=Status.UNPAID.value)

    if pagopa_interaction == PagoPaInteractionModel.ACA.value:
        step_verify_presence_debt_position_in_aca(context=context, status="valid")

    step_debt_position_workflow_check_expiration(context=context, status="scheduled")


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


def validate_debt_position_created(org_info, debt_position_request: DebtPosition, debt_position_response: dict, status: Status):
    assert debt_position_response['status'] == status.value
    assert debt_position_response['debtPositionTypeOrgId'] == debt_position_request.debt_position_type_org_id
    if debt_position_request.iupd_org is None:
        assert debt_position_response['iupdOrg'].startswith(org_info.fiscal_code)
    else:
        assert debt_position_response['iupdOrg'] == debt_position_request.iupd_org

    assert len(debt_position_response['paymentOptions']) == len(debt_position_request.payment_options)

    map_po_request = dict((po.payment_option_index, po) for po in debt_position_request.payment_options)
    for po_response in debt_position_response['paymentOptions']:
        po_request = map_po_request.get(po_response['paymentOptionIndex'])
        assert po_response['status'] == status.value
        assert po_response['paymentOptionType'] == po_request.payment_option_type.value
        assert po_response['totalAmountCents'] == calculate_po_total_amount(po_request)
        assert len(po_response['installments']) == len(po_request.installments)

        map_inst_request = dict((inst.iud, inst) for inst in po_request.installments)
        for inst_response in po_response['installments']:
            inst_request = map_inst_request.get(inst_response['iud'])
            assert inst_response['status'] == status.value
            if status == Status.TO_SYNC:
                assert inst_response['syncStatus']['syncStatusFrom'] == Status.DRAFT.value
                assert inst_response['syncStatus']['syncStatusTo'] == Status.UNPAID.value
            assert inst_response['iupdPagopa'].startswith(org_info.fiscal_code)
            assert len(inst_response['iuv']) == 17
            assert len(inst_response['nav']) == 18 and inst_response['nav'] == '3' + inst_response['iuv']
            assert inst_response['dueDate'] == inst_request.due_date
            assert inst_response['amountCents'] == inst_request.amount_cents
            assert inst_response['debtor'] == json.loads(inst_request.debtor.to_json())
            assert len(inst_response['transfers']) == len(inst_request.transfers) + 1

            first_transfer = next(transfer for transfer in inst_response['transfers'] if transfer['transferIndex'] == 1)

            assert first_transfer is not None
            assert first_transfer['orgFiscalCode'] == org_info.fiscal_code
            assert first_transfer['orgName'] == org_info.name
            assert first_transfer['iban'] == org_info.iban
            assert first_transfer['category'] is not None

            assert first_transfer['remittanceInformation'] == inst_request.remittance_information
            assert (first_transfer['amountCents'] ==
                    calculate_amount_first_transfer(installment=Installment.from_dict(inst_request)))
