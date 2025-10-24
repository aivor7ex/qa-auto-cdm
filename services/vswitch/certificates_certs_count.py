import pytest
from typing import Dict, Any

# =====================================================================================================================
# Constants
# =====================================================================================================================

ENDPOINT = "/certificates/certs/count"
RESPONSE_SCHEMA = {"count": int}

# =====================================================================================================================
# Fixtures
# =====================================================================================================================

@pytest.fixture(scope="module")
def response(api_client):
    """Provides the response from the endpoint."""
    return api_client.get(ENDPOINT)

# =====================================================================================================================
# Test Cases
# =====================================================================================================================

def test_certs_count_static_response(response):
    """Test 1: Verifies the static response from the endpoint."""
    # 1. Check status code
    assert response.status_code == 200, f"Expected status 200, got {response.status_code}"

    # 2. Check response body structure
    try:
        data = response.json()
        # Check that response has the expected structure
        assert "count" in data, f"Expected 'count' field in response, got: {data}"
        assert isinstance(data['count'], int), f"Expected 'count' to be int, but got {type(data['count'])}"
        assert data['count'] >= 0, f"Expected 'count' to be non-negative, but got: {data['count']}"
    except Exception as e:
        pytest.fail(f"Response validation failed: {e}")

# =====================================================================================================================
# Parametrized Stability Tests
# =====================================================================================================================

def generate_stability_params():
    """Generates 34 diverse parameter sets for stability testing."""
    return [
        # --- Potentially relevant filters ---
        ("filter_by_issuer", "some-ca"), ("filter_by_status", "expired"), ("subject_contains", "example.com"),
        ("expires_before", "2026-01-01"), ("has_private_key", "true"), ("is_ca", "false"),
        ("key_size_gt", "2048"), ("sig_alg", "sha256"),
        # --- Fuzzing and edge cases ---
        ("fuzz_empty", ""), ("fuzz_long", "a" * 256), ("fuzz_special", "!@#$%^&*()"),
        ("fuzz_unicode", "тест"), ("fuzz_sql", "' OR 1=1;"), ("fuzz_xss", "<script>"),
        ("fuzz_path", "../etc/passwd"), ("fuzz_numeric", "12345"), ("fuzz_bool_true", "true"),
        ("fuzz_bool_false", "false"), ("fuzz_null", "null"), ("fuzz_none", None),
        ("fuzz_list[]", "a"), ("fuzz_dict[key]", "value"), ("fuzz_int", 100),
        ("fuzz_float", 99.9), ("fuzz_negative", -1), ("fuzz_zero", 0),
        ("fuzz_large_int", 9999999999), ("fuzz_uuid", "123e4567-e89b-12d3-a456-426614174000"),
        ("fuzz_date", "2025-06-27"), ("fuzz_mac", "00:1B:44:11:3A:B7"),
        ("fuzz_hostname", "server.local"), ("fuzz_semver", "2.1.0"),
        ("fuzz_url", "https://a.com/b"), ("fuzz_html", "a%20b"),
    ]

def _format_curl_command(api_client, endpoint, params=None, headers=None):
    base_url = getattr(api_client, "base_url", getattr(api_client, 'base_url', 'http://127.0.0.1'))
    full_url = f"{base_url.rstrip('/')}/{endpoint.lstrip('/')}"
    if params:
        param_str = "&".join([f"{k}={v}" for k, v in params.items() if v is not None])
        if param_str:
            full_url += f"?{param_str}"
    headers = headers or getattr(api_client, 'headers', {})
    headers_str = " \\\n  ".join([f"-H '{k}: {v}'" for k, v in headers.items()])
    curl_command = f"curl -X GET '{full_url}'"
    if headers_str:
        curl_command += f" \\\n  {headers_str}"
    return curl_command

@pytest.mark.parametrize("param, value", generate_stability_params())
def test_certs_count_stability_with_params(api_client, param, value):
    """
    Tests 2-35: Ensures the endpoint consistently returns a 200 OK with valid count structure,
    regardless of the query parameters provided, ensuring endpoint stability.
    """
    query_params = {param: value} if value is not None else param
    response = api_client.get(ENDPOINT, params=query_params)

    assert response.status_code == 200, \
        f"Expected status 200 for param '{param}', but got {response.status_code}"

    try:
        data = response.json()
        # Check that response has the expected structure
        assert "count" in data, f"Expected 'count' field in response for param '{param}', got: {data}"
        assert isinstance(data['count'], int), f"Expected 'count' to be int for param '{param}', but got {type(data['count'])}"
        assert data['count'] >= 0, f"Expected 'count' to be non-negative for param '{param}', but got: {data['count']}"
    except Exception as e:
        pytest.fail(f"Response for param '{param}' failed validation. Error: {e}")
