import base64
import re

from bdd.steps.utils.debt_position_utility import format_amount
from common import http_client
from config.configuration import settings, secrets
from model.debt_position import Installment, Transfer, Stamp, SilDebtPositionAction
from model.debt_position_mixed import DebtPositionMixed
from typing import Optional

TEMPLATE_DIR = './api/soap/requests_template_sil'


def _render(template_name: str, **values) -> str:
    with open(f'{TEMPLATE_DIR}/{template_name}', 'r') as file:
        return file.read().format(**values)


def _to_base64(value: str) -> str:
    return base64.b64encode(value.encode('utf-8')).decode('utf-8')


def _build_marca_bollo(stamp: Optional[Stamp]) -> str:
    if stamp is None:
        return ''
    stamp_fields = (stamp.stamp_type, stamp.stamp_hash_document, stamp.stamp_provincial_residence)
    if not all(stamp_fields):
        raise ValueError(f'MdB data incomplete: {stamp_fields}')
    return _render(
        'datiMarcaBolloDigitale.xml',
        tipo_bollo=stamp.stamp_type,
        hash_documento=stamp.stamp_hash_document,
        provincia=stamp.stamp_provincial_residence,
    )


def _build_dati_singolo_versamento(iud: str, amount_cents, tipo_dovuto: str, dati_specifici_riscossione: str,
                                   marca_bollo: Stamp = None) -> str:
    return _render(
        'datiVersamento.xml',
        iud=iud,
        importo=format_amount(amount_cents),
        tipo_dovuto=tipo_dovuto,
        dati_specifici_riscossione=dati_specifici_riscossione,
        dati_marca_bollo=_build_marca_bollo(marca_bollo),
    )


def _build_dovuti_base64(debtor, dati_versamento: str) -> str:
    dovuti = _render(
        'dovuti.xml',
        codice_fiscale=debtor.fiscal_code,
        nome=debtor.full_name,
        email=debtor.email,
        dati_versamento=dati_versamento,
    )
    return _to_base64(dovuti)


def _build_dovuto_base64(installment: Installment, debt_position_type_org_code: str,
                         stamp: Stamp = None) -> str:
    dati_singolo_versamento = _build_dati_singolo_versamento(
        iud=installment.iud,
        amount_cents=installment.amount_cents,
        tipo_dovuto=debt_position_type_org_code,
        dati_specifici_riscossione=installment.legacy_payment_metadata,
        marca_bollo=stamp,
    )
    return _build_dovuti_base64(installment.debtor, dati_singolo_versamento)


def _build_dovuto_secondario_base64(second_transfer: Transfer) -> str:
    dovuti_enti_secondari = _render(
        'dovutiEntiSecondari.xml',
        codice_fiscale_ente_secondario=second_transfer.org_fiscal_code,
        nome_ente_secondario=second_transfer.org_name,
        iban_ente_secondario=second_transfer.iban,
        causale_ente_secondario=second_transfer.remittance_information,
        dati_specifici_riscossione_ente_secondario=second_transfer.category,
        importo_ente_secondario=format_amount(second_transfer.amount_cents),
    )
    return _to_base64(dovuti_enti_secondari)


def _build_iuv_element(iuv: Optional[str]) -> str:
    if iuv is None:
        return ''
    return f'<identificativoUnivocoVersamento>{iuv}</identificativoUnivocoVersamento>'


def _build_versamento_base64(installment: Installment, debt_position_type_org_code: str,
                             action: SilDebtPositionAction) -> str:
    versamento = _render(
        'versamento.xml',
        codice_fiscale=installment.debtor.fiscal_code,
        nome=installment.debtor.full_name,
        email=installment.debtor.email,
        data_esecuzione_pagamento=installment.due_date,
        identificativo_univoco_versamento=_build_iuv_element(installment.iuv),
        iud=installment.iud,
        importo=format_amount(installment.amount_cents),
        tipo_dovuto=debt_position_type_org_code,
        causale=installment.remittance_information,
        dati_specifici_riscossione=installment.legacy_payment_metadata,
        azione=action.value,
    )
    return _to_base64(versamento)


