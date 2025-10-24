import pytest
import random
import string

ENDPOINT = "Managers/downloadUpdates"
SCHEMA = {}

# --- Fixtures ---
@pytest.fixture
def download_updates_data(api_client, attach_curl_on_fail):
    with attach_curl_on_fail(ENDPOINT, payload=None, method="GET"):
        response = api_client.get(ENDPOINT)
        assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}"
        return response.json()

# --- Test Data for Parameterization ---
def generate_random_string(length=10):
    """Generates a random alphanumeric string."""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

# Generate ~30 varied sets of parameters and headers for robustness testing.
ROBUSTNESS_CASES = []
for i in range(15):
    ROBUSTNESS_CASES.append(pytest.param(
        {generate_random_string(): generate_random_string()}, {}, id=f"random_param_{i}"
    ))
for i in range(15):
    ROBUSTNESS_CASES.append(pytest.param(
        {}, {f"X-{generate_random_string()}": generate_random_string()}, id=f"random_header_{i}"
    ))

# --- Tests ---
@pytest.mark.ids
def test_managers_download_updates_schema(download_updates_data):
    """
    Checks that the response from GET /Managers/downloadUpdates matches the expected schema,
    which is an empty object.
    """
    assert download_updates_data == SCHEMA, f"Response data {download_updates_data} does not match schema {SCHEMA}"

@pytest.mark.ids
@pytest.mark.parametrize("params, headers", ROBUSTNESS_CASES)
def test_managers_download_updates_robustness(api_client, params, headers, attach_curl_on_fail):
    """
    Verifies that the endpoint ignores any unexpected query parameters or headers
    and consistently returns a 200 OK with an empty object.
    """
    with attach_curl_on_fail(ENDPOINT, payload=params, headers=headers, method="GET"):
        response = api_client.get(ENDPOINT, params=params, headers=headers)
        assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}"
        assert response.json() == SCHEMA, f"Response data {response.json()} does not match schema {SCHEMA}"

