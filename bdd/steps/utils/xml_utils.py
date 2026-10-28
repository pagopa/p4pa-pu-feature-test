import xml.etree.ElementTree as ET
from typing import Optional


def xml_elements_equal(
        xml_a: str,
        xml_b: str,
        xpath_a: Optional[str] = None,
        xpath_b: Optional[str] = None,
) -> bool:
    """
    Compare the children of two XML elements, ignoring the root tag name.

    xpath_a / xpath_b: optional ElementTree find() path to locate the element
    to compare within each document. If omitted, the document root is used.
    Namespace-agnostic matching is supported via '{*}' wildcards in the path.
    """
    element_a = _resolve_element(xml_a, xpath_a)
    element_b = _resolve_element(xml_b, xpath_b)

    children_a = sorted(element_a, key=lambda e: _local_name(e.tag))
    children_b = sorted(element_b, key=lambda e: _local_name(e.tag))

    canon_a = [ET.canonicalize(ET.tostring(c, encoding='unicode')) for c in children_a]
    canon_b = [ET.canonicalize(ET.tostring(c, encoding='unicode')) for c in children_b]

    return canon_a == canon_b


def _resolve_element(xml_str: str, xpath: Optional[str]) -> ET.Element:
    root = ET.fromstring(xml_str)
    if xpath is None:
        return root

    element = root.find(xpath)
    assert element is not None, f"Element not found for xpath '{xpath}'"
    return element


def _local_name(tag: str) -> str:
    return tag.split('}')[-1]