def _post_sil_soap(token, traceparent: str, data: str, path: str):
    return http_client.post(
        url=f'{secrets.base_url}{path}',
        headers={
            'Content-Type': 'text/xml',
            'Authorization': f'Bearer {token}',
            'traceparent': f'{traceparent}'
        },
        data=data,
        timeout=settings.default_timeout
    )


def post_sil_payments(token, traceparent: str, data: str):
    return _post_sil_soap(token=token, traceparent=traceparent, data=data,
                          path=settings.api.ingress_path.sil_payments)


def post_sil_reconciliation(token, traceparent: str, data: str):
    return _post_sil_soap(token=token, traceparent=traceparent, data=data,
                          path=settings.api.ingress_path.sil_reconciliation)


def checkout_url_pattern(org_fiscal_code: str) -> str:
    base = f'{secrets.base_url}{settings.api.ingress_path.sil}'
    return re.escape(base) + rf'/organization/{re.escape(org_fiscal_code)}/checkout\?token=[^&]+$'


def get_sil_print_payment_notice(token, traceparent: str, url: str):
    return http_client.get(
        url=url,
        headers={
            'Authorization': f'Bearer {token}',
            'traceparent': f'{traceparent}'
        },
        timeout=settings.default_timeout
    )


# ---------------------------------------------------------------------------
# Payments
# ---------------------------------------------------------------------------

def post_sil_invia_dovuti(token, traceparent: str, installment: Installment, debt_position_type_org_code: str,
                          ipa_code: str, marca_bollo: Optional[Stamp] = None):
    dovuto_base64 = _build_dovuto_base64(installment, debt_position_type_org_code, marca_bollo)
    data = _render('inviaDovuti.xml', dovuto=dovuto_base64, codice_ipa=ipa_code)

    return post_sil_payments(token=token, traceparent=traceparent, data=data)


def post_sil_invia_dovuto_eterogeneo(token, traceparent: str, debt_position_mixed: DebtPositionMixed, ipa_code: str):
    dati_versamento = "".join(
        _build_dati_singolo_versamento(
            iud=transfer_mixed.iud,
            amount_cents=transfer_mixed.amount_cents,
            tipo_dovuto=transfer_mixed.debt_position_type_org_code,
            dati_specifici_riscossione=transfer_mixed.legacy_payment_metadata,
        )
        for transfer_mixed in debt_position_mixed.transfers
    )
    dovuto_base64 = _build_dovuti_base64(debt_position_mixed.debtor, dati_versamento)
    data = _render('inviaDovuti.xml', dovuto=dovuto_base64, codice_ipa=ipa_code)

    return post_sil_payments(token=token, traceparent=traceparent, data=data)


def post_sil_invia_carrello_dovuti(token, traceparent: str, installment: Installment, debt_position_type_org_code: str,
                                   ipa_code: str, marca_bollo: Optional[Stamp] = None):
    dovuto_base64 = _build_dovuto_base64(installment, debt_position_type_org_code, marca_bollo)
    data = _render('inviaCarrelloDovuti.xml', dovuto=dovuto_base64, codice_ipa=ipa_code)

    return post_sil_payments(token=token, traceparent=traceparent, data=data)


def post_sil_invia_carrello_dovuti_enti_secondari(token, traceparent: str, installment: Installment, ipa_code: str,
                                                  second_transfer: Transfer, debt_position_type_org_code: str,
                                                  marca_bollo: Optional[Stamp] = None):
    dovuto_base64 = _build_dovuto_base64(installment, debt_position_type_org_code, marca_bollo)
    dovuto_secondario_base64 = _build_dovuto_secondario_base64(second_transfer)
    data = _render(
        'inviaCarrelloDovuti_entiSecondari.xml',
        dovuto=dovuto_base64,
        dovuto_secondario=dovuto_secondario_base64,
        codice_ipa=ipa_code,
    )

    return post_sil_payments(token=token, traceparent=traceparent, data=data)


def post_sil_importa_dovuto(token, traceparent: str, installment: Installment, debt_position_type_org_code: str,
                            ipa_code: str, action: SilDebtPositionAction = SilDebtPositionAction.INSERT):
    dovuto_base64 = _build_versamento_base64(installment, debt_position_type_org_code, action)
    data = _render('importaDovuto.xml', dovuto=dovuto_base64, codice_ipa=ipa_code)

    return post_sil_payments(token=token, traceparent=traceparent, data=data)


