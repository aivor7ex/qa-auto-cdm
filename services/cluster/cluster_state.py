import pytest
from collections.abc import Mapping, Sequence
from qa_constants import SERVICES

ENDPOINT = "/cluster/state"

CLUSTER_STATE_SCHEMA = {
    "type": "object",
    "properties": {
        "applying": {"type": "boolean"},
        "revision": {"type": "string", "pattern": r"^(?:[a-f0-9]{40}|\?)$"},
        "dirty": {"type": "boolean"},
    },
    "required": ["applying", "revision", "dirty"],
}

PARAMS = [
    ({}, 200),
    ({"filter": '{"applying": true}'}, 200),
    ({"filter": '{"dirty": false}'}, 200),
    ({"filter": "{}"}, 200),
    ({"sort": "revision"}, 200),
    ({"order": "asc"}, 200),
    ({"limit": "20"}, 200),
    ({"offset": "10"}, 200),
    ({"page": "2"}, 200),
    ({"perPage": "100"}, 200),
    ({"q": "search_term"}, 200),
    ({"long_param": "b" * 1024}, 200),
    ({"param with space": "value with space"}, 200),
    ({"special-chars": "!@#$%^&*()_+-=[]{};':\",./<>?"}, 200),
    ({"unicode_param": "тестовый_запрос"}, 200),
    ({"numeric_param": 54321}, 200),
    ({"boolean_param": False}, 200),
    ({"null_param": None}, 200),
    ({"empty_param": ""}, 200),
    ({"very_long_value": "y" * 2048}, 200),
    ({"injection": '{"$gt": ""}'}, 200),
    ({"another_injection": "UNION SELECT 1,2,3 --"}, 200),
    ({"SensitiveCase": "Value"}, 200),
    ({"sensitivecase": "value"}, 200),
    ({"_": 1234567890}, 200),
    ({"param-with-dash-": "value"}, 200),
    ({"param.with..dot": "value"}, 200),
    ({"str": "string", "int": 456, "bool": True}, 200),
    ({"key1": "v1", "key2": "v2", "key3": "v3", "key4": "v4"}, 200),
    ({"p1": "val1", "p2": "val2"}, 200),
    ({"filter(field)": "value"}, 200),
    ({"array[]": ["item1", "item2"]}, 200),
    ({"nested[param][deep]": "value"}, 200),
    ({"invalid_json_in_filter": '{"key":'}, 200),
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
def test_cluster_state_robustness(api_client, params, expected_status, attach_curl_on_fail):
    with attach_curl_on_fail(ENDPOINT, params, method="GET"):
        response = api_client.get(ENDPOINT, params=params)
        # Искусственно вызовем ошибку для проверки вывода cURL (убрать после проверки):
        # if params == {}:
        #     assert False, "Проверка вывода cURL"
        assert response.status_code == expected_status
        if response.status_code == 200:
            data = response.json()
            _check_types_recursive(data, CLUSTER_STATE_SCHEMA)
