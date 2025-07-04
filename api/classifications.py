import requests

from config.configuration import secrets, settings


def get_classification(token, organization_id: int, iuv: str,
                       last_classification_date_from: str, last_classification_date_to: str):
    return requests.get(
        url=f'{secrets.internal_base_url}{settings.api.ingress_path.classifications}/organization/{organization_id}/classifications/treasured',
        headers={
            'Authorization': f'Bearer {token}'
        },
        params={
            'lastClassificationDateFrom': last_classification_date_from,
            'lastClassificationDateTo': last_classification_date_to,
            'iuv': iuv,
            'debtPositionTypeOrgCodes': [settings.debt_position_type_org_code, 'UNKNOWN']
        },
        timeout=settings.default_timeout
    )
