from bdd.steps.enti_step import step_check_ente_status
from bdd.steps.enti_step import step_insert_ente
from config.configuration import secrets
from config.configuration import settings

fiscal_code_ente = secrets.ente.fiscal_code
status_ente = settings.ente.status


def insert_new_ente(context, label: str):
    ente_data = settings.ente_data[label]

    label = label.replace('ente', '')
    ente_data['fiscal_code'] = fiscal_code_ente.get(label)
    context.ente_data = {label: ente_data}

    step_insert_ente(context=context, user='Amministratore Globale', label=label)
    step_check_ente_status(context=context, label=label, status=status_ente.inserito)
