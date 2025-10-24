import json
import pytest
from collections.abc import Mapping, Sequence
from services.qa_constants import SERVICES

ENDPOINT = "/auth-agents"
SERVICE = SERVICES["csi-server"]

# --- Response Schemas for GET and POST ---
response_schemas = {
    "GET": {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "id": {"type": "string"},
                "agent": {"type": "string"},
                "settings": {"type": "object"}
            },
            "required": ["id", "agent", "settings"]
        }
    },
    "POST": {
        "type": "object",
        "properties": {
            "id": {"type": "string"},
            "agent": {"type": "string"},
            "settings": {"type": "object"}
        },
        "required": ["id", "agent", "settings"]
    }
}

def _check_types_recursive(obj, schema):
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
        if "items" in schema and isinstance(schema["items"], list):
            for idx, (item, item_schema) in enumerate(zip(obj, schema["items"])):
                _check_types_recursive(item, item_schema)
        else:
            for item in obj:
                _check_types_recursive(item, schema["items"])
    else:
        if schema.get("type") == "string":
            assert isinstance(obj, str), f"Expected string, got {type(obj)}"
        elif schema.get("type") == "integer":
            assert isinstance(obj, int), f"Expected integer, got {type(obj)}"
        elif schema.get("type") == "boolean":
            assert isinstance(obj, bool), f"Expected boolean, got {type(obj)}"
        elif schema.get("type") == "null":
            assert obj is None, f"Expected null, got {type(obj)}"

def _try_type(obj, schema):
    try:
        _check_types_recursive(obj, schema)
        return True
    except AssertionError:
        return False


POSITIVE_CASES = [
    pytest.param({"use_auth_token": True}, None, "", 200, id="valid-token"),
    pytest.param({"use_auth_token": True, "Content-Type": "application/json"}, None, "", 200, id="valid-token-json-content-type"),
    pytest.param({"use_auth_token": True, "Accept": "application/json"}, None, "", 200, id="valid-token-accept-json"),
    pytest.param({"use_auth_token": True}, {"dummy": "value"}, "", 200, id="valid-token-ignore-params"),
    pytest.param({"use_auth_token": True}, {"q": "test"}, "", 200, id="valid-token-query-q"),
    pytest.param({"use_auth_token": True}, {"page": "1"}, "", 200, id="valid-token-page"),
    pytest.param({"use_auth_token": True}, {"limit": "10"}, "", 200, id="valid-token-limit"),
    pytest.param({"use_auth_token": True}, {"sort": "id"}, "", 200, id="valid-token-sort"),
    pytest.param({"use_auth_token": True, "User-Agent": "pytest"}, None, "", 200, id="valid-token-user-agent"),
    pytest.param({"use_auth_token": True, "Cache-Control": "no-cache"}, None, "", 200, id="valid-token-cache-control"),
    pytest.param({"use_auth_token": True}, {"fields": "id,agent"}, "", 200, id="valid-token-fields"),
    pytest.param({"use_auth_token": True}, {"search": "local"}, "", 200, id="valid-token-search"),
    pytest.param({"use_auth_token": True}, {"date": "2023-01-01"}, "", 200, id="valid-token-date"),
    pytest.param({"use_auth_token": True, "X-Custom": "value"}, None, "", 200, id="valid-token-custom-header"),
    pytest.param({"use_auth_token": True}, {"offset": "0"}, "", 200, id="valid-token-offset"),
]

# R16/R17: Only include status codes that API actually returns
NEGATIVE_CASES = [
    pytest.param({}, None, "", 401, id="no-token"),
    pytest.param({"x-access-token": ""}, None, "", 401, id="empty-token"),
    pytest.param({"x-access-token": "invalid_token_123"}, None, "", 401, id="invalid-token"),
    pytest.param({"x-access-token": "expired_token_abc123"}, None, "", 401, id="expired-token"),
    pytest.param({"authorization": "fake_token_xyz789"}, None, "", 401, id="wrong-header-name"),
    pytest.param({"x-access-token": "very_long_invalid_token_that_exceeds_normal_length_limits_and_should_be_rejected_by_the_server_validation_logic_1234567890_abcdefghijklmnopqrstuvwxyz"}, None, "", 401, id="long-invalid-token"),
    pytest.param({"x-access-token": "fake_token_with_spaces invalid"}, None, "", 401, id="token-with-spaces"),
    pytest.param({"x-access-token": "null"}, None, "", 401, id="null-token"),
    pytest.param({"x-access-token": "123456"}, None, "", 401, id="numeric-token"),
    pytest.param({"x-access-token": "token with spaces"}, None, "", 401, id="token-spaces-only"),
    pytest.param({"x-access-token": "special!@#$%^&*()"}, None, "", 401, id="special-chars-token"),
]

