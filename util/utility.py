import time
from datetime import datetime, timedelta

from api.dovuti import get_processed_dovuto_list
from api.enti import get_tipi_ente
from api.enti import get_funzionalita_ente
from api.enti import get_anagrafica_stati_ente
from api.tipi_dovuto import get_macro_area
from api.tipi_dovuto import get_tipi_dovuto_operatore
from api.tipi_dovuto import get_tipo_servizio
from api.tipi_dovuto import get_motivo_riscossione
from api.tipi_dovuto import get_cod_tassonomico
from config.configuration import secrets


def get_user_id(user: str) -> str:
    if user == 'Amministratore Globale':
        return secrets.user_info.admin_global.user_id
    elif user == 'Amministratore Ente':
        return secrets.user_info.admin_ente.user_id
    elif user == 'Operatore':
        return secrets.user_info.operator.user_id
    else:
        raise ValueError


def get_info_stato_ente(token, cod_stato: str) -> dict:
    res = get_anagrafica_stati_ente(token=token)
    assert res.status_code == 200

    anagrafica_stati = res.json()
    assert anagrafica_stati != []

    for i in range(len(anagrafica_stati)):
        if anagrafica_stati[i]['codStato'] == cod_stato:
            return anagrafica_stati[i]


def get_tipo_ente(token, desc_tipo: str) -> str:
    res = get_tipi_ente(token=token)
    assert res.status_code == 200

    tipi_ente = res.json()
    assert tipi_ente != []

    for i in range(len(tipi_ente)):
        if desc_tipo in tipi_ente[i]['description']:
            return tipi_ente[i]['code']


def get_funzionalita_details(token, ente_id, cod_funzionalita) -> dict:
    res = get_funzionalita_ente(token=token, ente_id=ente_id)

    assert res.status_code == 200

    funzionalita_list = res.json()
    assert funzionalita_list != []

    for i in range(len(funzionalita_list)):
        if funzionalita_list[i]['codFunzionalita'] == cod_funzionalita:
            return funzionalita_list[i]


def get_cod_macro_area(token, cod_tipo_ente, macro_area_desc):
    res = get_macro_area(token=token, tipo_ente=cod_tipo_ente)

    assert res.status_code == 200

    macro_area_list = res.json()
    assert macro_area_list != []

    for i in range(len(macro_area_list)):
        if macro_area_desc in macro_area_list[i]['description']:
            return macro_area_list[i]['code']


def get_cod_tipo_servizio(token, cod_tipo_ente, cod_macro_area, tipo_servizio_desc):
    res = get_tipo_servizio(token=token, tipo_ente=cod_tipo_ente, macro_area=cod_macro_area)

    assert res.status_code == 200

    tipo_servizio_list = res.json()
    assert tipo_servizio_list != []

    for i in range(len(tipo_servizio_list)):
        if tipo_servizio_desc in tipo_servizio_list[i]['description']:
            return tipo_servizio_list[i]['code']


def get_cod_motivo_riscossione(token, cod_tipo_ente, cod_macro_area, cod_tipo_servizio):
    res = get_motivo_riscossione(token=token,
                                 tipo_ente=cod_tipo_ente,
                                 macro_area=cod_macro_area,
                                 tipo_servizio=cod_tipo_servizio)

    assert res.status_code == 200

    motivo_risc_list = res.json()
    assert motivo_risc_list != []

    return motivo_risc_list[0]['code']


def get_cod_tassonomia(token, cod_tipo_ente, cod_macro_area, cod_tipo_servizio, cod_motivo_riscossione):
    res = get_cod_tassonomico(token=token,
                              tipo_ente=cod_tipo_ente,
                              macro_area=cod_macro_area,
                              tipo_servizio=cod_tipo_servizio,
                              motivo_risc=cod_motivo_riscossione)

    assert res.status_code == 200

    cod_tassonomico_list = res.json()
    assert cod_tassonomico_list != []

    return cod_tassonomico_list[0]['code']


def get_tipo_dovuto_of_operator(token, cod_tipo_dovuto, ente_id):
    res = get_tipi_dovuto_operatore(token=token,
                                    ente_id=ente_id)

    assert res.status_code == 200

    tipi_dovuto_operatore = res.json()
    assert tipi_dovuto_operatore != []

    for i in range(len(tipi_dovuto_operatore)):
        if cod_tipo_dovuto in tipi_dovuto_operatore[i]['codTipo']:
            return tipi_dovuto_operatore[i]


def retry_check_exists_processed_dovuto(token, ente_id, dovuto_iuv, tries=8, delay=2):
    count = 0
    date_from = (datetime.utcnow() - timedelta(days=1)).strftime('%Y/%m/%d')
    date_to = (datetime.utcnow() + timedelta(days=30)).strftime('%Y/%m/%d')

    res = get_processed_dovuto_list(token=token, ente_id=ente_id, date_from=date_from, date_to=date_to, iuv=dovuto_iuv)

    success = (res.status_code == 200 and len(res.json()['list']) == 1)
    while not success:
        count += 1
        if count == tries:
            break
        time.sleep(delay)
        res = get_processed_dovuto_list(token=token, ente_id=ente_id, date_from=date_from,
                                        date_to=date_to, iuv=dovuto_iuv)
        success = (res.status_code == 200 and len(res.json()['list']) == 1)

    assert success
    return res.json()['list'][0]


