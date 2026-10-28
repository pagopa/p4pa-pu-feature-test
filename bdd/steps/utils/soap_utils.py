import xmltodict


def _child_by_local_name(mapping, local_name):
    """Return the child whose tag matches `local_name`, ignoring any namespace prefix
    (so 'ns3:Foo', 'soap:Foo' and 'Foo' all match 'Foo'). Attribute/text keys are skipped."""
    for key, value in mapping.items():
        if key[:1] in ('@', '#'):
            continue
        if key.split(':')[-1] == local_name:
            return value
    raise KeyError(f"No element with local name '{local_name}' in SOAP response")


def extract_soap_body(response_content, tag_name):
    """Parse a SOAP response and return the body element identified by `tag_name`
    (the local response tag, without any namespace prefix). Navigation is namespace-prefix
    agnostic, so a change of prefix (e.g. 'ns3' -> 'ns4', 'soapenv' -> 'soap') does not
    break parsing."""
    res_parsed = xmltodict.parse(response_content.decode('utf-8'))
    envelope = _child_by_local_name(res_parsed, 'Envelope')
    body = _child_by_local_name(envelope, 'Body')
    return _child_by_local_name(body, tag_name)


def check_res_ok_and_get_body(response_content, tag_name):
    res_body = extract_soap_body(response_content, tag_name)
    assert res_body.get('fault') is None, f"SIL {tag_name} returned a fault: {res_body.get('fault')}"
    return res_body
