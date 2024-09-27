import io
import os
import random
import string
import zipfile
from datetime import datetime
from datetime import timedelta

import pandas
from behave import when
from behave import then
from behave import given

from api.dovuti import get_dovuto_list
from api.flussi import post_import_flusso
from api.flussi import get_insert_export_rt
from api.flussi import download_file_flusso
from bdd.steps.authentication_step import step_user_authentication
from config.configuration import secrets
from util.utility import retry_get_imported_flussi
from util.utility import retry_get_list_flussi_export

versione_flusso = '1_3'
versione_flusso_beneficiario = '1_4'

intermediato_2 = secrets.ente.intermediato_2
intermediato_1 = secrets.ente.intermediato_1

azione_inserimento = 'I'
citizens_available = ['Maria', 'Giovanni', 'Luca']
download_type_export = 'FLUSSI_EXPORT'
download_type_import = 'FLUSSI_IMPORT'


def create_row_data(context, citizen: str, i_th: int, file_multibeneficiario: bool = False,
                    dovuto_multibeneficiario: bool = False):
    citizen_data = secrets.citizen_info.get(citizen.lower())
    iud = ''.join(random.choices(string.ascii_letters + string.digits, k=35))
    data_scadenza = (datetime.utcnow() + timedelta(days=1)).strftime('%Y-%m-%d')
    importo = round(random.uniform(10, 100), 2)
    importo_ente_secondario = None
    causale = 'Dovuto flusso feature test'

    row = None
    if not file_multibeneficiario:
        row = (f'{iud};;F;{citizen_data.fiscal_code};{citizen_data.name};;;;;;;{citizen_data.email};{data_scadenza};'
               f'{importo};0.00;{intermediato_2.tipo_dovuto.cod_tipo};ALL;{causale};'
               f'{intermediato_2.tipo_dovuto.cod_tassonomico};;TRUE;{azione_inserimento}')
    elif file_multibeneficiario and not dovuto_multibeneficiario:
        row = (f'{iud};;F;{citizen_data.fiscal_code};{citizen_data.name};;;;;;;{citizen_data.email};{data_scadenza};'
               f'{importo};0.00;{intermediato_2.tipo_dovuto.cod_tipo};ALL;{causale};'
               f'{intermediato_2.tipo_dovuto.cod_tassonomico};;TRUE;FALSE;;;;;;;;;;;;;{azione_inserimento}')
    elif file_multibeneficiario and dovuto_multibeneficiario:
        importo_ente_secondario = round(random.uniform(10, 100), 2)
        causale_ente_secondario = 'Dovuto multibeneficiario feature test flusso'

        row = (f'{iud};;F;{citizen_data.fiscal_code};{citizen_data.name};;;;;;;{citizen_data.email};{data_scadenza};'
               f'{importo};0.00;{intermediato_2.tipo_dovuto.cod_tipo};ALL;{causale};'
               f'{intermediato_2.tipo_dovuto.cod_tassonomico};;TRUE;TRUE;{intermediato_1.fiscal_code};'
               f'{intermediato_1.name};{intermediato_1.iban};;;;;;;{intermediato_1.tipo_dovuto.cod_tassonomico};'
               f'{causale_ente_secondario};{importo_ente_secondario};{azione_inserimento}')

    dovuto_flusso = {
        'iud': iud,
        'anagrafica': citizen_data.name,
        'cod_fiscale': citizen_data.fiscal_code,
        'email': citizen_data.email,
        'importo': importo,
        'data_scadenza': data_scadenza,
        'causale': causale,
        'multibeneficiario': dovuto_multibeneficiario,
        'importo_secondario': importo_ente_secondario
    }
    try:
        context.dovuto_flusso[i_th] = dovuto_flusso
    except AttributeError:
        context.dovuto_flusso = {i_th: dovuto_flusso}

    return row


