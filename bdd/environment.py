# -- FILE: features/environment.py
import steps.utils.utility
from bdd.steps.utils import utility

def before_scenario(context, scenario):
    context.traceparent = utility.generate_traceparent()
    print(f"[TRACE_PARENT] Scenario {scenario.name} with trace parent: {context.traceparent}")