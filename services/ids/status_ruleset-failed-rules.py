import pytest
import random
import string

# --- Schema Definition ---

DETAILS_SCHEMA = {
    "required": {
        "msg": str,
        "sid": int,
        "rev": int,
    },
    "optional": {
        "classtype": str,
        "flow": str,
        "content": list,
        "reference": list,
        "metadata": dict,
        "app-layer-event": str,
        "within": int,
        "fast_pattern": (bool, str),
        "nocase": bool,
        "depth": int,
        "offset": int,
        "distance": int,
        "flowbits": list,
    }
}

ITEM_SCHEMA = {
    "required": {
        "id": str,
        "details": dict,
        "raw": str,
        "sid": str,
        "groupId": str,
        "message": str,
        "classtype": str,
        "tenantId": int,
        "rawRule": str,
    },
    "optional": {}
}

# --- Validation Helper ---

def _validate_schema(data, schema, path=""):
    """
    Recursively validates data against a schema with 'required' and 'optional' keys.
    """
    for key, expected_type in schema.get("required", {}).items():
        assert key in data, f"Path '{path}': Required key '{key}' is missing."
        value = data[key]
        assert isinstance(value, expected_type), \
            f"Path '{path}.{key}': Expected type {expected_type}, got {type(value)}."

    for key, expected_type in schema.get("optional", {}).items():
        if key in data:
            value = data[key]
            assert isinstance(value, expected_type), \
                f"Path '{path}.{key}': Optional key has wrong type. Expected {expected_type}, got {type(value)}."

# --- Fixtures ---

@pytest.fixture
def failed_rules_data(api_client, attach_curl_on_fail):
    """
    Performs a single GET request to the endpoint and returns the JSON response.
    This fixture is used by all tests to minimize network requests.
    """
    with attach_curl_on_fail("/status/ruleset-failed-rules", method="GET"):
        response = api_client.get("/status/ruleset-failed-rules")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list), "Response is not a list."
    # Only proceed with tests if there's data to check
    if not data:
        pytest.skip("Response is empty, skipping detailed checks.")
    return data

# --- Core Tests ---

def test_failed_rules_schema(failed_rules_data):
    """
    Validates that each item in the response list conforms to the defined schema.
    """
    for item in failed_rules_data:
        _validate_schema(item, ITEM_SCHEMA, path="item")
        # Validate the nested 'details' object
        if "details" in item:
            _validate_schema(item["details"], DETAILS_SCHEMA, path="item.details")

def test_data_integrity_and_consistency(failed_rules_data):
    """
    Performs several data integrity checks on each item.
    - Non-empty strings for key fields.
    - Consistency between top-level 'sid' and 'details.sid'.
    """
    for item in failed_rules_data:
        # Check that key string fields are not empty
        for key in ["id", "raw", "sid", "groupId", "message", "classtype", "rawRule"]:
            assert isinstance(item[key], str) and item[key].strip(), f"Field '{key}' must be a non-empty string."

        # Check SID consistency
        if "details" in item and "sid" in item["details"]:
            assert item["sid"] == str(item["details"]["sid"]), "SID mismatch between top-level and details."
        
        # Check that tenantId is a non-negative integer
        assert item["tenantId"] >= 0

# --- Robustness Tests ---

def generate_random_string(length=8):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

# Generate 30 sets of random query parameters for robustness testing
robustness_params = [
    {generate_random_string(): generate_random_string()} for _ in range(30)
]
robustness_params.extend([
    {"limit": 10, "offset": 5},
    {"sort_by": "sid", "order": "desc"},
    {"filter[classtype]": "exploit-kit"},
])

@pytest.mark.parametrize("params", robustness_params)
def test_endpoint_robustness_with_params(api_client, params, attach_curl_on_fail):
    """
    Checks that the endpoint remains stable and returns a valid (even if empty)
    list structure when given various unexpected query parameters.
    """
    with attach_curl_on_fail("/status/ruleset-failed-rules", method="GET"):
        response = api_client.get("/status/ruleset-failed-rules", params=params)
        assert response.status_code == 200
        assert isinstance(response.json(), list)

# Generate 25 sets of random headers for robustness testing
robustness_headers = [
    {f"X-{generate_random_string().title()}": generate_random_string()} for _ in range(25)
]
robustness_headers.extend([
    {"Accept": "text/plain"},
    {"X-Custom-Auth": "some-token"},
    {"If-None-Match": "some-etag"},
])

@pytest.mark.parametrize("headers", robustness_headers)
def test_endpoint_robustness_with_headers(api_client, headers, attach_curl_on_fail):
    """
    Checks that the endpoint remains stable and returns a valid list structure
    when given various unexpected headers.
    """
    with attach_curl_on_fail("/status/ruleset-failed-rules", headers=headers, method="GET"):
        response = api_client.get("/status/ruleset-failed-rules", headers=headers)
        # The server correctly returns 406 if the client requests an unsupported content type.
        # We should handle this case gracefully instead of failing the test.
        if headers.get("Accept") and "application/json" not in headers["Accept"]:
            assert response.status_code == 406
        else:
            assert response.status_code == 200
            assert isinstance(response.json(), list) 