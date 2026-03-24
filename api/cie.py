import requests

from config.configuration import secrets, settings


def get_cie_organizations():
    return requests.get(
        url=f'{secrets.base_url}{settings.api.ingress_path.cie}/organizations',
        timeout=settings.default_timeout
    )


def get_cie_amount(org_fiscal_code: str, debt_position_type_org_code: str):
    return requests.get(
        url=f'{secrets.base_url}{settings.api.ingress_path.cie}/organizations/{org_fiscal_code}/amount',
        params={
            'debtPositionTypeOrgCode': debt_position_type_org_code
        },
        timeout=settings.default_timeout
    )
