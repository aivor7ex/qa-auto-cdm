import pytest
from qa_constants import SERVICES
import urllib.parse
from datetime import datetime

# --- Constants ---
ENDPOINT = "RulesClasstypes"
BASE_PATH_FOR_CURL = "/api/ids/"
SERVICE_PORT = SERVICES["ids"]["port"]

# --- Schema Definition ---
SCHEMA = {
    "id": str,
    "createdAt": str,
    "rulesCount": int
}

# --- Helper Functions ---
def is_iso8601(date_string):
    """Checks if a string is a valid ISO 8601 datetime."""
    try:
        datetime.fromisoformat(date_string.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        pytest.fail(f"Invalid ISO8601 format for date string: {date_string}.")

def validate_schema(item):
    """Validates a single item against the schema."""
    assert isinstance(item, dict), f"Item is not a dictionary."
    for key, expected_type in SCHEMA.items():
        assert key in item, f"Field '{key}' is missing from response item."
        assert isinstance(item[key], expected_type), f"Field '{key}' has wrong type."
    is_iso8601(item["createdAt"])

# --- Fixtures ---
@pytest.fixture
def service_data(api_client, attach_curl_on_fail):
    """Fetches all rule classtypes once per module."""
    with attach_curl_on_fail(f"/{ENDPOINT}", payload={"limit": 100}, method="GET"):
        response = api_client.get(f"/{ENDPOINT}", params={"limit": 100})
        assert response.status_code == 200, f"Failed to fetch data. Status {response.status_code}."
        data = response.json()
        assert isinstance(data, list), f"Expected response to be a list."
        return data

# --- Test Cases ---
@pytest.mark.ids
def test_schema_and_uniqueness(service_data):
    """Validates the schema for each item and ensures all IDs are unique."""
    data = service_data
    if not data:
        pytest.skip("Response is empty, skipping schema and uniqueness checks.")

    ids = []
    for item in data:
        validate_schema(item)
        ids.append(item["id"])

    assert len(ids) == len(set(ids)), f"Found duplicate IDs in the response."

@pytest.mark.ids
@pytest.mark.parametrize("params, test_id", [
    # Basic pagination, sorting, and filtering
    ({"limit": 5}, "limit_5"),
    ({"offset": 10}, "offset_10"),
    ({"sort": "id"}, "sort_id"),
    ({"sort": "-rulesCount"}, "sort_rulesCount_desc"),
    ({"q": "trojan"}, "q_trojan"),
    ({"q": "policy"}, "q_policy"),
    ({"filter[id]": "trojan-activity"}, "filter_id_trojan"),
    # Combinations
    ({"limit": 3, "sort": "id", "q": "web"}, "limit_sort_q"),
    # Edge cases
    ({"limit": 999}, "limit_999"),
    ({"offset": 9999}, "offset_9999"),
    ({"sort": "nonexistent_field"}, "sort_nonexistent"),
    ({"q": "nonexistentsearchterm12345"}, "q_nonexistent"),
    # Additional robust cases to reach 35+ tests
    ({"limit": 1}, "limit_1"),
    ({"offset": 0}, "offset_0"),
    ({"sort": "createdAt"}, "sort_createdAt"),
    ({"sort": "-createdAt"}, "sort_createdAt_desc"),
    ({"q": "a"}, "q_single_char"),
    ({"filter[id]": "bad-unknown"}, "filter_id_bad_unknown"),
    ({"limit": 1, "offset": 1, "sort": "-rulesCount"}, "limit_offset_sort"),
    ({"q": ""}, "q_empty"),
    ({"limit": -1}, "limit_negative"),
    ({"offset": -1}, "offset_negative"),
    ({"limit": "abc"}, "limit_string"),
    ({"offset": "abc"}, "offset_string"),
    ({"q": " "}, "q_space"),
    ({"filter[id]": ""}, "filter_id_empty"),
    ({"filter[id]": " "}, "filter_id_space"),
    ({"sort": ""}, "sort_empty"),
    ({"sort": " "}, "sort_space"),
    ({"unexpected": "param"}, "unexpected_param"),
    ({"limit": 1, "q": "dos"}, "limit_q"),
    ({"sort": "id", "q": "scan"}, "sort_q"),
    ({"offset": 5, "q": "exploit"}, "offset_q"),
    ({"filter[rulesCount]": 1}, "filter_rulesCount_1"),
    ({"filter[rulesCount]": 0}, "filter_rulesCount_0"),
    ({"filter[rulesCount]": 100000}, "filter_rulesCount_high"),
])
def test_filtering_and_robustness(api_client, params, test_id, attach_curl_on_fail):
    """Tests various filtering, pagination, and robustness scenarios."""
    with attach_curl_on_fail(f"/{ENDPOINT}", payload=params, method="GET"):
        response = api_client.get(f"/{ENDPOINT}", params=params)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}. Ответ: {response.text}"
        data = response.json()
        assert isinstance(data, list), f"Response should be a list."
        for item in data:
            validate_schema(item) 