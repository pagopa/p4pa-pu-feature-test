import requests

from config.configuration import secrets, settings
from model.file import IngestionFlowFileType, FileOrigin


def post_upload_file(token, organization_id: int, ingestion_flow_file_type: IngestionFlowFileType,
                     file_origin: FileOrigin, file_name: str):
    return requests.post(
        url=f'{secrets.internal_base_url}{settings.api.ingress_path.fileshare}/organization/{organization_id}/ingestionflowfiles',
        headers={
            'Authorization': f'Bearer {token}'
        },
        params={
            'ingestionFlowFileType': ingestion_flow_file_type.value,
            'fileOrigin': file_origin.value,
            'fileName': file_name
        },
        files={
            'ingestionFlowFile': (file_name, open(file_name, 'rb'))
        },
        timeout=settings.default_timeout
    )
