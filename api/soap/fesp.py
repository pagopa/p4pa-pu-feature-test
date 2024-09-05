from datetime import datetime, timezone

import requests

from config.configuration import settings
from config.configuration import secrets


def pa_get_payment_v2(ente_fiscal_code: str, broker_fiscal_code: str, broker_station_id: str, iuv: str):
    with open('./api/soap/requests_template/paGetPaymentV2.xml', 'r') as file:
        data = file.read()
    data = data.format(ente_fiscal_code=ente_fiscal_code,
                       broker_fiscal_code=broker_fiscal_code,
                       broker_station_id=broker_station_id,
                       iuv=iuv)

    return requests.post(
        url=f'{secrets.internal_base_url}/payhub/ws/fesp/PagamentiTelematiciCCP36',
        headers={
            'Content-Type': 'text/xml',
            settings.SOAP_ACTION_HEADER: 'paGetPaymentV2'
        },
        data=data,
        timeout=settings.default_timeout
    )


def pa_send_rt_v2(body: dict):
    with open('./api/soap/requests_template/paSendRTV2.xml', 'r') as file:
        data = file.read()
    data = data.format(ente_fiscal_code=body.get('ente_fiscal_code'),
                       ente_name=body.get('ente_name'),
                       broker_fiscal_code=body.get('broker_fiscal_code'),
                       broker_station_id=body.get('broker_station_id'),
                       receipt_id=body.get('receipt_id'),
                       iuv=body.get('iuv'),
                       amount=body.get('amount'),
                       citizen_fiscal_code=body.get('citizen_fiscal_code'),
                       citizen_name=body.get('citizen_name'),
                       citizen_email=body.get('citizen_email'),
                       current_datetime=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
                       current_date=datetime.now(timezone.utc).strftime("%Y-%m-%d")
                       )

    return requests.post(
        url=f'{secrets.internal_base_url}/payhub/ws/fesp/PagamentiTelematiciCCP36',
        headers={
            'Content-Type': 'text/xml',
            settings.SOAP_ACTION_HEADER: 'paSendRTV2'
        },
        data=data,
        timeout=settings.default_timeout
    )
