from enum import Enum

from behave import given

from api.auth import post_auth_token, post_external_auth_token
from bdd.steps.utils.utility import retrieve_org_id_by_ipa_code
from config.configuration import secrets
from model.workflow_hub import WorkflowType


class PagoPaInteractionModel(Enum):
    ACA = 'ACA'
    GPD = 'GPD'
    SYNC = 'SYNC'


@given("organization interacting with {pagopa_interaction}")
def get_token_org(context, pagopa_interaction):
    user_id = None
    org_info = None
    match pagopa_interaction:
        case PagoPaInteractionModel.ACA.value:
            user_id = secrets.user_info.admin_org_aca.user_id
            org_info = secrets.organization.aca
            org_info.workflow_type = WorkflowType.SYNC_ACA
            org_info.pagopa_interaction = PagoPaInteractionModel.ACA.value
        case PagoPaInteractionModel.GPD.value:
            user_id = secrets.user_info.admin_org_gpd.user_id
            org_info = secrets.organization.gpd
            org_info.workflow_type = WorkflowType.ASYNC_GPD
            org_info.pagopa_interaction = PagoPaInteractionModel.GPD.value

    res = post_auth_token(user_id=user_id)

    assert res.status_code == 200
    assert res.json()['access_token'] is not None

    organization_id = retrieve_org_id_by_ipa_code(token=res.json()['access_token'], ipa_code=org_info.ipa_code)
    org_info['id'] = organization_id

    context.org_info = org_info
    context.token = res.json()['access_token']


@given("a SIL acting on behalf of an organization interacting with {pagopa_interaction}")
def get_token_sil(context, pagopa_interaction: PagoPaInteractionModel):
    client = None
    org_info = None
    match pagopa_interaction:
        case PagoPaInteractionModel.ACA.value:
            client = secrets.send_info.aca
            org_info = secrets.organization.aca
        case PagoPaInteractionModel.GPD.value:
            client = secrets.send_info.gpd
            org_info = secrets.organization.gpd

    res = post_external_auth_token(client_id=client.client_id, client_secret=client.client_secret)

    assert res.status_code == 200
    assert res.json()['access_token'] is not None

    organization_id = retrieve_org_id_by_ipa_code(token=res.json()['access_token'], ipa_code=org_info.ipa_code)
    org_info['id'] = organization_id

    context.org_info = org_info
    context.token = res.json()['access_token']
