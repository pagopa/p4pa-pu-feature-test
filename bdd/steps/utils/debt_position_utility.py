from model.debt_position import DebtPosition, PaymentOption, Status, Installment


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
