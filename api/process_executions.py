import requests

from config.configuration import secrets, settings


def get_by_org_and_file_path_and_file_name(token, organization_id: int, file_path_name: str, file_name: str):
    return requests.get(
        url=f'{secrets.internal_base_url}{settings.api.ingress_path.process_executions_crud}/findByOrganizationIdAndFilePathNameAndFileName',
        headers={
            'Authorization': f'Bearer {token}'
        },
        params={
            'organizationId': organization_id,
            'filePathName': file_path_name,
            'fileName': file_name
        },
        timeout=settings.default_timeout
    )