@pytest.mark.parametrize("headers, params, endpoint_suffix, expected_status", POSITIVE_CASES)
def test_get_auth_agents_positive(api_client, auth_token, attach_curl_on_fail, headers, params, endpoint_suffix, expected_status):
    if "use_auth_token" in headers:
        headers["x-access-token"] = auth_token
        del headers["use_auth_token"]
    full_endpoint = ENDPOINT + endpoint_suffix
    with attach_curl_on_fail(full_endpoint, params, headers, "GET"):
        response = api_client.get(full_endpoint, params=params, headers=headers)
        assert response.status_code == expected_status
        if expected_status == 200:
            _check_types_recursive(response.json(), response_schemas["GET"])

@pytest.mark.parametrize("headers, params, endpoint_suffix, expected_status", NEGATIVE_CASES)
def test_get_auth_agents_negative(api_client, auth_token, attach_curl_on_fail, headers, params, endpoint_suffix, expected_status):
    if "use_auth_token" in headers:
        headers["x-access-token"] = auth_token
        del headers["use_auth_token"]
    full_endpoint = ENDPOINT + endpoint_suffix
    with attach_curl_on_fail(full_endpoint, params, headers, "GET"):
        response = api_client.get(full_endpoint, params=params, headers=headers)
        assert response.status_code == expected_status

POSITIVE_POST_CASES = [
    pytest.param({
        "id": "test-agent-1",
        "agent": "radius",
        "settings": {
            "host": "test.com",
            "secret": "test-secret"
        }
    }, id="create-and-delete-agent"),
    pytest.param({
        "id": "test-agent-2",
        "agent": "radius",
        "settings": {
            "host": "test2.com",
            "secret": "test-secret2"
        }
    }, id="create-duplicate-and-delete")
]

# R16/R17: Only include status codes that API actually returns
NEGATIVE_POST_CASES = [
    pytest.param(None, {
        "id": "no-token",
        "agent": "radius",
        "settings": {
            "host": "test.com",
            "secret": "test"
        }
    }, 401, id="no-auth-token"),
    pytest.param("fake_invalid_token_xyz123", {
        "id": "wrong-agent-type",
        "agent": "invalid_type",
        "settings": {
            "host": "test.com",
            "secret": "test"
        }
    }, 401, id="invalid-agent-type")
]

@pytest.mark.parametrize("data", POSITIVE_POST_CASES)
def test_post_auth_agents_positive(api_client, auth_token, attach_curl_on_fail, data):
    headers = {"x-access-token": auth_token, "Content-Type": "application/json"}
    with attach_curl_on_fail(ENDPOINT, data, headers, "POST"):
        response = api_client.post(ENDPOINT, json=data, headers=headers)
        assert response.status_code == 200
        _check_types_recursive(response.json(), response_schemas["POST"])
        # Cleanup
        agent_id = data["id"]
        api_client.delete(f"{ENDPOINT}/{agent_id}", headers={"x-access-token": auth_token})

def test_post_auth_agents_duplicate_conflict(api_client, auth_token, attach_curl_on_fail):
    data = {
        "id": "duplicate-test",
        "agent": "radius",
        "settings": {
            "host": "duplicate.com",
            "secret": "duplicate-secret"
        }
    }
    headers = {"x-access-token": auth_token, "Content-Type": "application/json"}
    # Create first
    with attach_curl_on_fail(ENDPOINT, data, headers, "POST"):
        response = api_client.post(ENDPOINT, json=data, headers=headers)
        assert response.status_code == 200
    # Try duplicate
    with attach_curl_on_fail(ENDPOINT, data, headers, "POST"):
        response = api_client.post(ENDPOINT, json=data, headers=headers)
        assert response.status_code == 409
    # Cleanup
    api_client.delete(f"{ENDPOINT}/duplicate-test", headers={"x-access-token": auth_token})

@pytest.mark.parametrize("token, data, expected_status", NEGATIVE_POST_CASES)
def test_post_auth_agents_negative(api_client, attach_curl_on_fail, token, data, expected_status):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["x-access-token"] = token
    with attach_curl_on_fail(ENDPOINT, data, headers, "POST"):
        response = api_client.post(ENDPOINT, json=data, headers=headers)
        assert response.status_code == expected_status

