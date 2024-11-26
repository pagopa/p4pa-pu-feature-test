import requests

from config.configuration import secrets
from config.configuration import settings


def get_tesoreria_by_iuf(token, ente_id: str, iuf: str):
    return requests.get(
        f'{secrets.internal_base_url}/{settings.api.path_root.payhub_pivot}/tesoreria/search/{ente_id}',
        headers={
            'Authorization': f'Bearer {token}',
            settings.BROKER_ID_HEADER: secrets.ente.intermediario_id
        },
        params={
            'idr': iuf
        },
        timeout=settings.default_timeout
    )
