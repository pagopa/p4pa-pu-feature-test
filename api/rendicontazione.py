import requests

from config.configuration import secrets
from config.configuration import settings


def get_rendicontazione_by_iuf_and_id_regolamento(token, ente_id: int, iuf: str, id_regolamento: str):
    return requests.get(
        f'{secrets.internal_base_url}/{settings.api.path_root.payhub_pivot}/rendicontazione/detail/{ente_id}/{iuf}/{id_regolamento}',
        headers={
            'Authorization': f'Bearer {token}',
            settings.BROKER_ID_HEADER: secrets.ente.intermediario_id
        },
        timeout=settings.default_timeout
    )
