from enum import Enum


class FilePathName(Enum):
    TREASURY_OPI = 'data/treasury/opi'
    RECEIPT_PAGOPA = 'data/receipt/pagopa'
    RECEIPT = 'data/receipt'
    PAYMENTS_REPORTING = 'data/payments_reporting'
    PAYMENTS_REPORTING_PAGOPA = 'data/payments_reporting/pagopa'
    INSTALLMENT = 'data/installment'


class FileStatus(Enum):
    UPLOADED = 'UPLOADED'
    PROCESSING = 'PROCESSING'
    COMPLETED = 'COMPLETED'
    ERROR = 'ERROR'


class IngestionFlowFileType(Enum):
    RECEIPT = 'RECEIPT'
    RECEIPT_PAGOPA = 'RECEIPT_PAGOPA'
    PAYMENTS_REPORTING = 'PAYMENTS_REPORTING'
    PAYMENTS_REPORTING_PAGOPA = 'PAYMENTS_REPORTING_PAGOPA'
    TREASURY_OPI = 'TREASURY_OPI'
    DP_INSTALLMENTS = 'DP_INSTALLMENTS'


class FileOrigin(Enum):
    PAGOPA = 'PAGOPA'
    SIL = 'SIL'
    PORTAL = 'PORTAL'
