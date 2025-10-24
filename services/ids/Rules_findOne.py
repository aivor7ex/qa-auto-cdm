import pytest
import urllib.parse
from qa_constants import SERVICES

# --- Constants ---
ENDPOINT = "Rules/findOne"
BASE_PATH_FOR_CURL = "/api/"
SERVICE_PORT = SERVICES["ids"]["port"]

# --- Schema Definitions ---
SCHEMA = {
    "id": str,
    "sid": str,
    "groupId": str,
    "message": str,
    "classtype": (str, type(None)),
    "details": dict
}

DETAILS_SCHEMA = {
    "msg": str,
    "flow": (str, type(None)),
    "content": (list, type(None)),
    "classtype": (str, type(None)),
    "sid": int,
    "rev": int,
    "depth": (int, type(None)),
    "nocase": (bool, type(None)),
    "distance": (int, type(None)),
    "fast_pattern": (bool, type(None)),
    "within": (int, type(None)),
    "reference": (str, type(None)),
    "threshold": (str, type(None)),
    "flowbits": (list, type(None)),
    "metadata": (dict, type(None))
}

# --- Helper Functions ---
def validate_schema(data, schema, parent_key="root"):
    assert isinstance(data, dict), f"{parent_key} is not a dict."
    for key, expected_type in schema.items():
        is_optional = isinstance(expected_type, tuple)
        if key not in data:
            assert is_optional, f"Mandatory key '{key}' is missing from {parent_key}."
            continue
        value = data[key]
        allowed_types = expected_type if is_optional else (expected_type,)
        assert isinstance(value, allowed_types), \
            f"Key '{key}' in {parent_key} has wrong type. Expected {allowed_types}, got {type(value)}."

# --- Fixtures ---
@pytest.fixture
def rule_data(api_client, attach_curl_on_fail):
    with attach_curl_on_fail(f"/{ENDPOINT}", payload=None, method="GET"):
        response = api_client.get(f"/{ENDPOINT}")
        assert response.status_code == 200, f"Failed to fetch a rule with findOne. Status {response.status_code}."
        data = response.json()
        validate_schema(data, SCHEMA)
        if "details" in data and data["details"] is not None:
            validate_schema(data["details"], DETAILS_SCHEMA, parent_key="details")
        return data

# --- Test Data for Parameterization ---
VALID_IDS = {
    "sid": "15003001",
    "groupId": "CDM-1.rules",
    "classtype": "trojan-activity",
    "id": "CDM-1.rules-15003001"
}

FILTER_CASES = [
    pytest.param({"filter[sid]": VALID_IDS["sid"]}, 200, "by_sid_ok"),
    pytest.param({"filter[groupId]": VALID_IDS["groupId"]}, 200, "by_groupId_ok"),
    pytest.param({"filter[id]": VALID_IDS["id"]}, 200, "by_id_ok"),
    pytest.param({"filter[sid]": "9999999999"}, 200, "by_sid_not_found_returns_first"),
    pytest.param({"filter[id]": "non-existent-id-string"}, 200, "by_id_not_found_returns_first"),
    pytest.param({"filter[classtype]": "non-existent-classtype"}, 200, "by_classtype_not_found_returns_first"),
    pytest.param({"filter[": "malformed"}, 200, "malformed_filter_returns_first"),
    pytest.param({"filter[message]": "A" * 500}, 200, "long_message_filter_returns_first"),
]
for i in range(30):
    FILTER_CASES.append(pytest.param({"filter[q]": f"search{i}"}, 200, f"robustness_q_{i}_returns_first"))

# --- Tests ---
@pytest.mark.ids
@pytest.mark.rules
def test_rule_findone_schema(rule_data):
    data = rule_data
    validate_schema(data, SCHEMA)
    if "details" in data and data["details"] is not None:
        validate_schema(data["details"], DETAILS_SCHEMA, parent_key="details")

@pytest.mark.ids
@pytest.mark.rules
@pytest.mark.parametrize("params, expected_status, test_id", FILTER_CASES)
def test_rule_findone_filters(api_client, params, expected_status, test_id, attach_curl_on_fail):
    with attach_curl_on_fail(f"/{ENDPOINT}", payload=params, method="GET"):
        response = api_client.get(f"/{ENDPOINT}", params=params)
        assert response.status_code == expected_status, f"Expected {expected_status} for params {params}, but got {response.status_code}."
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, dict), f"Response is not a dict."
            validate_schema(data, SCHEMA)
            if "details" in data and data["details"] is not None:
                validate_schema(data["details"], DETAILS_SCHEMA, parent_key="details")