from bdd.steps.utils import generic_utils

def before_scenario(context, scenario):
    context.traceparent = generic_utils.generate_traceparent()
    context.debt_positions = {}
    context.payment_reporting_flows = {}
    context.installments_paid_by_id = {}
    print(f"""\n---------------------------------------------------------------------------------
           \n[TRACE_PARENT] {context.traceparent}""")