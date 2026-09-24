import base64
import re

from common import http_client
from config.configuration import settings, secrets
from model.debt_position import Installment, Transfer
from model.debt_position_mixed import DebtPositionMixed


def checkout_url_pattern(org_fiscal_code: str) -> str:
    base = f'{secrets.base_url}{settings.api.ingress_path.sil}'
    return re.escape(base) + rf'/organization/{re.escape(org_fiscal_code)}/checkout\?token=[^&]+$'


def post_sil_invia_dovuto(token, traceparent: str, debt_position_mixed: DebtPositionMixed, ipa_code: str):
    dati_versamento = ""
    for transfer_mixed in debt_position_mixed.transfers:
        with open('./api/soap/requests_template_sil/datiVersamento.xml', 'r') as file:
            dati_singolo_versamento_data = file.read()
        dati_singolo_versamento = dati_singolo_versamento_data.format(iud=transfer_mixed.iud,
                                                                      importo="{:.2f}".format(
                                                                          int(transfer_mixed.amount_cents) / 100),
                                                                      tipo_dovuto=transfer_mixed.debt_position_type_org_code,
                                                                      dati_specifici_riscossione=transfer_mixed.legacy_payment_metadata)

        dati_versamento += dati_singolo_versamento

    with open('./api/soap/requests_template_sil/dovuti.xml', 'r') as file:
        dovuti_data = file.read()
    dovuti = dovuti_data.format(codice_fiscale=debt_position_mixed.debtor.fiscal_code,
                                nome=debt_position_mixed.debtor.full_name,
                                email=debt_position_mixed.debtor.email,
                                dati_versamento=dati_versamento)

    dovuto_base64 = base64.b64encode(dovuti.encode('utf-8')).decode('utf-8')

    with open('./api/soap/requests_template_sil/inviaDovuti.xml', 'r') as file:
        invia_dovuti_data = file.read()
    data = invia_dovuti_data.format(dovuto=dovuto_base64, codice_ipa=ipa_code)

    return post_sil_payments(token=token, traceparent=traceparent, data=data)


def post_sil_prenota_export_flusso(token, traceparent: str, ipa_code: str, date_from: str, date_to: str,
                                   debt_position_type_org_code: str, version: str = 'v1.0'):
    with open('./api/soap/requests_template_sil/prenotaExportFlusso.xml', 'r') as file:
        data = file.read()
    data = data.format(codice_ipa=ipa_code, date_from=date_from, date_to=date_to,
                       tipo_dovuto=debt_position_type_org_code, versione_tracciato=version)

    return post_sil_payments(token=token, traceparent=traceparent, data=data)


def post_sil_prenota_export_flusso_incrementale_con_ricevuta(token, traceparent: str, ipa_code: str, date_from: str,
                                                             date_to: str, debt_position_type_org_code: str,
                                                             receipt: bool,
                                                             incremental: bool, version: str = 'v1.0'):
    with open('./api/soap/requests_template_sil/prenotaExportFlussoIncrementaleConRicevuta.xml', 'r') as file:
        data = file.read()
    data = data.format(codice_ipa=ipa_code, date_from=date_from, date_to=date_to,
                       tipo_dovuto=debt_position_type_org_code,
                       ricevuta=str(receipt).lower(), incrementale=str(incremental).lower(),
                       versione_tracciato=version)

    return post_sil_payments(token=token, traceparent=traceparent, data=data)


def post_sil_chiedi_stato_export_flusso(token, traceparent: str, ipa_code: str, request_token: str):
    with open('./api/soap/requests_template_sil/chiediStatoExportFlusso.xml', 'r') as file:
        data = file.read()
    data = data.format(codice_ipa=ipa_code, request_token=request_token)

    return post_sil_payments(token=token, traceparent=traceparent, data=data)


