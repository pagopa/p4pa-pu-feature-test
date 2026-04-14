from dataclasses import dataclass
from datetime import datetime, timezone

import requests

from config.configuration import settings


@dataclass
class PSP:
    id: str
    id_broker: str
    id_channel: str
    password: str


def verify_payment_notice(psp: PSP,
                          org_fiscal_code: str,
                          nav: str):
    with open('./api/soap/requests_template_nodo/verifyPaymentNotice.xml', 'r') as file:
        data = file.read()
    data = data.format(psp_id=psp.id, psp_id_broker=psp.id_broker, psp_id_channel=psp.id_channel,
                       psp_password=psp.password, org_fiscal_code=org_fiscal_code, nav=nav)

    return requests.post(
        url=f'{settings.api.base_path.nodo_psp}',
        headers={
            'Content-Type': 'text/xml',
            settings.SOAP_ACTION_HEADER: 'verifyPaymentNotice'
        },
        verify=False,
        data=data,
        timeout=settings.default_timeout
    )


def activate_payment_notice(psp: PSP,
                            org_fiscal_code: str,
                            nav: str,
                            amount: str,
                            due_date: str):
    with open('./api/soap/requests_template_nodo/activatePaymentNoticeV2.xml', 'r') as file:
        data = file.read()
    data = data.format(psp_id=psp.id, psp_id_broker=psp.id_broker, psp_id_channel=psp.id_channel,
                       psp_password=psp.password, org_fiscal_code=org_fiscal_code, nav=nav,
                       amount=amount, due_date=due_date)
    print(data)
    return requests.post(
        url=f'{settings.api.base_path.nodo_psp}',
        headers={
            'Content-Type': 'text/xml',
            settings.SOAP_ACTION_HEADER: 'activatePaymentNoticeV2'
        },
        verify=False,
        data=data,
        timeout=settings.default_timeout
    )


def send_payment_outcome(psp: PSP,
                         payment_token: str,
                         citizen_fiscal_code: str,
                         citizen_name: str,
                         citizen_email: str):
    with open('./api/soap/requests_template_nodo/sendPaymentOutcomeV2.xml', 'r') as file:
        data = file.read()
    data = data.format(psp_id=psp.id, psp_id_broker=psp.id_broker, psp_id_channel=psp.id_channel,
                       psp_password=psp.password, payment_token=payment_token, citizen_fiscal_code=citizen_fiscal_code,
                       citizen_name=citizen_name, citizen_email=citizen_email,
                       current_date=datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    print(data)
    return requests.post(
        url=f'{settings.api.base_path.nodo_psp}',
        headers={
            'Content-Type': 'text/xml',
            settings.SOAP_ACTION_HEADER: 'sendPaymentOutcomeV2'
        },
        verify=False,
        data=data,
        timeout=settings.default_timeout
    )
