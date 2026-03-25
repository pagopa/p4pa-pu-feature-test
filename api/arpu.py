import json

import requests

from config.configuration import secrets, settings


def get_broker_info(external_id: str):
    return requests.get(
        url=f'{secrets.base_url}{settings.api.ingress_path.arpu}/brokers',
        params={
            'externalId': external_id,
        },
        timeout=settings.default_timeout
    )


def get_orgs_info_for_spontaneous(broker_id: int):
    return requests.get(
        url=f'{secrets.base_url}{settings.api.ingress_path.arpu}/brokers/{broker_id}/spontaneous/organizations',
        timeout=settings.default_timeout
    )


def get_debt_position_type_orgs_for_spontaneous(broker_id: int, organization_id: int):
    return requests.get(
        url=f'{secrets.base_url}{settings.api.ingress_path.arpu}/brokers/{broker_id}/spontaneous/organizations/{organization_id}/debt-position-type-orgs',
        timeout=settings.default_timeout
    )


def post_create_spontaneous(broker_id: int, debt_position_spontaneous: str):
    return requests.post(
        url=f'{secrets.base_url}{settings.api.ingress_path.arpu}/brokers/{broker_id}/spontaneous/debt-positions',
        json=json.loads(debt_position_spontaneous),
        headers={
            'X-recaptcha-token': 'test'
        },
        timeout=settings.default_timeout
    )
