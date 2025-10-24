import pytest
import json
from collections.abc import Mapping, Sequence
from services.qa_constants import SERVICES

ENDPOINT = "/parse-value"
SERVICE = SERVICES["objects"]
PORT = SERVICE["port"]
BASE_PATH = SERVICE["base_path"]

# Схема оставлена для справки, но не используется в тестах, так как успешных кейсов нет
IPV4_SCHEMA = {"type": "string"}
IPV6_SCHEMA = {"type": "string"}

def _check_types_recursive(obj, schema):
    if "anyOf" in schema:
        assert any(_try_type(obj, s) for s in schema["anyOf"]), f"Тип {type(obj)} не соответствует anyOf"
        return
    if schema.get("type") == "object":
        assert isinstance(obj, Mapping), f"Ожидался объект, получено: {type(obj)}"
        for key, prop in schema.get("properties", {}).items():
            if key in obj:
                _check_types_recursive(obj[key], prop)
        for req in schema.get("required", []):
            assert req in obj, f"Обязательное поле '{req}' отсутствует"
    elif schema.get("type") == "array":
        assert isinstance(obj, Sequence) and not isinstance(obj, str), f"Ожидался список, получено: {type(obj)}"
        for item in obj:
            _check_types_recursive(item, schema["items"])
    else:
        if schema.get("type") == "string":
            assert isinstance(obj, str)
        elif schema.get("type") == "integer":
            assert isinstance(obj, int)
        elif schema.get("type") == "boolean":
            assert isinstance(obj, bool)
        elif schema.get("type") == "null":
            assert obj is None

def _try_type(obj, schema):
    try:
        _check_types_recursive(obj, schema)
        return True
    except AssertionError:
        return False

# Параметры для проверки (валидные и невалидные)
PARSE_VALUE_PARAMS = [
    pytest.param({"type": "ip", "source": "1.1.1.1"}, id="ip-class-a-public"),
    pytest.param({"type": "ip", "source": "192.168.1.1"}, id="ip-class-c-private"),
    pytest.param({"type": "ip", "source": "8.8.8.8"}, id="ip-google-dns"),
    pytest.param({"type": "ip", "source": "0.0.0.0"}, id="ip-unspecified"),
    pytest.param({"type": "ip", "source": "255.255.255.255"}, id="ip-broadcast"),
    pytest.param({"type": "ip", "source": "127.0.0.1"}, id="ip-loopback"),
    pytest.param({"type": "ip", "source": "10.0.0.1"}, id="ip-class-a-private"),
    pytest.param({"type": "ip", "source": "172.16.0.1"}, id="ip-class-b-private"),
    pytest.param({"type": "ip", "source": "100.64.0.1"}, id="ip-carrier-grade-nat"),
    pytest.param({"type": "ip", "source": "192.0.2.1"}, id="ip-test-net-1"),
    pytest.param({"type": "ip", "source": "198.51.100.255"}, id="ip-test-net-2"),
    pytest.param({"type": "ip", "source": "203.0.113.123"}, id="ip-test-net-3"),
    pytest.param({"type": "ip", "source": "224.0.0.1"}, id="ip-multicast"),
    pytest.param({"type": "ip", "source": "169.254.0.1"}, id="ip-link-local"),
    pytest.param({"type": "ip", "source": "1.2.3.4"}, id="ip-simple-a"),
    pytest.param({"type": "ip", "source": "130.88.203.1"}, id="ip-simple-b"),
    pytest.param({"type": "ip", "source": "200.100.50.25"}, id="ip-simple-c"),
    pytest.param({"type": "ip", "source": "240.0.0.1"}, id="ip-class-e-reserved"),
    pytest.param({"type": "ipv6", "source": "::1"}, id="ipv6-loopback"),
    pytest.param({"type": "ipv6", "source": "2001:db8:85a3::8a2e:370:7334"}, id="ipv6-long-compressed"),
    pytest.param({"type": "ipv6", "source": "fe80::1ff:fe23:4567:890a"}, id="ipv6-link-local"),
    pytest.param({"type": "ipv6", "source": "fd12:3456:789a:1::1"}, id="ipv6-ula"),
    pytest.param({"type": "ipv6", "source": "::ffff:192.0.2.128"}, id="ipv6-v4-mapped"),
    pytest.param({"type": "ipv6", "source": "2001:0db8:85a3:0000:0000:8a2e:0370:7334"}, id="ipv6-uncompressed"),
    pytest.param({"type": "ipv6", "source": "2001:db8::1"}, id="ipv6-double-colon-end"),
    pytest.param({"type": "ipv6", "source": "::2:3:4"}, id="ipv6-double-colon-start"),
    pytest.param({"type": "ipv6", "source": "2001:db8:1::2:3:4"}, id="ipv6-double-colon-middle"),
    pytest.param({"type": "ipv6", "source": "::"}, id="ipv6-unspecified"),
    pytest.param({"type": "ipv6", "source": "::ffff:0:0"}, id="ipv6-v4-mapped-unspecified"),
    pytest.param({"type": "ipv6", "source": "64:ff9b::"}, id="ipv6-well-known-prefix-nat64"),
    pytest.param({"type": "ipv6", "source": "100::"}, id="ipv6-discard-prefix"),
    pytest.param({"type": "ipv6", "source": "2001:db8::"}, id="ipv6-documentation-prefix"),
    pytest.param({"type": "ipv6", "source": "2002:c0a8:101::"}, id="ipv6-6to4-prefix"),
    pytest.param({"type": "ipv6", "source": "2606:2800:220:1:248:1893:25c8:1946"}, id="ipv6-example-com"),
    pytest.param({"type": "ipv6", "source": "2001:4860:4860::8888"}, id="ipv6-google-dns"),
]


@pytest.mark.parametrize("payload", PARSE_VALUE_PARAMS)
def test_parse_value_always_error(api_client, payload, attach_curl_on_fail):
    params = {"q": json.dumps(payload, separators=(',', ':'))}
    with attach_curl_on_fail(ENDPOINT, params, method="GET"):
        response = api_client.get(ENDPOINT, params=params)
        assert response.status_code in (400, 404), f"Тест с payload={payload} упал. Ожидается статус 400 или 404, получен {response.status_code}"
