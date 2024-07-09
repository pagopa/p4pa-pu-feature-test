import requests

from config.configuration import settings


def post_auth_password(user_id: str):
    return requests.post(
        url=f'{settings.api.base_path.internal}/p4paauth/payhub/auth/token',
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
