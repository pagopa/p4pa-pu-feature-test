import io
from datetime import datetime
from datetime import timedelta

import fitz
import xmltodict
from behave import given
from behave import then
from behave import when

from api.dovuti import delete_dovuto
from api.dovuti import download_avviso
from api.dovuti import download_rt
from api.dovuti import get_debt_position_details_by_nav
from api.dovuti import get_dovuto_details
from api.dovuti import get_dovuto_list
from api.dovuti import post_insert_dovuto
from api.dovuti import post_update_dovuto
from api.gpd import get_debt_position_by_iupd
from api.soap.nodo import PSP
from api.soap.nodo import activate_payment_notice
from api.soap.nodo import send_payment_outcome
from api.soap.nodo import verify_payment_notice
from bdd.steps.authentication_step import step_user_authentication
from config.configuration import secrets
from util.utility import get_tipo_dovuto_of_operator
from util.utility import get_user_info
from util.utility import retry_check_exists_processed_dovuto

cod_tipo_dovuto = secrets.ente.intermediato_2.tipo_dovuto.cod_tipo
ente_id = secrets.ente.intermediato_2.id
ente_name = secrets.ente.intermediato_2.name
ente_fiscal_code = secrets.ente.intermediato_2.fiscal_code
broker_fiscal_code = secrets.payment_info.broker_fiscal_code
broker_station_id = secrets.payment_info.broker_station_id
psp_info = secrets.payment_info.psp


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
        'data_scadenza': (datetime.utcnow() + timedelta(days=1)).strftime('%Y/%m/%d'),
        'causale': 'Dovuto feature test'
    }

    try:
        context.dovuto_data[label] = dovuto_data
    except AttributeError:
        context.dovuto_data = {label: dovuto_data}


@given('l\'aggiunta dell\'Ente intermediato 1 come altro beneficiario del dovuto {label} con importo di {importo} euro')
def step_add_multibeneficiario_data(context, label, importo):
    ente_beneficiario = secrets.ente.intermediato_1

    altro_beneficiario = {
        'denominazioneBeneficiario': ente_beneficiario.name,
        'codiceIdentificativoUnivoco': ente_beneficiario.fiscal_code,
        'ibanAddebito': ente_beneficiario.iban,
        'importoSecondario': importo,
        'datiSpecificiRiscossione': ente_beneficiario.tipo_dovuto.cod_tassonomico
    }

    context.dovuto_data[label]['altro_beneficiario'] = altro_beneficiario


@when('l\'{user} inserisce il dovuto {label} con generazione avviso')
def step_insert_dovuto(context, user, label, generate_iuv=True, multibeneficiario=False, altro_beneficiario=None):
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
                             data_scadenza=dovuto_data['data_scadenza'],
                             flag_multibeneficiario=multibeneficiario,
                             altro_beneficiario=altro_beneficiario)

    assert res.status_code == 200
    new_dovuto = res.json()

    context.dovuto_data[label]['id'] = new_dovuto['id']
    context.dovuto_data[label]['iud'] = new_dovuto['iud']

    if generate_iuv:
        assert new_dovuto['iuv'] is not None
        context.dovuto_data[label]['iuv'] = new_dovuto['iuv']


@when('l\'{user} inserisce il dovuto {label} con generazione avviso e con multibeneficiario')
def step_insert_dovuto_multibeneficiario(context, user, label):
    altro_beneficiario = context.dovuto_data[label]['altro_beneficiario']
    step_insert_dovuto(context=context, user=user, label=label,
                       multibeneficiario=True, altro_beneficiario=altro_beneficiario)


