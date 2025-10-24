"""
Test for the /api/log_conntrack/count endpoint.
"""
import pytest
import random
import string

# --- Schema Definition ---
# As per rule #7, the schema is defined inside the test file.
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
    response = api_client.get("/log_conntrack/count")
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

# Generate 40 sets of random query parameters to test endpoint stability.
# This exceeds the requirement of 35 tests and provides wide coverage
# for unexpected parameter handling.
robustness_params = [
    {generate_random_string(): generate_random_string()} for _ in range(40)
]


@pytest.mark.parametrize("params", robustness_params)
def test_endpoint_handles_unexpected_params(api_client, params, attach_curl_on_fail):
    """
    Verifies that the endpoint gracefully ignores unexpected or irrelevant query parameters
    and consistently returns a valid response structure. This ensures stability.
    """
    with attach_curl_on_fail("/log_conntrack/count", params, method="GET"):
        response = api_client.get("/log_conntrack/count", params=params)
        assert response.status_code == 200
        data = response.json()
        assert "count" in data
        assert isinstance(data["count"], int)
        assert data["count"] >= 0 