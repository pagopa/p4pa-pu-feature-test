import base64
import io

from PIL import Image
from behave import when
from behave import then
from behave import given

from api.enti import get_ente_details_public
from api.enti import get_enti_list
from api.enti import post_save_logo
from api.enti import post_insert_ente
from api.enti import get_ente_details
from api.enti import post_update_ente
from api.enti import get_activate_funzionalita
from api.enti import get_deactivate_funzionalita
from bdd.steps.authentication_step import step_user_authentication
from config.configuration import settings
from config.configuration import secrets
from util.utility import get_info_stato_ente
from util.utility import get_funzionalita_details
from util.utility import get_tipo_ente

cod_ipa_ente_template = 'FEATURE_TEST_{label}'
name_ente_template = 'Ente Feature Test {label}'
email_ente_template = 'entefeaturetest{label}@email.it'
file_path = './util/file/feature_test_logo.png'
file_name = 'feature_test_logo.png'

fiscal_code_ente = secrets.ente.fiscal_code
status_ente = settings.ente.status
tipo_ente = settings.ente.tipo
funzionalita_ente = settings.ente.funzionalita


@given('un nuovo Ente di tipo {tipo} con codice IPA {label}')
def step_create_ente_data(context, tipo, label):
    cod_ipa = cod_ipa_ente_template.format(label=label)
    name = name_ente_template.format(label=label)
    email = email_ente_template.format(label=label)
    application_code = '0' + label

    ente_data = {
        'cod_ipa': cod_ipa,
        'name': name,
        'email': email,
        'fiscal_code': fiscal_code_ente.get(label),
        'application_code': application_code,
        'tipo': tipo
    }

    try:
        context.ente_data[label] = ente_data
    except AttributeError:
        context.ente_data = {label: ente_data}


@when('l\'{user} inserisce correttamente i dati dell\'Ente {label}')
@given('l\'{user} che inserisce correttamente i dati dell\'Ente {label}')
def step_insert_ente(context, user, label):
    step_user_authentication(context, user)
    token = context.token[user]

    ente_data = context.ente_data[label]
    context.ente_data[label]['cod_stato_ente'] = get_info_stato_ente(token=token, cod_stato=status_ente.inserito)
    context.ente_data[label]['cod_tipo_ente'] = get_tipo_ente(token=token, desc_tipo=ente_data['tipo'].upper())

    res = post_insert_ente(token=token,
                           name_ente=ente_data['name'],
                           cod_ipa_ente=ente_data['cod_ipa'],
                           email_ente=ente_data['email'],
                           application_code=ente_data['application_code'],
                           fiscal_code_ente=ente_data['fiscal_code'],
                           cod_stato_ente=ente_data['cod_stato_ente'],
                           cod_tipo_ente=ente_data['cod_tipo_ente'])

    assert res.status_code == 200
    ente_id = res.json()['mygovEnteId']
    assert ente_id is not None
    context.ente_data[label]['id'] = ente_id


@given('un Ente di tipo {tipo} con codice IPA {label} già inserito correttamente')
def step_insert_ente_ok(context, tipo, label):
    step_create_ente_data(context=context, tipo=tipo, label=label)
    step_insert_ente(context=context, user='Amministratore Globale', label=label)
    step_check_ente_status(context=context, label=label, status=status_ente.inserito)


@when('l\'{user} prova a reinserire i dati dell\'Ente {label}')
@when('l\'{user} prova ad inserire i dati dell\'Ente {label}')
@when('l\'{user} prova ad inserire i dati dell\'Ente {label} con valore del dato {field} non valido')
def step_try_insert_ente(context, user, label, field=None):
    step_user_authentication(context, user)
    token = context.token[user]

    if field == 'codice fiscale':
        context.ente_data[label]['fiscal_code'] = fiscal_code_ente.get('not_valid')
    elif field == 'email':
        context.ente_data[label]['email'] = 'email$email.it'

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

    context.latest_insert_ente = res


@then('l\'inserimento non va a buon fine a causa di "{cause_ko}"')
def step_check_latest_insert_ente(context, cause_ko):
    if cause_ko == 'Ente già presente':
        assert context.latest_insert_ente.status_code == 500
        assert context.latest_insert_ente.json()['message'] == 'Ente già presente nel database'
    elif cause_ko == 'Codice fiscale invalido':
        assert context.latest_insert_ente.status_code == 500
        assert context.latest_insert_ente.json()['message'] == 'Codice Fiscale Ente è invalido'
    elif cause_ko == 'E-mail invalida':
        assert context.latest_insert_ente.status_code == 500
        assert context.latest_insert_ente.json()['message'] == 'E-mail Amministratore è invalido'
    elif cause_ko == 'Utente non autorizzato':
        assert context.latest_insert_ente.status_code == 401
        assert 'utente non autorizzato' in context.latest_insert_ente.json()['message']


