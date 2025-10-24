import pytest
from typing import Dict, Any

# =====================================================================================================================
# Constants
# =====================================================================================================================

ENDPOINT = "/managers/interfaceAddr"
RESPONSE_SCHEMA = {"addr": str, "netmask": str}
BASE_PARAMS = {"name": "lo"}
EXPECTED_RESPONSE = {"addr": "127.0.0.1", "netmask": "255.0.0.0"}

# =====================================================================================================================
# Fixtures
# =====================================================================================================================

@pytest.fixture(scope="module")
def response(api_client):
    """Provides the response from the endpoint with base parameters."""
    return api_client.get(ENDPOINT, params=BASE_PARAMS)

@pytest.fixture(scope="module")
def response_data(response) -> Dict[str, Any]:
    """Provides the JSON data from the response."""
    assert response.status_code == 200
    return response.json()

# =====================================================================================================================
# Test Cases
# =====================================================================================================================

def test_interface_addr_status_code(response):
    """Test 1: Ensures the endpoint returns a 200 OK status code for a valid interface."""
    assert response.status_code == 200

def test_interface_addr_exact_response(response_data):
    """Test 2: Verifies the exact response for the loopback interface."""
    assert response_data == EXPECTED_RESPONSE

def test_interface_addr_schema(response_data):
    """Test 3: Validates the schema of the response."""
    for key, expected_type in RESPONSE_SCHEMA.items():
        assert key in response_data, f"Required key '{key}' is missing."
        assert isinstance(response_data[key], expected_type), \
            f"Key '{key}' expected {expected_type.__name__}, got {type(response_data[key]).__name__}."
    
    unexpected_fields = set(response_data.keys()) - set(RESPONSE_SCHEMA.keys())
    assert not unexpected_fields, f"Found unexpected fields: {sorted(list(unexpected_fields))}"

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
def test_interface_addr_stability_with_params(api_client, param, value):
    """
    Tests 4-35: Verifies that the endpoint ignores extraneous query parameters
    and consistently returns the same valid response for the 'lo' interface.
    """
    query_params = {**BASE_PARAMS, param: value}
    response = api_client.get(ENDPOINT, params=query_params)

    assert response.status_code == 200, \
        f"Expected status 200 for params {query_params}, but got {response.status_code}"
    try:
        data = response.json()
        assert data == EXPECTED_RESPONSE, \
            f"Response should be stable but changed with param '{param}'"
    except Exception as e:
        pytest.fail(f"Response for params {query_params} failed validation. Error: {e}")
