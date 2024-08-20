from datetime import datetime
from datetime import timedelta

from behave import when
from behave import then
from behave import given

from api.dovuti import post_insert_dovuto
from api.dovuti import get_dovuto_details
from api.dovuti import get_debt_position_details_by_nav
from api.dovuti import delete_dovuto
from api.dovuti import get_processed_dovuto_list
from api.dovuti import post_update_dovuto
from api.gpd import get_debt_position_by_iupd
from bdd.steps.authentication_step import step_user_authentication
from config.configuration import secrets
from util.utility import get_tipo_dovuto_of_operator

cod_tipo_dovuto = 'LICENZA_FEATURE_TEST'
ente_id = secrets.user_info.operator.ente_id
ente_fiscal_code = secrets.user_info.operator.ente_fiscal_code


@given('il dovuto {label} di tipo Licenza di Test del valore di {importo} euro per la cittadina {citizen}')
def step_create_dovuto_data(context, label, importo, citizen):
    step_user_authentication(context, 'Operatore')
    token = context.token['Operatore']
    tipo_dovuto = get_tipo_dovuto_of_operator(token=token, cod_tipo_dovuto=cod_tipo_dovuto, ente_id=ente_id)

    citizen_data = secrets.citizen_info.get(citizen.lower())

    dovuto_data = {
        'tipo_dovuto': tipo_dovuto,
        'anagrafica': citizen_data.name,
        'cod_fiscale': citizen_data.fiscal_code,
        'email': citizen_data.email,
        'importo': importo,
        'data_scadenza': (datetime.utcnow() + timedelta(days=10)).strftime('%Y/%m/%d'),
        'causale': 'Dovuto feature test'
    }

    try:
        context.dovuto_data[label] = dovuto_data
    except AttributeError:
        context.dovuto_data = {label: dovuto_data}


@when('l\'{user} inserisce il dovuto {label} con generazione avviso')
def step_insert_dovuto(context, user, label, generate_iuv=True):
    step_user_authentication(context, user)
    token = context.token[user]

    dovuto_data = context.dovuto_data[label]

    res = post_insert_dovuto(token=token,
                             ente_id=ente_id,
                             tipo_dovuto=dovuto_data['tipo_dovuto'],
                             anagrafica=dovuto_data['anagrafica'],
                             cod_fiscale=dovuto_data['cod_fiscale'],
                             email=dovuto_data['email'],
                             importo=dovuto_data['importo'],
                             causale=dovuto_data['causale'],
                             flag_generate_iuv=generate_iuv,
                             data_scadenza=dovuto_data['data_scadenza'])

    assert res.status_code == 200
    new_dovuto = res.json()

    context.dovuto_data[label]['id'] = new_dovuto['id']
    context.dovuto_data[label]['iud'] = new_dovuto['iud']

    if generate_iuv:
        assert new_dovuto['iuv'] is not None
        context.dovuto_data[label]['iuv'] = new_dovuto['iuv']


@then('il dovuto {label} è in stato "{status}"')
def step_check_dovuto_status(context, label, status):
    token = context.token[context.latest_user_authenticated]
    status = status.upper()
    dovuto_id = context.dovuto_data[label]['id']

    res = get_dovuto_details(token=token, ente_id=ente_id, dovuto_id=dovuto_id)

    assert res.status_code == 200
    assert res.json()['stato'] == status


@given('il dovuto {label} inserito correttamente con la relativa posizione debitoria')
def step_dovuto_insert_ok_and_check_gpd(context, label):
    step_insert_dovuto(context=context, user='Operatore', label=label)
    step_check_dovuto_status(context=context, label=label, status='da pagare')
    step_check_debt_position_exists(context=context, label=label)


@when('l\'{user} annulla il dovuto {label}')
def step_delete_dovuto(context, user, label):
    step_user_authentication(context, user)
    token = context.token[user]

    res = delete_dovuto(token=token, ente_id=ente_id, dovuto_id=context.dovuto_data[label]['id'])

    assert res.status_code == 200


