import requests

from config.configuration import settings
from config.configuration import secrets


def post_import_flusso(token, file, ente_id: int, upload_type: str = 'FLUSSI_IMPORT'):
    return requests.post(
        f'{secrets.internal_base_url}/{settings.api.path_root.payhub}/mybox/upload/{ente_id}',
        headers={
            'Authorization': f'Bearer {token}',
            settings.BROKER_ID_HEADER: secrets.ente.intermediario_id
        },
        params={
            'type': upload_type
        },
        files=file,
        timeout=settings.default_timeout
    )


def get_imported_flussi(token, ente_id: int, date_from, date_to, nome_flusso: str = None):
    return requests.get(
        f'{secrets.internal_base_url}/{settings.api.path_root.operatore}/flussi/import/{ente_id}',
        headers={
            'Authorization': f'Bearer {token}',
            settings.BROKER_ID_HEADER: secrets.ente.intermediario_id
        },
        params={
            'from': date_from,
            'to': date_to,
            'nomeFlusso': nome_flusso
        },
        timeout=settings.default_timeout
    )


def get_insert_export_rt(token, ente_id: int, date_from, date_to, tipo_dovuto: str, versione_tracciato: str = '1.3'):
    return requests.get(
        f'{secrets.internal_base_url}/{settings.api.path_root.operatore}/flussi/export/insert/{ente_id}',
        headers={
            'Authorization': f'Bearer {token}',
            settings.BROKER_ID_HEADER: secrets.ente.intermediario_id
        },
        params={
            'from': date_from,
            'to': date_to,
            'tipoDovuto': tipo_dovuto,
            'versioneTracciato': versione_tracciato
        },
        timeout=settings.default_timeout
    )


def get_list_flussi_export(token, ente_id: int, date_from, date_to, nome_flusso: str = None):
    return requests.get(
        f'{secrets.internal_base_url}/{settings.api.path_root.operatore}/flussi/export/{ente_id}',
        headers={
            'Authorization': f'Bearer {token}',
            settings.BROKER_ID_HEADER: secrets.ente.intermediario_id
        },
        params={
            'from': date_from,
            'to': date_to,
            'nomeFlusso': nome_flusso
        },
        timeout=settings.default_timeout
    )


def download_file_flusso(token, ente_id: int, file_name: str, security_token: str,
                         download_type: str):
    return requests.get(
        f'{secrets.internal_base_url}/{settings.api.path_root.payhub}/mybox/download/{ente_id}',
        headers={
            'Authorization': f'Bearer {token}',
            settings.BROKER_ID_HEADER: secrets.ente.intermediario_id
        },
        params={
            'type': download_type,
            'filename': file_name,
            'securityToken': security_token
        },
        timeout=settings.default_timeout
    )