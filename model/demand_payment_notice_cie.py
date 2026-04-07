from dataclasses import dataclass

from dataclasses_json import dataclass_json, LetterCase

@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class RequestData:
    debt_position_type_org_code: str
    cie_org_fiscal_code: str
    debtor_fiscal_code: str
    debtor_full_name: str

@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class DemandPaymentNotice:
    delegate_org_fiscal_code: str
    broker_fiscal_code: str
    service_id: str
    station_id: str
    service_subject_id: str
    request_data: RequestData