@then('il dovuto {label} è in stato "{status}" nell\'archivio')
def step_check_processed_dovuto_status(context, label, status):
    token = context.token[context.latest_user_authenticated]
    status = status.upper()
    dovuto_iuv = context.dovuto_data[label]['iuv']

    date_from = datetime.utcnow().strftime('%Y/%m/%d')
    date_to = (datetime.utcnow() + timedelta(days=30)).strftime('%Y/%m/%d')

    res = get_processed_dovuto_list(token=token, ente_id=ente_id, date_from=date_from, date_to=date_to, iuv=dovuto_iuv)

    assert res.status_code == 200
    processed_dovuto_list = res.json()['list']
    assert len(processed_dovuto_list) == 1

    assert processed_dovuto_list[0]['stato'] == status


@when('l\'{user} modifica il valore dell\'importo del dovuto {label} da {old_value} a {new_value} euro')
def step_update_amount_dovuto(context, user, label, old_value, new_value):
    step_user_authentication(context, user)
    token = context.token[user]
    dovuto_data = context.dovuto_data[label]

    res = post_update_dovuto(token=token,
                             ente_id=ente_id,
                             dovuto_id=dovuto_data['id'],
                             dovuto_iud=dovuto_data['iud'],
                             tipo_dovuto=dovuto_data['tipo_dovuto'],
                             anagrafica=dovuto_data['anagrafica'],
                             cod_fiscale=dovuto_data['cod_fiscale'],
                             email=dovuto_data['email'],
                             importo=new_value,
                             causale=dovuto_data['causale'],
                             data_scadenza=dovuto_data['data_scadenza'])

    assert res.status_code == 200
    assert res.json()['iuv'] == dovuto_data['iuv']
    assert res.json()['stato'] == 'DA PAGARE'
    assert float(res.json()['importo']) == float(new_value)


# GPD
@then('una nuova posizione debitoria relativa al dovuto {label} risulta creata')
def step_check_debt_position_exists(context, label):
    step_user_authentication(context, 'Amministratore Globale')
    token = context.token['Amministratore Globale']

    dovuto = context.dovuto_data[label]
    nav = '3' + dovuto['iuv']

    res = get_debt_position_details_by_nav(token=token, ente_fiscal_code=ente_fiscal_code, nav=nav)

    assert res.status_code == 200
    debt_position = res.json()

    assert debt_position['iupd'] is not None
    context.dovuto_data[label]['iupd'] = debt_position['iupd']

    assert debt_position['status'] == 'VALID'

    payment_options = debt_position['paymentOption']

    for i in range(len(payment_options)):
        if nav == payment_options[i]['nav']:
            assert payment_options[i]['status'] == 'PO_UNPAID'
            assert str(round(payment_options[i]['amount'] / 100, 2)) == context.dovuto_data[label]['importo']


@then('la posizione debitoria relativa al dovuto {label} non è più presente')
def step_check_debt_position_not_exists(context, label):
    dovuto_iupd = context.dovuto_data[label]['iupd']

    res = get_debt_position_by_iupd(ente_fiscal_code=ente_fiscal_code, iupd=dovuto_iupd)

    assert res.status_code == 404
    assert res.json()['detail'] == (f"Not found a debt position for Organization Fiscal Code {ente_fiscal_code} "
                                    f"and IUPD {dovuto_iupd}")


@then('l\'{field} della posizione debitoria relativa al dovuto {label} è ora di {value}')
def step_check_detail_of_debt_position(context, label, field, value):
    dovuto_iupd = context.dovuto_data[label]['iupd']

    res = get_debt_position_by_iupd(ente_fiscal_code=ente_fiscal_code, iupd=dovuto_iupd)

    assert res.status_code == 200
    debt_position = res.json()

    payment_options = debt_position['paymentOption']

    for i in range(len(payment_options)):
        if context.dovuto_data[label]['iuv'] == payment_options[i]['iuv']:
            assert payment_options[i]['status'] == 'PO_UNPAID'
            if field == 'importo':
                assert str(round(payment_options[i]['amount'] / 100, 2)) == value.removesuffix(' euro')
