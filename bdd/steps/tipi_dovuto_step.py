from datetime import datetime
from datetime import timezone

from behave import when
from behave import then
from behave import given

from api.generic import get_service_io
from api.generic import delete_service_io
from bdd.steps.authentication_step import step_user_authentication
from api.tipi_dovuti import post_insert_tipo_dovuto
from api.tipi_dovuti import get_tipo_dovuto_by_id
from api.tipi_dovuti import post_update_tipo_dovuto
from api.tipi_dovuti import get_activate_tipo_dovuto
from api.tipi_dovuti import get_deactivate_tipo_dovuto
from api.tipi_dovuti import get_tipi_dovuto_list
from api.tipi_dovuti import get_details_tipo_dovuto
from api.tipi_dovuti import delete_tipo_dovuto
from util.utility import get_cod_macro_area
from util.utility import get_cod_tipo_servizio
from util.utility import get_cod_motivo_riscossione
from util.utility import get_cod_tassonomia

cod_tipo_dovuto_template = 'LICENZA_DI_TEST_{label}'


@given('il tipo dovuto {label} con macro-area {macro_area} e tipo servizio {tipo_servizio}')
def step_create_tipo_dovuto_data(context, label, macro_area, tipo_servizio):
    step_user_authentication(context, 'Amministratore Globale')
    token = context.token['Amministratore Globale']

    ente_data = context.current_ente
    cod_macro_area = get_cod_macro_area(token=token,
                                        cod_tipo_ente=ente_data['cod_tipo_ente'],
                                        macro_area_desc=macro_area.upper())
    cod_tipo_servizio = get_cod_tipo_servizio(token=token,
                                              cod_tipo_ente=ente_data['cod_tipo_ente'],
                                              cod_macro_area=cod_macro_area,
                                              tipo_servizio_desc=tipo_servizio)
    cod_motivo_riscossione = get_cod_motivo_riscossione(token=token,
                                                        cod_tipo_ente=ente_data['cod_tipo_ente'],
                                                        cod_macro_area=cod_macro_area,
                                                        cod_tipo_servizio=cod_tipo_servizio)
    cod_tassonomico = get_cod_tassonomia(token=token,
                                         cod_tipo_ente=ente_data['cod_tipo_ente'],
                                         cod_macro_area=cod_macro_area,
                                         cod_tipo_servizio=cod_tipo_servizio,
                                         cod_motivo_riscossione=cod_motivo_riscossione)

    tipo_dovuto_data = {
        'ente_id': ente_data['id'],
        'cod_ipa_ente': ente_data['cod_ipa'],
        'cod_tipo': cod_tipo_dovuto_template.format(label=label),
        'desc_tipo': 'Licenza di Feature Test',
        'cod_macro_area': cod_macro_area,
        'cod_tipo_servizio': cod_tipo_servizio,
        'cod_motivo_riscossione': cod_motivo_riscossione,
        'cod_tassonomico': cod_tassonomico
    }

    try:
        context.tipo_dovuto_data[label] = tipo_dovuto_data
    except AttributeError:
        context.tipo_dovuto_data = {label: tipo_dovuto_data}


@when('l\'{user} inserisce il nuovo tipo dovuto {label}')
def step_insert_tipo_dovuto(context, user, label):
    step_user_authentication(context, user)
    token = context.token[user]

    tipo_dovuto_data = context.tipo_dovuto_data[label]

    res = post_insert_tipo_dovuto(token=token,
                                  ente_id=tipo_dovuto_data['ente_id'],
                                  cod_ipa_ente=tipo_dovuto_data['cod_ipa_ente'],
                                  cod_tipo=tipo_dovuto_data['cod_tipo'],
                                  desc_tipo=tipo_dovuto_data['desc_tipo'],
                                  macro_area=tipo_dovuto_data['cod_macro_area'],
                                  tipo_servizio=tipo_dovuto_data['cod_tipo_servizio'],
                                  motivo_riscossione=tipo_dovuto_data['cod_motivo_riscossione'],
                                  cod_tassonomico=tipo_dovuto_data['cod_tassonomico'])

    assert res.status_code == 200
    tipo_dovuto_id = res.json()['mygovEnteTipoDovutoId']
    assert tipo_dovuto_id is not None
    context.tipo_dovuto_data[label]['id'] = tipo_dovuto_id


