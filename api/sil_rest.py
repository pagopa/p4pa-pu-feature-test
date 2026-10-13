from common import http_client
from config.configuration import secrets, settings
from model.file import IngestionFlowFileType


def post_authorize_import_massive_file(token, traceparent: str, org_fiscal_code: str,
                                       ingestion_flow_file_type: IngestionFlowFileType):
    return http_client.post(
        url=f'{secrets.internal_base_url}{settings.api.ingress_path.sil}/organization/{org_fiscal_code}/import',
        headers={
            'Authorization': f'Bearer {token}',
            'traceparent': f'{traceparent}'
        },
        json={
            'importFileType': ingestion_flow_file_type.value,
        },
        timeout=settings.default_timeout
    )
