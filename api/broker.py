import requests

from config.configuration import secrets
from config.configuration import settings


def get_broker_by_broker_id(token, broker_id: int):
    return requests.get(
        url=f'{secrets.internal_base_url}{settings.api.ingress_path.organization}/crud/brokers/{broker_id}',
        headers={
            'Authorization': f'Bearer {token}'
        },
        timeout=settings.default_timeout
    )
