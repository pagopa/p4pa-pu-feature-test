import random
import string
from datetime import datetime

from behave import given
from behave import then
from behave import when

from config.configuration import secrets

psp_info = secrets.payment_info.psp
ente_fiscal_code = secrets.ente.intermediato_2.fiscal_code


@given('la generazione del file contenente il flusso di rendicontazione del dovuto {label}')
def step_create_fdr_file(context, label):
    with open('./bdd/steps/file_template/flusso_rendicontazione.xml', 'r') as file:
        flusso = file.read()

    dovuto = context.dovuto_data[label]

    data = datetime.utcnow().strftime('%Y-%m-%d')
    date_ora = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S')
    identificativo_flusso = data + psp_info.id + '-S' + str(random.randint(1000000000, 9999999999))
    identificativo_univoco_regolamento = ''.join(random.choices(string.digits, k=28)) + 'IT'

    flusso = flusso.format(identificativo_flusso=identificativo_flusso,
                           data_ora_flusso=date_ora,
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


@when('il file della rendicontazione viene importato')
def step_import_fdr(context):
    # TODO invocazione workflow di ingestion FdR
    pass


@then('il flusso di rendicontazione è caricato')
def step_check_fdr(context):
    # TODO invocazione api BE che verifica il corretto caricamento a DB del file
    pass
