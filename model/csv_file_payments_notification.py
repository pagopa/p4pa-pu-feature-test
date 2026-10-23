from dataclasses import dataclass
from decimal import Decimal
from enum import Enum

from config.configuration import settings


class CSVLanguage(Enum):
    IT = "IT"
    EN = "EN"


@dataclass
class CSVRow:
    _HEADER_FIELDS = {
        'iud': {'IT': 'IUD', 'EN': 'iud'},
        'iuv': {'IT': 'codIuv', 'EN': 'iuv'},
        'debtorUniqueIdentifierType': {'IT': 'tipoIdentificativoUnivoco', 'EN': 'debtorUniqueIdentifierType'},
        'debtorUniqueIdentifierCode': {'IT': 'codiceIdentificativoUnivoco', 'EN': 'debtorUniqueIdentifierCode'},
        'debtorFullName': {'IT': 'anagraficaPagatore', 'EN': 'debtorFullName'},
        'debtorAddress': {'IT': 'indirizzoPagatore', 'EN': 'debtorAddress'},
        'debtorCivic': {'IT': 'civicoPagatore', 'EN': 'debtorCivic'},
        'debtorPostalCode': {'IT': 'capPagatore', 'EN': 'debtorPostalCode'},
        'debtorLocation': {'IT': 'localitaPagatore', 'EN': 'debtorLocation'},
        'debtorProvince': {'IT': 'provinciaPagatore', 'EN': 'debtorProvince'},
        'debtorNation': {'IT': 'nazionePagatore', 'EN': 'debtorNation'},
        'debtorEmail': {'IT': 'e-mailPagatore', 'EN': 'debtorEmail'},
        'paymentExecutionDate': {'IT': 'dataEsecuzionePagamento', 'EN': 'paymentExecutionDate'},
        'amountPaid': {'IT': 'importoDovutoPagato', 'EN': 'amountPaid'},
        'paCommission': {'IT': 'commissioneCaricoPa', 'EN': 'paCommission'},
        'debtPositionTypeOrgCode': {'IT': 'tipoDovuto', 'EN': 'debtPositionTypeOrgCode'},
        'paymentType': {'IT': 'tipoVersamento', 'EN': 'paymentType'},
        'remittanceInformation': {'IT': 'causaleVersamento', 'EN': 'remittanceInformation'},
        'transferCategory': {'IT': 'datiSpecificiRiscossione', 'EN': 'transferCategory'},
        'balance': {'IT': 'bilancio', 'EN': 'balance'}
    }

    iud: str = None
    iuv: str = None
    debtorUniqueIdentifierType: str = None
    debtorUniqueIdentifierCode: str = None
    debtorFullName: str = None
    paymentExecutionDate: str = None
    amountPaid: Decimal = None
    paCommission: Decimal = Decimal("1")
    debtPositionTypeOrgCode: str = settings.debt_position_type_org_code.feature_test
    paymentType: str = "ALL"
    remittanceInformation: str = None
    transferCategory: str = None
    debtorAddress: str = None
    debtorCivic: str = None
    debtorPostalCode: str = None
    debtorLocation: str = None
    debtorProvince: str = None
    debtorNation: str = None
    debtorEmail: str = None
    balance: str | None = None

    @property
    def HEADER_FIELDS(self):
        return self._HEADER_FIELDS