@when('l\'{user} prova ad inserire il nuovo tipo dovuto {label}')
@when('l\'{user} prova a reinserire il tipo dovuto {label}')
def step_try_insert_tipo_dovuto(context, user, label):
    step_user_authentication(context, user)
    token = context.token[user]

    tipo_dovuto_data = context.tipo_dovuto_data[label]

    res = post_insert_tipo_dovuto(token=token,
                                  ente_id=tipo_dovuto_data['ente_id'],
                                  cod_ipa_ente=tipo_dovuto_data['cod_ipa_ente'],
                                  cod_tipo=tipo_dovuto_data['cod_tipo'],
                                  desc_tipo=tipo_dovuto_data['desc_tipo'],
                                  macro_area=tipo_dovuto_data['cod_macro_area'],
                                  tipo_servizio=tipo_dovuto_data['cod_tipo_servizio'],
                                  motivo_riscossione=tipo_dovuto_data['cod_motivo_riscossione'],
                                  cod_tassonomico=tipo_dovuto_data['cod_tassonomico'])

    context.latest_tipo_dovuto_insert = res


@then('l\'inserimento del tipo dovuto {label} non va a buon fine a causa di "{cause_ko}"')
def step_check_latest_insert_tipo_dovuto(context, label, cause_ko):
    if cause_ko == 'Utente non autorizzato':
        assert context.latest_tipo_dovuto_insert.status_code == 401
        assert 'utente non autorizzato' in context.latest_tipo_dovuto_insert.json()['message']
    elif cause_ko == 'Tipo dovuto già presente':
        assert context.latest_tipo_dovuto_insert.status_code == 500
        tipo_dovuto_ente = (context.tipo_dovuto_data[label]['cod_ipa_ente'] + '-' +
                            context.tipo_dovuto_data[label]['cod_tipo'])
        assert context.latest_tipo_dovuto_insert.json()['message'] == 'Tipo dovuto {} già presente nel database'.format(
            tipo_dovuto_ente)


@given('il tipo dovuto {label} già inserito nella lista dei tipi dovuti dell\'Ente {ente_label}')
def step_insert_tipo_dovuto_ok(context, label, ente_label):
    step_insert_tipo_dovuto(context=context, user='Amministratore Globale', label=label)
    step_check_tipo_dovuto_in_list(context=context, label=label, ente_label=ente_label)


@then('il tipo dovuto {label} è presente nella lista dei tipi dovuti dell\'Ente {ente_label}')
def step_check_tipo_dovuto_in_list(context, label, ente_label, is_present=True):
    token = context.token[context.latest_user_authenticated]

    ente_id = context.ente_data[ente_label]['id']
    res = get_tipi_dovuto_list(token=token, ente_id=ente_id)

    assert res.status_code == 200

    tipi_dovuto_list = res.json()
    assert tipi_dovuto_list != []
    if is_present:
        assert any(tipo_dovuto['mygovEnteTipoDovutoId'] == context.tipo_dovuto_data[label]['id']
                   for tipo_dovuto in tipi_dovuto_list)
    else:
        assert not any(tipo_dovuto['mygovEnteTipoDovutoId'] == context.tipo_dovuto_data[label]['id']
                       for tipo_dovuto in tipi_dovuto_list)


@then('di default, il tipo dovuto {label} è in stato {status}')
@then('il tipo dovuto {label} è in stato {status}')
def step_check_status_tipo_dovuto(context, label, status):
    is_active = True if status == 'abilitato' else False

    token = context.token[context.latest_user_authenticated]
    tipo_dovuto = context.tipo_dovuto_data[label]
    res = get_details_tipo_dovuto(token=token, ente_id=tipo_dovuto['ente_id'], cod_tipo=tipo_dovuto['cod_tipo'])

    assert res.status_code == 200

    assert res.json()['flgAttivo'] == is_active
    if is_active and 'latest_td_activation_date' in context:
        assert context.latest_td_activation_date in res.json()['dtUltimaAbilitazione']
    elif not is_active and 'latest_td_deactivation_date' in context:
        assert context.latest_td_deactivation_date in res.json()['dtUltimaDisabilitazione']


@when('l\'{user} abilita il tipo dovuto {label}')
def step_activate_tipo_dovuto(context, user, label):
    step_user_authentication(context, user)
    token = context.token[user]

    res = get_activate_tipo_dovuto(token=token, tipo_dovuto_id=context.tipo_dovuto_data[label]['id'])

    assert res.status_code == 200
    context.latest_td_activation_date = str(datetime.now(timezone.utc).strftime("%Y/%m/%d-%H:%M"))


@when('l\'{user} disabilita il tipo dovuto {label}')
def step_deactivate_tipo_dovuto(context, user, label):
    step_user_authentication(context, user)
    token = context.token[user]

    res = get_deactivate_tipo_dovuto(token=token, tipo_dovuto_id=context.tipo_dovuto_data[label]['id'])

    assert res.status_code == 200
    context.latest_td_deactivation_date = str(datetime.now(timezone.utc).strftime("%Y/%m/%d-%H:%M"))