def _build_dovuto_base64(installment: Installment, debt_position_type_org_code: str) -> str:
    with open('./api/soap/requests_template_sil/datiVersamento.xml', 'r') as file:
        dati_singolo_versamento_data = file.read()
    dati_singolo_versamento = dati_singolo_versamento_data.format(
        iud=installment.iud,
        importo="{:.2f}".format(int(installment.amount_cents) / 100),
        tipo_dovuto=debt_position_type_org_code,
        dati_specifici_riscossione=installment.legacy_payment_metadata,
    )

    with open('./api/soap/requests_template_sil/dovuti.xml', 'r') as file:
        dovuti_data = file.read()
    dovuti = dovuti_data.format(
        codice_fiscale=installment.debtor.fiscal_code,
        nome=installment.debtor.full_name,
        email=installment.debtor.email,
        dati_versamento=dati_singolo_versamento,
    )

    return base64.b64encode(dovuti.encode('utf-8')).decode('utf-8')


def _build_dovuto_secondario_base64(second_transfer: Transfer) -> str:
    with open('./api/soap/requests_template_sil/dovutiEntiSecondari.xml', 'r') as file:
        dovuti_enti_secondari_data = file.read()
    dovuti_enti_secondari = dovuti_enti_secondari_data.format(
        codice_fiscale_ente_secondario=second_transfer.org_fiscal_code,
        nome_ente_secondario=second_transfer.org_name,
        iban_ente_secondario=second_transfer.iban,
        causale_ente_secondario=second_transfer.remittance_information,
        dati_specifici_riscossione_ente_secondario=second_transfer.category,
        importo_ente_secondario="{:.2f}".format(int(second_transfer.amount_cents) / 100),
    )

    return base64.b64encode(dovuti_enti_secondari.encode('utf-8')).decode('utf-8')


def post_sil_invia_carrello_dovuti(token, traceparent: str, installment: Installment, debt_position_type_org_code: str,
                                   ipa_code: str):
    dovuto_base64 = _build_dovuto_base64(installment, debt_position_type_org_code)

    with open('./api/soap/requests_template_sil/inviaCarrelloDovuti.xml', 'r') as file:
        invia_carrello_dovuti_data = file.read()
    data = invia_carrello_dovuti_data.format(dovuto=dovuto_base64, codice_ipa=ipa_code)

    return post_sil_payments(token=token, traceparent=traceparent, data=data)


def post_sil_invia_carrello_dovuti_enti_secondari(token, traceparent: str, installment: Installment, ipa_code: str,
                                                  second_transfer: Transfer, debt_position_type_org_code: str):
    dovuto_base64 = _build_dovuto_base64(installment, debt_position_type_org_code)
    dovuto_secondario_base64 = _build_dovuto_secondario_base64(second_transfer)

    with open('./api/soap/requests_template_sil/inviaCarrelloDovuti_entiSecondari.xml', 'r') as file:
        invia_carrello_dovuti_data = file.read()
    data = invia_carrello_dovuti_data.format(
        dovuto=dovuto_base64,
        dovuto_secondario=dovuto_secondario_base64,
        codice_ipa=ipa_code,
    )

    return post_sil_payments(token=token, traceparent=traceparent, data=data)


def post_sil_chiedi_esito_carrello_dovuti(token, traceparent: str, installment_id: int, ipa_code: str):
    with open('./api/soap/requests_template_sil/chiediEsitoCarrelloDovuti.xml', 'r') as file:
        invia_dovuti_data = file.read()
    data = invia_dovuti_data.format(codice_ipa=ipa_code, id_session_carrello=installment_id)

    return post_sil_payments(token=token, traceparent=traceparent, data=data)


def post_sil_payments(token, traceparent: str, data: str):
    return http_client.post(
        url=f'{secrets.base_url}{settings.api.ingress_path.sil_payments}',
        headers={
            'Content-Type': 'text/xml',
            'Authorization': f'Bearer {token}',
            'traceparent': f'{traceparent}'
        },
        data=data,
        timeout=settings.default_timeout
    )
