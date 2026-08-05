import random
import string
import uuid
from datetime import datetime, timedelta

from api.debt_position_type import get_debt_position_type_org_by_code, get_debt_position_type_by_id
from api.debt_positions import get_debt_position
from bdd.steps.utils.assertions import assert_response_ok
from config.configuration import secrets
from model.debt_position import DebtPosition, PaymentOption, Status, Installment, SyncStatus, Transfer
from model.debt_position import Debtor, PaymentOptionType
from model.debt_position_mixed import MIXED_REMITTANCE

FEATURE_TEST_IUD_PREFIX = 'FeatureTest_'


def build_feature_test_iud(seq_num) -> str:
    return f'{FEATURE_TEST_IUD_PREFIX}{seq_num}_{datetime.now().strftime("%Y%m%d%H%M%S%f")[:15]}_{uuid.uuid4().hex[:5]}'


def seq_num_of(iud: str) -> int:
    return int(iud.split('_')[1])


def find_installment_by_seq_num_and_po_index(debt_position: DebtPosition, po_index: int, seq_num: int) -> Installment:
    installment = None
    for po in debt_position.payment_options:
        if po.payment_option_index == po_index:
            for inst in po.installments:
                if inst.iud.startswith(FEATURE_TEST_IUD_PREFIX) and seq_num_of(inst.iud) == int(seq_num):
                    installment = inst
    return installment


def find_mixed_installment(debt_position: DebtPosition) -> Installment:
    installment = None
    for po in debt_position.payment_options:
        for inst in po.installments:
            if inst.remittance_information == MIXED_REMITTANCE:
                installment = inst
    return installment


def find_installment_by_iuv(debt_position: DebtPosition, iuv: str) -> Installment:
    installment = None
    for po in debt_position.payment_options:
        for inst in po.installments:
            if inst.iuv == iuv:
                installment = inst
    return installment


def find_payment_option_by_po_index(debt_position: DebtPosition, po_index: int) -> PaymentOption:
    payment_option = None
    for po in debt_position.payment_options:
        if po.payment_option_index == po_index:
            payment_option = po
    return payment_option


def retrieve_iuv_list(debt_position: DebtPosition) -> list[str]:
    iuv_list = []
    for po in debt_position.payment_options:
        for installment in po.installments:
            iuv_list.append(installment.iuv)

    return iuv_list


def calculate_po_total_amount(payment_option: PaymentOption) -> int:
    return sum(installment.amount_cents for installment in payment_option.installments
               if installment.status != Status.CANCELLED.value)


def calculate_amount_first_transfer(installment: Installment) -> int:
    other_transfers_amount = sum(transfer.amount_cents for transfer in installment.transfers
                                 if transfer.transfer_index != 1)

    return installment.amount_cents - other_transfers_amount


def create_transfer(token, traceparent: str, org_info: dict, debt_position_type_org_code: str,
                    remittance_information: str, amount_cents: int) -> Transfer:
    debt_position_type_org = retrieve_dp_type_org_by_code(token=token, traceparent=traceparent,
                                                          organization_id=org_info.id,
                                                          debt_position_type_org_code=debt_position_type_org_code)
    category = retrieve_taxonomy_code_by_dp_type_org(token=token, traceparent=traceparent,
                                                     debt_position_type_id=debt_position_type_org['debtPositionTypeId'])

    transfer = Transfer(transfer_index=1,
                        org_fiscal_code=org_info.fiscal_code,
                        org_name=org_info.name,
                        iban=org_info.iban,
                        category=category,
                        amount_cents=amount_cents,
                        remittance_information=remittance_information)

    return transfer


def create_installment(expiration_days: int, seq_num: int, amount_cents: int = None,
                       ingestion_flow_file_action: str = None, balance: str = None, citizen_identifier: str = None,
                       status: Status.UNPAID.value = None) -> Installment:
    due_date = (datetime.now() + timedelta(days=expiration_days)).strftime('%Y-%m-%d')
    amount_cents = random.randint(1, 200) * 100 if amount_cents is None else amount_cents
    citizen = secrets.citizen_info.get(citizen_identifier)
    debtor = Debtor(fiscal_code=citizen.fiscal_code, full_name=citizen.name,
                    email=citizen.email) if citizen is not None else Debtor()

    sync_status = SyncStatus(sync_status_from=Status.DRAFT,
                             sync_status_to=Status.UNPAID) if status == Status.TO_SYNC.value else None

    installment = Installment(amount_cents=amount_cents,
                              due_date=due_date,
                              debtor=debtor,
                              remittance_information=f'Feature test installment {seq_num}',
                              iud=build_feature_test_iud(seq_num),
                              ingestion_flow_file_action=ingestion_flow_file_action,
                              balance=balance,
                              status=status,
                              sync_status=sync_status)

    return installment


def create_payment_option(po_index: int, payment_option_type: PaymentOptionType) -> PaymentOption:
    payment_option = PaymentOption(payment_option_index=int(po_index),
                                   payment_option_type=payment_option_type,
                                   description=f'Feature test payment option {po_index}')

    return payment_option


def create_debt_position(token, traceparent: str, organization_id: int, debt_position_type_org_code: str,
                         iupd_org: str = None, identifier: str = '') -> DebtPosition:
    debt_position_type_org = retrieve_dp_type_org_by_code(token=token, traceparent=traceparent,
                                                          organization_id=organization_id,
                                                          debt_position_type_org_code=debt_position_type_org_code)

    debt_position = DebtPosition(organization_id=organization_id,
                                 debt_position_type_org_id=debt_position_type_org['debtPositionTypeOrgId'],
                                 iupd_org=iupd_org,
                                 description='Feature test debt position ' + identifier)

    return debt_position


def generate_iuv() -> str:
    return f"0199{''.join(random.choices(string.digits, k=13))}"


def retrieve_taxonomy_code_by_dp_type_org(token, traceparent: str, debt_position_type_id: int):
    res_dp_type = get_debt_position_type_by_id(token=token, traceparent=traceparent,
                                               debt_position_type_id=debt_position_type_id)

    assert_response_ok(res_dp_type, "Get debt position type by id")
    taxonomy_code = res_dp_type.json()['taxonomyCode']
    return taxonomy_code


def retrieve_dp_type_org_by_code(token, traceparent: str, organization_id: int, debt_position_type_org_code: str):
    res_dp_type_org = get_debt_position_type_org_by_code(token=token, traceparent=traceparent,
                                                         organization_id=organization_id,
                                                         code=debt_position_type_org_code)

    assert_response_ok(res_dp_type_org, "Get debt position type org by code")
    assert res_dp_type_org.json() is not None

    return res_dp_type_org.json()


def set_installment_paid(context, installment, dp_identifier=None):
    context.installments_paid_by_id[dp_identifier] = installment


def get_installment_paid(context, dp_identifier=None):
    return context.installments_paid_by_id[dp_identifier]


def get_stored_debt_position(context, dp_identifier=None):
    return context.debt_position if dp_identifier is None else context.debt_positions[dp_identifier]


def store_debt_position_by_id(context, dp_identifier):
    context.debt_positions[dp_identifier] = context.debt_position


def fetch_debt_position(context, debt_position_id=None) -> DebtPosition:
    debt_position_id = debt_position_id if debt_position_id is not None else context.debt_position.debt_position_id
    res = get_debt_position(token=context.token, traceparent=context.traceparent, debt_position_id=debt_position_id)

    assert_response_ok(res, "Get debt position by id")
    return DebtPosition.from_dict(res.json())