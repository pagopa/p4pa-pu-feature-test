import requests

from config.configuration import settings
from config.configuration import secrets


def get_debt_position_on_gpd(org_fiscal_code: str, iupd_pagopa: str):
    return requests.get(
        f'{settings.api.base_path.gpd}/organizations/{org_fiscal_code}/debtpositions/{iupd_pagopa}',
        headers={
            settings.API_KEY_HEADER: secrets.api_key.gpd
        },
        timeout=settings.default_timeout
    )


def get_debt_position_on_aca(org_fiscal_code: str, iupd_pagopa: str):
    return requests.get(
        f'{settings.api.base_path.gpd}/organizations/{org_fiscal_code}/debtpositions/{iupd_pagopa}',
        headers={
            settings.API_KEY_HEADER: secrets.api_key.aca
        },
        timeout=settings.default_timeout
    )
