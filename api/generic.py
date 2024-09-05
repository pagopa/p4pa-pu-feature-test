import requests

from config.configuration import settings
from config.configuration import secrets


def get_service_io(ente_id: int, tipo_dovuto_id: int):
    return requests.get(
        f'{secrets.internal_base_url}/{settings.api.path_root.io_notification}/service/{ente_id}/{tipo_dovuto_id}',
        timeout=settings.default_timeout
    )


def delete_service_io(service_id: str):
    return requests.delete(
        f'{secrets.internal_base_url}/{settings.api.path_root.io_notification}/service/{service_id}',
        timeout=settings.default_timeout
    )
