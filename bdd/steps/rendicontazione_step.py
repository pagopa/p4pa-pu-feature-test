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


@given('la generazione del file contenente il flusso di rendicontazione relativo ai dovuti {label1} e {label2}')
def step_create_fdr_file(context, label1, label2):
    with open('./bdd/steps/file_template/flusso_rendicontazione_2_dovuti.xml', 'r') as file:
        flusso = file.read()

    # dovuto1 = context.dovuto_data[label1]
    dovuto1 = {
        'iuv': '01000000000209391',
        'iur': 'c9cccd0c26484fd1904e8baf1db2dfac',
        'importo': '10.00'
    }
    # dovuto2 = context.dovuto_data[label2]
    dovuto2 = {
        'iuv': '01000000000209390',
        'iur': 'd9cccd0c26484fd1904e8baf1db2dfac',
        'importo': '1.00'
    }

    data = datetime.utcnow().strftime('%Y-%m-%d')
    date_ora = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S')
    identificativo_flusso = '2024-10-08PPAYITR1XXX-S2003042830'
    # identificativo_flusso = data + psp_info.id + '-S' + str(random.randint(1000000000, 9999999999))
    identificativo_univoco_regolamento = '49509-241007-39X-451585346538'
    # identificativo_univoco_regolamento = ''.join(random.choices(string.digits, k=28)) + 'IT'

    flusso = flusso.format(identificativo_flusso=identificativo_flusso,
                           data_ora_flusso=date_ora,
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

    with open('./bdd/steps/flusso_rendicontazione_2_dovuti.xml', 'w') as file:
        file.write(flusso)

    context.fdr = {
        'iuf': identificativo_flusso,
        'id_regolamento': identificativo_univoco_regolamento
    }


@when('il file della rendicontazione viene importato')
def step_import_fdr(context):
    # TODO invocazione workflow di ingestion FdR
    pass


@then('il flusso di rendicontazione è caricato e comprende i dovuti {label1} e {label2}')
def step_check_fdr(context, label1, label2):
    step_user_authentication(context, 'Amministratore Globale')
    token = context.token['Amministratore Globale']

    fdr = context.fdr
    # dovuto1 = context.dovuto_data[label1]
    dovuto1 = {
        'iuv': '01000000000209391',
        'iur': 'c9cccd0c26484fd1904e8baf1db2dfac',
        'importo': '10.00'
    }
    # dovuto2 = context.dovuto_data[label2]
    dovuto2 = {
        'iuv': '01000000000209390',
        'iur': 'd9cccd0c26484fd1904e8baf1db2dfac',
        'importo': '1.00'
    }

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
            print('yes')
        elif payment['codRpSilinviarpIdUnivocoVersamento'] == dovuto2['iuv']:
            assert payment['codEDatiPagDatiSingPagIdUnivocoRiscoss'] == dovuto2['iur']
            assert payment['numEDatiPagDatiSingPagSingoloImportoPagato'] == float(dovuto2['importo'])
            print('yes')
        else:
            assert False
