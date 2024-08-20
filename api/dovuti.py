import requests

from config.configuration import settings


def post_insert_dovuto(token,
                       ente_id: int,
                       tipo_dovuto: dict,
                       anagrafica: str,
                       cod_fiscale: str,
                       email: str,
                       importo: str,
                       causale: str,
                       flag_generate_iuv: bool,
                       tipo_soggetto: str = 'F',
                       flag_anagrafica_anonima: bool = False,
                       flag_multibeneficiario: bool = False,
                       data_scadenza: str = None
                       ):
    return requests.post(
        f'{settings.api.base_path.payhub}/{settings.api.path_root.operatore}/dovuti/insert/{ente_id}',
        headers={
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        },
        json={
            'tipoDovuto': tipo_dovuto,
            'anagrafica': anagrafica,
            'tipoSoggetto': tipo_soggetto,
            'flgAnagraficaAnonima': flag_anagrafica_anonima,
            'codFiscale': cod_fiscale,
            'email': email,
            'importo': importo,
            'dataScadenza': data_scadenza,
            'causale': causale,
            'flgGenerateIuv': flag_generate_iuv,
            'flgMultibeneficiario': flag_multibeneficiario,
        },
        timeout=settings.default_timeout
    )


def get_dovuto_details(token, ente_id: int, dovuto_id: int):
    return requests.get(
        f'{settings.api.base_path.payhub}/{settings.api.path_root.operatore}/dovuti/{ente_id}/{dovuto_id}',
        headers={
            'Authorization': f'Bearer {token}'
        },
        timeout=settings.default_timeout
    )


def delete_dovuto(token, ente_id: int, dovuto_id: int):
    return requests.post(
        f'{settings.api.base_path.payhub}/{settings.api.path_root.operatore}/dovuti/remove/{ente_id}/{dovuto_id}',
        headers={
            'Authorization': f'Bearer {token}'
        },
        timeout=settings.default_timeout
    )


def get_debt_position_details_by_nav(token, ente_fiscal_code: str, nav: str):
    return requests.get(
        f'{settings.api.base_path.payhub}/{settings.api.path_root.operatore}/dovuti/gpd/{ente_fiscal_code}/{nav}',
        headers={
            'Authorization': f'Bearer {token}'
        },
        timeout=settings.default_timeout
    )


def get_processed_dovuto_list(token, ente_id: int, date_from, date_to, iuv: str = None):
    return requests.get(
        f'{settings.api.base_path.payhub}/{settings.api.path_root.operatore}/pagati/{ente_id}/search',
        headers={
            'Authorization': f'Bearer {token}'
        },
        params={
            'from': date_from,
            'to': date_to,
            'iuv': iuv
        },
        timeout=settings.default_timeout
    )


def post_update_dovuto(token,
                       ente_id: int,
                       dovuto_id: int,
                       dovuto_iud: str,
                       tipo_dovuto: dict,
                       anagrafica: str,
                       cod_fiscale: str,
                       email: str,
                       importo: str,
                       causale: str,
                       flag_generate_iuv: bool = False,
                       tipo_soggetto: str = 'F',
                       flag_anagrafica_anonima: bool = False,
                       flag_multibeneficiario: bool = False,
                       has_avviso: bool = True,
                       has_cod_fiscale: bool = True,
                       data_scadenza: str = None
                       ):
    return requests.post(
        f'{settings.api.base_path.payhub}/{settings.api.path_root.operatore}/dovuti/update/{ente_id}/{dovuto_id}',
        headers={
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        },
        json={
            'id': dovuto_id,
            'iud': dovuto_iud,
            'tipoDovuto': tipo_dovuto,
            'anagrafica': anagrafica,
            'tipoSoggetto': tipo_soggetto,
            'flgAnagraficaAnonima': flag_anagrafica_anonima,
            'codFiscale': cod_fiscale,
            'email': email,
            'importo': importo,
            'dataScadenza': data_scadenza,
            'causale': causale,
            'flgGenerateIuv': flag_generate_iuv,
            'flgMultibeneficiario': flag_multibeneficiario,
            'hasAvviso': has_avviso,
            'hasCodFiscale': has_cod_fiscale
        },
        timeout=settings.default_timeout
    )
