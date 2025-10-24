import pytest
import random
import string

# --- Schema Definition ---

SCHEMA = {
    "ok": int,
}

# --- Fixtures ---

@pytest.fixture
def status_data(api_client, attach_curl_on_fail):
    """
    Performs a single GET request to the /status endpoint.
    """
    with attach_curl_on_fail("/status", payload=None, method="GET"):
        response = api_client.get("/status")
        assert response.status_code == 200
        return response.json()

# --- Core Tests ---

def test_status_schema_and_value(status_data):
    """
    Validates the response schema and the value of the 'ok' field.
    """
    # Validate schema: presence and type of 'ok' key
    assert "ok" in status_data, "Response must contain the 'ok' key."
    assert isinstance(status_data["ok"], int), f"'ok' key must be an integer, got {type(status_data['ok'])}."
    
    # Validate value
    assert status_data["ok"] == 1, f"The value of 'ok' should be 1, but got {status_data['ok']}."

# --- Robustness Tests ---

def generate_random_string(length=10):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

# Generate 30 varied sets of parameters and headers to test endpoint stability.
# The endpoint should ignore them all.
robustness_cases = []
for _ in range(15):
    robustness_cases.append(
        pytest.param(
            {generate_random_string(): generate_random_string()},
            {},
            id=f"random_param_{_}"
        )
    )
for _ in range(15):
    robustness_cases.append(
        pytest.param(
            {},
            {f"X-{generate_random_string()}": generate_random_string()},
            id=f"random_header_{_}"
        )
    )

@pytest.mark.parametrize("params, headers", robustness_cases)
def test_status_robustness(api_client, params, headers, attach_curl_on_fail):
    """
    Verifies that the /status endpoint ignores any unexpected query parameters
    or headers and always returns a successful, valid response.
    """
    with attach_curl_on_fail("/status", payload=params, headers=headers, method="GET"):
        response = api_client.get("/status", params=params, headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        # The response should always be the same, regardless of inputs
        assert "ok" in data
        assert data["ok"] == 1