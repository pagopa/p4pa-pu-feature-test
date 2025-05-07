import requests

from config.configuration import secrets
from config.configuration import settings


def get_debt_position_type_org_by_code(token, organization_id: int, code: str):
    return requests.get(
        url=f'{secrets.internal_base_url}{settings.api.ingress_path.debt_position_type_org_crud}/findByOrganizationIdAndCode',
        params={
            'organizationId': organization_id,
            'code': code
        },
        headers={
            'Authorization': f'Bearer {token}'
        },
        timeout=settings.default_timeout
    )