@when('l\'{user} prova ad inserire il dovuto {label}')
@when('l\'{user} prova ad inserire il dovuto {label} senza {missing_field}')
def step_try_insert_dovuto(context, user, label, missing_field=None):
    step_user_authentication(context, user)
    token = context.token[user]

    dovuto_data = context.dovuto_data[label]

    if missing_field == 'codice fiscale':
        dovuto_data['cod_fiscale'] = None
    elif missing_field == 'causale':
        dovuto_data['causale'] = None

    res = post_insert_dovuto(token=token,
                             ente_id=ente_id,
                             tipo_dovuto=dovuto_data['tipo_dovuto'],
                             anagrafica=dovuto_data['anagrafica'],
                             cod_fiscale=dovuto_data['cod_fiscale'],
                             email=dovuto_data['email'],
                             importo=dovuto_data['importo'],
                             causale=dovuto_data['causale'],
                             flag_generate_iuv=False,
                             data_scadenza=dovuto_data['data_scadenza'])

    context.latest_insert_dovuto = res


@then('l\'inserimento del nuovo dovuto non va a buon fine a causa di "{cause_ko}"')
def step_check_latest_delete_dovuto(context, cause_ko):
    # TODO it is correct that if there is an error then response return 200 as status code?
    if cause_ko == 'tipo dovuto non attivo per l\'operatore':
        assert context.latest_insert_dovuto.status_code == 200
        cod_fed_user_id = get_user_info(context.latest_user_authenticated).cod_fed_user_id
        assert (f'The operator {cod_fed_user_id} is not authorized on the DebtPositionTypeOrg'
                in context.latest_insert_dovuto.json()['invalidDesc'])
    elif cause_ko == 'codice fiscale obbligatorio':
        assert context.latest_insert_dovuto.status_code == 200
        assert 'Codice fiscale / Partita Iva: campo obbligatorio' in context.latest_insert_dovuto.json()['invalidDesc']
    elif cause_ko == 'causale obbligatoria':
        assert context.latest_insert_dovuto.status_code == 200
        assert 'Causale: campo obbligatorio' in context.latest_insert_dovuto.json()['invalidDesc']


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
    step_user_authentication(context, 'Operatore')
    token = context.token['Operatore']
    status = status.upper()
    dovuto_iuv = context.dovuto_data[label]['iuv']

    dovuto = retry_check_exists_processed_dovuto(token=token, ente_id=ente_id, dovuto_iuv=dovuto_iuv)

    assert dovuto['stato'] == status
    context.dovuto_data[label]['id_elaborato'] = dovuto['id']


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
def step_check_debt_position_exists(context, label, multibeneficiario=False):
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
            if not multibeneficiario:
                assert float(payment_options[i]['amount'] / 100) == float(dovuto['importo'])
            else:
                importo_secondario = dovuto['altro_beneficiario']['importoSecondario']
                assert float(payment_options[i]['amount'] / 100) == float(dovuto['importo']) + float(importo_secondario)
                transfer = payment_options[i]['transfer']
                assert len(transfer) == 2
                assert transfer[0]['organizationFiscalCode'] == ente_fiscal_code
                assert float(transfer[0]['amount'] / 100) == float(dovuto['importo'])
                assert transfer[1]['organizationFiscalCode'] == dovuto['altro_beneficiario'][
                    'codiceIdentificativoUnivoco']
                assert float(transfer[1]['amount'] / 100) == float(importo_secondario)


@then(
    'una nuova posizione debitoria relativa al dovuto {label} risulta creata con il dettaglio dei due enti beneficiari')
def step_check_debt_position_with_multibeneficiario(context, label):
    step_check_debt_position_exists(context=context, label=label, multibeneficiario=True)


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
                assert float(payment_options[i]['amount'] / 100) == float(value.removesuffix(' euro'))


def check_res_ok_and_get_body(response_content, tag_name):
    res_parsed = xmltodict.parse(response_content.decode('utf-8'))
    res_body = res_parsed['soapenv:Envelope']['soapenv:Body'][f'nfp:{tag_name}']
    assert res_body['outcome'] == 'OK'
    return res_body


