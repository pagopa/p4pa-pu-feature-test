from enum import Enum

from behave import given

from api.auth import post_auth_token
from config.configuration import secrets
from model.workflow_hub import WorkflowType
from util.utility import get_user_id


class PagoPaInteractionModel(Enum):
    ACA = 'ACA'
    GPD = 'GPD'
    SYNC = 'SYNC'


@given("organization interacting with {pagopa_interaction}")
def get_token_org(context, pagopa_interaction):
    user = None
    org_info = None
    match pagopa_interaction:
        case PagoPaInteractionModel.ACA.value:
            user = 'Admin org ACA'
            org_info = secrets.organization.aca
            org_info.workflow_type = WorkflowType.SYNC_ACA
        case PagoPaInteractionModel.GPD.value:
            user = 'Admin org GPD'
            org_info = secrets.organization.gpd
            org_info.workflow_type = WorkflowType.ASYNC_GPD

    res = post_auth_token(get_user_id(user))
    assert res.status_code == 200
    assert res.json()['access_token'] is not None

    context.token = res.json()['access_token']
    context.org_info = org_info
