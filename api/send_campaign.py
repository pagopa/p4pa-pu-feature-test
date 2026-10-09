from common import http_client
from config.configuration import secrets, settings


def get_send_campaigns(token, traceparent: str, organization_id: int, external_campaign_id: str):
    return http_client.get(
        url=f'{secrets.internal_base_url}{settings.api.ingress_path.send_bff}/{organization_id}/campaigns/',
        headers={
            'Authorization': f'Bearer {token}',
            'traceparent': f'{traceparent}'
        },
        params={
            'fetchAll': False,
            'page': 0,
            'size': 10,
            'externalCampaignId': external_campaign_id
        },
        timeout=settings.default_timeout
    )


def get_send_campaign_notifications(token, traceparent: str, organization_id: int, campaign_id: str):
    return http_client.get(
        url=f'{secrets.internal_base_url}{settings.api.ingress_path.send_bff}/{organization_id}/campaigns/{campaign_id}/notifications',
        headers={
            'Authorization': f'Bearer {token}',
            'traceparent': f'{traceparent}'
        },
        params={
            'page': 0,
            'size': 10
        },
        timeout=settings.default_timeout
    )


def get_send_campaign_notification_detail(token, traceparent: str, organization_id: int, campaign_id: str, notification_id: str):
    return http_client.get(
        url=f'{secrets.internal_base_url}{settings.api.ingress_path.send_bff}/{organization_id}/campaigns/{campaign_id}/notifications/{notification_id}',
        headers={
            'Authorization': f'Bearer {token}',
            'traceparent': f'{traceparent}'
        },
        timeout=settings.default_timeout
    )