def create_flusso_rows(context, citizens: list, file_multibeneficiario: bool = False):
    if not file_multibeneficiario:
        header = (f'IUD;codIuv;tipoIdentificativoUnivoco;codiceIdentificativoUnivoco;anagraficaPagatore;'
                  f'indirizzoPagatore;civicoPagatore;capPagatore;localitaPagatore;provinciaPagatore;nazionePagatore;'
                  f'mailPagatore;dataScadenzaPagamento;importoDovuto;commissioneCaricoPa;tipoDovuto;tipoVersamento;'
                  f'causaleVersamento;datiSpecificiRiscossione;bilancio;flgGeneraIuv;azione')
    else:
        header = (f'IUD;codIuv;tipoIdentificativoUnivoco;codiceIdentificativoUnivoco;anagraficaPagatore;'
                  f'indirizzoPagatore;civicoPagatore;capPagatore;localitaPagatore;provinciaPagatore;nazionePagatore;'
                  f'mailPagatore;dataScadenzaPagamento;importoDovuto;commissioneCaricoPa;tipoDovuto;tipoVersamento;'
                  f'causaleVersamento;datiSpecificiRiscossione;bilancio;flgGeneraIuv;flgMultibeneficiario;'
                  f'codiceFiscaleEnteSecondario;denominazioneEnteSecondario;ibanAccreditoEnteSecondario;'
                  f'indirizzoEnteSecondario;civicoEnteSecondario;capEnteSecondario;localitaEnteSecondario;'
                  f'provinciaEnteSecondario;nazioneEnteSecondario;datiSpecificiRiscossioneEnteSecondario;'
                  f'causaleVersamentoEnteSecondario;importoVersamentoEnteSecondario;azione')

    flusso_csv = [header]
    i_th = 1
    for citizen in citizens:
        flusso_csv.append(create_row_data(context=context, citizen=citizen, i_th=i_th,
                                          file_multibeneficiario=file_multibeneficiario))
        i_th += 1

    return flusso_csv


def create_flusso_zip(flusso):
    flusso_rows = flusso['rows']
    dataset_dataframe = pandas.DataFrame(data=flusso_rows)

    zip_file_path = f'{flusso["filename"]}.zip'
    dataset_dataframe.to_csv(zip_file_path, index=False, header=False,
                             compression=dict(method='zip', archive_name=f'{flusso["filename"]}.csv'))
    return zip_file_path


@given('un nuovo flusso {label} con {num} dovuti di tipo Licenza di Test')
@given('un nuovo flusso {label} con {num} dovuti di tipo Licenza di Test e versione tracciato "{versione}"')
def step_create_flusso_data(context, label, num, versione=None):
    nome_flusso = f'FLUSSO_FEATURE_TEST_{datetime.now().strftime("%Y%m%d_%H%M%S")}'

    citizens = []
    for i in range(int(num)):
        citizens.append(random.choice(citizens_available))

    file_multibeneficiario = False
    if versione is None:
        versione = versione_flusso
    elif versione == versione_flusso_beneficiario:
        file_multibeneficiario = True

    flusso_data = {
        'nome': nome_flusso,
        'num_dovuti': len(citizens),
        'rows': create_flusso_rows(context=context, citizens=citizens, file_multibeneficiario=file_multibeneficiario),
        'filename': f'{intermediato_2.cod_ipa}-{nome_flusso}-{versione}'
    }

    try:
        context.flusso[label] = flusso_data
    except AttributeError:
        context.flusso = {label: flusso_data}


@given('un dovuto {i_th} aggiunto nel flusso {label} a cui non è stato inserito il codice fiscale')
def step_create_flusso_data_with_one_row_wrong(context, label, i_th):
    flusso = context.flusso[label]
    row = create_row_data(context=context, citizen='Maria', i_th=i_th)
    row = row.replace(f'{secrets.citizen_info.get("maria").fiscal_code}', '')
    flusso['rows'].append(row)
    context.flusso[label]['rows'] = flusso['rows']
    context.flusso[label]['num_dovuti'] = flusso['num_dovuti'] + 1
    context.flusso[label]['dovuto_wrong'] = i_th


