import requests

from config.configuration import settings


def get_utenti(token, only_oper: bool = True):
    return requests.get(
        f'{settings.api.base_path.payhub}/{settings.api.path_root.operatore_admin}/utenti/search?onlyOper={only_oper}',
        headers={
            'Authorization': f'Bearer {token}'
        },
        timeout=settings.default_timeout)


def get_utenti_ente(token, ente_id: int):
    return requests.get(
        f'{settings.api.base_path.payhub}/{settings.api.path_root.operatore_admin}/utenti/search/ente/{ente_id}',
        headers={
            'Authorization': f'Bearer {token}'
        },
        timeout=settings.default_timeout)
