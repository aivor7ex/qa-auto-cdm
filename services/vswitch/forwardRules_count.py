import pytest
from typing import Dict, Any

# =====================================================================================================================
# Constants
# =====================================================================================================================

ENDPOINT = "/forwardRules/count"
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

def test_forward_rules_count_static_response(response, attach_curl_on_fail):
    """Test 1: Verifies the response structure and data types from the endpoint."""
    with attach_curl_on_fail(ENDPOINT, method="GET"):
        assert response.status_code == 200, f"Expected status 200, got {response.status_code}"
        data = response.json()
        
        # Check response structure
        assert isinstance(data, dict), f"Expected dict response, got {type(data)}"
        assert "count" in data, f"Expected 'count' key in response, got keys: {list(data.keys())}"
        
        # Check data type
        assert isinstance(data['count'], int), f"Expected 'count' to be int, got {type(data['count'])}"
        assert data['count'] >= 0, f"Expected 'count' to be non-negative, got {data['count']}"

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

@pytest.mark.parametrize("param, value", generate_stability_params())
def test_forward_rules_count_stability_with_params(api_client, param, value, attach_curl_on_fail):
    """
    Tests 2-35: Ensures the endpoint consistently returns a 200 OK with valid response structure,
    regardless of the query parameters provided.
    """
    query_params = {param: value} if value is not None else param
    
    with attach_curl_on_fail(ENDPOINT, method="GET"):
        response = api_client.get(ENDPOINT, params=query_params)

        assert response.status_code == 200, \
            f"Expected status 200 for param '{param}', but got {response.status_code}"
        
        data = response.json()
        
        # Check response structure
        assert isinstance(data, dict), f"Expected dict response for param '{param}', got {type(data)}"
        assert "count" in data, f"Expected 'count' key for param '{param}', got keys: {list(data.keys())}"
        assert isinstance(data['count'], int), f"Expected 'count' to be int for param '{param}', got {type(data['count'])}"
        assert data['count'] >= 0, f"Expected 'count' to be non-negative for param '{param}', got {data['count']}"
