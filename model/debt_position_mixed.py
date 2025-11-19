from dataclasses import dataclass, field

from dataclasses_json import dataclass_json, LetterCase

from model.debt_position import DebtPositionOrigin, Debtor


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class TransferMixed:
    iud: str
    debt_position_type_org_code: str
    amount: float
    remittance_information: str
    legacy_payment_metadata: str
    balance: str = None
    iban: str = None
    debt_position_type_org_id: int = None
    transfer_index: int = None


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class DebtPositionMixed:
    organization_id: int
    debtor: Debtor = field(default_factory=lambda: Debtor())
    debt_position_origin: DebtPositionOrigin = DebtPositionOrigin.SPONTANEOUS_SIL.value
    source_flow_name: str = None
    description: str = None
    due_date: str = None
    transfers: list[TransferMixed] = field(default_factory=list)