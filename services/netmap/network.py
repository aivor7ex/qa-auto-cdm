import pytest
from collections.abc import Mapping, Sequence
from services.qa_constants import SERVICES

ENDPOINT = "/network"
SERVICE = SERVICES["netmap"]
PORT = SERVICE["port"]
BASE_PATH = SERVICE["base_path"]

NETWORK_SCHEMA = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "id": {"type": "string"},
            "network": {"type": "string", "format": "ipv4-network"},
            "gw": {"type": "string", "format": "ipv4"}
        },
        "required": ["id", "network", "gw"]
    }
}

test_cases = [
    ({}, 200),
    ({"limit": 1}, 422),
    ({"limit": 50}, 422),
    ({"offset": 0}, 422),
    ({"offset": 10}, 422),
    ({"sort": "id"}, 422),
    ({"sort": "-id"}, 422),
    ({"sort": "network"}, 422),
    ({"sort": "-network"}, 422),
    ({"sort": "gw"}, 422),
    ({"sort": "-gw"}, 422),
    ({"filter": 'id=="some_id"'}, 422),
    ({"filter": 'network=="192.168.1.0/24"'}, 422),
    ({"filter": 'gw=="192.168.1.1"'}, 422),
    ({"limit": 5, "offset": 2, "sort": "-id"}, 422),
    ({"limit": 10, "filter": 'network=="10.0.0.0/8"'}, 422),
    ({"sort": "-gw", "filter": 'up==true'}, 422),
    ({"offset": 20, "sort": "id", "limit": 20}, 422),
    ({"filter": 'hostname.contains("server")'}, 422),
    ({"limit": 999}, 422),
    ({"limit": -1}, 422),
    ({"limit": "abc"}, 422),
    ({"limit": 1001}, 422),
    ({"offset": -1}, 422),
    ({"offset": "abc"}, 422),
    ({"sort": "unknown_field"}, 422),
    ({"sort": ""}, 422),
    ({"filter": "invalid-query"}, 422),
    ({"filter": 'id=='}, 422),
    ({"filter": 'network=="not-a-network"'}, 422),
    ({"filter": 'gw=="not-an-ip"'}, 422),
    ({"unsupported_param": "value"}, 422),
    ({"sort": "id,-network"}, 422),
    ({"filter": 'id=="a",network=="b"'}, 422),
    ({"random_param": "random_value"}, 422),
]

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


@pytest.fixture(scope="module")
def netmap_api_client(api_client):
    return api_client

@pytest.mark.parametrize("params, expected_status", test_cases)
def test_network_api(api_client, params, expected_status, attach_curl_on_fail):
    with attach_curl_on_fail(ENDPOINT, payload=params, method="GET"):
        response = api_client.get(ENDPOINT, params=params)
        assert response.status_code == expected_status
        if response.status_code == 200:
            response_data = response.json()
            _check_types_recursive(response_data, NETWORK_SCHEMA)
