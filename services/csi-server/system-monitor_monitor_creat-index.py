import pytest
from services.qa_constants import SERVICES

ENDPOINT = "/system-monitor/monitor/creat-index"
SERVICE = SERVICES["csi-server"]

# Since the API returns 204 with no content, we don't need a complex schema
SUCCESS_RESPONSE_SCHEMA = {
    "type": "null"  # 204 No Content response
}

# Positive test cases - various valid scenarios
POSITIVE_CASES = [
    pytest.param({"use_auth_token": True}, None, "", 204, id="valid-token"),
    pytest.param({"use_auth_token": True, "Content-Type": "application/json"}, None, "", 204, id="valid-token-json-content-type"),
    pytest.param({"use_auth_token": True, "Accept": "application/json"}, None, "", 204, id="valid-token-accept-json"),
    pytest.param({"use_auth_token": True}, {"dummy": "value"}, "", 204, id="valid-token-ignore-params"),
    pytest.param({"use_auth_token": True}, {"q": "test"}, "", 204, id="valid-token-query-q"),
    pytest.param({"use_auth_token": True}, {"page": "1"}, "", 204, id="valid-token-page"),
    pytest.param({"use_auth_token": True}, {"limit": "10"}, "", 204, id="valid-token-limit"),
    pytest.param({"use_auth_token": True}, {"sort": "id"}, "", 204, id="valid-token-sort"),
    pytest.param({"use_auth_token": True, "User-Agent": "pytest"}, None, "", 204, id="valid-token-user-agent"),
    pytest.param({"use_auth_token": True, "Cache-Control": "no-cache"}, None, "", 204, id="valid-token-cache-control"),
]

# Negative test cases - authentication and authorization errors
NEGATIVE_CASES = [
    pytest.param({}, None, "", 401, id="no-token"),
    pytest.param({"x-access-token": ""}, None, "", 401, id="empty-token"),
    pytest.param({"x-access-token": "invalid_token_123"}, None, "", 401, id="invalid-token"),
    pytest.param({"x-access-token": "expired_token_abc123"}, None, "", 401, id="expired-token"),
    pytest.param({"authorization": "WODAw3Jt8hnlE-cGXghzmOBcLbBpKkaQL-jMyWHBVtuU"}, None, "", 401, id="wrong-header-name"),
    pytest.param({"x-access-token": "very_long_invalid_token_that_exceeds_normal_length_limits_and_should_be_rejected_by_the_server_validation_logic_1234567890_abcdefghijklmnopqrstuvwxyz"}, None, "", 401, id="long-invalid-token"),
    pytest.param({"x-access-token": "WODAw3Jt8hnlE-cGXghzmOBcLbBpKkaQL-jMyWHBVtuU invalid"}, None, "", 401, id="token-with-spaces"),
    pytest.param({"use_auth_token": True}, None, "%20with%20spaces", 404, id="malformed-url"),
    pytest.param({"x-access-token": "null"}, None, "", 401, id="null-token"),
    pytest.param({"x-access-token": "123456"}, None, "", 401, id="numeric-token"),
]

@pytest.mark.parametrize("headers, params, endpoint_suffix, expected_status", POSITIVE_CASES)
def test_get_system_monitor_creat_index_positive(api_client, auth_token, attach_curl_on_fail, headers, params, endpoint_suffix, expected_status):
    """Test GET /system-monitor/monitor/creat-index with valid authentication and parameters."""
    if "use_auth_token" in headers:
        headers["x-access-token"] = auth_token
        del headers["use_auth_token"]
    full_endpoint = ENDPOINT + endpoint_suffix
    with attach_curl_on_fail(full_endpoint, params, headers, "GET"):
        response = api_client.get(full_endpoint, params=params, headers=headers)
        assert response.status_code == expected_status
        # For 204 No Content, we expect empty response body
        if expected_status == 204:
            assert response.content == b"", "204 response should have empty body"

@pytest.mark.parametrize("headers, params, endpoint_suffix, expected_status", NEGATIVE_CASES)
def test_get_system_monitor_creat_index_negative(api_client, auth_token, attach_curl_on_fail, headers, params, endpoint_suffix, expected_status):
    """Test GET /system-monitor/monitor/creat-index with invalid authentication and parameters."""
    if "use_auth_token" in headers:
        headers["x-access-token"] = auth_token
        del headers["use_auth_token"]
    full_endpoint = ENDPOINT + endpoint_suffix
    with attach_curl_on_fail(full_endpoint, params, headers, "GET"):
        response = api_client.get(full_endpoint, params=params, headers=headers)
        assert response.status_code == expected_status
