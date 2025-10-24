import pytest
from typing import Any, Dict, List, Union

ENDPOINT = "/auth-agents/{id}"

SUCCESS_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
        "agent": {"type": "string"},
        "settings": {
            "type": "object",
            "properties": {
                "different_case_required": {"type": "boolean"},
                "min_password_length": {"type": "integer"},
                "numbers_required": {"type": "boolean"},
                "special_characters_required": {"type": "boolean"}
            },
            "required": ["different_case_required", "min_password_length", "numbers_required", "special_characters_required"]
        }
    },
    "required": ["id", "agent", "settings"]
}

def validate_json_schema(data: Any, schema: Dict) -> None:
    if schema.get("type") == "list":
        assert isinstance(data, list), f"Expected list, got {type(data)}"
        item_schema = schema.get("items", {})
        for item in data:
            validate_json_schema(item, item_schema)
    elif schema.get("type") == "object":
        assert isinstance(data, dict), f"Expected dict, got {type(data)}"
        required_keys = schema.get("required", [])
        for key in required_keys:
            assert key in data, f"Missing required key: {key}"
        properties = schema.get("properties", {})
        for key, prop_schema in properties.items():
            if key in data:
                validate_json_schema(data[key], prop_schema)

@pytest.mark.parametrize("test_id, description, auth_type, agent_id, extra_headers, expected_status", [
    ("P01", "Valid auth token with local agent", "valid", "local", None, 200),
    ("P02", "Valid auth token with local agent and content-type", "valid", "local", {"Content-Type": "application/json"}, 200),
    ("P03", "Valid auth token with local agent and accept header", "valid", "local", {"Accept": "application/json"}, 200),
    ("P04", "Valid auth token with local agent and user-agent", "valid", "local", {"User-Agent": "pytest"}, 200),
    ("P05", "Valid auth token with local agent and cache-control", "valid", "local", {"Cache-Control": "no-cache"}, 200),
    ("P06", "Valid auth token with local agent and custom header", "valid", "local", {"X-Custom": "value"}, 200),
    ("P07", "Valid auth token prefix with local agent", "valid", "local", {"Authorization": "Bearer test"}, 200),
    ("P08", "Valid auth token with local agent and multiple headers", "valid", "local", {"Accept": "application/json", "Content-Type": "application/json"}, 200),
    ("P09", "Valid auth token with local agent minimal headers", "valid", "local", {}, 200),
    ("P10", "Valid auth token with local agent standard headers", "valid", "local", {"Accept": "*/*", "User-Agent": "curl/7.68.0"}, 200),
    ("N11", "Non-existent agent ID with valid auth", "valid", "nonexistent", None, 200),
])
def test_positive_auth_agents_cases(api_client, auth_token, test_id, description, auth_type, agent_id, extra_headers, expected_status, attach_curl_on_fail):
    headers = {}
    if auth_type == "valid":
        headers["x-access-token"] = auth_token
    elif auth_type != "none":
        headers["x-access-token"] = auth_type
    
    # Добавляем дополнительные заголовки если они есть
    if extra_headers:
        headers.update(extra_headers)
    
    endpoint = ENDPOINT.format(id=agent_id)
    with attach_curl_on_fail(endpoint, None, headers, "GET"):
        response = api_client.get(endpoint, headers=headers)
        assert response.status_code == expected_status, f"[{test_id}] {description}: Expected {expected_status}, got {response.status_code}"
        
        if expected_status == 200:
            # Для позитивных кейсов с agent_id != "local" проверяем только базовую структуру
            if agent_id != "local":
                data = response.json()
                assert isinstance(data, dict), f"Expected dict, got {type(data)}"
                assert "id" in data, f"Missing required key: id"
            else:
                validate_json_schema(response.json(), SUCCESS_RESPONSE_SCHEMA)

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
])
def test_negative_auth_agents_cases(api_client, auth_token, test_id, description, auth_type, agent_id, expected_status, attach_curl_on_fail):
    headers = {}
    if auth_type == "valid":
        headers["x-access-token"] = auth_token
    elif auth_type != "none":
        headers["x-access-token"] = auth_type
    
    endpoint = ENDPOINT.format(id=agent_id)
    with attach_curl_on_fail(endpoint, None, headers, "GET"):
        response = api_client.get(endpoint, headers=headers)
        assert response.status_code == expected_status, f"[{test_id}] {description}: Expected {expected_status}, got {response.status_code}"
