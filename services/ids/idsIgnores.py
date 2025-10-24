import pytest
import random
import string

# --- Schema Definitions ---

# Defines the schema for the nested 'match' object.
# 'sid' is required, others are optional.
MATCH_SCHEMA = {
    "required": {"sid": int},
    "optional": {
        "dest_ip": list,
        "src_net": list,
    },
}

# Defines the schema for the main item in the response list.
IDS_IGNORE_SCHEMA = {
    "required": {
        "hash": str,
        "description": str,
        "match": dict,
        "active": bool,
        "id": str,
    },
    "optional": {},
}

# --- Validation Helper ---

def _validate_schema(data, schema):
    """
    Validates a data dictionary against a schema with 'required' and 'optional' parts.
    """
    for key, expected_type in schema.get("required", {}).items():
        assert key in data, f"Required key '{key}' missing from data: {data}"
        assert isinstance(data[key], expected_type), f"Key '{key}' has wrong type."

    for key, expected_type in schema.get("optional", {}).items():
        if key in data:
            assert isinstance(data[key], expected_type), f"Optional key '{key}' has wrong type."
            if expected_type is list:
                assert all(isinstance(elem, str) for elem in data[key]), f"Elements of list '{key}' must be strings."

# --- Fixtures ---

@pytest.fixture
def ids_ignores_data(api_client, attach_curl_on_fail):
    """
    Fetches all idsIgnores rules once and provides them to the tests.
    """
    with attach_curl_on_fail("/idsIgnores", method="GET"):
        response = api_client.get("/idsIgnores")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        if not data:
            pytest.skip("Response is empty, skipping detailed validation.")
        return data

# --- Core Tests ---

def test_ids_ignores_schema(ids_ignores_data):
    """
    Validates the schema of each item returned by the /idsIgnores endpoint.
    """
    for item in ids_ignores_data:
        _validate_schema(item, IDS_IGNORE_SCHEMA)
        _validate_schema(item["match"], MATCH_SCHEMA)

def test_ids_ignores_unique_ids(ids_ignores_data):
    """
    Checks that all returned items have a unique ID.
    """
    ids = [item["id"] for item in ids_ignores_data]
    assert len(ids) == len(set(ids)), f"Found duplicate IDs in response: {ids}"

# --- Filtering and Robustness Tests ---

def generate_random_string(length=8):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

# ~35 test cases for various filters, sorting, and edge cases.
filter_params = [
    # Basic filtering
    {"active": "true"}, {"active": "false"},
    {"sid": "999999"}, {"dest_ip": "10.0.0.2"},
    {"description": "Test"}, {"hash": "some_hash"},
    # Sorting
    {"sort": "id"}, {"sort": "-description"},
    # Pagination
    {"limit": 5}, {"offset": 1},
    {"limit": 1, "offset": 1},
    # Edge cases
    {"limit": 0}, {"limit": -1}, {"offset": -1},
    # Non-existent filters
    {"sid": "0"}, {"description": generate_random_string()},
    # Combined and unexpected
    {"active": "true", "sort": "id"},
    {"unexpected": "param"},
]
# Add more random cases
for _ in range(15):
    filter_params.append({generate_random_string(): generate_random_string()})

@pytest.mark.parametrize("params", filter_params)
def test_ids_ignores_filters_and_robustness(api_client, params, attach_curl_on_fail):
    """
    Checks endpoint stability and correct handling of various query parameters.
    """
    with attach_curl_on_fail("/idsIgnores", payload=params, method="GET"):
        response = api_client.get("/idsIgnores", params=params)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # If data is returned, perform a light schema check
        if data:
            for item in data:
                _validate_schema(item, IDS_IGNORE_SCHEMA)
                _validate_schema(item["match"], MATCH_SCHEMA) 