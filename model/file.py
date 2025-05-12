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
