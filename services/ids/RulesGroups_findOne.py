import pytest
import urllib.parse
from datetime import datetime
from qa_constants import SERVICES

# --- Constants ---
ENDPOINT = "RulesGroups/findOne"
BASE_PATH_FOR_CURL = "/api/"
SERVICE_PORT = SERVICES["ids"]["port"]

SCHEMA = {
    "id": str,
    "created": str,
    "modified": str,
    "enabled": bool,
    "size": int,
    "rulesCount": int,
}

# --- Helper Functions ---
def is_iso8601(date_string):
    try:
        datetime.fromisoformat(date_string.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        pytest.fail(f"Invalid ISO8601 format for date: {date_string}.")

def validate_schema(data):
    assert isinstance(data, dict), f"Response is not a dict."
    for key, expected_type in SCHEMA.items():
        assert key in data, f"Mandatory key '{key}' is missing."
        assert isinstance(data[key], expected_type), f"Key '{key}' has wrong type."
    is_iso8601(data["created"])
    is_iso8601(data["modified"])
    assert data["size"] >= 0, f"Field 'size' is negative."
    assert data["rulesCount"] >= 0, f"Field 'rulesCount' is negative."

# --- Fixtures ---
@pytest.fixture
def rules_group_data(api_client, attach_curl_on_fail):
    with attach_curl_on_fail(f"/{ENDPOINT}", payload=None, method="GET"):
        response = api_client.get(f"/{ENDPOINT}")
        assert response.status_code == 200, f"Failed to fetch a rule group with findOne. Status {response.status_code}."
        data = response.json()
        validate_schema(data)
        return data

# --- Test Data for Parameterization ---
FILTER_CASES = [
    pytest.param({"filter[id]": "3coresec.rules"}, id="by_id_exists"),
    pytest.param({"filter[id]": "non-existent-id"}, id="by_id_not_found"),
    pytest.param({"filter[enabled]": "true"}, id="by_enabled_true"),
    pytest.param({"filter[enabled]": "false"}, id="by_enabled_false"),
    pytest.param({"q": "emerging"}, id="q_search"),
    pytest.param({"sort": "-size"}, id="sort_desc"),
    pytest.param({"limit": 10}, id="with_limit"),
    pytest.param({"offset": 5}, id="with_offset"),
    pytest.param({"garbage": "parameter"}, id="garbage_param"),
    pytest.param({"filter[": "malformed"}, id="malformed_filter"),
]
for i in range(25):
    FILTER_CASES.append(pytest.param({"q": f"search{i}", "limit": i}, id=f"robustness_case_{i}"))

# --- Tests ---
@pytest.mark.ids
@pytest.mark.rules_groups
def test_rules_group_findone_schema(rules_group_data):
    data = rules_group_data
    validate_schema(data)

@pytest.mark.ids
@pytest.mark.rules_groups
@pytest.mark.parametrize("params", FILTER_CASES)
def test_rules_group_findone_filters_always_return_200(api_client, params, attach_curl_on_fail):
    with attach_curl_on_fail(f"/{ENDPOINT}", payload=params, method="GET"):
        response = api_client.get(f"/{ENDPOINT}", params=params)
        assert response.status_code == 200, f"Expected 200 for params {params}, but got {response.status_code}."
        validate_schema(response.json())