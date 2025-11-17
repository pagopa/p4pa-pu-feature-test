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


def post_external_auth_token(client_id: str, client_secret: str):
    return requests.post(
        url=f'{secrets.base_url}/pu/auth/oauth/token',
        params={
            'client_id': client_id,
            'client_secret': client_secret,
            'grant_type': 'client_credentials',
            'scope': 'openid'
        },
        timeout=settings.default_timeout
    )