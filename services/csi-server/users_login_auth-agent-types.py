import pytest
import json
from collections.abc import Mapping, Sequence

ENDPOINT = "/users/login/auth-agent-types"

SUCCESS_RESPONSE_SCHEMA = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "id": {"type": "string"},
            "settings": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "type": {"type": "string"},
                        "name": {"type": "string"}
                    },
                    "required": ["type", "name"]
                }
            }
        },
        "required": ["id", "settings"]
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
    pytest.param({"use_auth_token": True}, None, "", 200, id="P01: valid-token-basic"),
    pytest.param({"use_auth_token": True, "Accept": "application/json"}, None, "", 200, id="P02: valid-token-accept-json"),
    pytest.param({"use_auth_token": True, "Cache-Control": "no-cache"}, None, "", 200, id="P03: valid-token-cache-control"),
    pytest.param({"use_auth_token": True, "User-Agent": "pytest-test-agent"}, None, "", 200, id="P04: valid-token-user-agent"),
    pytest.param({"use_auth_token": True, "X-Request-ID": "test-req-123"}, None, "", 200, id="P05: valid-token-custom-header"),
    pytest.param({"use_auth_token": True, "Content-Type": "application/json"}, None, "", 200, id="P06: valid-token-json-content"),
    pytest.param({"use_auth_token": True, "Accept": "application/json", "Accept-Encoding": "gzip"}, None, "", 200, id="P07: valid-token-multiple-headers"),
    pytest.param({"use_auth_token": True}, {}, "", 200, id="P08: valid-token-empty-params"),
    pytest.param({"use_auth_token": True}, {"v": "1"}, "", 200, id="P09: valid-token-version-param"),
    pytest.param({"use_auth_token": True, "Connection": "keep-alive"}, None, "", 200, id="P10: valid-token-keepalive"),
]

NEGATIVE_CASES = [
    pytest.param({}, None, "", 401, id="N01: no-token"),
    pytest.param({"x-access-token": ""}, None, "", 401, id="N02: empty-token"),
    pytest.param({"x-access-token": "invalid_token_xyz_123"}, None, "", 401, id="N03: invalid-token"),
    pytest.param({"x-access-token": "token with spaces"}, None, "", 401, id="N04: token-with-spaces"),
    pytest.param({"x-access-token": "short"}, None, "", 401, id="N05: short-token"),
    pytest.param({"x-access-token": "special!@#$%^&*()"}, None, "", 401, id="N06: special-chars-token"),
    pytest.param({"x-access-token": "null"}, None, "", 401, id="N07: null-token-string"),
    pytest.param({"Authorization": "Bearer WODAw3Jt8hnlE"}, None, "", 401, id="N08: wrong-header-name"),
    pytest.param({"x-access-token": "a" * 200}, None, "", 401, id="N09: very-long-invalid-token"),
    pytest.param({"x-access-token": "undefined"}, None, "", 401, id="N10: undefined-token"),
]

@pytest.mark.parametrize("headers, params, endpoint_suffix, expected_status", POSITIVE_CASES)
def test_get_auth_agent_types_positive(api_client, auth_token, attach_curl_on_fail, headers, params, endpoint_suffix, expected_status):
    """Тесты успешных запросов к эндпоинту /users/login/auth-agent-types"""
    if "use_auth_token" in headers:
        headers["x-access-token"] = auth_token
        del headers["use_auth_token"]
    
    full_endpoint = ENDPOINT + endpoint_suffix
    with attach_curl_on_fail(full_endpoint, None, headers, "GET"):
        response = api_client.get(full_endpoint, params=params, headers=headers)
        assert response.status_code == expected_status, f"Expected {expected_status}, got {response.status_code}: {response.text}"
        
        if expected_status == 200:
            response_data = response.json()
            assert isinstance(response_data, list), f"Response should be an array, got {type(response_data)}"
            _check_types_recursive(response_data, SUCCESS_RESPONSE_SCHEMA)
            # Дополнительная валидация - проверяем что ответ не пуст
            assert len(response_data) > 0, "Response array should not be empty"
            # Проверяем структуру каждого элемента
            for item in response_data:
                assert "id" in item, f"Missing 'id' field in auth agent type: {item}"
                assert "settings" in item, f"Missing 'settings' field in auth agent type: {item}"
                assert isinstance(item["settings"], list), f"'settings' should be an array, got {type(item['settings'])}"

@pytest.mark.parametrize("headers, params, endpoint_suffix, expected_status", NEGATIVE_CASES)
def test_get_auth_agent_types_negative(api_client, attach_curl_on_fail, headers, params, endpoint_suffix, expected_status):
    """Тесты ошибок аутентификации для эндпоинта /users/login/auth-agent-types"""
    full_endpoint = ENDPOINT + endpoint_suffix
    with attach_curl_on_fail(full_endpoint, None, headers, "GET"):
        response = api_client.get(full_endpoint, params=params, headers=headers)
        assert response.status_code == expected_status, f"Expected {expected_status}, got {response.status_code}: {response.text}"
