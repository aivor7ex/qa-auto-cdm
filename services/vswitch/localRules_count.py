import pytest
from typing import Dict, Any

# =====================================================================================================================
# Constants
# =====================================================================================================================

ENDPOINT = "/localRules/count"
RESPONSE_SCHEMA = {"count": int}

# R10: Declare SUCCESS_RESPONSE_SCHEMA at the top of the file
SUCCESS_RESPONSE_SCHEMA = {"count": int}

# =====================================================================================================================
# Fixtures
# =====================================================================================================================

@pytest.fixture(scope="module")
def response(api_client):
    """Provides the response from the endpoint."""
    return api_client.get(ENDPOINT)

@pytest.fixture(scope="module")
def baseline_count(response) -> int:
    """Extracts the baseline count from the initial response to avoid hardcoding."""
    data = response.json()
    assert isinstance(data, dict), "Response JSON must be a dict"
    assert "count" in data, "Response must include 'count'"
    assert isinstance(data["count"], int), "'count' must be an int"
    return data["count"]

# =====================================================================================================================
# Test Cases
# =====================================================================================================================

def test_local_rules_count_static_response(response):
    """Test 1: Verifies the response conforms to schema and is successful."""
    assert response.status_code == 200, f"Expected status 200, got {response.status_code}"
    data = response.json()
    assert isinstance(data, dict), f"Expected dict JSON, got: {type(data)}"
    assert "count" in data, "Missing 'count' in response JSON"
    assert isinstance(data['count'], int), f"Expected 'count' to be int, got {type(data['count'])}"
    assert data['count'] >= 0, "'count' should be non-negative"

# =====================================================================================================================
# Parametrized Stability Tests
# =====================================================================================================================

def generate_stability_params():
    """Generates 34 diverse parameter sets for stability testing."""
    return [
        # --- Potentially relevant filters ---
        ("filter_by", "active"), ("group_by", "source_ip"), ("having_min", "1"),
        ("since_date", "2025-01-01"), ("unsupported_format", "xml"), ("cache_control", "no-cache"),
        ("src_ip", "192.168.1.1"), ("dst_port", "8080"), ("protocol", "tcp"),
        # --- Fuzzing and edge cases ---
        ("fuzz_empty", ""), ("fuzz_long", "a" * 256), ("fuzz_special", "!@#$%^&*()"),
        ("fuzz_unicode", "тест"), ("fuzz_sql", "' OR 1=1;"), ("fuzz_xss", "<script>"),
        ("fuzz_path", "../etc/passwd"), ("fuzz_numeric", "12345"), ("fuzz_bool_true", "true"),
        ("fuzz_bool_false", "false"), ("fuzz_null", "null"), ("fuzz_none", None),
        ("fuzz_list[]", "a"), ("fuzz_dict[key]", "value"), ("fuzz_int", 100),
        ("fuzz_float", 99.9), ("fuzz_negative", -1), ("fuzz_zero", 0),
        ("fuzz_large_int", 9999999999), ("fuzz_uuid", "123e4567-e89b-12d3-a456-426614174000"),
        ("fuzz_date", "2025-06-27"), ("fuzz_ip", "1.1.1.1"),
        ("fuzz_mac", "00:1B:44:11:3A:B7"), ("fuzz_hostname", "server.local"),
        ("fuzz_another", "param"),
    ]

# =====================================================================================================================
# R12: Use attach_curl_on_fail and avoid try/except that hides it
# R13: Add R0 availability check using fixtures without hardcoded URL
# =====================================================================================================================

def test_local_rules_count_r0_availability(api_client, api_base_url, attach_curl_on_fail):
    """Ensures API availability for base request (R13)."""
    url = f"{api_base_url.rstrip('/')}/{ENDPOINT.lstrip('/')}"
    with attach_curl_on_fail(ENDPOINT, None, None, "GET"):
        resp = api_client.get(url)
        assert resp.status_code == 200, (
            f"API недоступно на R0-запросе: ожидался 200, получено {resp.status_code}"
        )

@pytest.mark.parametrize("param, value", generate_stability_params())
def test_local_rules_count_stability_with_params(api_client, api_base_url, attach_curl_on_fail, baseline_count, param, value):
    """
    Tests 2-35: Ensures the endpoint consistently returns a 200 OK and a valid
    JSON with an integer 'count' that matches the baseline, regardless of the
    query parameters provided.
    """
    query_params = {param: value} if value is not None else param
    url = f"{api_base_url.rstrip('/')}/{ENDPOINT.lstrip('/')}"
    with attach_curl_on_fail(ENDPOINT, query_params, None, "GET"):
        response = api_client.get(url, params=query_params)

    assert response.status_code == 200, \
        f"Expected status 200 for param '{param}', but got {response.status_code}"
    data = response.json()
    assert isinstance(data, dict), f"Expected dict JSON for '{param}', got: {type(data)}"
    assert "count" in data, f"Missing 'count' for '{param}'"
    assert isinstance(data['count'], int), f"'count' must be int for '{param}', got {type(data['count'])}"
    assert data['count'] == baseline_count, \
        f"Expected count {baseline_count} for param '{param}', but got: {data['count']}"
