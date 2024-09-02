import io
import random
import string
from datetime import datetime
from datetime import timedelta

import xmltodict
import fitz
from behave import when
from behave import then
from behave import given

from api.dovuti import post_insert_dovuto
from api.dovuti import get_dovuto_details
from api.dovuti import get_debt_position_details_by_nav
from api.dovuti import delete_dovuto
from api.dovuti import post_update_dovuto
from api.dovuti import download_rt
from api.dovuti import download_avviso
from api.gpd import get_debt_position_by_iupd
from api.soap.fesp import pa_get_payment_v2
from api.soap.fesp import pa_send_rt_v2
from bdd.steps.authentication_step import step_user_authentication
from config.configuration import secrets
from util.utility import get_tipo_dovuto_of_operator, retry_check_exists_processed_dovuto

cod_tipo_dovuto = 'LICENZA_FEATURE_TEST'
ente_id = secrets.user_info.operator.ente_id
ente_name = secrets.user_info.operator.ente_name
ente_fiscal_code = secrets.user_info.operator.ente_fiscal_code
broker_fiscal_code = secrets.payment_info.broker_fiscal_code
broker_station_id = secrets.payment_info.broker_station_id


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


@given('l\'aggiunta dell\'Ente intermediato 1 come altro beneficiario del dovuto {label} con importo di {importo} euro')
def step_add_multibeneficiario_data(context, label, importo):
    ente_beneficiario = secrets.ente.intermediato_1

    altro_beneficiario = {
        'denominazioneBeneficiario': ente_beneficiario.name,
        'codiceIdentificativoUnivoco': ente_beneficiario.fiscal_code,
        'ibanAddebito': ente_beneficiario.iban,
        'importoSecondario': importo,
        'datiSpecificiRiscossione': '9/' + ente_beneficiario.tipo_dovuto + '/'
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
                assert transfer[1]['organizationFiscalCode'] == dovuto['altro_beneficiario']['codiceIdentificativoUnivoco']
                assert float(transfer[1]['amount'] / 100) == float(importo_secondario)


@then('una nuova posizione debitoria relativa al dovuto {label} risulta creata con il dettaglio dei due enti beneficiari')
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


@when('la cittadina {citizen} effettua il pagamento del dovuto {label}')
def step_pay_dovuto(context, citizen, label):
    dovuto_iuv = context.dovuto_data[label]['iuv']
    citizen_data = secrets.citizen_info.get(citizen.lower())

    res_pa_get_payment = pa_get_payment_v2(ente_fiscal_code=ente_fiscal_code,
                                           broker_fiscal_code=broker_fiscal_code,
                                           broker_station_id=broker_station_id,
                                           iuv=dovuto_iuv)
    assert res_pa_get_payment.status_code == 200
    res_parsed = xmltodict.parse(res_pa_get_payment.content.decode('utf-8'))
    res_body = res_parsed['SOAP-ENV:Envelope']['SOAP-ENV:Body']['ns3:paGetPaymentV2Response']
    assert res_body['outcome'] == 'OK'

    receipt_id = ''.join(random.choices(string.ascii_letters, k=15))
    context.dovuto_data[label]['receipt_id'] = receipt_id

    request_body = {
        'ente_fiscal_code': ente_fiscal_code,
        'ente_name': ente_name,
        'broker_fiscal_code': broker_fiscal_code,
        'broker_station_id': broker_station_id,
        'iuv': dovuto_iuv,
        'receipt_id': receipt_id,
        'amount': context.dovuto_data[label]['importo'],
        'citizen_fiscal_code': citizen_data.fiscal_code,
        'citizen_name': citizen_data.name,
        'citizen_email': citizen_data.email
    }

    res_pa_send_rt = pa_send_rt_v2(body=request_body)
    assert res_pa_send_rt.status_code == 200
    res_parsed = xmltodict.parse(res_pa_send_rt.content.decode('utf-8'))
    res_body = res_parsed['SOAP-ENV:Envelope']['SOAP-ENV:Body']['ns3:paSendRTV2Response']
    assert res_body['outcome'] == 'OK'


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
        check_data_on_pdf(page=page, dovuto=dovuto_data)


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
    assert data_dict['Id Univoco Riscossione'] == dovuto['receipt_id']
    assert data_dict['Importo pagato'] == '€ ' + dovuto['importo'].replace('.', ',')
    assert data_dict['Data pagamento'] == datetime.utcnow().strftime('%d/%m/%Y')

    # Assertion of other values in pdf
    text = page.get_text("text")
    assert 'CODICE UNIVOCO:\n'+dovuto['cod_fiscale'] in text
    assert ente_fiscal_code in text


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
