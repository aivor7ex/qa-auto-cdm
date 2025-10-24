"""
Test for the /api/log-records/count endpoint.
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
    response = api_client.get("/log-records/count")
    return response

# --- Core Tests ---
def test_status_code(api_response):
    assert api_response.status_code == 200, \
        f"Expected status code 200, but got {api_response.status_code}. Response: {api_response.text}"

def test_count_schema_and_value(api_response):
    response_json = api_response.json()
    for key in COUNT_SCHEMA["required"]:
        assert key in response_json, f"Required key '{key}' is missing from the response."
    count_value = response_json["count"]
    expected_type = COUNT_SCHEMA["required"]["count"]
    assert isinstance(count_value, expected_type), \
        f"Key 'count' has type {type(count_value).__name__}, but expected {expected_type.__name__}."
    assert count_value >= 0, f"'count' should be a non-negative integer, but got {count_value}."

# --- Robustness and Parametrization Tests ---
def generate_random_string(length=10):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

robustness_params = [
    {generate_random_string(): generate_random_string()} for _ in range(40)
]


@pytest.mark.parametrize("params", robustness_params)
def test_endpoint_handles_unexpected_params(api_client, params, attach_curl_on_fail):
    with attach_curl_on_fail("/log-records/count", params, method="GET"):
        response = api_client.get("/log-records/count", params=params)
        assert response.status_code == 200
        data = response.json()
        assert "count" in data
        assert isinstance(data["count"], int)
        assert data["count"] >= 0 