@when('la cittadina {citizen} effettua il pagamento del dovuto {label}')
def step_pay_dovuto_with_nodo(context, citizen, label):
    dovuto_iuv = context.dovuto_data[label]['iuv']
    citizen_data = secrets.citizen_info.get(citizen.lower())

    psp = PSP(id=psp_info.id, id_broker=psp_info.id_broker, id_channel=psp_info.id_channel, password=psp_info.password)

    res_verify_payment = verify_payment_notice(psp=psp, ente_fiscal_code=ente_fiscal_code, iuv=dovuto_iuv)
    assert res_verify_payment.status_code == 200
    print(res_verify_payment.content)
    res_verify_payment_body = check_res_ok_and_get_body(res_verify_payment.content, tag_name='verifyPaymentNoticeRes')

    amount = res_verify_payment_body["paymentList"]["paymentOptionDescription"]["amount"]
    due_date = res_verify_payment_body["paymentList"]["paymentOptionDescription"]["dueDate"]

    res_activate_payment = activate_payment_notice(psp=psp, ente_fiscal_code=ente_fiscal_code, iuv=dovuto_iuv,
                                                   amount=amount, due_date=due_date)
    assert res_activate_payment.status_code == 200
    res_activate_payment_body = check_res_ok_and_get_body(response_content=res_activate_payment.content,
                                                          tag_name='activatePaymentNoticeRes')

    payment_token = res_activate_payment_body["paymentToken"]

    res_send_outcome = send_payment_outcome(psp=psp, payment_token=payment_token,
                                            citizen_fiscal_code=citizen_data.fiscal_code,
                                            citizen_name=citizen_data.name,
                                            citizen_email=citizen_data.email)
    assert res_send_outcome.status_code == 200
    check_res_ok_and_get_body(response_content=res_send_outcome.content, tag_name='sendPaymentOutcomeRes')


@given('il dovuto {label} inserito e pagato correttamente dalla cittadina {citizen}')
def step_dovuto_paid_ok(context, citizen, label):
    step_insert_dovuto(context=context, user='Operatore', label=label)
    step_pay_dovuto_with_nodo(context=context, citizen=citizen, label=label)
    step_check_processed_dovuto_status(context=context, label=label, status='pagato')


@given('un dovuto {label} pagato correttamente compresa la ricezione della RT')
def step_dovuto_paid_ok_and_rt(context, label):
    citizen = 'Maria'
    user = 'Operatore'
    step_create_dovuto_data(context=context, label=label, importo='45.50', citizen=citizen)
    step_insert_dovuto(context=context, user=user, label=label)
    step_pay_dovuto_with_nodo(context=context, citizen=citizen, label=label)
    step_check_processed_dovuto_status(context=context, label=label, status='pagato')
    step_download_rt(context=context, user=user, label=label)


@then('l\'{user} può scaricare la ricevuta di pagamento effettuato per il dovuto {label}')
def step_download_rt(context, user, label):
    step_user_authentication(context, user)
    token = context.token[user]

    dovuto_data = context.dovuto_data[label]

    res = download_rt(token=token, dovuto_id=dovuto_data['id_elaborato'])
    assert res.status_code == 200
    assert res.headers.get('content-type') == 'application/pdf'

    with fitz.open(stream=io.BytesIO(res.content)) as pdf:
        page = pdf[0]
        iur = check_data_on_pdf(page=page, dovuto=dovuto_data)

    context.dovuto_data[label]['iur'] = iur


def check_data_on_pdf(page, dovuto: dict):
    def convert(lst):
        res_dict = {}
        for i in range(0, len(lst), 2):
            res_dict[lst[i]] = lst[i + 1]
        return res_dict

    # in RT there is only one table, regarding the dovuto data
    data_dict = {}
    table = page.find_tables()[0]
    data_list = table.extract()
    for data in data_list:
        data_dict.update(convert(data))

    assert data_dict['Id Univoco Dovuto'] == dovuto['iud']
    assert data_dict['Importo pagato'] == '€ ' + dovuto['importo'].replace('.', ',')
    assert data_dict['Data pagamento'] == datetime.utcnow().strftime('%d/%m/%Y')
    assert data_dict['Id Univoco Riscossione'] is not None

    # Assertion of other values in pdf
    text = page.get_text("text")
    assert 'CODICE UNIVOCO:\n' + dovuto['cod_fiscale'] in text
    assert ente_fiscal_code in text

    return data_dict['Id Univoco Riscossione']


