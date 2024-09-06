import requests

from config.configuration import settings
from config.configuration import secrets


def get_enti_list(token, logo_mode: str = 'hash', cod_ipa_ente: str = None):
    return requests.get(
        f'{secrets.internal_base_url}/{settings.api.path_root.operatore_admin}/enti',
        headers={
            'Authorization': f'Bearer {token}',
            settings.BROKER_ID_HEADER: secrets.ente.intermediario_id
        },
        params={
            'logoMode': logo_mode,
            'codIpaEnte': cod_ipa_ente
        },
        timeout=settings.default_timeout
    )


def get_ente_details(token, ente_id: int):
    return requests.get(
        f'{secrets.internal_base_url}/{settings.api.path_root.operatore_admin}/enti/{ente_id}',
        headers={
            'Authorization': f'Bearer {token}',
            settings.BROKER_ID_HEADER: secrets.ente.intermediario_id
        },
        timeout=settings.default_timeout
    )


def get_ente_details_public(token, ente_id: int):
    return requests.get(
        f'{secrets.internal_base_url}/{settings.api.path_root.public}/enti/{ente_id}',
        headers={
            'Authorization': f'Bearer {token}',
            settings.BROKER_ID_HEADER: secrets.ente.intermediario_id
        },
        timeout=settings.default_timeout
    )


def post_insert_ente(token,
                     name_ente: str,
                     cod_ipa_ente: str,
                     email_ente: str,
                     application_code: str,
                     fiscal_code_ente: str,
                     cod_tipo_ente: str,
                     cod_stato_ente: dict,
                     insert_default_set: bool = False,
                     bic_accredito_seller: bool = False,
                     iban_accredito: str = ''
                     ):
    return requests.post(
        f'{secrets.internal_base_url}/{settings.api.path_root.operatore_admin}/enti/ente/insert',
        headers={
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
            settings.BROKER_ID_HEADER: secrets.ente.intermediario_id
        },
        json={
            'codIpaEnte': cod_ipa_ente,
            'deNomeEnte': name_ente,
            'cdStatoEnte': cod_stato_ente,
            'emailAmministratore': email_ente,
            'applicationCode': application_code,
            'codiceFiscaleEnte': fiscal_code_ente,
            'codTipoEnte': cod_tipo_ente,
            'flagInsertDefaultSet': insert_default_set,
            'codRpDatiVersDatiSingVersBicAccreditoSeller': bic_accredito_seller,
            'codRpDatiVersDatiSingVersIbanAccredito': iban_accredito
        },
        timeout=settings.default_timeout
    )


def post_update_ente(token,
                     ente_id: int,
                     name_ente: str,
                     cod_ipa_ente: str,
                     email_ente: str,
                     application_code: str,
                     fiscal_code_ente: str,
                     cod_tipo_ente: str,
                     cod_stato_ente: dict,
                     insert_default_set: bool = False,
                     bic_accredito_seller: bool = False,
                     iban_accredito: str = ''
                     ):
    return requests.post(
        f'{secrets.internal_base_url}/{settings.api.path_root.operatore_admin}/enti/{ente_id}/update',
        headers={
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
            settings.BROKER_ID_HEADER: secrets.ente.intermediario_id
        },
        json={
            'mygovEnteId': ente_id,
            'codIpaEnte': cod_ipa_ente,
            'deNomeEnte': name_ente,
            'cdStatoEnte': cod_stato_ente,
            'emailAmministratore': email_ente,
            'applicationCode': application_code,
            'codiceFiscaleEnte': fiscal_code_ente,
            'codTipoEnte': cod_tipo_ente,
            'flagInsertDefaultSet': insert_default_set,
            'codRpDatiVersDatiSingVersBicAccreditoSeller': bic_accredito_seller,
            'codRpDatiVersDatiSingVersIbanAccredito': iban_accredito
    },
        timeout=settings.default_timeout
    )


def get_anagrafica_stati_ente(token):
    return requests.get(
        f'{secrets.internal_base_url}/{settings.api.path_root.operatore_admin}/enti/anagraficaStati',
        headers={
            'Authorization': f'Bearer {token}',
            settings.BROKER_ID_HEADER: secrets.ente.intermediario_id
        },
        timeout=settings.default_timeout
    )


def get_tipi_ente(token):
    return requests.get(
        f'{secrets.internal_base_url}/{settings.api.path_root.operatore_admin}/enti/tipiEnte',
        headers={
            'Authorization': f'Bearer {token}',
            settings.BROKER_ID_HEADER: secrets.ente.intermediario_id
        },
        timeout=settings.default_timeout
    )


def get_funzionalita_ente(token, ente_id: int):
    return requests.get(
        f'{secrets.internal_base_url}/{settings.api.path_root.operatore_admin}/enti/funzionalita/{ente_id}',
        headers={
            'Authorization': f'Bearer {token}',
            settings.BROKER_ID_HEADER: secrets.ente.intermediario_id
        },
        timeout=settings.default_timeout
    )


def get_registro_funzionalita(token, ente_id: int, funzionalita: str):
    return requests.get(
        f'{secrets.internal_base_url}/{settings.api.path_root.operatore_admin}/enti/funzionalita/{ente_id}/{funzionalita}',
        headers={
            'Authorization': f'Bearer {token}',
            settings.BROKER_ID_HEADER: secrets.ente.intermediario_id
        },
        timeout=settings.default_timeout
    )


def get_activate_funzionalita(token, funzionalita_id: int):
    return requests.get(
        f'{secrets.internal_base_url}/{settings.api.path_root.operatore_admin}/enti/funzionalita/activate/{funzionalita_id}',
        headers={
            'Authorization': f'Bearer {token}',
            settings.BROKER_ID_HEADER: secrets.ente.intermediario_id
        },
        timeout=settings.default_timeout
    )


def get_deactivate_funzionalita(token, funzionalita_id: int):
    return requests.get(
        f'{secrets.internal_base_url}/{settings.api.path_root.operatore_admin}/enti/funzionalita/deactivate/{funzionalita_id}',
        headers={
            'Authorization': f'Bearer {token}',
            settings.BROKER_ID_HEADER: secrets.ente.intermediario_id
        },
        timeout=settings.default_timeout
    )


def post_save_logo(token, ente_id: int, file):
    return requests.post(
        f'{secrets.internal_base_url}/{settings.api.path_root.operatore_admin}/enti/{ente_id}/saveLogo',
        headers={
            'Authorization': f'Bearer {token}',
            settings.BROKER_ID_HEADER: secrets.ente.intermediario_id
        },
        files={
            'file': file
        },
        timeout=settings.default_timeout
    )
