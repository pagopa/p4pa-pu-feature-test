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
