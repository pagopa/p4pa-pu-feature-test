import json

import requests

from config.configuration import secrets
from config.configuration import settings


def get_spontaneous_form_by_organization_id_and_debt_position_type_org_code(token, organization_id, debt_position_type_org_code: str):
    return requests.get(
        url=f'{secrets.internal_base_url}{settings.api.ingress_path.spontaneous_form_crud}/findByOrganizationIdAndCode',
        headers={
            'Authorization': f'Bearer {token}'
        },
      params={
        'organizationId': organization_id,
        'code': debt_position_type_org_code
      },
        timeout=settings.default_timeout
    )
