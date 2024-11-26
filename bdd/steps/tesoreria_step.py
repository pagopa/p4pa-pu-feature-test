import random
import string
from dataclasses import dataclass
from datetime import datetime

from behave import given
from behave import then
from behave import when

from api.tesoreria import get_tesoreria_by_iuf
from bdd.steps.authentication_step import step_user_authentication
from config.configuration import secrets

ente_id = secrets.ente.intermediato_2.id


@dataclass
class EnteBT:
    codice_abi_BT: str
    codice_ente: str
    descrizione_ente: str
    codice_istat_ente: str
    codice_fiscale_ente: str
    codice_tramite_ente: str
    codice_tramite_BT: str
    codice_ente_BT: str


ente_BT = EnteBT(codice_abi_BT='01234', codice_ente='XX77XX', descrizione_ente=secrets.ente.intermediato_2.name.upper(),
                 codice_istat_ente='000123456', codice_fiscale_ente=secrets.ente.intermediato_2.fiscal_code,
                 codice_tramite_ente='A2A-12345678', codice_tramite_BT='A2A-01234567', codice_ente_BT='1010345')


@given('la generazione del file di tesoreria correlato alla rendicontazione')
def step_create_file_tesoreria(context):
    with open('./bdd/steps/file_template/flusso_tesoreria_opi_con_iuf.xml', 'r') as file:
        tesoreria = file.read()

    # fdr = context.fdr
    fdr = {
        'iuf': 'iuf',
        'importo': '10.00'
    }

    data = datetime.utcnow().strftime('%Y-%m-%d')
    data_ora = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S')
    identificativo_flusso_bt = 'GDC-' + ''.join(random.choices(string.digits, k=36)) + '#001#001'
    anno_esercizio = str(datetime.utcnow().year)
    numero_bolletta = ''.join(random.choices(string.digits, k=7))
    anagrafica = 'DEBITORE ' + str(random.randint(111, 999))
    causale = f'ACCREDITO INCASSI {anagrafica}/PUR/LGPE-RIVERSAMENTO/URI/{fdr["iuf"]}'

    tesoreria = tesoreria.format(cod_abi_BT=ente_BT.codice_abi_BT,
                                 data_ora_flusso=data_ora,
                                 cod_ente=ente_BT.codice_ente,
                                 desc_ente=ente_BT.descrizione_ente,
                                 cod_istat_ente=ente_BT.codice_istat_ente,
                                 cod_fiscale_ente=ente_BT.codice_fiscale_ente,
                                 cod_tramite_ente=ente_BT.codice_tramite_ente,
                                 cod_tramite_BT=ente_BT.codice_tramite_BT,
                                 cod_ente_BT=ente_BT.codice_ente_BT,
                                 identificativo_flusso_BT=identificativo_flusso_bt,
                                 anno_esercizio=anno_esercizio,
                                 data_riferimento_GdC=data,
                                 identificativo_flusso_conto=''.join(random.choices(string.digits, k=17)),
                                 numero_movimento_conto=''.join(random.choices(string.digits, k=7)),
                                 numero_documento=''.join(random.choices(string.digits, k=7)),
                                 data_effettiva_sospeso=data,
                                 progressivo_documento=''.join(random.choices(string.digits, k=7)),
                                 importo=fdr['importo'],
                                 numero_bolletta_quietanza=numero_bolletta,
                                 data_movimento=data,
                                 data_movimento_siope=data,
                                 data_valuta_ente=data,
                                 anagrafica_cliente=anagrafica,
                                 causale=causale)

    with open('./bdd/steps/flusso_tesoreria_opi_con_iuf.xml', 'w') as file:
        file.write(tesoreria)

    context.tesoreria = {
        'iuf': fdr['iuf'],
        'importo': fdr['importo'],
        'numero_bolletta': numero_bolletta,
        'anno_bolletta': anno_esercizio
    }


@when('il file della tesoreria viene importato')
def step_import_tesoreria(context):
    # TODO invocazione workflow di ingestion Tesoreria
    pass


@then('il flusso di tesoreria è caricato con lo IUF della rendicontazione')
def step_check_tesoreria_with_iuf(context):
    step_user_authentication(context, 'Amministratore Globale')
    token = context.token['Amministratore Globale']

    tesoreria = context.tesoreria

    res = get_tesoreria_by_iuf(token=token, ente_id=ente_id, iuf=tesoreria['iuf'])

    assert res.status_code == 200
    assert res.json()['list'] != []
    assert len(res.json()['list']) == 1

    tesoreria_info = res.json()['list'][0]
    assert tesoreria_info['idRendicontazione'] == tesoreria['iuf']
    assert tesoreria_info['importoTesoreria'] == float(tesoreria['importo'])
    assert tesoreria_info['codBolletta'] == tesoreria['numero_bolletta']
    assert tesoreria_info['annoBolletta'] == tesoreria['anno_bolletta']
