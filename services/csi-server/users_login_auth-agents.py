import pytest
import json
from collections.abc import Mapping, Sequence

ENDPOINT = "/users/login/auth-agents"

SUCCESS_RESPONSE_SCHEMA = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "agent": {"type": "string"}
        },
        "required": ["name", "agent"]
    }
}

def _check_types_recursive(obj, schema):
    """Рекурсивно проверяет типы данных по схеме"""
    if "anyOf" in schema:
        assert any(_try_type(obj, s) for s in schema["anyOf"]), f"Value {obj} does not match anyOf {schema['anyOf']}"
        return
    
    if schema.get("type") == "object":
        assert isinstance(obj, Mapping), f"Expected object, got {type(obj)}"
        for key, prop in schema.get("properties", {}).items():
            if key in obj:
                _check_types_recursive(obj[key], prop)
        for req in schema.get("required", []):
            assert req in obj, f"Missing required field: {req}"
    elif schema.get("type") == "array":
        assert isinstance(obj, Sequence) and not isinstance(obj, str), f"Expected array, got {type(obj)}"
        if "items" in schema:
            for item in obj:
                _check_types_recursive(item, schema["items"])
    else:
        if schema.get("type") == "string":
            assert isinstance(obj, str), f"Expected string, got {type(obj)}"
        elif schema.get("type") == "integer":
            assert isinstance(obj, int) and not isinstance(obj, bool), f"Expected integer, got {type(obj)}"
        elif schema.get("type") == "number":
            assert isinstance(obj, (int, float)) and not isinstance(obj, bool), f"Expected number, got {type(obj)}"
        elif schema.get("type") == "boolean":
            assert isinstance(obj, bool), f"Expected boolean, got {type(obj)}"
        elif schema.get("type") == "null":
            assert obj is None, f"Expected null, got {type(obj)}"

def _try_type(obj, schema):
    """Пытается проверить тип объекта по схеме, возвращает True/False"""
    try:
        _check_types_recursive(obj, schema)
        return True
    except AssertionError:
        return False


POSITIVE_CASES = [
    pytest.param({}, None, "", 200, id="P01: basic-request"),
    pytest.param({"Accept": "application/json"}, None, "", 200, id="P02: accept-json"),
    pytest.param({"Cache-Control": "no-cache"}, None, "", 200, id="P03: cache-control"),
    pytest.param({"User-Agent": "pytest-test-agent"}, None, "", 200, id="P04: user-agent"),
    pytest.param({"X-Request-ID": "test-req-123"}, None, "", 200, id="P05: custom-header"),
    pytest.param({"Content-Type": "application/json"}, None, "", 200, id="P06: content-type-json"),
    pytest.param({"Accept": "application/json", "Accept-Encoding": "gzip"}, None, "", 200, id="P07: multiple-headers"),
    pytest.param({}, {}, "", 200, id="P08: empty-params"),
    pytest.param({}, {"filter": "active"}, "", 200, id="P09: filter-param"),
    pytest.param({"Connection": "keep-alive"}, {"limit": "10"}, "", 200, id="P10: keepalive-with-limit"),
]

@pytest.mark.parametrize("headers, params, endpoint_suffix, expected_status", POSITIVE_CASES)
def test_get_auth_agents(api_client, attach_curl_on_fail, headers, params, endpoint_suffix, expected_status):
    """Тесты успешных запросов к эндпоинту /users/login/auth-agents"""
    full_endpoint = ENDPOINT + endpoint_suffix
    with attach_curl_on_fail(full_endpoint, None, headers, "GET"):
        response = api_client.get(full_endpoint, params=params, headers=headers)
        assert response.status_code == expected_status, f"Expected {expected_status}, got {response.status_code}: {response.text}"
        
        if expected_status == 200:
            response_data = response.json()
            assert isinstance(response_data, list), f"Response should be an array, got {type(response_data)}"
            _check_types_recursive(response_data, SUCCESS_RESPONSE_SCHEMA)
            # Дополнительная валидация - проверяем структуру каждого элемента
            for item in response_data:
                assert "name" in item, f"Missing 'name' field in auth agent: {item}"
                assert "agent" in item, f"Missing 'agent' field in auth agent: {item}"
                assert isinstance(item["name"], str), f"'name' should be string, got {type(item['name'])}"
                assert isinstance(item["agent"], str), f"'agent' should be string, got {type(item['agent'])}"
