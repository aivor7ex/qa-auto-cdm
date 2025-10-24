import json
import pytest
from collections.abc import Mapping, Sequence
from services.qa_constants import SERVICES

ENDPOINT = "/users/count"
SERVICE = SERVICES["csi-server"]

SUCCESS_RESPONSE_SCHEMA = {
    "type": "integer"
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
            assert isinstance(obj, int) and not isinstance(obj, bool), f"Expected integer, got {type(obj)}"
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
    pytest.param({"use_auth_token": True}, None, "", 200, id="valid-token-basic"),
    pytest.param({"use_auth_token": True, "Accept": "application/json"}, None, "", 200, id="valid-token-accept-json"),
    pytest.param({"use_auth_token": True, "Cache-Control": "no-cache"}, None, "", 200, id="valid-token-cache-control"),
    pytest.param({"use_auth_token": True, "User-Agent": "pytest-test"}, None, "", 200, id="valid-token-user-agent"),
    pytest.param({"use_auth_token": True, "X-Custom-Header": "custom-value"}, None, "", 200, id="valid-token-custom-header"),
    pytest.param({"use_auth_token": True}, {"count": "true"}, "", 200, id="valid-token-with-query-param"),
    pytest.param({"use_auth_token": True}, {"filter": "active"}, "", 200, id="valid-token-filter-param"),
    pytest.param({"use_auth_token": True, "Content-Type": "application/json", "Accept": "application/json"}, None, "", 200, id="valid-token-multiple-headers"),
    pytest.param({"use_auth_token": True}, {"offset": "0"}, "", 200, id="valid-token-offset-param"),
    pytest.param({"use_auth_token": True, "Content-Type": "application/json"}, None, "", 200, id="valid-token-json-content-type"),
]

NEGATIVE_CASES = [
    pytest.param({}, None, "", 401, id="no-token"),
    pytest.param({"x-access-token": ""}, None, "", 401, id="empty-token"),
    pytest.param({"x-access-token": "invalid_token_123"}, None, "", 401, id="invalid-token"),
    pytest.param({"x-access-token": "token with spaces"}, None, "", 401, id="token-with-spaces"),
    pytest.param({"x-access-token": "short"}, None, "", 401, id="short-token"),
    pytest.param({"x-access-token": "special!@#$%^&*()"}, None, "", 401, id="special-chars-token"),
    pytest.param({"x-access-token": "null"}, None, "", 401, id="null-token"),
    pytest.param({"Authorization": "WODAw3Jt8hnlE-cGXghzmOBcLbBpKkaQL-jMyWHBVtuU"}, None, "", 401, id="wrong-header-name"),
    pytest.param({"x-access-token": "very_long_invalid_token_that_exceeds_normal_length_limits_and_should_be_rejected_by_the_server_validation_logic_1234567890"}, None, "", 401, id="long-invalid-token"),
    pytest.param({"x-access-token": "undefined"}, None, "", 401, id="undefined-token"),
]

@pytest.mark.parametrize("headers, params, endpoint_suffix, expected_status", POSITIVE_CASES)
def test_get_users_count_positive(api_client, auth_token, attach_curl_on_fail, headers, params, endpoint_suffix, expected_status):
    if "use_auth_token" in headers:
        headers["x-access-token"] = auth_token
        del headers["use_auth_token"]
    full_endpoint = ENDPOINT + endpoint_suffix
    with attach_curl_on_fail(full_endpoint, params, headers, "GET"):
        response = api_client.get(full_endpoint, params=params, headers=headers)
        assert response.status_code == expected_status
        if expected_status == 200:
            _check_types_recursive(response.json(), SUCCESS_RESPONSE_SCHEMA)

@pytest.mark.parametrize("headers, params, endpoint_suffix, expected_status", NEGATIVE_CASES)
def test_get_users_count_negative(api_client, attach_curl_on_fail, headers, params, endpoint_suffix, expected_status):
    full_endpoint = ENDPOINT + endpoint_suffix
    with attach_curl_on_fail(full_endpoint, params, headers, "GET"):
        response = api_client.get(full_endpoint, params=params, headers=headers)
        assert response.status_code == expected_status
