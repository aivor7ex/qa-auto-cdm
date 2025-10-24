import pytest
import random
import string
import urllib.parse
from qa_constants import SERVICES

# --- Constants ---
ENDPOINT = "StorageManagers/info"
BASE_PATH_FOR_CURL = "/api/"
SERVICE_PORT = SERVICES["ids"]["port"]

SCHEMA = {
    "files": int,
    "dirs": int,
    "bytes": int
}

# --- Helper Functions ---
def validate_schema(data):
    assert isinstance(data, dict), f"Response is not a dict."
    for key, expected_type in SCHEMA.items():
        assert key in data, f"Key '{key}' missing from response."
        assert isinstance(data[key], expected_type), f"Key '{key}' has wrong type."
        if key in ("files", "dirs", "bytes"):
            assert data[key] >= 0, f"Key '{key}' should be non-negative."

# --- Fixtures ---
@pytest.fixture
def storage_info_data(api_client, attach_curl_on_fail):
    with attach_curl_on_fail(f"/{ENDPOINT}", payload=None, method="GET"):
        response = api_client.get(f"/{ENDPOINT}")
        assert response.status_code == 200, f"Failed to fetch storage manager info. Status {response.status_code}."
        data = response.json()
        validate_schema(data)
        return data

# --- Test Data for Parameterization ---
def generate_random_string(length=10):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

ROBUSTNESS_CASES = []
for i in range(15):
    ROBUSTNESS_CASES.append(pytest.param(
        {generate_random_string(): generate_random_string()}, {}, f"random_param_{i}"
    ))
for i in range(15):
    ROBUSTNESS_CASES.append(pytest.param(
        {}, {f"X-{generate_random_string()}": generate_random_string()}, f"random_header_{i}"
    ))

# --- Core Tests ---
@pytest.mark.ids
def test_storage_managers_info_schema(storage_info_data):
    data = storage_info_data
    validate_schema(data)

# --- Parameterized Tests ---
@pytest.mark.ids
@pytest.mark.parametrize("params, headers, test_id", ROBUSTNESS_CASES)
def test_storage_managers_info_robustness(api_client, params, headers, test_id, attach_curl_on_fail):
    with attach_curl_on_fail(f"/{ENDPOINT}", payload=params, headers=headers, method="GET"):
        response = api_client.get(f"/{ENDPOINT}", params=params, headers=headers)
        assert response.status_code == 200, f"Expected 200 for params {params}, headers {headers}, but got {response.status_code}."
        data = response.json()
        validate_schema(data)