# -- FILE: features/environment.py
from bdd.steps.utils import utility

def before_scenario(context, scenario):
    context.traceparent = utility.generate_traceparent()
    print(f"""\n---------------------------------------------------------------------------------
           \n[TRACE_PARENT] Scenario {scenario.name} with trace parent: {context.traceparent}""")