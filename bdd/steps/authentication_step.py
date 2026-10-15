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


_WORKFLOW_TYPE_BY_INTERACTION = {
    PagoPaInteractionModel.ACA: WorkflowType.SYNC_ACA,
    PagoPaInteractionModel.GPD: WorkflowType.ASYNC_GPD,
}

_INTERACTION_BY_ORG_NAME = {
    'Ente Locale': PagoPaInteractionModel.ACA,
    'Ente P4PA': PagoPaInteractionModel.GPD,
}


def _resolve_org_info(interaction: PagoPaInteractionModel, print_notice_enabled: bool = False) -> dict:
    """Finds in secrets the organization with the given PagoPA interaction. It:

    - if print notice is required, selects the organization having print notice enabled;
    - otherwise, when more organizations match, prefers the one without print notice enabled,
      so the same organization can be used for both cases in environments where only one is configured.
    """
    matches = [org for org in secrets.organization.values() if org.pagopa_interaction == interaction.value]

    if print_notice_enabled:
        matches = [org for org in matches if org.print_notice_enabled == True]
    elif len(matches) > 1:
        matches = [org for org in matches if org.print_notice_enabled != True]

    assert len(matches) == 1, \
        f"Expected one organization interacting with '{interaction.value}'" \
        f"{' having print notice enabled' if print_notice_enabled else ''}, found {len(matches)}"

    org_info = matches[0]
    org_info.workflow_type = _WORKFLOW_TYPE_BY_INTERACTION[interaction]
    return org_info


def _enrich_org_info_with_id(context, org_info: dict, token: str) -> dict:
    org_info['id'] = retrieve_org_id_by_ipa_code(token=token, traceparent=context.traceparent,
                                                 ipa_code=org_info.ipa_code)
    return org_info


def get_access_token(res, description: str) -> str:
    assert_response_ok(res, description)
    token = res.json()['access_token']
    assert token is not None, "Access token is missing from the auth response"
    return token


def get_org_token(context, pagopa_interaction, print_notice_enabled: bool = False) -> tuple[dict, str]:
    """Authenticates as an organization user and returns (org_info, token) without touching context."""
    org_info = _resolve_org_info(PagoPaInteractionModel(pagopa_interaction), print_notice_enabled)

    res = post_auth_token(user_id=org_info.admin_user_id, traceparent=context.traceparent)
    token = get_access_token(res, "Post auth token")

    return _enrich_org_info_with_id(context, org_info, token), token


def get_sil_org_token(context, pagopa_interaction, print_notice_enabled: bool = False) -> tuple[dict, str]:
    """Authenticates as SIL on behalf of an organization and returns (org_info, token) without touching context."""
    org_info = _resolve_org_info(PagoPaInteractionModel(pagopa_interaction), print_notice_enabled)
    assert 'sil_client' in org_info, f"Organization '{org_info.name}' has no SIL client configured"

    res = post_external_auth_token(client_id=org_info.sil_client.client_id,
                                   client_secret=org_info.sil_client.client_secret,
                                   traceparent=context.traceparent)
    token = get_access_token(res, "Post client auth token")

    return _enrich_org_info_with_id(context, org_info, token), token


def get_send_token(org_info, traceparent: str) -> str:
    """Authenticates on SEND with the client of the organization and returns the access token."""
    res = post_external_auth_token(client_id=org_info.send_client.client_id,
                                   client_secret=org_info.send_client.client_secret,
                                   traceparent=traceparent)

    return get_access_token(res, "Post external auth token")


def get_org_token_by_name(context, org_name: str) -> tuple[dict, str]:
    if org_name not in _INTERACTION_BY_ORG_NAME:
        raise ValueError(f"Unknown organization name: '{org_name}'")

    return get_org_token(context, _INTERACTION_BY_ORG_NAME[org_name].value)


@given("organization having print notice enabled interacting with {pagopa_interaction}")
def step_get_token_org_print_notice(context, pagopa_interaction):
    context.org_info, context.token = get_org_token(context, pagopa_interaction, print_notice_enabled=True)


@given("organization interacting with {pagopa_interaction}")
def step_get_token_org(context, pagopa_interaction):
    context.org_info, context.token = get_org_token(context, pagopa_interaction)


@given("a SIL acting on behalf of an organization having print notice enabled interacting with {pagopa_interaction}")
def step_get_token_sil_print_notice(context, pagopa_interaction):
    context.org_info, context.token = get_sil_org_token(context, pagopa_interaction, print_notice_enabled=True)


@given("a SIL acting on behalf of an organization interacting with {pagopa_interaction}")
def step_get_token_sil(context, pagopa_interaction):
    context.org_info, context.token = get_sil_org_token(context, pagopa_interaction)