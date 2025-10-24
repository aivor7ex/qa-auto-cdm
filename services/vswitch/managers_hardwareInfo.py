import pytest
from typing import Dict, Any, Union

# =====================================================================================================================
# Constants
# =====================================================================================================================

ENDPOINT = "/managers/hardwareInfo"
RESPONSE_SCHEMA = {
    "manufacturer": str, "model": str, "version": str, "serial": str, "assetTag": str,
    "memMax": (int, type(None)), "memSlots": (int, type(None))
}
REQUIRED_STRING_FIELDS = ["manufacturer", "model", "version", "serial", "assetTag"]

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
    return response.json()

# =====================================================================================================================
# Test Cases (Total: 1 + 1 + 7 + 7 + 5 + 14 = 35)
# =====================================================================================================================

def test_hardware_info_status_code(response):
    """Test 1: Ensures the endpoint returns a 200 OK status code."""
    assert response.status_code == 200

def test_hardware_info_no_unexpected_fields(response_data):
    """Test 2: Ensures no unexpected fields are in the response."""
    unexpected_fields = set(response_data.keys()) - set(RESPONSE_SCHEMA.keys())
    assert not unexpected_fields, f"Found unexpected fields: {sorted(list(unexpected_fields))}"

@pytest.mark.parametrize("field_name", RESPONSE_SCHEMA.keys())
def test_hardware_info_field_presence(response_data, field_name):
    """Tests 3-9: Checks for the presence of each required and optional field."""
    assert field_name in response_data, f"Field '{field_name}' is missing."

@pytest.mark.parametrize("field_name, expected_type", RESPONSE_SCHEMA.items())
def test_hardware_info_field_type(response_data, field_name, expected_type):
    """Tests 10-16: Validates the data type of each field."""
    field_value = response_data.get(field_name)
    assert isinstance(field_value, expected_type), \
        f"Field '{field_name}' should be type {expected_type}, but is {type(field_value).__name__}."

@pytest.mark.parametrize("field_name", REQUIRED_STRING_FIELDS)
def test_hardware_info_required_strings_not_empty(response_data, field_name):
    """Tests 17-21: Ensures that required string fields are not empty."""
    field_value = response_data.get(field_name)
    assert field_value is not None and field_value.strip() != "", \
        f"Required string field '{field_name}' should not be empty."

# --- Stability Tests ---
def generate_stability_params():
    """Generates 14 diverse parameter sets for stability testing."""
    return [("param" + str(i), "value" + str(i)) for i in range(14)]

@pytest.mark.parametrize("param, value", generate_stability_params())
def test_hardware_info_stability_with_params(api_client, response_data, param, value):
    """
    Tests 22-35: Verifies that the endpoint ignores any provided query parameters
    and consistently returns the same, valid hardware info object.
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
