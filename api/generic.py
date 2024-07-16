import requests

from config.configuration import settings


def get_service_io(ente_id: int, tipo_dovuto_id: int):
    return requests.get(
        f'{settings.api.base_path.io_notification}/service/{ente_id}/{tipo_dovuto_id}',
        timeout=settings.default_timeout
    )


def delete_service_io(service_id: str):
    return requests.delete(
        f'{settings.api.base_path.io_notification}/service/{service_id}',
        timeout=settings.default_timeout
    )
