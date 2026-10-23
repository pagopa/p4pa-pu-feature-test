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


def to_csv_lines(csv_rows: list[CSVRow], lang: str = CSVLanguage.IT.value, with_header=True) -> list:
    if not csv_rows:
        return []

    first_row = csv_rows[0]
    active_fields = list(first_row.HEADER_FIELDS.keys())

    lines = []

    if with_header:
        headers = [first_row.HEADER_FIELDS[f][lang] for f in active_fields]
        lines.append(';'.join(f'"{h}"' if ';' in h else h for h in headers))

    for row in csv_rows:
        values = []
        for f in active_fields:
            val = getattr(row, f)
            if val is None:
                values.append('')
            elif hasattr(val, 'value'):
                values.append(val.value)
            else:
                values.append(str(val))

        lines.append(';'.join(f'"{v}"' if ';' in v else v for v in values))

    return lines
