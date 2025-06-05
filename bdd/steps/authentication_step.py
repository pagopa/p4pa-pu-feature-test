from enum import Enum

from behave import given

from api.auth import post_auth_token
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

    context.token = res.json()['access_token']
    context.org_info = org_info
