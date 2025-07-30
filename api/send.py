import json

import requests

from config.configuration import secrets, settings


def post_create_send_notification(token, payload: str):
    return requests.post(
        url=f'{secrets.internal_base_url}{settings.api.ingress_path.send_notification}/notification',
        headers={
            'Authorization': f'Bearer {token}'
        },
        json=json.loads(payload),
        timeout=settings.default_timeout
    )

def post_upload_send_file(token, org_id: int, notification_id: str, file_path: str, digest: str):
    return requests.post(
        url=f'{secrets.internal_base_url}{settings.api.ingress_path.fileshare}/organization/{org_id}/send-files/{notification_id}',
        headers={
            'Authorization': f'Bearer {token}'
        },
        data={
            'digest': digest
        },
        files={
            'sendFile': open(file_path, 'rb')
        },
        timeout=settings.default_timeout
    )

def get_send_notification_status(token, notification_id: str):
    return requests.get(
        url=f'{secrets.internal_base_url}{settings.api.ingress_path.send_notification}/send/{notification_id}/status',
        headers={
            'Authorization': f'Bearer {token}'
        },
        timeout=settings.default_timeout
    )


def get_send_notification_fee(token, nav: str, org_id: int):
    return requests.get(
        url=f'{secrets.internal_base_url}{settings.api.ingress_path.send_notification}/send/notificationprice',
        headers={
            'Authorization': f'Bearer {token}'
        },
        params={
            'organizationId': org_id,
            'nav': nav
        },
        timeout=settings.default_timeout
    )
