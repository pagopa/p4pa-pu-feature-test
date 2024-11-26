import random
import string
from datetime import datetime

from behave import given
from behave import then
from behave import when

from api.rendicontazione import get_rendicontazione_by_iuf_and_id_regolamento
from bdd.steps.authentication_step import step_user_authentication
from config.configuration import secrets

psp_info = secrets.payment_info.psp
ente_id = secrets.ente.intermediato_2.id
ente_fiscal_code = secrets.ente.intermediato_2.fiscal_code


@given('la generazione del file contenente il flusso di rendicontazione relativo al dovuto {label}')
def step_create_fdr_file(context, label):
    with open('./bdd/steps/file_template/flusso_rendicontazione.xml', 'r') as file:
        flusso = file.read()

    dovuto = context.dovuto_data[label]

    data = datetime.utcnow().strftime('%Y-%m-%d')
    data_ora = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S')
    identificativo_flusso = data + psp_info.id + '-S' + str(random.randint(1000000000, 9999999999))
    identificativo_univoco_regolamento = ''.join(random.choices(string.digits, k=28)) + 'IT'

    flusso = flusso.format(identificativo_flusso=identificativo_flusso,
                           data_ora_flusso=data_ora,
                           identificativo_univoco_regolamento=identificativo_univoco_regolamento,
                           data_regolamento=data,
                           tipo_identificativo_univoco_mittente='B',
                           codice_identificativo_univoco_mittente=psp_info.id,
                           denominazione_mittente=psp_info.name,
                           tipo_identificativo_univoco_ricevente='G',
                           codice_identificativo_univoco_ricevente=ente_fiscal_code,
                           numero_totale_pagamenti=1,
                           importo_totale_pagamenti=dovuto['importo'],
                           iuv=dovuto['iuv'],
                           iur=dovuto['iur'],
                           indice_dati_singolo_pagamento=1,
                           singolo_importo_pagato=dovuto['importo'],
                           codice_esito_singolo_pagamento=0,
                           data_esito_singolo_pagamento=data
                           )

    with open('./bdd/steps/flusso_rendicontazione.xml', 'w') as file:
        file.write(flusso)

    context.fdr = {
        'iuf': identificativo_flusso,
        'id_regolamento': identificativo_univoco_regolamento,
        'importo': dovuto['importo']
    }


@given('la generazione del file contenente il flusso di rendicontazione relativo ai dovuti {label1} e {label2}')
def step_create_fdr_file_with_2_payment(context, label1, label2):
    with open('./bdd/steps/file_template/flusso_rendicontazione_2_pagamenti.xml', 'r') as file:
        flusso = file.read()

    dovuto1 = context.dovuto_data[label1]
    dovuto2 = context.dovuto_data[label2]

    data = datetime.utcnow().strftime('%Y-%m-%d')
    data_ora = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S')
    identificativo_flusso = data + psp_info.id + '-S' + str(random.randint(1000000000, 9999999999))
    identificativo_univoco_regolamento = ''.join(random.choices(string.digits, k=28)) + 'IT'

    flusso = flusso.format(identificativo_flusso=identificativo_flusso,
                           data_ora_flusso=data_ora,
                           identificativo_univoco_regolamento=identificativo_univoco_regolamento,
                           data_regolamento=data,
                           tipo_identificativo_univoco_mittente='B',
                           codice_identificativo_univoco_mittente=psp_info.id,
                           denominazione_mittente=psp_info.name,
                           tipo_identificativo_univoco_ricevente='G',
                           codice_identificativo_univoco_ricevente=ente_fiscal_code,
                           numero_totale_pagamenti=2,
                           importo_totale_pagamenti=float(dovuto1['importo']) + float(dovuto2['importo']),
                           iuv_1=dovuto1['iuv'],
                           iur_1=dovuto1['iur'],
                           indice_dati_singolo_pagamento_1=1,
                           singolo_importo_pagato_1=dovuto1['importo'],
                           iuv_2=dovuto2['iuv'],
                           iur_2=dovuto2['iur'],
                           indice_dati_singolo_pagamento_2=1,
                           singolo_importo_pagato_2=dovuto2['importo'],
                           codice_esito_singolo_pagamento=0,
                           data_esito_singolo_pagamento=data
                           )

    with open('./bdd/steps/flusso_rendicontazione_2_pagamenti.xml', 'w') as file:
        file.write(flusso)

    context.fdr = {
        'iuf': identificativo_flusso,
        'id_regolamento': identificativo_univoco_regolamento,
        'importo': str(float(dovuto1['importo']) + float(dovuto2['importo']))
    }


@when('il file della rendicontazione viene importato')
def step_import_fdr(context):
    # TODO invocazione workflow di ingestion FdR
    pass


@then('il flusso di rendicontazione è caricato e comprende il dovuto {label}')
def step_check_fdr(context, label):
    step_user_authentication(context, 'Amministratore Globale')
    token = context.token['Amministratore Globale']

    fdr = context.fdr
    dovuto = context.dovuto_data[label]

    res = get_rendicontazione_by_iuf_and_id_regolamento(token=token, ente_id=ente_id,
                                                        iuf=fdr['iuf'], id_regolamento=fdr['id_regolamento'])

    assert res.status_code == 200
    assert float(res.json()['importoTotale']) == float(dovuto['importo'])
    assert res.json()['countTotalePagamenti'] == 1
    assert res.json()['details'] != []
    assert len(res.json()['details']) == 1

    assert res.json()['details'][0]['codRpSilinviarpIdUnivocoVersamento'] == dovuto['iuv']
    assert res.json()['details'][0]['codEDatiPagDatiSingPagIdUnivocoRiscoss'] == dovuto['iur']
    assert res.json()['details'][0]['numEDatiPagDatiSingPagSingoloImportoPagato'] == float(dovuto['importo'])


@then('il flusso di rendicontazione è caricato e comprende i dovuti {label1} e {label2}')
def step_check_fdr_with_2_payment(context, label1, label2):
    step_user_authentication(context, 'Amministratore Globale')
    token = context.token['Amministratore Globale']

    fdr = context.fdr
    dovuto1 = context.dovuto_data[label1]
    dovuto2 = context.dovuto_data[label2]

    res = get_rendicontazione_by_iuf_and_id_regolamento(token=token, ente_id=ente_id,
                                                        iuf=fdr['iuf'], id_regolamento=fdr['id_regolamento'])

    assert res.status_code == 200
    assert float(res.json()['importoTotale']) == float(dovuto1['importo']) + float(dovuto2['importo'])
    assert res.json()['countTotalePagamenti'] == 2
    assert res.json()['details'] != []
    assert len(res.json()['details']) == 2

    for payment in res.json()['details']:
        if payment['codRpSilinviarpIdUnivocoVersamento'] == dovuto1['iuv']:
            assert payment['codEDatiPagDatiSingPagIdUnivocoRiscoss'] == dovuto1['iur']
            assert payment['numEDatiPagDatiSingPagSingoloImportoPagato'] == float(dovuto1['importo'])
        elif payment['codRpSilinviarpIdUnivocoVersamento'] == dovuto2['iuv']:
            assert payment['codEDatiPagDatiSingPagIdUnivocoRiscoss'] == dovuto2['iur']
            assert payment['numEDatiPagDatiSingPagSingoloImportoPagato'] == float(dovuto2['importo'])
        else:
            assert False


@given('il flusso di rendicontazione relativo al dovuto {label} importato correttamente')
def step_import_fdr_and_check(context, label):
    step_create_fdr_file(context=context, label=label)
    step_import_fdr(context=context)
    step_check_fdr(context=context, label=label)
