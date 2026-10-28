from decimal import Decimal


def cents_to_euro_str(amount_cents) -> str:
    return "{:.2f}".format(int(amount_cents) / 100)


def cents_to_euro_decimal(amount_cents) -> Decimal:
    return Decimal(amount_cents) / Decimal(100)
