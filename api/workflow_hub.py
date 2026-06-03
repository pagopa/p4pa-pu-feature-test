import requests

from config.configuration import secrets
from config.configuration import settings


def get_workflow_status(token, traceparent: str, workflow_id: str):
    return requests.get(
        url=f'{secrets.internal_base_url}{settings.api.ingress_path.workflow_hub}/{workflow_id}/status',
        headers={
            'Authorization': f'Bearer {token}',
            'traceparent': f'{traceparent}'
        },
        timeout=settings.default_timeout
    )
