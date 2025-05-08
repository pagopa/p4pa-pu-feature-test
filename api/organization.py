import requests

from config.configuration import settings
from config.configuration import secrets


def get_org_by_ipa_code(token, ipa_code: str):
    return requests.get(
        url=f'{secrets.internal_base_url}{settings.api.ingress_path.organization_crud}/findByIpaCode',
        params={
            'ipaCode': ipa_code
        },
        headers={
            'Authorization': f'Bearer {token}'
        },
        timeout=settings.default_timeout
    )
