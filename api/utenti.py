import requests

from config.configuration import settings
from config.configuration import secrets


def get_utenti(token, only_oper: bool = True):
    return requests.get(
        f'{settings.api.base_path.payhub}/{settings.api.path_root.operatore_admin}/utenti/search?onlyOper={only_oper}',
        headers={
            'Authorization': f'Bearer {token}',
            settings.BROKER_ID_HEADER: secrets.ente.intermediario_id
        },
        timeout=settings.default_timeout)


def get_utenti_ente(token, ente_id: int):
    return requests.get(
        f'{settings.api.base_path.payhub}/{settings.api.path_root.operatore_admin}/utenti/search/ente/{ente_id}',
        headers={
            'Authorization': f'Bearer {token}',
            settings.BROKER_ID_HEADER: secrets.ente.intermediario_id
        },
        timeout=settings.default_timeout)


def get_utenti_ente_tipo_dovuto(token, ente_id: int, tipo_dovuto_id: int):
    return requests.get(
        f'{settings.api.base_path.payhub}/{settings.api.path_root.operatore_admin}/utenti/search/tipoDovuto/{ente_id}/{tipo_dovuto_id}',
        headers={
            'Authorization': f'Bearer {token}',
            settings.BROKER_ID_HEADER: secrets.ente.intermediario_id
        },
        timeout=settings.default_timeout)
