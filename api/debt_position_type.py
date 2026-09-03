from common import http_client
from config.configuration import secrets
from config.configuration import settings


def get_debt_position_type_org_by_code(token, traceparent: str, organization_id: int, code: str):
    return http_client.get(
        url=f'{secrets.internal_base_url}{settings.api.ingress_path.debt_position_type_org_crud}/findByOrganizationIdAndCode',
        params={
            'organizationId': organization_id,
            'code': code
        },
        headers={
            'Authorization': f'Bearer {token}',
            'traceparent': f'{traceparent}'
        },
        timeout=settings.default_timeout
    )


def get_debt_position_type_by_id(token, traceparent: str, debt_position_type_id: int):
    return http_client.get(
        url=f'{secrets.internal_base_url}{settings.api.ingress_path.debt_positions}/crud/debt-position-types/{debt_position_type_id}',
        headers={
            'Authorization': f'Bearer {token}',
            'traceparent': f'{traceparent}'
        },
        timeout=settings.default_timeout
    )


def get_dpto_balance_cost_by_id(token, traceparent: str, dptobc_id: str):
    return http_client.get(
        url=f'{secrets.internal_base_url}{settings.api.ingress_path.debt_positions}/crud/debt-position-type-org-balance-costs/{dptobc_id}',
        headers={
            'Authorization': f'Bearer {token}',
            'traceparent': f'{traceparent}'
        },
        timeout=settings.default_timeout
    )
