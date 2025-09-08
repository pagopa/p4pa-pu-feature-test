import xmltodict
import execjs

from model.classification import AssessmentRegistry


def extract_balance_from_xml(balance_xml: str) -> dict:
    return xmltodict.parse(balance_xml)

def extract_assessment_registry_from_balance_dict(balance_dict: dict) -> AssessmentRegistry:
    capitolo = balance_dict['bilancio']['capitolo']

    return AssessmentRegistry(section_code=capitolo['codCapitolo'],
                              office_code=capitolo.get('codUfficio'),
                              assessment_code=capitolo['accertamento'].get('codAccertamento'))

def calculate_amount_from_balance(balance_dict: dict, installment_amount: int) -> int:
    balance_amount = balance_dict['bilancio']['capitolo']['accertamento']['importo']

    if balance_amount is not None:
        balance_amount = balance_amount.strip()

        if balance_amount.startswith('function'):
            js_extractor = JavaScriptExtractor(balance_amount)
            amount_calculated = js_extractor.execute_calculate_amount(installment_amount)
            return amount_calculated
        elif balance_amount == 'TOTALE':
            return installment_amount
        else:
            return int(float(balance_amount) * 100)
    else:
        raise ValueError("Balance amount not found")


class JavaScriptExtractor:
    def __init__(self, js_code):
        self.js_context = execjs.compile(js_code)

    def execute_calculate_amount(self, amount_value):
        try:
            result = self.js_context.call('calcola_importo', amount_value)
            return result
        except Exception as e:
            raise RuntimeError(f"Error in function JavaScript: {e}")
