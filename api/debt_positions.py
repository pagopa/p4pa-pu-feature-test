import json

import requests

from config.configuration import secrets
from config.configuration import settings


def post_create_debt_position(token, debt_position: str, massive: bool = False):
    return requests.post(
        url=f'{secrets.internal_base_url}{settings.api.ingress_path.debt_positions}/debt-positions',
        headers={
            'Authorization': f'Bearer {token}'
        },
        json=json.loads(debt_position),
        params={
            'massive': massive
        },
        timeout=settings.default_timeout
    )


def get_debt_position(token, debt_position_id: int):
    return requests.get(
        url=f'{secrets.internal_base_url}{settings.api.ingress_path.debt_positions}/debt-positions/{debt_position_id}',
        headers={
            'Authorization': f'Bearer {token}'
        },
        timeout=settings.default_timeout
    )


def get_debt_position_by_organization_id_and_installment_nav(token, organization_id: int, installment_nav: int):
    return requests.get(
        url=f'{secrets.internal_base_url}{settings.api.ingress_path.debt_positions}/crud/debt-positions/search/findByOrganizationIdAndInstallmentNav',
        headers={
            'Authorization': f'Bearer {token}'
        },
        params={
            'organizationId': organization_id,
            'nav': installment_nav
        },
        timeout=settings.default_timeout
    )


def get_installment(token, installment_id: int):
    return requests.get(
        url=f'{secrets.internal_base_url}{settings.api.ingress_path.debt_positions}/crud/installments/{installment_id}',
        headers={
            'Authorization': f'Bearer {token}'
        },
        timeout=settings.default_timeout
    )


def get_debt_positions_by_ingestion_flow_id(token, ingestion_flow_id: int):
    return requests.get(
        url=f'{secrets.internal_base_url}{settings.api.ingress_path.debt_positions}/debt-positions/ingestion-flow-file/{ingestion_flow_id}',
        headers={
            'Authorization': f'Bearer {token}'
        },
        timeout=settings.default_timeout
    )


def get_receipt(token, organization_id, receipt_origin, iuv, iur):
    return requests.get(
        url=f'{secrets.internal_base_url}{settings.api.ingress_path.bff}/organization/{organization_id}/receipts',
        headers={
            'Authorization': f'Bearer {token}'
        },
        params={
            'receiptOrigin': receipt_origin,
            'iuv': iuv,
            'iur': iur
        },
        timeout=settings.default_timeout
    )
