from dataclasses import dataclass, fields

from model.debt_position import Debtor
from model.send_notification import SendPdfDigest, CONTENT_TYPE, PhysicalAddress


@dataclass
class CSVRow:
    organizationId: int
    paProtocolNumber: str
    externalCampaignId: str
    notificationFeePolicy: str = 'DELIVERY_MODE'
    physicalCommunicationType: str = 'AR_REGISTERED_LETTER'
    subject: str = 'Feature-test send massive import'
    senderDenomination: str = None
    senderTaxId: str = None
    amount: int = 0
    paymentExpirationDate: str = None
    taxonomyCode: str = '030101P'
    paFee: int = 100
    vat: int = 22
    pagoPaIntMode: str = 'ASYNC'
    recipientType: str = 'PF'
    taxId: str = Debtor.fiscal_code
    denomination: str = Debtor.full_name
    address: str = PhysicalAddress.address
    zip: str = PhysicalAddress.zip
    municipality: str = PhysicalAddress.municipality
    province: str = PhysicalAddress.province
    digitalDomicileAddress: str = Debtor.email
    digitalDomicileType: str = 'PEC'
    paymentNoticeCode_1: str = None
    paymentCreditorTaxId_1: str = None
    paymentApplyCost_1: bool = True
    attachmentDigest_1: str = SendPdfDigest.payment_pdf_digest
    attachmentContentType_1: str = CONTENT_TYPE
    attachmentFileName_1: str = 'payment_1.pdf'
    documentDigest_1: str = SendPdfDigest.notification_pdf_digest
    documentContentType_1: str = CONTENT_TYPE
    documentFileName_1: str = 'notification_1.pdf'

    @classmethod
    def header(cls) -> list[str]:
        return [f.name for f in fields(cls)]


def _escape(value: str) -> str:
    return f'"{value}"' if ';' in value else value


def to_csv_lines(csv_rows: list[CSVRow], with_header=True) -> list[str]:
    if not csv_rows:
        return []

    header = CSVRow.header()
    lines = []

    if with_header:
        lines.append(';'.join(_escape(h) for h in header))

    for row in csv_rows:
        values = []
        for f in header:
            val = getattr(row, f)
            if val is None:
                values.append('')
            elif hasattr(val, 'value'):
                values.append(val.value)
            else:
                values.append(str(val))
        lines.append(';'.join(_escape(v) for v in values))

    return lines
