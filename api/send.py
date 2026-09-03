import json

from common import http_client
from config.configuration import secrets, settings


def post_create_send_notification(token, traceparent: str, payload: str):
    return http_client.post(
        url=f'{secrets.internal_base_url}{settings.api.ingress_path.send_notification}/notification',
        headers={
            'Authorization': f'Bearer {token}',
            'traceparent': f'{traceparent}'
        },
        json=json.loads(payload),
        timeout=settings.default_timeout
    )

def post_upload_send_file(token, traceparent: str, org_id: int, notification_id: str, file_path: str, digest: str):
    return http_client.post(
        url=f'{secrets.internal_base_url}{settings.api.ingress_path.fileshare}/organization/{org_id}/send-files/{notification_id}',
        headers={
            'Authorization': f'Bearer {token}',
            'traceparent': f'{traceparent}'
        },
        data={
            'digest': digest
        },
        files={
            'sendFile': open(file_path, 'rb')
        },
        timeout=settings.default_timeout
    )

def get_send_notification(token, traceparent: str, notification_id: str):
    return http_client.get(
        url=f'{secrets.internal_base_url}{settings.api.ingress_path.send_notification}/notification/{notification_id}',
        headers={
            'Authorization': f'Bearer {token}',
            'traceparent': f'{traceparent}'
        },
        timeout=settings.default_timeout
    )

def get_send_notification_fee(token, traceparent: str, nav: str, org_id: int):
    return http_client.get(
        url=f'{secrets.internal_base_url}{settings.api.ingress_path.send_notification}/send/notificationprice',
        headers={
            'Authorization': f'Bearer {token}',
            'traceparent': f'{traceparent}'
        },
        params={
            'organizationId': org_id,
            'nav': nav
        },
        timeout=settings.default_timeout
    )