@then('l\'Ente {label} è in stato "{status}"')
def step_check_ente_status(context, label, status):
    token = context.token[context.latest_user_authenticated]
    status = status.upper()
    res = get_ente_details(token=token, ente_id=context.ente_data[label]['id'])

    assert res.status_code == 200

    ente = res.json()
    assert ente['cdStatoEnte']['codStato'] == status


@given('l\'Ente {label} censito correttamente')
def step_check_ente_exists(context, label):
    step_user_authentication(context, 'Amministratore Globale')
    token = context.token['Amministratore Globale']

    res = get_enti_list(token=token, cod_ipa_ente=context.ente_data[label]['cod_ipa'])
    assert res.status_code == 200
    assert res.json() != []
    assert res.json()[0]['codIpaEnte'] == context.ente_data[label]['cod_ipa']

    context.current_ente = context.ente_data[label]


@when('l\'{user} aggiunge il logo all\'Ente {label}')
def step_add_logo_ente(context, user, label):
    token = context.token[user]
    file = (file_name, open(file_path, "rb"))

    res = post_save_logo(token=token, ente_id=context.ente_data[label]['id'], file=file)

    assert res.status_code == 200
    res_data = res.json()

    assert res_data['deLogoEnte'] is not None
    assert res_data['thumbLogoEnte'] is not None
    assert res_data['hashThumbLogoEnte'] is not None


@then('l\'Ente {label} presenta il suo logo correttamente')
def step_check_correct_logo(context, label):
    token = context.token[context.latest_user_authenticated]

    res = get_ente_details_public(token=token, ente_id=context.ente_data[label]['id'])

    assert res.status_code == 200

    res_data = res.json()

    image_uploaded = Image.open(file_path)
    image_returned = Image.open(io.BytesIO(base64.decodebytes(bytes(res_data['deLogoEnte'], "utf-8"))))

    assert list(image_returned.getdata()) == list(image_uploaded.getdata())


@when('l\'{user} modifica {field_to_change} dell\'Ente {label} in {new_value}')
def step_update_info_ente(context, user, label, field_to_change, new_value):
    step_user_authentication(context, user)
    token = context.token[user]
    ente_data = context.ente_data[label]

    status = status_ente.get(new_value) if field_to_change == 'lo stato' else status_ente.inserito
    context.ente_data[label]['cod_stato_ente'] = get_info_stato_ente(token=token, cod_stato=status)

    desc_tipo = new_value.upper() if field_to_change == 'il tipo' else ente_data['tipo'].upper()
    context.ente_data[label]['cod_tipo_ente'] = get_tipo_ente(token=token, desc_tipo=desc_tipo)

    res = post_update_ente(token=token,
                           ente_id=context.ente_data[label]['id'],
                           name_ente=ente_data['name'],
                           cod_ipa_ente=ente_data['cod_ipa'],
                           email_ente=ente_data['email'],
                           application_code=ente_data['application_code'],
                           fiscal_code_ente=ente_data['fiscal_code'],
                           cod_stato_ente=context.ente_data[label]['cod_stato_ente'],
                           cod_tipo_ente=context.ente_data[label]['cod_tipo_ente'])

    assert res.status_code == 200


@then('{field} dell\'Ente {label} risulta correttamente modificato')
def step_check_ente_info_updated(context, field, label):
    token = context.token[context.latest_user_authenticated]
    res = get_ente_details(token=token, ente_id=context.ente_data[label]['id'])

    assert res.status_code == 200

    ente = res.json()
    if 'stato' in field:
        assert ente['cdStatoEnte']['codStato'] == context.ente_data[label]['cod_stato_ente']['codStato']
    if 'tipo' in field:
        assert ente['codTipoEnte'] == context.ente_data[label]['cod_tipo_ente']


@when('l\'{user} prova a modificare {field_to_change} dell\'Ente {label} in {new_value}')
def step_update_info_ente(context, user, label, field_to_change, new_value):
    step_user_authentication(context, user)
    token = context.token[user]
    ente_data = context.ente_data[label]

    email = new_value if field_to_change == 'la email' else ente_data['email']
    application_code = new_value if field_to_change == 'il codice segregazione' else ente_data['application_code']

    res = post_update_ente(token=token,
                           ente_id=context.ente_data[label]['id'],
                           name_ente=ente_data['name'],
                           cod_ipa_ente=ente_data['cod_ipa'],
                           email_ente=email,
                           application_code=application_code,
                           fiscal_code_ente=ente_data['fiscal_code'],
                           cod_stato_ente=context.ente_data[label]['cod_stato_ente'],
                           cod_tipo_ente=context.ente_data[label]['cod_tipo_ente'])

    context.latest_update_ente = res