@given('un dovuto {i_th} di tipo multibeneficiario aggiunto nel flusso {label}')
def step_add_dovuto_multibeneficiario_to_flusso(context, label, i_th):
    flusso = context.flusso[label]
    row = create_row_data(context=context, citizen='Maria', i_th=i_th, file_multibeneficiario=True,
                          dovuto_multibeneficiario=True)
    flusso['rows'].append(row)
    context.flusso[label]['rows'] = flusso['rows']
    context.flusso[label]['num_dovuti'] = flusso['num_dovuti'] + 1


@when('l\'{user} carica il flusso {label}')
def step_import_flusso(context, user, label):
    step_user_authentication(context, user)
    token = context.token[user]

    zip_file_path = create_flusso_zip(context.flusso[label])

    res = post_import_flusso(token=token, ente_id=intermediato_2.id,
                             file={'file': (zip_file_path, open(zip_file_path, 'rb'))})
    os.remove(zip_file_path)
    assert res.status_code == 200


@given('l\'{user} che carica correttamente il flusso {label}')
def step_import_flusso_ok(context, user, label):
    step_import_flusso(context=context, user=user, label=label)
    step_check_status_flusso(context=context, label=label, status='caricato')


@when('l\'{user} prova a caricare il flusso {label} con lo stesso nome del flusso {label_1}')
@when('l\'{user} prova a caricare il flusso {label} con nome del file che non inizia con il codice ipa')
def step_try_import_flusso(context, user, label, label_1=None):
    step_user_authentication(context, user)
    token = context.token[user]

    if label_1 is not None:
        context.flusso[label]['filename'] = context.flusso[label_1]['filename']
    else:
        context.flusso[label]['filename'] = f'NOT_CODE_IPA'
    zip_file_path = create_flusso_zip(context.flusso[label])

    res = post_import_flusso(token=token, ente_id=intermediato_2.id,
                             file={'file': (zip_file_path, open(zip_file_path, 'rb'))})
    os.remove(zip_file_path)
    context.latest_import_flusso = res


@then('il caricamento del flusso {label} non va a buon fine a causa di "{cause_ko}"')
def step_check_latest_import_flusso(context, label, cause_ko):
    if cause_ko == 'flusso esistente con stesso nome':
        assert context.latest_import_flusso.status_code == 500
        assert (context.latest_import_flusso.json()['message'] ==
                f'Lo stesso nome di file [{context.flusso[label]["filename"]}.zip] esiste gia\'.')

    elif cause_ko == 'il nome del file deve iniziare con il codice ipa':
        assert context.latest_import_flusso.status_code == 500
        assert (context.latest_import_flusso.json()['message'] ==
                f'Il nome del file [{context.flusso[label]["filename"]}.zip] deve iniziare col codice dell\'ente.')


@then('inizialmente il flusso {label} è in stato "{status}"')
@then('poi il flusso {label} passa nello stato "{status}"')
@then('il flusso {label} è in stato "{status}" a causa di "{cause_ko}"')
def step_check_status_flusso(context, label, status, cause_ko=None):
    token = context.token[context.latest_user_authenticated]
    cod_stato = status.upper().replace(' ', '_')

    if status == 'flusso in caricamento':
        cod_stato = 'LOAD_FLOW'

    nome_flusso = context.flusso[label]['nome']
    flusso = retry_get_imported_flussi(token=token, ente_id=intermediato_2.id, nome_flusso=nome_flusso,
                                       field='codStato', expected_value=cod_stato)

    if cause_ko is not None:
        if cause_ko == 'versione tracciato \'1_45\' non supportata':
            assert ('La versione tracciato del file ' in flusso['codErrore'] and
                    'non è supportata.' in flusso['codErrore'])


