from api.enti import get_tipi_ente
from api.enti import get_funzionalita_ente
from api.enti import get_anagrafica_stati_ente
from config.configuration import secrets


def get_user_info_login(user: str) -> dict:
    if user == 'Amministratore Globale':
        return secrets.user_info.admin_global
    elif user == 'Amministratore Ente':
        return secrets.user_info.admin_ente
    elif user == 'Operatore':
        return secrets.user_info.operator
    else:
        raise ValueError


def get_info_stato_ente(token, cod_stato: str) -> dict:
    res = get_anagrafica_stati_ente(token=token)
    assert res.status_code == 200

    anagrafica_stati = res.json()
    info_stato = None

    for i in range(len(anagrafica_stati)):
        if anagrafica_stati[i]['codStato'] == cod_stato:
            info_stato = anagrafica_stati[i]
            break

    return info_stato


def get_tipo_ente(token, desc_tipo: str) -> str:
    res = get_tipi_ente(token=token)
    assert res.status_code == 200

    tipi_ente = res.json()
    cod_tipo_ente = None

    for i in range(len(tipi_ente)):
        if desc_tipo in tipi_ente[i]['description']:
            cod_tipo_ente = tipi_ente[i]['code']
            break
    return cod_tipo_ente


def get_funzionalita_details(token, ente_id, cod_funzionalita) -> dict:
    res = get_funzionalita_ente(token=token, ente_id=ente_id)

    assert res.status_code == 200

    funzionalita_list = res.json()
    assert funzionalita_list != []

    funzionalita = None
    for i in range(len(funzionalita_list)):
        if funzionalita_list[i]['codFunzionalita'] == cod_funzionalita:
            funzionalita = funzionalita_list[i]

    return funzionalita
