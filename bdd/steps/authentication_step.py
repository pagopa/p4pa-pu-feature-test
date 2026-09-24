from enum import Enum

from behave import given

from api.auth import post_auth_token, post_external_auth_token
from bdd.steps.utils.assertions import assert_response_ok
from bdd.steps.utils.utility import retrieve_org_id_by_ipa_code
from config.configuration import secrets
from model.workflow_hub import WorkflowType


class PagoPaInteractionModel(Enum):
    ACA = 'ACA'
    GPD = 'GPD'
    SYNC = 'SYNC'


_ORG_INFO_BY_INTERACTION = {
    PagoPaInteractionModel.ACA: secrets.organization.aca,
    PagoPaInteractionModel.GPD: secrets.organization.gpd,
}

_WORKFLOW_TYPE_BY_INTERACTION = {
    PagoPaInteractionModel.ACA: WorkflowType.SYNC_ACA,
    PagoPaInteractionModel.GPD: WorkflowType.ASYNC_GPD,
}

_USER_ID_BY_INTERACTION = {
    PagoPaInteractionModel.ACA: secrets.user_info.admin_org_aca.user_id,
    PagoPaInteractionModel.GPD: secrets.user_info.admin_org_gpd.user_id,
}

_SIL_CLIENT_BY_INTERACTION = {
    PagoPaInteractionModel.ACA: secrets.send_info.aca,
    PagoPaInteractionModel.GPD: secrets.send_info.gpd,
}

_INTERACTION_BY_ORG_NAME = {
    'Ente Locale': PagoPaInteractionModel.ACA,
    'Ente P4PA': PagoPaInteractionModel.GPD,
}


def _resolve_org_info(interaction: PagoPaInteractionModel) -> dict:
    if interaction not in _ORG_INFO_BY_INTERACTION:
        raise ValueError(f"Unsupported PagoPA interaction: '{interaction.value}'")

    org_info = _ORG_INFO_BY_INTERACTION[interaction]
    org_info.workflow_type = _WORKFLOW_TYPE_BY_INTERACTION[interaction]
    org_info.pagopa_interaction = interaction.value
    return org_info


def _enrich_org_info_with_id(context, org_info: dict, token: str) -> dict:
    organization_id = retrieve_org_id_by_ipa_code(
        token=token,
        traceparent=context.traceparent,
        ipa_code=org_info.ipa_code,
    )
    org_info['id'] = organization_id
    return org_info


def get_org_token(context, pagopa_interaction) -> tuple[dict, str]:
    """Authenticates as an organization user and returns (org_info, token) without touching context."""

    interaction = PagoPaInteractionModel(pagopa_interaction)
    org_info = _resolve_org_info(interaction)
    user_id = _USER_ID_BY_INTERACTION[interaction]

    res = post_auth_token(user_id=user_id, traceparent=context.traceparent)
    assert_response_ok(res, "Post auth token")
    token = res.json()['access_token']
    assert token is not None, "Access token is missing from the auth response"

    org_info = _enrich_org_info_with_id(context, org_info, token)
    return org_info, token


def get_sil_org_token(context, pagopa_interaction) -> tuple[dict, str]:
    """Authenticates as SIL on behalf of an organization and returns (org_info, token) without touching context."""

    interaction = PagoPaInteractionModel(pagopa_interaction)
    org_info = _resolve_org_info(interaction)
    client = _SIL_CLIENT_BY_INTERACTION[interaction]

    res = post_external_auth_token(
        client_id=client.client_id,
        client_secret=client.client_secret,
        traceparent=context.traceparent,
    )
    assert_response_ok(res, "Post client auth token")
    token = res.json()['access_token']
    assert token is not None, "Access token is missing from the auth response"

    org_info = _enrich_org_info_with_id(context, org_info, token)
    return org_info, token


def get_org_token_by_name(context, org_name: str) -> tuple[dict, str]:
    if org_name not in _INTERACTION_BY_ORG_NAME:
        raise ValueError(f"Unknown organization name: '{org_name}'")

    interaction = _INTERACTION_BY_ORG_NAME[org_name]
    return get_org_token(context, interaction.value)


@given("organization interacting with {pagopa_interaction}")
def step_get_token_org(context, pagopa_interaction):
    org_info, token = get_org_token(context, pagopa_interaction)
    context.org_info = org_info
    context.token = token


@given("a SIL acting on behalf of an organization interacting with {pagopa_interaction}")
def step_get_token_sil(context, pagopa_interaction):
    org_info, token = get_sil_org_token(context, pagopa_interaction)
    context.org_info = org_info
    context.token = token