"""
Test for the /api/arp-watch/count endpoint.
"""
import pytest
import random
import string

# --- Schema Definition ---
COUNT_SCHEMA = {
    "required": {
        "count": int
    }
}

# --- Fixtures ---

@pytest.fixture(scope="module")
def api_response(api_client):
    """
    Performs a single, clean GET request to the endpoint
    and returns the response object.
    """
    response = api_client.get("/arp-watch/count")
    return response

# --- Core Tests ---

def test_status_code(api_response):
    """
    Tests that the API returns a 200 OK status code.
    """
    assert api_response.status_code == 200, \
        f"Expected status code 200, but got {api_response.status_code}. Response: {api_response.text}"

def test_count_schema_and_value(api_response):
    """
    Validates the response schema, data types, and basic data validity.
    """
    response_json = api_response.json()
    
    # Schema validation: check for required key
    for key in COUNT_SCHEMA["required"]:
        assert key in response_json, f"Required key '{key}' is missing from the response."

    # Type validation
    count_value = response_json["count"]
    expected_type = COUNT_SCHEMA["required"]["count"]
    assert isinstance(count_value, expected_type), \
        f"Key 'count' has type {type(count_value).__name__}, but expected {expected_type.__name__}."

    # Data validity check
    assert count_value >= 0, f"'count' should be a non-negative integer, but got {count_value}."

# --- Robustness and Parametrization Tests ---

def generate_random_string(length=10):
    """Generates a random alphanumeric string for parameter names and values."""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

robustness_params = [
    {"alpha": "abcde12345"},
    {"numeric": "9876543210"},
    {"special": "!@#%&*()_"},
    {"empty": ""},
    {"unicode": "тестЮникод"},
]


@pytest.mark.parametrize("params", robustness_params)
def test_endpoint_handles_unexpected_params(api_client, params, attach_curl_on_fail):
    """
    Verifies that the endpoint gracefully ignores unexpected or irrelevant query parameters
    and consistently returns a valid response structure. This ensures stability.
    """
    with attach_curl_on_fail("/arp-watch/count", params, method="GET"):
        response = api_client.get("/arp-watch/count", params=params)
        assert response.status_code == 200
        data = response.json()
        assert "count" in data
        assert isinstance(data["count"], int)
        assert data["count"] >= 0 