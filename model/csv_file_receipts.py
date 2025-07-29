from dataclasses import dataclass
from enum import Enum
from typing import List


class CSVVersion(Enum):
    V1_0 = "1_0"
    V1_1 = "1_1"
    V1_2 = "1_2"
    V1_3 = "1_3"

    @property
    def object_version(self) -> str:
        return f"objectVersion{self.value.replace('_', '.')}"


class CSVLanguage(Enum):
    IT = "IT"
    EN = "EN"


class PersonEntityType(Enum):
    F = "F"
    G = "G"


class EntityIdType(Enum):
    G = "G"


def version(versions: List[str]):
    def decorator(func):
        func._versions = versions
        return func

    return decorator


@dataclass
class CSVRow:
    _HEADER_FIELDS = {
        'sourceFlowName': {'versions': ['1_0', '1_1', '1_2', '1_3'], 'IT': 'iuf', 'EN': 'sourceFlowName'},
        'flowRowNumber': {'versions': ['1_0', '1_1', '1_2', '1_3'], 'IT': 'numRigaFlusso', 'EN': 'flowRowNumber'},
        'iud': {'versions': ['1_0', '1_1', '1_2', '1_3'], 'IT': 'codIud', 'EN': 'iud'},
        'noticeNumber': {'versions': ['1_0', '1_1', '1_2', '1_3'], 'IT': 'codIuv', 'EN': 'noticeNumber'},
        'objectVersion': {'versions': ['1_0', '1_1', '1_2', '1_3'], 'IT': 'versioneOggetto', 'EN': 'objectVersion'},
        'orgFiscalCode': {'versions': ['1_0', '1_1', '1_2', '1_3'], 'IT': 'identificativoDominio',
                          'EN': 'orgFiscalCode'},
        'requestingStationId': {'versions': ['1_0', '1_1', '1_2', '1_3'], 'IT': 'identificativoStazioneRichiedente',
                                'EN': 'requestingStationId'},
        'paymentReceiptId': {'versions': ['1_0', '1_1', '1_2', '1_3'], 'IT': 'identificativoMessaggioRicevuta',
                             'EN': 'paymentReceiptId'},
        'paymentDateTime': {'versions': ['1_0', '1_1', '1_2', '1_3'], 'IT': 'dataOraMessaggioRicevuta',
                            'EN': 'paymentDateTime'},
        'requestMessageReference': {'versions': ['1_0', '1_1', '1_2', '1_3'], 'IT': 'riferimentoMessaggioRichiesta',
                                    'EN': 'requestMessageReference'},
        'requestDateReference': {'versions': ['1_0', '1_1', '1_2', '1_3'], 'IT': 'riferimentoDataRichiesta',
                                 'EN': 'requestDateReference'},
        'uniqueIdType': {'versions': ['1_0', '1_1', '1_2', '1_3'], 'IT': 'tipoIdentificativoUnivoco',
                         'EN': 'uniqueIdType'},
        'idPsp': {'versions': ['1_0', '1_1', '1_2', '1_3'], 'IT': 'codiceIdentificativoUnivoco', 'EN': 'idPsp'},
        'pspCompanyName': {'versions': ['1_0', '1_1', '1_2', '1_3'], 'IT': 'denominazioneAttestante',
                           'EN': 'pspCompanyName'},
        'certifierOperationalUnitCode': {'versions': ['1_0', '1_1', '1_2', '1_3'], 'IT': 'codiceUnitOperAttestante',
                                         'EN': 'certifierOperationalUnitCode'},
        'certifierOperationalUnitName': {'versions': ['1_0', '1_1', '1_2', '1_3'], 'IT': 'denomUnitOperAttestante',
                                         'EN': 'certifierOperationalUnitName'},
        'certifierAddress': {'versions': ['1_0', '1_1', '1_2', '1_3'], 'IT': 'indirizzoAttestante',
                             'EN': 'certifierAddress'},
        'certifierCivicNumber': {'versions': ['1_0', '1_1', '1_2', '1_3'], 'IT': 'civicoAttestante',
                                 'EN': 'certifierCivicNumber'},
        'certifierPostalCode': {'versions': ['1_0', '1_1', '1_2', '1_3'], 'IT': 'capAttestante',
                                'EN': 'certifierPostalCode'},
        'certifierLocation': {'versions': ['1_0', '1_1', '1_2', '1_3'], 'IT': 'localitaAttestante',
                              'EN': 'certifierLocation'},
        'certifierProvince': {'versions': ['1_0', '1_1', '1_2', '1_3'], 'IT': 'provinciaAttestante',
                              'EN': 'certifierProvince'},
        'certifierNation': {'versions': ['1_0', '1_1', '1_2', '1_3'], 'IT': 'nazioneAttestante',
                            'EN': 'certifierNation'},
        'beneficiaryEntityIdType': {'versions': ['1_0', '1_1', '1_2', '1_3'],
                                    'IT': 'enteBenefTipoIdentificativoUnivoco', 'EN': 'beneficiaryEntityIdType'},
        'beneficiaryEntityIdCode': {'versions': ['1_0', '1_1', '1_2', '1_3'],
                                    'IT': 'enteBenefCodiceIdentificativoUnivoco', 'EN': 'beneficiaryEntityIdCode'},
        'beneficiaryCompanyName': {'versions': ['1_0', '1_1', '1_2', '1_3'], 'IT': 'denominazioneBeneficiario',
                                   'EN': 'beneficiaryCompanyName'},
        'beneficiaryOperationalUnitCode': {'versions': ['1_0', '1_1', '1_2', '1_3'], 'IT': 'codiceUnitOperBeneficiario',
                                           'EN': 'beneficiaryOperationalUnitCode'},
        'beneficiaryOperationalUnitName': {'versions': ['1_0', '1_1', '1_2', '1_3'], 'IT': 'denomUnitOperBeneficiario',
                                           'EN': 'beneficiaryOperationalUnitName'},
        'beneficiaryAddress': {'versions': ['1_0', '1_1', '1_2', '1_3'], 'IT': 'indirizzoBeneficiario',
                               'EN': 'beneficiaryAddress'},
        'beneficiaryCivic': {'versions': ['1_0', '1_1', '1_2', '1_3'], 'IT': 'civicoBeneficiario',
                             'EN': 'beneficiaryCivic'},
        'beneficiaryPostalCode': {'versions': ['1_0', '1_1', '1_2', '1_3'], 'IT': 'capBeneficiario',
                                  'EN': 'beneficiaryPostalCode'},
        'beneficiaryCity': {'versions': ['1_0', '1_1', '1_2', '1_3'], 'IT': 'localitaBeneficiario',
                            'EN': 'beneficiaryCity'},
        'beneficiaryProvince': {'versions': ['1_0', '1_1', '1_2', '1_3'], 'IT': 'provinciaBeneficiario',
                                'EN': 'beneficiaryProvince'},
        'beneficiaryNation': {'versions': ['1_0', '1_1', '1_2', '1_3'], 'IT': 'nazioneBeneficiario',
                              'EN': 'beneficiaryNation'},
        'payerEntityType': {'versions': ['1_0', '1_1', '1_2', '1_3'], 'IT': 'soggVersTipoIdentificativoUnivoco',
                            'EN': 'payerEntityType'},
        'payerFiscalCode': {'versions': ['1_0', '1_1', '1_2', '1_3'], 'IT': 'soggVersCodiceIdentificativoUnivoco',
                            'EN': 'payerFiscalCode'},
        'payerFullName': {'versions': ['1_0', '1_1', '1_2', '1_3'], 'IT': 'anagraficaVersante', 'EN': 'payerFullName'},
        'payerAddress': {'versions': ['1_0', '1_1', '1_2', '1_3'], 'IT': 'indirizzoVersante', 'EN': 'payerAddress'},
        'payerCivic': {'versions': ['1_0', '1_1', '1_2', '1_3'], 'IT': 'civicoVersante', 'EN': 'payerCivic'},
        'payerPostalCode': {'versions': ['1_0', '1_1', '1_2', '1_3'], 'IT': 'capVersante', 'EN': 'payerPostalCode'},
        'payerLocation': {'versions': ['1_0', '1_1', '1_2', '1_3'], 'IT': 'localitaVersante', 'EN': 'payerLocation'},
        'payerProvince': {'versions': ['1_0', '1_1', '1_2', '1_3'], 'IT': 'provinciaVersante', 'EN': 'payerProvince'},
        'payerNation': {'versions': ['1_0', '1_1', '1_2', '1_3'], 'IT': 'nazioneVersante', 'EN': 'payerNation'},
        'payerEmail': {'versions': ['1_0', '1_1', '1_2', '1_3'], 'IT': 'emailVersante', 'EN': 'payerEmail'},
        'debtorEntityType': {'versions': ['1_0', '1_1', '1_2', '1_3'], 'IT': 'soggPagTipoIdentificativoUnivoco',
                             'EN': 'debtorEntityType'},
        'debtorFiscalCode': {'versions': ['1_0', '1_1', '1_2', '1_3'], 'IT': 'soggPagCodiceIdentificativoUnivoco',
                             'EN': 'debtorFiscalCode'},
        'debtorFullName': {'versions': ['1_0', '1_1', '1_2', '1_3'], 'IT': 'anagraficaPagatore',
                           'EN': 'debtorFullName'},
        'debtorAddress': {'versions': ['1_0', '1_1', '1_2', '1_3'], 'IT': 'indirizzoPagatore', 'EN': 'debtorAddress'},
        'debtorCivic': {'versions': ['1_0', '1_1', '1_2', '1_3'], 'IT': 'civicoPagatore', 'EN': 'debtorCivic'},
        'debtorPostalCode': {'versions': ['1_0', '1_1', '1_2', '1_3'], 'IT': 'capPagatore', 'EN': 'debtorPostalCode'},
        'debtorLocation': {'versions': ['1_0', '1_1', '1_2', '1_3'], 'IT': 'localitaPagatore', 'EN': 'debtorLocation'},
        'debtorProvince': {'versions': ['1_0', '1_1', '1_2', '1_3'], 'IT': 'provinciaPagatore', 'EN': 'debtorProvince'},
        'debtorNation': {'versions': ['1_0', '1_1', '1_2', '1_3'], 'IT': 'nazionePagatore', 'EN': 'debtorNation'},
        'debtorEmail': {'versions': ['1_0', '1_1', '1_2', '1_3'], 'IT': 'emailPagatore', 'EN': 'debtorEmail'},
        'outcome': {'versions': ['1_0', '1_1', '1_2', '1_3'], 'IT': 'codiceEsitoPagamento', 'EN': 'outcome'},
        'paymentAmountCents': {'versions': ['1_0', '1_1', '1_2', '1_3'], 'IT': 'importoTotalePagato',
                               'EN': 'paymentAmountCents'},
        'creditorReferenceId': {'versions': ['1_0', '1_1', '1_2', '1_3'], 'IT': 'identificativoUnivocoVersamento',
                                'EN': 'creditorReferenceId'},
        'paymentContextCode': {'versions': ['1_0', '1_1', '1_2', '1_3'], 'IT': 'codiceContestoPagamento',
                               'EN': 'paymentContextCode'},
        'singlePaymentAmount': {'versions': ['1_0', '1_1', '1_2', '1_3'], 'IT': 'singoloImportoPagato',
                                'EN': 'singlePaymentAmount'},
        'singlePaymentOutcome': {'versions': ['1_0', '1_1', '1_2', '1_3'], 'IT': 'esitoSingoloPagamento',
                                 'EN': 'singlePaymentOutcome'},
        'singlePaymentOutcomeDate': {'versions': ['1_0', '1_1', '1_2', '1_3'], 'IT': 'dataEsitoSingoloPagamento',
                                     'EN': 'singlePaymentOutcomeDate'},
        'uniqueCollectionId': {'versions': ['1_0', '1_1', '1_2', '1_3'], 'IT': 'identificativoUnivocoRiscoss',
                               'EN': 'uniqueCollectionId'},
        'remittanceInformation': {'versions': ['1_0', '1_1', '1_2', '1_3'], 'IT': 'causaleVersamento',
                                  'EN': 'remittanceInformation'},
        'paymentNote': {'versions': ['1_0', '1_1', '1_2', '1_3'], 'IT': 'datiSpecificiRiscossione',
                        'EN': 'paymentNote'},
        'debtPositionTypeOrgCode': {'versions': ['1_0', '1_1', '1_2', '1_3'], 'IT': 'tipoDovuto',
                                    'EN': 'debtPositionTypeOrgCode'},
        'signatureType': {'versions': ['1_0', '1_1', '1_2', '1_3'], 'IT': 'tipoFirma', 'EN': 'signatureType'},
        'rt': {'versions': ['1_0', '1_1', '1_2', '1_3'], 'IT': 'rt', 'EN': 'rt'},
        'idTransfer': {'versions': ['1_0', '1_1', '1_2', '1_3'], 'IT': 'indiceDatiSingoloPagamento',
                       'EN': 'idTransfer'},
        'feeCents': {'versions': ['1_0', '1_1', '1_2', '1_3'], 'IT': 'numRtDatiPagDatiSingPagCommissioniApplicatePsp',
                     'EN': 'feeCents'},
        'receiptAttachmentTypeCode': {'versions': ['1_0', '1_1', '1_2', '1_3'],
                                      'IT': 'codRtDatiPagDatiSingPagAllegatoRicevutaTipo',
                                      'EN': 'receiptAttachmentTypeCode'},
        'mbdAttachment': {'versions': ['1_0', '1_1', '1_2', '1_3'], 'IT': 'blbRtDatiPagDatiSingPagAllegatoRicevutaTest',
                          'EN': 'mbdAttachment'},
        'balance': {'versions': ['1_0', '1_1', '1_2', '1_3'], 'IT': 'bilancio', 'EN': 'balance'},
        'fiscalCodePA': {'versions': ['1_0', '1_1', '1_2', '1_3'], 'IT': 'cod_fiscale_pa1', 'EN': 'fiscalCodePA'},
        'companyName': {'versions': ['1_0', '1_1', '1_2', '1_3'], 'IT': 'de_nome_pa1', 'EN': 'companyName'},
        'transferCategory': {'versions': ['1_0', '1_1', '1_2', '1_3'], 'IT': 'cod_tassonomico_dovuto_pa1',
                             'EN': 'transferCategory'}
    }

    iud: str = None
    noticeNumber: str = None
    orgFiscalCode: str = None
    paymentReceiptId: str = None
    paymentDateTime: str = None
    idPsp: str = None
    pspCompanyName: str = None
    beneficiaryCompanyName: str = None
    payerEntityType: PersonEntityType = None
    debtorEntityType: PersonEntityType = None
    debtorFullName: str = None
    debtorFiscalCode: str = None
    outcome: str = None
    paymentAmountCents: str = None
    creditorReferenceId: str = None
    remittanceInformation: str = None
    idTransfer: int = None
    fiscalCodePA: str = None
    transferCategory: str = None
    # Nullable fields:
    sourceFlowName: str = None
    flowRowNumber: int = None
    objectVersion: str = None
    requestingStationId: str = None
    requestMessageReference: str = None
    requestDateReference: str = None
    uniqueIdType: str = None
    certifierOperationalUnitCode: str = None
    certifierOperationalUnitName: str = None
    certifierAddress: str = None
    certifierCivicNumber: str = None
    certifierPostalCode: str = None
    certifierLocation: str = None
    certifierProvince: str = None
    certifierNation: str = None
    beneficiaryEntityIdType: EntityIdType = None
    beneficiaryEntityIdCode: str = None
    beneficiaryOperationalUnitCode: str = None
    beneficiaryOperationalUnitName: str = None
    beneficiaryAddress: str = None
    beneficiaryCivic: str = None
    beneficiaryPostalCode: str = None
    beneficiaryCity: str = None
    beneficiaryProvince: str = None
    beneficiaryNation: str = None
    payerFiscalCode: str = None
    payerFullName: str = None
    payerAddress: str = None
    payerCivic: str = None
    payerPostalCode: str = None
    payerLocation: str = None
    payerProvince: str = None
    payerNation: str = None
    payerEmail: str = None
    debtorAddress: str = None
    debtorCivic: str = None
    debtorPostalCode: str = None
    debtorLocation: str = None
    debtorProvince: str = None
    debtorNation: str = None
    debtorEmail: str = None
    paymentContextCode: str = None
    singlePaymentAmount: str = None
    singlePaymentOutcome: str = None
    singlePaymentOutcomeDate: str = None
    uniqueCollectionId: str = None
    paymentNote: str = None
    debtPositionTypeOrgCode: str = None
    signatureType: str = None
    rt: str = None
    feeCents: str = None
    receiptAttachmentTypeCode: str = None
    mbdAttachment: str = None
    balance: str = None
    companyName: str = None

    @property
    def HEADER_FIELDS(self):
        return self._HEADER_FIELDS


def to_csv_lines(csv_rows: list[CSVRow], csv_version: CSVVersion = CSVVersion.V1_3, with_header=True) -> list:
    if not csv_rows:
        return []

    lang = CSVLanguage.IT.value  # Currently, the only language used for this file is italian

    first_row = csv_rows[0]
    active_fields = [f for f, meta in first_row.HEADER_FIELDS.items()
                     if csv_version.value in meta['versions'] and hasattr(first_row, f)]

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
