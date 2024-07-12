import requests

from config.configuration import settings


def get_macro_area(token, tipo_ente: str):
    return requests.get(
        f'{settings.api.base_path.payhub}/{settings.api.path_root.operatore_admin}/tipiDovuto/macroArea',
        headers={
            'Authorization': f'Bearer {token}'
        },
        params={
            'tipoEnte': tipo_ente
        },
        timeout=settings.default_timeout
    )


def get_tipo_servizio(token, tipo_ente: str, macro_area: str):
    return requests.get(
        f'{settings.api.base_path.payhub}/{settings.api.path_root.operatore_admin}/tipiDovuto/tipoServizio',
        headers={
            'Authorization': f'Bearer {token}'
        },
        params={
            'tipoEnte': tipo_ente,
            'macroArea': macro_area
        },
        timeout=settings.default_timeout
    )


def get_motivo_riscossione(token, tipo_ente: str, macro_area: str, tipo_servizio: str):
    return requests.get(
        f'{settings.api.base_path.payhub}/{settings.api.path_root.operatore_admin}/tipiDovuto/motivoRiscossione',
        headers={
            'Authorization': f'Bearer {token}'
        },
        params={
            'tipoEnte': tipo_ente,
            'macroArea': macro_area,
            'tipoServizio': tipo_servizio
        },
        timeout=settings.default_timeout
    )


def get_cod_tassonomico(token, tipo_ente: str, macro_area: str, tipo_servizio: str, motivo_risc: str):
    return requests.get(
        f'{settings.api.base_path.payhub}/{settings.api.path_root.operatore_admin}/tipiDovuto/codTassonomico',
        headers={
            'Authorization': f'Bearer {token}'
        },
        params={
            'tipoEnte': tipo_ente,
            'macroArea': macro_area,
            'tipoServizio': tipo_servizio,
            'motivoRisc': motivo_risc
        },
        timeout=settings.default_timeout
    )


def post_insert_tipo_dovuto(token,
                            ente_id: int,
                            cod_ipa_ente: str,
                            cod_tipo: str,
                            desc_tipo: str,
                            macro_area: str,
                            tipo_servizio: str,
                            motivo_riscossione: str,
                            cod_tassonomico: str):
    return requests.post(
        f'{settings.api.base_path.payhub}/{settings.api.path_root.operatore_admin}/tipiDovuto/insert',
        headers={
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        },
        json={
            'mygovEnteId': ente_id,
            'codIpaEnte': cod_ipa_ente,
            'codTipo': cod_tipo,
            'deTipo': desc_tipo,
            'macroArea': macro_area,
            'tipoServizio': tipo_servizio,
            'motivoRiscossione': motivo_riscossione,
            'codTassonomico': cod_tassonomico
        },
        timeout=settings.default_timeout
    )


def post_update_tipo_dovuto(token,
                            tipo_dovuto_id: int,
                            ente_id: int,
                            cod_ipa_ente: str,
                            cod_tipo: str,
                            desc_tipo: str,
                            macro_area: str,
                            tipo_servizio: str,
                            motivo_riscossione: str,
                            cod_tassonomico: str,
                            flag_notifica_io: bool = False,
                            cod_xsd_causale: str = 'mypay_default'
                            ):
    return requests.post(
        f'{settings.api.base_path.payhub}/{settings.api.path_root.operatore_admin}/tipiDovuto/update',
        headers={
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        },
        json={
            'mygovEnteTipoDovutoId': tipo_dovuto_id,
            'mygovEnteId': ente_id,
            'codIpaEnte': cod_ipa_ente,
            'codTipo': cod_tipo,
            'deTipo': desc_tipo,
            'macroArea': macro_area,
            'tipoServizio': tipo_servizio,
            'motivoRiscossione': motivo_riscossione,
            'codTassonomico': cod_tassonomico,
            'flgNotificaIo': flag_notifica_io,
            'codXsdCausale': cod_xsd_causale
        },
        timeout=settings.default_timeout
    )


def get_tipi_dovuto_list(token, ente_id: int, with_activation_info: bool = True):
    return requests.get(
        f'{settings.api.base_path.payhub}/{settings.api.path_root.operatore_admin}/tipiDovuto/search/{ente_id}',
        headers={
            'Authorization': f'Bearer {token}'
        },
        params={
          'withActivationInfo': with_activation_info
        },
        timeout=settings.default_timeout
    )


def get_details_tipo_dovuto(token, ente_id: int, cod_tipo: str):
    return requests.get(
        f'{settings.api.base_path.payhub}/{settings.api.path_root.operatore_admin}/tipiDovuto/search/{ente_id}/cod/{cod_tipo}',
        headers={
            'Authorization': f'Bearer {token}'
        },
        timeout=settings.default_timeout
    )


def get_tipo_dovuto_by_id(token, tipo_dovuto_id: int):
    return requests.get(
        f'{settings.api.base_path.payhub}/{settings.api.path_root.operatore_admin}/tipiDovuto/{tipo_dovuto_id}',
        headers={
            'Authorization': f'Bearer {token}'
        },
        timeout=settings.default_timeout
    )


def get_activate_tipo_dovuto(token, tipo_dovuto_id: int):
    return requests.get(
        f'{settings.api.base_path.payhub}/{settings.api.path_root.operatore_admin}/tipiDovuto/activate/{tipo_dovuto_id}',
        headers={
            'Authorization': f'Bearer {token}'
        },
        timeout=settings.default_timeout
    )


def get_deactivate_tipo_dovuto(token, tipo_dovuto_id: int):
    return requests.get(
        f'{settings.api.base_path.payhub}/{settings.api.path_root.operatore_admin}/tipiDovuto/deactivate/{tipo_dovuto_id}',
        headers={
            'Authorization': f'Bearer {token}'
        },
        timeout=settings.default_timeout
    )


def delete_tipo_dovuto(token, tipo_dovuto_id: int):
    return requests.delete(
        f'{settings.api.base_path.payhub}/{settings.api.path_root.operatore_admin}/tipiDovuto/delete/{tipo_dovuto_id}',
        headers={
            'Authorization': f'Bearer {token}'
        },
        timeout=settings.default_timeout
    )
