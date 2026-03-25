from dataclasses import dataclass, field

from dataclasses_json import dataclass_json, LetterCase

from config.configuration import secrets
from model.debt_position import EntityType


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class DebtorSpontaneous:
    entity_type: EntityType = EntityType.F.value
    fiscal_code: str = secrets.citizen_info.X.fiscal_code
    full_name: str = secrets.citizen_info.X.name
    email: str = secrets.citizen_info.X.email


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class InstallmentSpontaneous:
    amount_cents: int
    remittance_information: str
    user_remittance_information: str
    debtor: DebtorSpontaneous


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class PaymentOptionSpontaneous:
    total_amount_cents: int
    installments: list[InstallmentSpontaneous] = field(default_factory=list)


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class FieldValues:
    org_fiscal_code: str


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class DebtPositionSpontaneous:
    organization_id: int
    debt_position_type_org_id: int
    field_values: FieldValues
    payment_options: list[PaymentOptionSpontaneous] = field(default_factory=list)


def get_debt_position_type_org_code_by_reason(reason_desc: str) -> str:
    match reason_desc:
        case 'lost card':
            return '1'
        case 'stolen card':
            return '2'
        case 'degradated card':
            return '4'
        case 'renewal expired card':
            return '7'
        case 'first card issuance':
            return '9'
        case 'renewal expiring card':
            return '10'
        case 'renewal for personal details changes':
            return '11'
        case _:
            return '9'