@then('la modifica non va a buon fine a causa di "{cause_ko}"')
def step_check_latest_update_ente(context, cause_ko):
    if cause_ko == 'E-mail invalida':
        assert context.latest_update_ente.status_code == 500
        assert context.latest_update_ente.json()['message'] == 'E-mail Amministratore è invalido'
    elif cause_ko == 'Codice segregazione invalido':
        assert context.latest_update_ente.status_code == 500
        assert context.latest_update_ente.json()['message'] == 'Segregation Code è invalido'


@when('l\'{user} attiva la funzionalità {cod_funzionalita} per l\'Ente {label}')
def step_activate_funzionalita(context, user, cod_funzionalita, label):
    step_user_authentication(context, user)
    token = context.token[user]

    cod_funzionalita = cod_funzionalita.upper().replace(" ", "_")
    funzionalita = get_funzionalita_details(token=token,
                                            ente_id=context.ente_data[label]['id'],
                                            cod_funzionalita=cod_funzionalita)
    assert funzionalita is not None

    res = get_activate_funzionalita(token=token, funzionalita_id=funzionalita['mygovEnteFunzionalitaId'])

    assert res.status_code == 200


@when('l\'{user} disattiva la funzionalità {cod_funzionalita} per l\'Ente {label}')
def step_deactivate_funzionalita(context, user, cod_funzionalita, label):
    step_user_authentication(context, user)
    token = context.token[user]

    cod_funzionalita = cod_funzionalita.upper().replace(" ", "_")
    funzionalita = get_funzionalita_details(token=token,
                                            ente_id=context.ente_data[label]['id'],
                                            cod_funzionalita=cod_funzionalita)
    assert funzionalita is not None

    res = get_deactivate_funzionalita(token=token, funzionalita_id=funzionalita['mygovEnteFunzionalitaId'])

    assert res.status_code == 200


@given('l\'{user} che attiva correttamente la funzionalità {cod_funzionalita} per l\'Ente {label}')
def step_activate_funzionalita_ok(context, user, cod_funzionalita, label):
    step_activate_funzionalita(context=context, user=user, cod_funzionalita=cod_funzionalita, label=label)
    step_check_active_funzionalita_ente(context=context, cod_funzionalita=cod_funzionalita, label=label)


@when('l\'{user} prova ad attivare la funzionalità {cod_funzionalita} per l\'Ente {label}')
def step_try_activate_funzionalita(context, user, cod_funzionalita, label):
    step_user_authentication(context, user)
    token = context.token[user]

    cod_funzionalita = cod_funzionalita.upper().replace(" ", "_")
    funzionalita = get_funzionalita_details(token=token,
                                            ente_id=context.ente_data[label]['id'],
                                            cod_funzionalita=cod_funzionalita)
    if funzionalita is None:
        funzionalita_id = 0
    else:
        funzionalita_id = funzionalita['mygovEnteFunzionalitaId']

    res = get_activate_funzionalita(token=token, funzionalita_id=funzionalita_id)
    context.latest_activate_funzionalita = res


@then('l\'attivazione non va a buon fine a causa di "{cause_ko}"')
def step_check_latest_activate_funzionalita(context, cause_ko):
    if cause_ko == 'Funzionalità non esistente':
        assert context.latest_activate_funzionalita.status_code == 418
        assert 'EnteFunzionalita not found.' in context.latest_activate_funzionalita.json()['message']


@then('l\'Ente {label} ha la funzionalità di {cod_funzionalita} attivata')
def step_check_active_funzionalita_ente(context, label, cod_funzionalita, active=True):
    token = context.token[context.latest_user_authenticated]
    cod_funzionalita = cod_funzionalita.upper().replace(" ", "_")

    funzionalita = get_funzionalita_details(token=token,
                                            ente_id=context.ente_data[label]['id'],
                                            cod_funzionalita=cod_funzionalita)

    assert funzionalita['flgAttivo'] is active


@then('l\'Ente {label} ha la funzionalità di {cod_funzionalita} disattivata')
def step_check_not_active_funzionalita_ente(context, label, cod_funzionalita):
    step_check_active_funzionalita_ente(context=context, label=label, cod_funzionalita=cod_funzionalita, active=False)