@then('il flusso {label} è in stato "{status}" con {num_scarti} scarto a causa del dovuto con "{cause_error}"')
def step_check_flusso_scarti_error(context, label, status, num_scarti, cause_error):
    token = context.token[context.latest_user_authenticated]
    flusso = context.flusso[label]

    flusso_info = retry_get_imported_flussi(token=token, ente_id=intermediato_2.id, nome_flusso=flusso['nome'],
                                            field='codStato', expected_value=status.upper())

    assert (flusso_info['numRigheTotali'] - flusso_info['numRigheImportateCorrettamente']) == int(num_scarti)

    file_path_scarti = f'{flusso_info["path"]}_SCARTI.zip'
    res = download_file_flusso(token=token, ente_id=intermediato_2.id, file_name=file_path_scarti,
                               security_token=flusso_info['securityToken'],
                               download_type=download_type_import)

    assert res.status_code == 200
    assert res.headers.get('content-type') == 'application/octet-stream'

    zf = zipfile.ZipFile(io.BytesIO(res.content))
    scarti_file_name = f'{flusso["filename"]}_SCARTI.csv'
    dovuti_scartati_list = pandas.read_csv(zf.open(scarti_file_name), sep=';').to_dict(orient='records')
    assert len(dovuti_scartati_list) == int(num_scarti)
    dovuto_scartato = dovuti_scartati_list[0]

    dovuto_wrong = context.dovuto_flusso[flusso['dovuto_wrong']]

    if cause_error == 'codice fiscale non presente':
        assert dovuto_scartato['IUD'] == dovuto_wrong['iud']
        assert dovuto_scartato['cod_rifiuto'] == 'PAA_IMPORT_SINTASSI_CSV'
        assert 'CODICE_IDENTIFICATIVO_UNIVOCO NON PRESENTE' in dovuto_scartato['de_rifiuto']


@then('i {num_dovuti} dovuti inseriti tramite flusso {label} sono in stato "{status}"')
@then('gli altri {num_dovuti} dovuti inseriti tramite flusso {label} sono in stato "{status}"')
def step_check_status_dovuti_import(context, label, status, num_dovuti):
    token = context.token[context.latest_user_authenticated]
    status = status.upper()

    date_from = (datetime.utcnow() - timedelta(days=1)).strftime('%Y/%m/%d')
    date_to = (datetime.utcnow() + timedelta(days=1)).strftime('%Y/%m/%d')
    flusso_data = context.flusso[label]

    res = get_dovuto_list(token=token, ente_id=intermediato_2.id, date_from=date_from, date_to=date_to,
                          nome_flusso=flusso_data['nome'])

    assert res.status_code == 200

    dovuti = res.json()['list']
    assert len(dovuti) == int(num_dovuti)

    for dovuto in dovuti:
        assert dovuto['stato'] == status


@then('il dovuto {i_th} del flusso {label} nel dettaglio presenta due beneficiari')
def step_check_dovuto_flusso_details(context, label, i_th):
    token = context.token[context.latest_user_authenticated]

    date_from = (datetime.utcnow() - timedelta(days=1)).strftime('%Y/%m/%d')
    date_to = (datetime.utcnow() + timedelta(days=1)).strftime('%Y/%m/%d')
    flusso_data = context.flusso[label]
    dovuto_flusso = context.dovuto_flusso[i_th]

    res = get_dovuto_list(token=token, ente_id=intermediato_2.id, date_from=date_from, date_to=date_to,
                          nome_flusso=flusso_data['nome'], iud=dovuto_flusso['iud'])

    assert res.status_code == 200
    assert len(res.json()['list']) == 1
    dovuto = res.json()['list'][0]

    assert dovuto['flgMultibeneficiario'] is True
    assert dovuto['importo'] == str(float(dovuto_flusso['importo'] + dovuto_flusso['importo_secondario']))
    assert dovuto['dovutoMultibeneficiario'] is not None
    assert dovuto['dovutoMultibeneficiario']['codiceIdentificativoUnivoco'] == intermediato_1.fiscal_code


