import requests

from config.configuration import secrets
from config.configuration import settings


def post_auth_token(user_id: str):
    return requests.post(
        url=f'{secrets.base_url}/pu/auth/oauth/token',
        params={
            'client_id': 'piattaforma-unitaria',
            'grant_type': 'urn:ietf:params:oauth:grant-type:token-exchange',
            'subject_token': user_id,
            'subject_token_type': 'FAKE-AUTH',
            'subject_issuer': 'issuer-fake',
            'scope': 'openid-fake'
        },
        timeout=settings.default_timeout
    )