@then('l\'{user} può scaricare l\'avviso di pagamento per il dovuto {label}')
def step_download_avviso(context, user, label):
    step_user_authentication(context, user)
    token = context.token[user]
    dovuto_data = context.dovuto_data[label]

    res = download_avviso(token=token, dovuto_id=dovuto_data['id'])
    assert res.status_code == 200
    assert res.headers.get('content-type') == 'application/pdf'

    with fitz.open(stream=io.BytesIO(res.content)) as pdf:
        page = pdf[0]

        table = page.find_tables()[0]
        data_table = table.extract()[0]
        assert data_table[0] == 'ENTE CREDITORE Cod. Fiscale ' + ente_fiscal_code
        assert data_table[1] == 'DESTINATARIO AVVISO Cod. Fiscale ' + dovuto_data['cod_fiscale']

        text = page.get_text(sort=True)
        assert (dovuto_data['importo'].replace('.', ',') + ' Euro\nentro il\n' +
                datetime.strptime(dovuto_data['data_scadenza'], '%Y/%m/%d').strftime('%d/%m/%Y')) in text
        assert 'Oggetto del pagamento\n' + dovuto_data['causale']


#TODO this step could be replaced by a new 'dovuto' created to which the due date is forced
@given('il dovuto {label} di tipo Licenza di Test per la cittadina {citizen} in stato scaduto')
def step_search_dovuto_scaduto(context, label, citizen):
    step_user_authentication(context, 'Operatore')
    token = context.token['Operatore']

    citizen_data = secrets.citizen_info.get(citizen.lower())
    date_from = (datetime.utcnow() - timedelta(days=15)).strftime('%Y/%m/%d')
    date_to = (datetime.utcnow() + timedelta(days=1)).strftime('%Y/%m/%d')

    res = get_dovuto_list(token=token, ente_id=ente_id, date_from=date_from, date_to=date_to,
                          fiscal_code=citizen_data.fiscal_code, status='scaduto', causale='Dovuto feature test')

    assert res.status_code == 200
    assert len(res.json()['list']) != 0

    dovuto = res.json()['list'][0]
    data_scadenza = datetime.strptime(dovuto['dataScadenza'], '%Y/%m/%d')

    assert data_scadenza < datetime.today()

    res_details = get_dovuto_details(token=token, ente_id=ente_id, dovuto_id=dovuto['id'])
    assert res_details.status_code == 200

    try:
        context.dovuto_data[label] = res_details.json()
    except AttributeError:
        context.dovuto_data = {label: res_details.json()}


@when('l\'{user} proroga la data di scadenza del dovuto {label} di {period} giorni')
def step_update_due_date_dovuto(context, user, label, period):
    step_user_authentication(context, user)
    token = context.token[user]
    dovuto_data = context.dovuto_data[label]

    new_data_scadenza = (datetime.utcnow() + timedelta(days=int(period))).strftime('%Y/%m/%d')
    context.dovuto_data[label]['data_scadenza'] = new_data_scadenza

    res = post_update_dovuto(token=token,
                             ente_id=ente_id,
                             dovuto_id=dovuto_data['id'],
                             dovuto_iud=dovuto_data['iud'],
                             tipo_dovuto=dovuto_data['tipoDovuto'],
                             anagrafica=dovuto_data['anagrafica'],
                             cod_fiscale=dovuto_data['codFiscale'],
                             email=dovuto_data['email'],
                             importo=dovuto_data['importo'],
                             causale=dovuto_data['causale'],
                             data_scadenza=new_data_scadenza)

    assert res.status_code == 200


@then('la {field} del dovuto {label} è stata aggiornata correttamente')
def step_check_field_updated(context, label, field):
    token = context.token[context.latest_user_authenticated]

    res = get_dovuto_details(token=token, ente_id=ente_id, dovuto_id=context.dovuto_data[label]['id'])
    assert res.status_code == 200

    if field == 'data di scadenza':
        assert res.json()['dataScadenza'] == context.dovuto_data[label]['data_scadenza']
