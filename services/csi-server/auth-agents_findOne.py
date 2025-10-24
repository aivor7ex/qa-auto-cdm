import pytest
from typing import Any, Dict, List, Union

ENDPOINT = "/auth-agents/findOne"

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

@pytest.mark.parametrize("test_id, description, auth_type, query_params, expected_status", [
    ("P01", "Valid auth token", "valid", None, 200),
    ("P02", "Valid auth token with query params", "valid", {"param1": "value1"}, 200),
    ("P03", "Valid auth token with empty query", "valid", {}, 200),
    ("P04", "Valid auth token with numeric params", "valid", {"id": 123}, 200),
    ("P05", "Valid auth token with boolean params", "valid", {"active": True}, 200),
    ("P07", "Valid auth token with long query", "valid", {"search": "a" * 100}, 200),
    ("P08", "Valid auth token with multiple params", "valid", {"page": 1, "limit": 10}, 200),
    ("P10", "Valid auth token with array params", "valid", {"ids": [1, 2, 3]}, 200),
])
def test_positive_cases(api_client, auth_token, test_id, description, auth_type, query_params, expected_status, attach_curl_on_fail):
    headers = {}
    if auth_type == "valid":
        headers["x-access-token"] = auth_token
    elif auth_type != "none":
        headers["x-access-token"] = auth_type

    with attach_curl_on_fail(ENDPOINT, query_params, headers, "GET"):
        response = api_client.get(ENDPOINT, headers=headers, params=query_params)
        assert response.status_code == expected_status, f"[{test_id}] {description}: Expected {expected_status}, got {response.status_code}"

        if expected_status == 200:
            validate_json_schema(response.json(), SUCCESS_RESPONSE_SCHEMA)

@pytest.mark.parametrize("test_id, description, auth_type, query_params, expected_status", [
    ("N01", "No auth header", "none", None, 401),
    ("N02", "Invalid auth token", "invalid_token_12345", None, 401),
    ("N03", "Empty auth token", "", None, 401),
    ("N04", "Expired auth token", "expired_token_12345", None, 401),
    ("N05", "Malformed auth token", "malformed@token#123", None, 401),
    ("N06", "Wrong auth header name", "wrong_header", None, 401),
    ("N07", "Auth token with special chars", "token@#$%^&*()", None, 401),
    ("N08", "Auth token too long", "a" * 1000, None, 401),
    ("N09", "Auth token too short", "ab", None, 401),
    ("N10", "Multiple auth headers", "multiple_tokens", None, 401),
    ("N11", "Invalid query with special chars", "valid", {"filter": "test@domain.com"}, 400),
    ("N12", "Invalid query with nested objects", "valid", {"filter": {"type": "user"}}, 400),
])
def test_negative_cases(api_client, auth_token, test_id, description, auth_type, query_params, expected_status, attach_curl_on_fail):
    headers = {}
    if auth_type == "valid":
        headers["x-access-token"] = auth_token
    elif auth_type != "none":
        headers["x-access-token"] = auth_type

    with attach_curl_on_fail(ENDPOINT, query_params, headers, "GET"):
        response = api_client.get(ENDPOINT, headers=headers, params=query_params)
        assert response.status_code == expected_status, f"[{test_id}] {description}: Expected {expected_status}, got {response.status_code}"

        if expected_status == 200:
            validate_json_schema(response.json(), SUCCESS_RESPONSE_SCHEMA)
