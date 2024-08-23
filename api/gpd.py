import requests

from config.configuration import settings
from config.configuration import secrets


def get_debt_position_by_iupd(ente_fiscal_code: str, iupd: str):
    return requests.get(
        f'{settings.api.base_path.gpd}/organizations/{ente_fiscal_code}/debtpositions/{iupd}',
        headers={
            settings.API_KEY_HEADER: secrets.api_key.GPD
        },
        timeout=settings.default_timeout
    )
