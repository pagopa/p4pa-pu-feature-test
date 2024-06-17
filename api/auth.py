import requests

from config.configuration import settings


def post_auth_password(user_info: dict):
    return requests.post(
        url=f'{settings.api.base_path.payhub}/{settings.api.path_root.public}/authpassword',
        json=user_info,
        timeout=settings.default_timeout
    )

