import pytest
from typing import Dict, Any

# =====================================================================================================================
# Constants
# =====================================================================================================================

ENDPOINT = "/managers/bridges/links"
RESPONSE_SCHEMA = {"index": int}

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

def test_managers_bridges_links_static_response(response):
    """Test 1: Verifies the static response from the endpoint."""
    assert response.status_code == 200, f"Expected status 200, got {response.status_code}"
    try:
        data = response.json()
        expected_data = {"index": 0}
        assert data == expected_data, f"Expected {expected_data}, but got: {data}"
        assert isinstance(data['index'], int), f"Expected 'index' to be int, got {type(data['index'])}"
        assert data['index'] >= 0, f"Expected 'index' to be non-negative, got {data['index']}"
    except Exception as e:
        pytest.fail(f"Response validation failed: {e}")

# =====================================================================================================================
# Parametrized Stability Tests
# =====================================================================================================================

def generate_stability_params():
    """Generates 34 diverse parameter sets for stability testing."""
    return [
        ("param" + str(i), "value" + str(i)) for i in range(34)
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
def test_managers_bridges_links_stability_with_params(api_client, param, value):
    """
    Tests 2-35: Ensures the endpoint consistently returns a 200 OK with {'index': 0},
    regardless of the query parameters provided.
    """
    query_params = {param: value}
    response = api_client.get(ENDPOINT, params=query_params)

    assert response.status_code == 200, \
        f"Expected status 200 for param '{param}', but got {response.status_code}"
    try:
        data = response.json()
        expected_data = {"index": 0}
        assert data == expected_data, \
            f"Expected {expected_data} for param '{param}', but got: {data}"
    except Exception as e:
        pytest.fail(f"Response for param '{param}' failed validation. Error: {e}")
