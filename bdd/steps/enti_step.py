import random

from behave import when
from behave import then
from behave import given

from api.enti import get_funzionalita_ente
from api.enti import post_insert_ente
from api.enti import get_ente_details
from bdd.steps.authentication_step import step_user_authentication
from config.configuration import settings
from config.configuration import secrets
from util.utility import get_info_stato_ente
from util.utility import get_tipo_ente

cod_ipa_ente_template = 'FEATURE_TEST_{label}_{serial}'
name_ente_template = 'Ente Feature Test {label} {serial}'
email_ente_template = 'entefeaturetest{label}{serial}@email.it'

fiscal_code_ente = secrets.ente.fiscal_code
status_ente = settings.ente.status
tipo_ente = settings.ente.tipo
funzionalita_ente = settings.ente.funzionalita


@given('un nuovo Ente di tipo {tipo} con codice IPA {label}')
def step_create_ente_data(context, tipo, label):
    ente_serial_number = random.randint(1, 100)

    cod_ipa = cod_ipa_ente_template.format(label=label, serial=ente_serial_number)
    name = name_ente_template.format(label=label, serial=ente_serial_number)
    email = email_ente_template.format(label=label, serial=ente_serial_number)
    application_code = '0' + label
    tipo = tipo

    ente_data = {
        'cod_ipa': cod_ipa,
        'name': name,
        'email': email,
        'fiscal_code': fiscal_code_ente,
        'application_code': application_code,
        'tipo': tipo
    }

    try:
        context.ente_data[label] = ente_data
    except AttributeError:
        context.ente_data = {label: ente_data}


@when('l\'{user} inserisce correttamente i dati dell\'Ente {label}')
def step_insert_ente(context, user, label):
    step_user_authentication(context, user)
    token = context.token

    ente_data = context.ente_data[label]
    cod_stato_ente = get_info_stato_ente(token=token, cod_stato=status_ente.inserito)
    cod_tipo_ente = get_tipo_ente(token=token, desc_tipo=ente_data['tipo'].upper())

    res = post_insert_ente(token=token,
                           name_ente=ente_data['name'],
                           cod_ipa_ente=ente_data['cod_ipa'],
                           email_ente=ente_data['email'],
                           application_code=ente_data['application_code'],
                           fiscal_code_ente=ente_data['fiscal_code'],
                           cod_stato_ente=cod_stato_ente,
                           cod_tipo_ente=cod_tipo_ente)

    assert res.status_code == 200
    ente_id = res.json()['mygovEnteId']
    assert ente_id is not None
    context.ente_data[label]['id'] = ente_id


@then('l\'Ente {label} è in stato "{status}"')
def step_check_ente_details(context, label, status):
    token = context.token
    status = status.upper()
    res = get_ente_details(token=token, ente_id=context.ente_data[label]['id'])

    assert res.status_code == 200

    ente = res.json()
    assert ente['cdStatoEnte']['codStato'] == status


@then('l\'Ente {label} ha la funzionalità di {cod_funzionalita} attivata')
def step_check_default_funzionalita_ente(context, label, cod_funzionalita):
    token = context.token
    cod_funzionalita = cod_funzionalita.upper().replace(" ", "_")
    res = get_funzionalita_ente(token=token, ente_id=context.ente_data[label]['id'])

    assert res.status_code == 200

    funzionalita_list = res.json()
    assert funzionalita_list != []

    active_funzionalita = False
    for i in range(len(funzionalita_list)):
        if funzionalita_list[i]['codFunzionalita'] == cod_funzionalita and funzionalita_list[i]['flgAttivo']:
            active_funzionalita = True

    assert active_funzionalita