@given('il tipo dovuto {label} già inserito e abilitato nella lista dei tipi dovuti dell\'Ente {ente_label}')
def step_activate_tipo_dovuto_ok(context, label, ente_label):
    user = 'Amministratore Globale'
    step_insert_tipo_dovuto_ok(context=context, label=label, ente_label=ente_label)
    step_activate_tipo_dovuto(context=context, user=user, label=label)
    step_check_status_tipo_dovuto(context=context, label=label, status='abilitato')


@when('l\'{user} modifica il tipo dovuto {label} abilitando le notifiche di avviso su IO')
def step_update_tipo_dovuto(context, user, label):
    step_user_authentication(context, user)
    token = context.token[user]

    tipo_dovuto_data = context.tipo_dovuto_data[label]

    res = post_update_tipo_dovuto(token=token,
                                  tipo_dovuto_id=tipo_dovuto_data['id'],
                                  ente_id=tipo_dovuto_data['ente_id'],
                                  cod_ipa_ente=tipo_dovuto_data['cod_ipa_ente'],
                                  cod_tipo=tipo_dovuto_data['cod_tipo'],
                                  desc_tipo=tipo_dovuto_data['desc_tipo'],
                                  macro_area=tipo_dovuto_data['cod_macro_area'],
                                  tipo_servizio=tipo_dovuto_data['cod_tipo_servizio'],
                                  motivo_riscossione=tipo_dovuto_data['cod_motivo_riscossione'],
                                  cod_tassonomico=tipo_dovuto_data['cod_tassonomico'],
                                  flag_notifica_io=True)

    assert res.status_code == 200


@when('l\'{user} prova a modificare il codice del tipo dovuto {label}')
def step_try_to_update_tipo_dovuto(context, user, label):
    step_user_authentication(context, user)
    token = context.token[user]

    tipo_dovuto_data = context.tipo_dovuto_data[label]
    res = post_update_tipo_dovuto(token=token,
                                  tipo_dovuto_id=tipo_dovuto_data['id'],
                                  ente_id=tipo_dovuto_data['ente_id'],
                                  cod_ipa_ente=tipo_dovuto_data['cod_ipa_ente'],
                                  cod_tipo="COD_TIPO_NEW",
                                  desc_tipo=tipo_dovuto_data['desc_tipo'],
                                  macro_area=tipo_dovuto_data['cod_macro_area'],
                                  tipo_servizio=tipo_dovuto_data['cod_tipo_servizio'],
                                  motivo_riscossione=tipo_dovuto_data['cod_motivo_riscossione'],
                                  cod_tassonomico=tipo_dovuto_data['cod_tassonomico'])

    context.latest_tipo_dovuto_update = res


@then('la modifica del tipo dovuto {label} non va a buon fine a causa di "{cause_ko}"')
def step_check_latest_tipo_dovuto_update(context, label, cause_ko):
    if cause_ko == 'richiesta non valida':
        assert context.latest_tipo_dovuto_update.status_code == 400
        assert context.latest_tipo_dovuto_update.json()['message'] == ''


@then('per il tipo dovuto {label} le notifiche sono abilitate, grazie alla creazione di un servizio su IO')
def step_check_tipo_dovuto_flag_io(context, label):
    token = context.token[context.latest_user_authenticated]
    tipo_dovuto = context.tipo_dovuto_data[label]
    res = get_tipo_dovuto_by_id(token=token, tipo_dovuto_id=tipo_dovuto['id'])

    assert res.status_code == 200
    assert res.json()['flgNotificaIo']

    res_service = get_service_io(ente_id=tipo_dovuto['ente_id'], tipo_dovuto_id=tipo_dovuto['id'])

    assert res_service.status_code == 200
    assert res_service.json()['status'] == 'CREATED'
    assert res_service.json()['serviceId'] is not None

    # cancellation of Service IO to avoid burdening the DB
    res_delete = delete_service_io(service_id=res_service.json()['serviceId'])
    assert res_delete.status_code == 200


@when('l\'{user} cancella il tipo dovuto {label}')
def step_delete_tipo_dovuto(context, user, label):
    step_user_authentication(context, user)
    token = context.token[user]

    tipo_dovuto = context.tipo_dovuto_data[label]

    res = delete_tipo_dovuto(token=token, tipo_dovuto_id=tipo_dovuto['id'])
    assert res.status_code == 200


@then('il tipo dovuto {label} non è più presente tra i tipi dovuti dell\'Ente {ente_label}')
def step_check_tipo_dovuto_not_present(context, label, ente_label):
    step_check_tipo_dovuto_in_list(context=context, label=label, ente_label=ente_label, is_present=False)

    token = context.token[context.latest_user_authenticated]
    tipo_dovuto = context.tipo_dovuto_data[label]
    res = get_tipo_dovuto_by_id(token=token, tipo_dovuto_id=tipo_dovuto['id'])

    assert res.status_code == 500
