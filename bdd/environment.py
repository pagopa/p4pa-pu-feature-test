from bdd.steps.utility_step import insert_new_ente
from config.configuration import settings


def before_feature(context, feature):
    context.ente_data = {}

    for ente_name in feature.tags:
        if ente_name in settings.ente_data:
            insert_new_ente(context=context, label=ente_name)
