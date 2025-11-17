import base64

import requests

from config.configuration import settings, secrets
from model.debt_position_mixed import DebtPositionMixed


def post_sil_invia_dovuto(token, debt_position_mixed: DebtPositionMixed, ipa_code: str):
    dati_versamento = ""
    for transfer_mixed in debt_position_mixed.transfers:
        with open('./api/soap/requests_template_sil/datiVersamento.xml', 'r') as file:
            dati_singolo_versamento_data = file.read()
        dati_singolo_versamento = dati_singolo_versamento_data.format(iud=transfer_mixed.iud,
                                                                      importo=transfer_mixed.amount,
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

    return requests.post(
        url=f'{secrets.base_url}{settings.api.ingress_path.sil_payments}',
        headers={
            'Content-Type': 'text/xml',
            'Authorization': f'Bearer {token}'
        },
        verify=False,
        data=data,
        timeout=settings.default_timeout
    )
