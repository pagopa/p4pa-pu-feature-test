from dataclasses import dataclass, field
from enum import Enum

from dataclasses_json import dataclass_json, LetterCase

from config.configuration import secrets


class Status(Enum):
    TO_SYNC = "TO_SYNC"
    DRAFT = "DRAFT"
    UNPAID = "UNPAID"
    UNPAYABLE = "UNPAYABLE"
    CANCELLED = "CANCELLED"
    INVALID = "INVALID"
    EXPIRED = "EXPIRED"
    PARTIALLY_PAID = "PARTIALLY_PAID"
    PAID = "PAID"
    REPORTED = "REPORTED"


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class SyncStatus:
    sync_status_from: Status
    sync_status_to: Status


class EntityType(Enum):
    F = "F"
    G = "G"


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class Debtor:
    entity_type: EntityType = EntityType.F.value
    fiscal_code: str = secrets.citizen_info.fiscal_code
    full_name: str = secrets.citizen_info.name
    email: str = secrets.citizen_info.email
    address: str = "Via del Corso"
    civic: str = "1"
    postal_code: str = "00186"
    location: str = "Roma"
    province: str = "RM"
    nation: str = "IT"


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class Transfer:
    transfer_id: int
    installment_id: int
    transfer_index: int
    org_fiscal_code: str
    amount_cents: int
    remittance_information: str
    category: str
    iban: str = None
    org_name: str = None


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class Installment:
    amount_cents: int
    debtor: Debtor
    remittance_information: str
    iud: str
    due_date: str = None
    installment_id: int = None
    payment_option_id: int = None
    status: Status = Status.UNPAID.value
    sync_status: SyncStatus = None
    iupd_pagopa: str = None
    iuv: str = None
    nav: str = None
    iur: str | None = None
    iuf: str | None = None
    iun: str | None = None
    notification_fee_cents: int | None = None
    notification_date: str | None = None
    balance: str | None = None
    legacy_payment_metadata: str | None = None
    ingestion_flow_file_id: int | None = None
    ingestion_flow_file_line_number: int | None = None
    receipt_id: int | None = None
    transfers: list[Transfer] = field(default_factory=list)


class PaymentOptionType(Enum):
    INSTALLMENTS = "INSTALLMENTS"
    SINGLE_INSTALLMENT = "SINGLE_INSTALLMENT"
    REDUCED_SINGLE_INSTALLMENT = "REDUCED_SINGLE_INSTALLMENT"


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class PaymentOption:
    description: str
    payment_option_type: PaymentOptionType
    payment_option_index: int
    payment_option_id: int = None
    debt_position_id: int = None
    total_amount_cents: int = 0
    status: Status = Status.UNPAID.value
    installments: list[Installment] = field(default_factory=list)


class DebtPositionOrigin(Enum):
    ORDINARY = 'ORDINARY'
    ORDINARY_SIL = 'ORDINARY_SIL'
    SPONTANEOUS = 'SPONTANEOUS'
    SECONDARY_ORG = 'SECONDARY_ORG'
    RECEIPT_FILE = 'RECEIPT_FILE'
    RECEIPT_PAGOPA = 'RECEIPT_PAGOPA'
    REPORTING_PAGOPA = 'REPORTING_PAGOPA'


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class DebtPosition:
    description: str
    organization_id: int
    debt_position_type_org_id: int
    debt_position_id: int = None
    iupd_org: str = None
    status: Status = Status.UNPAID.value
    debt_position_origin: DebtPositionOrigin = DebtPositionOrigin.ORDINARY.value
    validity_date: str | None = None
    multi_debtor: bool = False
    flag_iuv_volatile: bool = False
    flag_pu_pago_pa_payment: bool = True
    payment_options: list[PaymentOption] = field(default_factory=list)
