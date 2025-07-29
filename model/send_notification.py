from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

from dataclasses_json import dataclass_json, LetterCase

from config.configuration import secrets


@dataclass
class SendStatus(Enum):
    WAITING = 'WAITING_FILE'
    SENDING = 'SENDING'
    REGISTERED = 'REGISTERED'
    COMPLETE = 'COMPLETE'
    ACCEPTED = 'ACCEPTED'


class SendPdfDigest:
    notification_pdf_digest = "YSxsCpvZHvwL8IIosWJBUDjgUwa01sBHu6Cj4laQRLA="
    payment_pdf_digest = "45Iba3tn9Dfm7TX+AbtWDR1csMuHgEbrHi/zZr6DjHU="


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class Document:
    file_name: str = 'notification.pdf'
    content_type: str = 'application/pdf'
    digest: str = SendPdfDigest.notification_pdf_digest


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class PhysicalAddress:
    address: str = 'Via Larga, 10'
    zip: str = '00186'
    municipality: str = 'Roma'
    province: str = "RM"


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class PaymentData:
    notice_code: str
    creditor_tax_id: str
    apply_cost: bool = True
    attachment: Document = field(
        default_factory=lambda: Document(file_name='payment_1.pdf', content_type='application/pdf',
                                         digest=SendPdfDigest.payment_pdf_digest))


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class Payment:
    pago_pa: PaymentData


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class Recipient:
    recipient_type: str = 'PF'
    tax_id: str = secrets.send_info.citizen.fiscal_code
    denomination: str = 'Michelangelo Buonarroti'
    physical_address: PhysicalAddress = field(default_factory=lambda: PhysicalAddress())
    payments: list[Payment] = field(default_factory=list)


def create_default_document_list():
    return [Document()]


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class NotificationRequest:
    organization_id: int
    pago_pa_int_mode: str
    pa_protocol_number: str = 'Prot_001'
    recipients: list[Recipient] = field(default_factory=list)
    documents: list[Document] = field(
        default_factory=create_default_document_list)
    notification_fee_policy: str = 'DELIVERY_MODE'
    physical_communication_type: str = 'AR_REGISTERED_LETTER'
    sender_denomination: str = None
    sender_tax_id: str = '00000000018'
    amount: int = 0
    payment_expiration_date: str = (datetime.now() + timedelta(days=3)).strftime('%Y-%m-%d')
    taxonomy_code: str = '010101P'
    pa_fee: int = 100
    vat: int = 22
