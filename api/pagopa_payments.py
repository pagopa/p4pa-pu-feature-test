import json

import requests

from config.configuration import settings
from config.configuration import secrets


def post_create_debt_position_on_gpd(token, traceparent: str, debt_position: str, iud: str):
    return requests.post(
        url=f'{secrets.internal_base_url}{settings.api.ingress_path.pagopa_payments}/gpd/sync',
        headers={
            'Authorization': f'Bearer {token}',
            'traceparent': f'{traceparent}'
        },
        json=json.loads(debt_position),
        params={
            'iud': iud
        },
        timeout=settings.default_timeout
    )