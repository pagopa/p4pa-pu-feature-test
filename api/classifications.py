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
            'debtPositionTypeOrgCodes': [settings.debt_position_type_org_code.feature_test, 'UNKNOWN']
        },
        timeout=settings.default_timeout
    )


def get_assessment(token, organization_id: int, debt_position_type_org_code: str,
                       assessment_name: str):
    return requests.get(
        url=f'{secrets.internal_base_url}{settings.api.ingress_path.classifications}/crud/assessments/search/findByOrganizationIdAndDebtPositionTypeOrgCodeAndAssessmentName',
        headers={
            'Authorization': f'Bearer {token}'
        },
        params={
            'organizationId': organization_id,
            'debtPositionTypeOrgCode': debt_position_type_org_code,
            'assessmentName': assessment_name
        },
        timeout=settings.default_timeout
    )


def get_assessment_details(token, assessment_id: int, iud: str, iuv: str):
    return requests.get(
        url=f'{secrets.internal_base_url}{settings.api.ingress_path.classifications}/crud/assessments-details/search/findAssessmentsRowsDetail',
        headers={
            'Authorization': f'Bearer {token}'
        },
        params={
            'assessmentId': assessment_id,
            'iud': iud,
            'iuv': iuv
        },
        timeout=settings.default_timeout
    )

def get_assessment_registry(token, organization_id: int, debt_position_type_org_code: str):
    return requests.get(
        url=f'{secrets.internal_base_url}{settings.api.ingress_path.classifications}/crud/assessments-registries/search/findAssessmentsRegistriesByFilters',
        headers={
            'Authorization': f'Bearer {token}'
        },
        params={
            'organizationId': organization_id,
            'debtPositionTypeOrgCodes': [debt_position_type_org_code],
            'status': 'ACTIVE'
        },
        timeout=settings.default_timeout
    )