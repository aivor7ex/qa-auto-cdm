import pytest
import requests
import json
import shlex
from urllib.parse import quote

# --- Test Case Constants ---
ENDPOINT = "/vlanInfos/count"
SERVICE_NAME = "core"

# --- JSON Schema for the Response ---
RESPONSE_SCHEMA = {
    "required": {"count": int},
    "optional": {}
}

# --- Helper Functions (reused from other tests for consistency) ---

def _format_curl_command(response):
    try:
        req = response.request
        method = req.method
        url = req.url
        headers = [f"-H '{k}: {v}'" for k, v in req.headers.items()]
        body = req.body.decode('utf-8') if req.body else None
        curl = f"curl -X {method} '{url}'"
        if headers:
            curl += ' \\n  ' + ' \\n  '.join(headers)
        if body:
            curl += f" \\n  -d '{body}'"
    except Exception:
        curl = "curl -X '<unknown-url>'"
    return curl

def validate_response_schema(response: requests.Response, schema: dict) -> None:
    """Validates the response JSON against a simple schema, raising AssertionError on failure."""
    curl_command = _format_curl_command(response)
    try:
        data = response.json()
    except json.JSONDecodeError:
        pytest.fail(f"Response is not valid JSON.\nCurl for reproduction:\n{curl_command}")

    for key, expected_type in schema.get("required", {}).items():
        assert key in data, f"Required key '{key}' is missing.\nCurl for reproduction:\n{curl_command}"
        actual_type = type(data[key])
        assert actual_type is expected_type, f"Key '{key}' has type {actual_type.__name__}, but expected {expected_type.__name__}.\nCurl: {curl_command}"

# --- Fixtures ---

@pytest.fixture(scope="module")
def actual_vlan_count(api_client):
    """
    Gets the actual number of VLANs by fetching all of them.
    This provides a reliable source of truth to compare the /count endpoint against.
    """
    response = api_client.get("/vlanInfos")
    if response.status_code != 200:
        pytest.skip("Could not retrieve VLAN list from /vlanInfos to verify the count.")
    try:
        data = response.json()
        assert isinstance(data, list), "Response from /vlanInfos is not a list."
        return len(data)
    except (json.JSONDecodeError, AssertionError) as e:
        pytest.skip(f"Could not parse VLAN list from /vlanInfos: {e}")

# --- Test Cases ---

class TestVlanCount:
    """Test suite for the GET /vlanInfos/count endpoint."""

    def test_vlan_count_matches_actual_list(self, api_client, actual_vlan_count):
        """Verify that the count from the endpoint matches the actual number of VLANs."""
        response = api_client.get(ENDPOINT)
        curl_command = _format_curl_command(response)
        try:
            assert response.status_code == 200, f"Expected status 200, but got {response.status_code}.\nCurl: {curl_command}"
            data = response.json()
            assert data['count'] >= 0, f"Count should be non-negative, but got {data['count']}.\nCurl: {curl_command}"
            assert data['count'] == actual_vlan_count, (
                f"Expected count to be {actual_vlan_count}, but got {data['count']}.\nCurl: {curl_command}"
            )
        except Exception as e:
            error_message = (
                f"\nТест /vlanInfos/count упал.\n"
                f"Ошибка: {e}\n\n"
                "================= Failed Test Request (cURL) ================\n"
                f"{curl_command}\n"
                "============================================================="
            )
            pytest.fail(error_message, pytrace=False)

    @pytest.mark.parametrize("query_params, description", [
        ("?foo=bar", "Simple unused parameter"),
        ("?limit=100", "Pagination parameter that should be ignored"),
        ("?offset=20", "Offset parameter that should be ignored"),
        ("?sort=name", "Sort parameter that should be ignored"),
        ("?filter=active", "Filter parameter that should be ignored"),
        ("?id=12345", "ID parameter that should be ignored"),
        ("?search=my-vlan", "Search parameter that should be ignored"),
        ("?unused_param=", "Parameter with empty value"),
        ("?flag", "Parameter with no value"),
        ("?a=1&b=2&c=3", "Multiple unused parameters"),
        ("?param=<script>alert('xss')</script>", "XSS attempt in parameter"),
        ("?file=../../etc/passwd", "Path traversal attempt"),
        ("?' OR 1=1;--", "SQL injection attempt"),
        ("?a[0]=1&a[1]=2", "Array-like parameter"),
        ("?user[name]=admin", "Object-like parameter"),
        ("?long_param=" + "a" * 500, "Very long parameter value"),
        ("?" + "b" * 100 + "=val", "Very long parameter name"),
        ("? " * 50 + "=" + " " * 50, "Parameter with only spaces"),
        ("?%20=%20", "URL-encoded space parameters"),
        ("?emoji=✅", "Unicode emoji in parameter"),
        ("?cyrillic=привет", "Cyrillic characters in parameter"),
        ("?null_val=null", "String 'null' as value"),
        ("?true_val=true", "String 'true' as value"),
        ("?a=1&a=2", "Duplicate parameter names"),
        ("?q=!@#$%^&*()", "Special characters in value"),
        ("?q=;,:/?@&=+$", "Reserved characters in value"),
        ("?p=%00", "Null byte injection attempt"),
        ("?p=1.0", "Float value"),
        ("?p=-1", "Negative value"),
        ("?p=1e6", "Scientific notation value"),
        ("?case=sensitive", "Case-sensitive key"),
        ("?CASE=sensitive", "Case-sensitive key (upper)"),
        ("?key=a\nb\rc", "Value with newlines"),
        ("?p=None", "String 'None' as value"),
        ("?p=undefined", "String 'undefined' as value"),
        ("?p={}", "JSON object string as value"),
        ("?p=[]", "JSON array string as value"),
        ("?_p=1", "Leading underscore in key"),
        ("?-p=1", "Leading hyphen in key (invalid, should be ignored)"),
    ])
    def test_vlan_count_ignores_query_params(self, api_client, actual_vlan_count, query_params, description):
        """
        Verify that the /count endpoint is robust and ignores any provided query parameters.
        The count should always remain the same regardless of the extra parameters.
        """
        url = f"{ENDPOINT}{query_params}"
        response = api_client.get(url)
        curl_command = _format_curl_command(response)
        try:
            assert response.status_code == 200, (
                f"Expected status 200 for case '{description}', but got {response.status_code}.\nCurl: {curl_command}"
            )
            data = response.json()
            assert data['count'] == actual_vlan_count, (
                f"Expected count to be {actual_vlan_count} for case '{description}', but got {data['count']}.\nCurl: {curl_command}"
            )
        except Exception as e:
            error_message = (
                f"\nПараметризованный тест /vlanInfos/count ('{description}') упал.\n"
                f"Ошибка: {e}\n\n"
                "================= Failed Test Request (cURL) ================\n"
                f"{curl_command}\n"
                "============================================================="
            )
            pytest.fail(error_message, pytrace=False) 