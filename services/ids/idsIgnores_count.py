import pytest
import random
import string

# --- Schema Definition ---
SCHEMA = {
    "count": int,
}

# --- Fixtures ---
@pytest.fixture
def count_data(api_client, attach_curl_on_fail):
    """
    Performs a single GET request to the /idsIgnores/count endpoint.
    """
    with attach_curl_on_fail("/idsIgnores/count", method="GET"):
        response = api_client.get("/idsIgnores/count")
        assert response.status_code == 200
        return response.json()

# --- Core Tests ---
def test_ids_ignores_count_schema(count_data):
    """
    Validates the response schema for /idsIgnores/count.
    """
    assert "count" in count_data, "Response must contain the 'count' key."
    assert isinstance(count_data["count"], int), f"'count' key must be an integer, got {type(count_data['count'])}."

# --- Robustness Tests ---
def generate_random_string(length=10):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

# Generate 30 varied sets of parameters and headers to test endpoint stability.
# The endpoint should ignore them all and return a valid count.
robustness_cases = []
for i in range(15):
    robustness_cases.append(
        pytest.param(
            {generate_random_string(): generate_random_string()},
            {},
            id=f"random_param_{i}"
        )
    )
for i in range(15):
    robustness_cases.append(
        pytest.param(
            {},
            {f"X-{generate_random_string()}": generate_random_string()},
            id=f"random_header_{i}"
        )
    )

@pytest.mark.parametrize("params, headers", robustness_cases)
def test_ids_ignores_count_robustness(api_client, params, headers, attach_curl_on_fail):
    """
    Verifies that the /idsIgnores/count endpoint ignores any unexpected query parameters
    or headers and always returns a successful, valid response.
    """
    with attach_curl_on_fail("/idsIgnores/count", payload=params, headers=headers, method="GET"):
        response = api_client.get("/idsIgnores/count", params=params, headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        # The response schema should always be valid
        assert "count" in data
        assert isinstance(data["count"], int) 