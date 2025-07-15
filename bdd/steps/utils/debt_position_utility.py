import random
import string
import uuid
from datetime import datetime, timedelta

from api.debt_position_type import get_debt_position_type_org_by_code
from model.debt_position import DebtPosition, PaymentOption, Status, Installment
from model.debt_position import Debtor, PaymentOptionType


def find_installment_by_seq_num_and_po_index(debt_position: DebtPosition, po_index: int, seq_num: int) -> Installment:
    installment = None
    for po in debt_position.payment_options:
        if po.payment_option_index == po_index:
            for inst in po.installments:
                if inst.iud.startswith('FeatureTest_' + str(seq_num)):
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


def create_installment(expiration_days: int, seq_num: int, amount_cents: int = None,
                       ingestion_flow_file_action: str = None, balance: str = None) -> Installment:
    due_date = (datetime.now() + timedelta(days=expiration_days)).strftime('%Y-%m-%d')
    amount_cents = random.randint(1, 200) * 100 if amount_cents is None else amount_cents

    installment = Installment(amount_cents=amount_cents,
                              due_date=due_date,
                              debtor=Debtor(),
                              remittance_information=f'Feature test installment {seq_num}',
                              iud=f'FeatureTest_{seq_num}_{datetime.now().strftime("%Y%m%d%H%M%S%f")[:15]}_{uuid.uuid4().hex[:5]}',
                              ingestion_flow_file_action=ingestion_flow_file_action,
                              balance=balance)
    return installment


def create_payment_option(po_index: int, payment_option_type: PaymentOptionType) -> PaymentOption:
    payment_option = PaymentOption(payment_option_index=int(po_index),
                                   payment_option_type=payment_option_type,
                                   description=f'Feature test payment option {po_index}')

    return payment_option


def create_debt_position(token, organization_id: int, debt_position_type_org_code: str,
                         iupd_org: str = None, identifier: str = '') -> DebtPosition:
    res_dp_type_org = get_debt_position_type_org_by_code(token=token, organization_id=organization_id,
                                                         code=debt_position_type_org_code)

    assert res_dp_type_org.status_code == 200
    debt_position_type_org_id = res_dp_type_org.json()['debtPositionTypeOrgId']
    assert debt_position_type_org_id is not None

    debt_position = DebtPosition(organization_id=organization_id,
                                 debt_position_type_org_id=debt_position_type_org_id,
                                 iupd_org=iupd_org,
                                 description='Feature test debt position ' + identifier)

    return debt_position


def generate_iuv() -> str:
    return f"0199{''.join(random.choices(string.digits, k=13))}"
