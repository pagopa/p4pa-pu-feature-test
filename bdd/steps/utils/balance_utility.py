import xmltodict
import execjs

from model.classification import AssessmentRegistry, Section


def extract_balance_from_xml(balance_xml: str) -> dict:
    return xmltodict.parse(balance_xml)


def extract_sections(balance_dict: dict) -> list:
    section = balance_dict['bilancio']['capitolo']
    if isinstance(section, list):
        return section
    return [section]


def extract_assessment_registry_from_section(section: dict) -> AssessmentRegistry:
    return AssessmentRegistry(section_code=section['codCapitolo'],
                              office_code=section.get('codUfficio'),
                              assessment_code=section['accertamento'].get('codAccertamento'))


def calculate_amount_from_section(section: dict, installment_amount: int) -> int:
    section_amount = section['accertamento']['importo']

    if section_amount is not None:
        section_amount = section_amount.strip()

        if section_amount.startswith('function'):
            js_extractor = JavaScriptExtractor(section_amount)
            return js_extractor.execute_calculate_amount(installment_amount)
        elif section_amount == 'TOTALE':
            return installment_amount
        else:
            return int(float(section_amount) * 100)
    else:
        raise ValueError("Section amount not found")

def build_section(section: dict, installment_amount: int) -> Section:
    return Section(
        amount_cents=calculate_amount_from_section(section=section, installment_amount=installment_amount),
        assessment_registry=extract_assessment_registry_from_section(section=section)
    )

class JavaScriptExtractor:
    def __init__(self, js_code):
        self.js_context = execjs.compile(js_code)

    def execute_calculate_amount(self, amount_value):
        try:
            result = self.js_context.call('calcola_importo', amount_value)
            return result
        except Exception as e:
            raise RuntimeError(f"Error in function JavaScript: {e}")
