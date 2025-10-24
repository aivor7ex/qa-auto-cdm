import pytest
from collections.abc import Mapping, Sequence
from qa_constants import SERVICES

ENDPOINT = "/cluster/host-status"

HOST_STATUS_SCHEMA = {
    "type": "object",
    "properties": {
        "address": {"anyOf": [{"type": "string"}, {"type": "null"}]},
        "hostMode": {"type": "string"},
    },
    "required": ["address", "hostMode"],
}

PARAMS = [
    ({}, 200),
    ({"filter": '{"hostMode": "master"}'}, 200),
    ({"filter": '{"hostMode": "slave"}'}, 200),
    ({"filter": "{}"}, 200),
    ({"sort": "hostMode"}, 200),
    ({"order": "desc"}, 200),
    ({"limit": "10"}, 200),
    ({"offset": "5"}, 200),
    ({"page": "1"}, 200),
    ({"perPage": "50"}, 200),
    ({"q": "some_query"}, 200),
    ({"long_param": "a" * 1024}, 200),
    ({"param_with_spaces": "value with spaces"}, 200),
    ({"special_chars": "!@#$%^&*()_+-=[]{};':\",./<>?"}, 200),
    ({"unicode_param": "тест"}, 200),
    ({"numeric_param": 12345}, 200),
    ({"boolean_param": True}, 200),
    ({"null_param": None}, 200),
    ({"empty_param": ""}, 200),
    ({"very_long_value": "x" * 2048}, 200),
    ({"injection_attempt": "'; DROP TABLE users; --"}, 200),
    ({"another_injection": '{"$ne": null}'}, 200),
    ({"CaseSensitive": "Value"}, 200),
    ({"casesensitive": "value"}, 200),
    ({"_timestamp": 1678886400}, 200),
    ({"id-with-dash": "value"}, 200),
    ({"param.with.dot": "value"}, 200),
    ({"mix1": "string", "mix2": 123, "mix3": False}, 200),
    ({"p1": "a", "p2": "b", "p3": "c", "p4": "d"}, 200),
    ({"param1": "value1", "param2": "value2"}, 200),
    ({"filter[field]": "value"}, 200),
    ({"array[]": "item1"}, 200),
    ({"nested[param][sub]": "value"}, 200),
    ({"invalid_filter_json": "{"}, 200),
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

@pytest.mark.parametrize("params, expected_status", PARAMS)
def test_host_status_robustness(api_client, params, expected_status, attach_curl_on_fail):
    with attach_curl_on_fail(ENDPOINT, params, method="GET"):
        response = api_client.get(ENDPOINT, params=params)
        # Искусственно вызовем ошибку для проверки вывода cURL (убрать после проверки):
        # if params == {}:
        #     assert False, "Проверка вывода cURL"
        assert response.status_code == expected_status
        if response.status_code == 200:
            data = response.json()
            _check_types_recursive(data, HOST_STATUS_SCHEMA)