@when('l\'{user} prenota l\'export delle ricevute telematiche')
def step_insert_export_rt(context, user):
    step_user_authentication(context, user)
    token = context.token[user]

    date_from = date_to = (datetime.utcnow()).strftime('%Y/%m/%d')

    res = get_insert_export_rt(token=token, ente_id=intermediato_2.id, date_from=date_from,
                               date_to=date_to, tipo_dovuto=intermediato_2.tipo_dovuto.cod_tipo)

    assert res.status_code == 200
    assert res.content is not None

    context.latest_flusso_export_rt = {'id': res.content}


@then('il flusso RT prenotato è visibile nella lista')
def step_check_flusso_rt_present(context):
    token = context.token[context.latest_user_authenticated]

    # this api research a flow with name containing also the id of the flow
    flusso_rt = retry_get_list_flussi_export(token=token, ente_id=intermediato_2.id,
                                             nome_flusso=context.latest_flusso_export_rt['id'])

    context.latest_flusso_export_rt['filepath'] = flusso_rt['path']
    context.latest_flusso_export_rt['security_token'] = flusso_rt['securityToken']
    context.latest_flusso_export_rt['filename'] = flusso_rt['name'].replace('.zip', '')


@then('l\'{user} scaricando il flusso verifica il dettaglio del dovuto {dovuto_label} pagato')
def step_download_flusso_rt_and_check_details(context, user, dovuto_label):
    step_user_authentication(context, user)
    token = context.token[user]

    flusso_export_rt = context.latest_flusso_export_rt
    res = download_file_flusso(token=token, ente_id=intermediato_2.id, file_name=flusso_export_rt['filepath'],
                               security_token=flusso_export_rt['security_token'],
                               download_type=download_type_export)

    assert res.status_code == 200
    assert res.headers.get('content-type') == 'application/octet-stream'

    zf = zipfile.ZipFile(io.BytesIO(res.content))
    dovuti_list = pandas.read_csv(zf.open(f"{flusso_export_rt['filename']}.csv"), sep=';').to_dict(orient='records')

    dovuto = context.dovuto_data[dovuto_label]
    for d in dovuti_list:
        if d['codIuv'] == dovuto['iuv']:
            assert d['codIud'] == dovuto['iud']
            assert d['identificativoUnivocoRiscoss'] == dovuto['receipt_id']
            assert d['soggPagCodiceIdentificativoUnivoco'] == dovuto['cod_fiscale']
            assert d['importoTotalePagato'] == float(dovuto['importo'])


@when('l\'{user} prova a prenotare l\'export delle ricevute telematiche inserendo un {field} invalido')
def step_try_insert_export_rt(context, user, field):
    step_user_authentication(context, user)
    token = context.token[user]

    date_from = date_to = (datetime.utcnow()).strftime('%Y/%m/%d')
    tipo_dovuto = intermediato_2.tipo_dovuto.cod_tipo

    if field == 'intervallo di date':
        date_to = (datetime.utcnow() - timedelta(days=2)).strftime('%Y/%m/%d')
    elif field == 'tipo dovuto':
        tipo_dovuto = 'NOT_EXISTENT'

    res = get_insert_export_rt(token=token, ente_id=intermediato_2.id, date_from=date_from,
                               date_to=date_to, tipo_dovuto=tipo_dovuto)

    context.latest_insert_export_rt = res


@then('la prenotazione dell\'export delle RT non va a buon fine a causa di "{cause_ko}"')
def step_check_latest_export_rt(context, cause_ko):
    if cause_ko == 'date non corrette':
        assert context.latest_insert_export_rt.status_code == 500
        assert context.latest_insert_export_rt.json()['message'] == 'La data di fine precede quella d\u00B4inizio'
    elif cause_ko == 'tipo dovuto non trovato':
        assert context.latest_insert_export_rt.status_code == 418  # TODO expected 404
        assert context.latest_insert_export_rt.json()['message'] == 'Tipo Dovuto not found'
