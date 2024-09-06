import requests

from config.configuration import settings
from config.configuration import secrets


def post_auth_password(user_id: str):
    return requests.post(
        url=f'{secrets.internal_base_url}/p4paauth/payhub/auth/token',
        params={
            'client_id': 'piattaforma-unitaria',
            'grant_type': 'grant-type-fake',
            'subject_token': user_id,
            'subject_token_type': 'FAKE-AUTH',
            'subject_issuer': 'issuer-fake',
            'scope': 'openid-fake'
        },
        timeout=settings.default_timeout
    )
