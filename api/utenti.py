import requests

from config.configuration import settings
from config.configuration import secrets


def get_utenti(token, only_oper: bool = True):
    return requests.get(
        f'{secrets.internal_base_url}/{settings.api.path_root.operatore_admin}/utenti/search?onlyOper={only_oper}',
        headers={
            'Authorization': f'Bearer {token}',
            settings.BROKER_ID_HEADER: secrets.ente.intermediario_id
        },
        timeout=settings.default_timeout)


def get_utenti_ente(token, ente_id: int):
    return requests.get(
        f'{secrets.internal_base_url}/{settings.api.path_root.operatore_admin}/utenti/search/ente/{ente_id}',
        headers={
            'Authorization': f'Bearer {token}',
            settings.BROKER_ID_HEADER: secrets.ente.intermediario_id
        },
        timeout=settings.default_timeout)
