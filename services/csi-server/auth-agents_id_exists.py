import pytest
from typing import Any, Dict, List, Union

ENDPOINT = "/auth-agents/{id}/exists"

SUCCESS_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "exists": {"type": "boolean"}
    },
    "required": ["exists"]
}

def _check_types_recursive(obj, schema):
    """Рекурсивно проверяет типы данных в объекте на соответствие схеме."""
    if "anyOf" in schema:
        assert any(_try_type(obj, s) for s in schema["anyOf"]), f"Тип {type(obj)} не соответствует ни одной из схем в anyOf"
        return

    schema_type = schema.get("type")
    if schema_type == "object":
        assert isinstance(obj, dict), f"Ожидался объект (dict), получено: {type(obj).__name__}"
        for key, prop_schema in schema.get("properties", {}).items():
            if key in obj:
                _check_types_recursive(obj[key], prop_schema)
        for required_key in schema.get("required", []):
            assert required_key in obj, f"Обязательное поле '{required_key}' отсутствует в объекте"
    elif schema_type == "array":
        assert isinstance(obj, list) and not isinstance(obj, str), f"Ожидался список (list), получено: {type(obj).__name__}"
        for item in obj:
            _check_types_recursive(item, schema["items"])
    elif schema_type == "string":
        assert isinstance(obj, str), f"Поле должно быть строкой (string), получено: {type(obj).__name__}"
    elif schema_type == "integer":
        assert isinstance(obj, int), f"Поле должно быть целым числом (integer), получено: {type(obj).__name__}"
    elif schema_type == "boolean":
        assert isinstance(obj, bool), f"Поле должно быть булевым (boolean), получено: {type(obj).__name__}"
    elif schema_type == "null":
        assert obj is None, "Поле должно быть null"

def _try_type(obj, schema):
    """Вспомогательная функция для проверки типа в 'anyOf'."""
    try:
        _check_types_recursive(obj, schema)
        return True
    except AssertionError:
        return False

@pytest.mark.parametrize("test_id, description, auth_type, agent_id, expected_status", [
    ("P01", "Valid auth token with local agent", "valid", "local", 200),
    ("P02", "Valid auth token with existing agent", "valid", "admin", 200),
    ("P03", "Valid auth token with test agent", "valid", "test", 200),
    ("P04", "Valid auth token with user agent", "valid", "user", 200),
    ("P05", "Valid auth token with system agent", "valid", "system", 200),
    ("P06", "Valid auth token with guest agent", "valid", "guest", 200),
    ("P07", "Valid auth token with root agent", "valid", "root", 200),
    ("P08", "Valid auth token with service agent", "valid", "service", 200),
    ("P09", "Valid auth token with api agent", "valid", "api", 200),
    ("P10", "Valid auth token with default agent", "valid", "default", 200),
])
def test_positive_auth_agents_exists_cases(api_client, auth_token, test_id, description, auth_type, agent_id, expected_status, attach_curl_on_fail):
    headers = {}
    if auth_type == "valid":
        headers["x-access-token"] = auth_token
    elif auth_type != "none":
        headers["x-access-token"] = auth_type
    
    endpoint = ENDPOINT.format(id=agent_id)
    with attach_curl_on_fail(endpoint, None, headers, "GET"):
        response = api_client.get(endpoint, headers=headers)
        assert response.status_code == expected_status, f"[{test_id}] {description}: Expected {expected_status}, got {response.status_code}"
        
        if expected_status == 200:
            _check_types_recursive(response.json(), SUCCESS_RESPONSE_SCHEMA)

@pytest.mark.parametrize("test_id, description, auth_type, agent_id, expected_status", [
    ("N01", "No auth header", "none", "local", 401),
    ("N02", "Invalid auth token", "invalid_token_12345", "local", 401),
    ("N03", "Empty auth token", "", "local", 401),
    ("N04", "Expired auth token", "expired_token_example", "local", 401),
    ("N05", "Malformed auth token", "malformed.token", "local", 401),
    ("N06", "Wrong auth token format", "Bearer invalid_token", "local", 401),
    ("N07", "Short auth token", "short", "local", 401),
    ("N08", "Auth token too long", "a" * 1000, "local", 401),
    ("N09", "Auth token with special chars", "token@#$%^&*()", "local", 401),
    ("N10", "Non-existent agent with invalid auth", "invalid_token", "nonexistent", 401),
])
def test_negative_auth_agents_exists_cases(api_client, auth_token, test_id, description, auth_type, agent_id, expected_status, attach_curl_on_fail):
    headers = {}
    if auth_type == "valid":
        headers["x-access-token"] = auth_token
    elif auth_type != "none":
        headers["x-access-token"] = auth_type
    
    endpoint = ENDPOINT.format(id=agent_id)
    with attach_curl_on_fail(endpoint, None, headers, "GET"):
        response = api_client.get(endpoint, headers=headers)
        assert response.status_code == expected_status, f"[{test_id}] {description}: Expected {expected_status}, got {response.status_code}"