def post_sil_verifica_avviso(token, traceparent: str, iuv: str, ipa_code: str):
    data = _render('verificaAvviso.xml', codice_ipa=ipa_code, iuv=iuv)

    return post_sil_payments(token=token, traceparent=traceparent, data=data)


def post_sil_chiedi_esito_carrello_dovuti(token, traceparent: str, installment_id: int, ipa_code: str):
    data = _render('chiediEsitoCarrelloDovuti.xml', codice_ipa=ipa_code, id_session_carrello=installment_id)

    return post_sil_payments(token=token, traceparent=traceparent, data=data)


def post_sil_chiedi_pagati(token, traceparent: str, installment_id: int, ipa_code: str):
    data = _render('chiediPagati.xml', codice_ipa=ipa_code, id_session=installment_id)

    return post_sil_payments(token=token, traceparent=traceparent, data=data)


def post_sil_chiedi_pagati_con_ricevuta(token, traceparent: str, installment_id: int, ipa_code: str):
    data = _render('chiediPagatiConRicevuta.xml', codice_ipa=ipa_code, id_session=installment_id)

    return post_sil_payments(token=token, traceparent=traceparent, data=data)


def post_sil_prenota_export_flusso(token, traceparent: str, ipa_code: str, date_from: str, date_to: str,
                                   debt_position_type_org_code: str, version: str = 'v1.0'):
    data = _render(
        'prenotaExportFlusso.xml',
        codice_ipa=ipa_code,
        date_from=date_from,
        date_to=date_to,
        tipo_dovuto=debt_position_type_org_code,
        versione_tracciato=version,
    )

    return post_sil_payments(token=token, traceparent=traceparent, data=data)


def post_sil_prenota_export_flusso_incrementale_con_ricevuta(token, traceparent: str, ipa_code: str, date_from: str,
                                                             date_to: str, debt_position_type_org_code: str,
                                                             receipt: bool,
                                                             incremental: bool, version: str = 'v1.0'):
    data = _render(
        'prenotaExportFlussoIncrementaleConRicevuta.xml',
        codice_ipa=ipa_code,
        date_from=date_from,
        date_to=date_to,
        tipo_dovuto=debt_position_type_org_code,
        ricevuta=str(receipt).lower(),
        incrementale=str(incremental).lower(),
        versione_tracciato=version,
    )

    return post_sil_payments(token=token, traceparent=traceparent, data=data)


def post_sil_chiedi_stato_export_flusso(token, traceparent: str, ipa_code: str, request_token: str):
    data = _render('chiediStatoExportFlusso.xml', codice_ipa=ipa_code, request_token=request_token)

    return post_sil_payments(token=token, traceparent=traceparent, data=data)


# ---------------------------------------------------------------------------
# Reconciliation
# ---------------------------------------------------------------------------

def post_sil_autorizza_import_flusso_tesoreria(token, traceparent: str, ipa_code: str, flow_type: str = 'O'):
    data = _render('autorizzaImportFlussoTesoreria.xml', codice_ipa=ipa_code, tipo_flusso=flow_type)

    return post_sil_reconciliation(token=token, traceparent=traceparent, data=data)


def post_sil_chiedi_stato_import_flusso_tesoreria(token, traceparent: str, ipa_code: str, request_token: str):
    data = _render('chiediStatoImportFlussoTesoreria.xml', codice_ipa=ipa_code, request_token=request_token)

    return post_sil_reconciliation(token=token, traceparent=traceparent, data=data)


def post_sil_prenota_export_flusso_riconciliazione(token, traceparent: str, ipa_code: str, iuv: str,
                                                   classification_label: str, version: str = 'v1.4'):
    data = _render(
        'prenotaExportFlussoRiconciliazione.xml',
        codice_ipa=ipa_code,
        classificazione=classification_label,
        iuv=iuv,
        versione_tracciato=version,
    )

    return post_sil_reconciliation(token=token, traceparent=traceparent, data=data)


def post_sil_chiedi_stato_export_flusso_riconciliazione(token, traceparent: str, ipa_code: str, request_token: str):
    data = _render('chiediStatoExportFlussoRiconciliazione.xml', codice_ipa=ipa_code, request_token=request_token)

    return post_sil_reconciliation(token=token, traceparent=traceparent, data=data)
