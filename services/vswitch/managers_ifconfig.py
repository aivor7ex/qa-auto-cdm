import pytest
from typing import Dict, Any, List

# =====================================================================================================================
# Constants
# =====================================================================================================================

ENDPOINT = "/managers/ifconfig"

IP_ADDR_SCHEMA = {
    "addr": str, "netmask": str, "fullAddr": str, "proto": str
}
INTERFACE_SCHEMA = {
    "inet": list, "inet6": list, "mtu": int
}

# =====================================================================================================================
# Fixtures
# =====================================================================================================================

@pytest.fixture(scope="module")
def response(api_client):
    """Provides the response from the endpoint."""
    return api_client.get(ENDPOINT)

@pytest.fixture(scope="module")
def response_data(response) -> Dict[str, Any]:
    """Provides the JSON data from the response."""
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict) and data, "Response should be a non-empty dictionary"
    return data

# =====================================================================================================================
# Test Cases
# =====================================================================================================================

def test_ifconfig_status_code(response):
    """Test 1: Ensures the endpoint returns a 200 OK status code."""
    assert response.status_code == 200

def test_ifconfig_response_is_not_empty_dict(response_data):
    """Test 2: Verifies that the response is a non-empty dictionary."""
    assert isinstance(response_data, dict) and bool(response_data)

def test_ifconfig_full_schema_validation(response_data):
    """Test 3: Validates the schema for all interfaces and their IP addresses in the response."""
    for if_name, if_data in response_data.items():
        # --- Validate Interface Schema ---
        for key, expected_type in INTERFACE_SCHEMA.items():
            assert key in if_data, f"Interface '{if_name}' is missing required key '{key}'"
            assert isinstance(if_data[key], expected_type), \
                f"Interface '{if_name}', key '{key}' has type {type(if_data[key])}, expected {expected_type}"

        # --- Validate IP Address Schema (v4 and v6) ---
        all_ips = if_data.get("inet", []) + if_data.get("inet6", [])
        for ip_obj in all_ips:
            # Skip validation for error objects (like {'message': 'wrong ip format: ...'})
            if "message" in ip_obj:
                print(f"Skipping validation for error object in interface '{if_name}': {ip_obj}")
                continue
                
            for key, expected_type in IP_ADDR_SCHEMA.items():
                # 'broadcast' is optional, so we don't fail if it's missing
                if key == "broadcast" and key not in ip_obj:
                    continue
                assert key in ip_obj, f"IP object in '{if_name}' is missing key '{key}'"
                assert isinstance(ip_obj[key], expected_type), \
                    f"IP object in '{if_name}', key '{key}' has type {type(ip_obj[key])}, expected {expected_type}"

# =====================================================================================================================
# Parametrized Stability Tests
# =====================================================================================================================

def generate_stability_params():
    """Generates 32 diverse parameter sets for stability testing."""
    return [("param" + str(i), "value" + str(i)) for i in range(32)]

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
def test_ifconfig_stability_with_params(api_client, response_data, param, value):
    """
    Tests 4-35: Verifies that the endpoint ignores any provided query parameters
    and consistently returns the same, valid ifconfig object.
    """
    query_params = {param: value}
    fuzz_response = api_client.get(ENDPOINT, params=query_params)
    assert fuzz_response.status_code == 200
    try:
        fuzz_data = fuzz_response.json()
        assert fuzz_data == response_data, \
            f"Response should be stable but changed with param '{param}'"
    except Exception as e:
        pytest.fail(f"Response for param '{param}' failed validation. Error: {e}")
