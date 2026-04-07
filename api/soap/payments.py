import base64

import requests

from config.configuration import settings, secrets
from model.demand_payment_notice_cie import DemandPaymentNotice


def post_demand_payment_notice(token, demand_payment_notice: DemandPaymentNotice):
    with open('./api/soap/requests_template_payments/datiSpecificiServizio.xml', 'r') as file:
        dati_specifici_servizio_data = file.read()
    dati_specifici_servizio = dati_specifici_servizio_data.format(debt_position_type_org_code=demand_payment_notice.request_data.debt_position_type_org_code,
                                                                  cie_org_fiscal_code=demand_payment_notice.request_data.cie_org_fiscal_code,
                                                                  debtor_fiscal_code=demand_payment_notice.request_data.debtor_fiscal_code,
                                                                  debtor_full_name=demand_payment_notice.request_data.debtor_full_name)
    dati_specifici_servizio_base64 = base64.b64encode(dati_specifici_servizio.encode('utf-8')).decode('utf-8')

    with open('./api/soap/requests_template_payments/demandPaymentNotice.xml', 'r') as file:
        demand_payment_notice_data = file.read()
    data = demand_payment_notice_data.format(delegate_org_fiscal_code=demand_payment_notice.delegate_org_fiscal_code,
                                             broker_id=demand_payment_notice.broker_fiscal_code,
                                             station_id=demand_payment_notice.station_id,
                                             service_id=demand_payment_notice.service_id,
                                             service_subject_id=demand_payment_notice.service_subject_id,
                                             request_data=dati_specifici_servizio_base64
                                             )

    return requests.post(
        url=f'{secrets.internal_base_url}{settings.api.ingress_path.payments_node}',
        headers={
            'Content-Type': 'text/xml',
            'Authorization': f'Bearer {token}'
        },
        data=data,
        timeout=settings.default_timeout
    )
