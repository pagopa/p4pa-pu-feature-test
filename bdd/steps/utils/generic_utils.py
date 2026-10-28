from secrets import token_hex

from api.organization import get_org_by_ipa_code
from api.workflow_hub import get_workflow_status
from bdd.steps.utils.assertions import assert_response_ok
from model.workflow_hub import WorkflowType


def get_workflow_id(workflow_type: WorkflowType, entity_id: int) -> str:
    return workflow_type.value + "-" + str(entity_id)


def get_workflow_run_id(token, traceparent: str, workflow_type: WorkflowType, entity_id) -> str:
    res = get_workflow_status(token=token, traceparent=traceparent,
                              workflow_id=get_workflow_id(workflow_type=workflow_type, entity_id=entity_id))
    assert_response_ok(res, "Get workflow status")
    return res.json()['runId']


def retrieve_org_id_by_ipa_code(token: str, traceparent: str, ipa_code: str) -> int:
    res_org = get_org_by_ipa_code(token=token, traceparent=traceparent, ipa_code=ipa_code)

    assert_response_ok(res_org, "Get organization by IPA code")
    organization_id = res_org.json()['organizationId']
    assert organization_id is not None, \
        f"\nNo organization found with IPA code {ipa_code}\n"

    return organization_id


def generate_traceparent():
    trace_id = token_hex(16)
    span_id = token_hex(8)
    flags = "01"  # means sampled trace

    return f"00-{trace_id}-{span_id}-{flags}"
