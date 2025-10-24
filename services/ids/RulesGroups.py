import pytest
import urllib.parse
from datetime import datetime
from qa_constants import SERVICES

# --- Constants ---
ENDPOINT = "RulesGroups"
BASE_PATH_FOR_CURL = "/api/"
SERVICE_PORT = SERVICES["ids"]["port"]

SCHEMA = {
    "id": str,
    "created": str,
    "modified": str,
    "enabled": bool,
    "size": int,
    "rulesCount": int
}

# --- Helper Functions ---
def is_iso8601(date_string):
    try:
        datetime.fromisoformat(date_string.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        pytest.fail(f"Invalid ISO8601 format for date: {date_string}.")

def validate_schema(item):
    assert isinstance(item, dict), f"Item is not a dict."
    for key, expected_type in SCHEMA.items():
        assert key in item, f"Field '{key}' missing."
        assert isinstance(item[key], expected_type), f"Field '{key}' has wrong type."
    is_iso8601(item["created"])
    is_iso8601(item["modified"])

# --- Fixtures ---
@pytest.fixture
def rules_groups_data(api_client, attach_curl_on_fail):
    with attach_curl_on_fail(f"/{ENDPOINT}", payload={"limit": 1000}, method="GET"):
        response = api_client.get(f"/{ENDPOINT}", params={"limit": 1000})
        assert response.status_code == 200, f"Failed to fetch rule groups. Status {response.status_code}."
        data = response.json()
        assert isinstance(data, list), f"Rule groups response should be a list."
        return data

# --- Test Cases ---
@pytest.mark.ids
@pytest.mark.rules_groups
def test_schema_and_unique_ids(rules_groups_data):
    """
    Проверяет схему и уникальность id для всех групп правил.
    """
    data = rules_groups_data
    assert data, f"Test requires at least one rule group."
    ids = set()
    for item in data:
        validate_schema(item)
        assert item["id"] not in ids, f"Duplicate id '{item['id']}' found."
        ids.add(item["id"])

# --- Parameterized Tests for Filters and Robustness ---
ROBUSTNESS_PARAMS = [
    # Basic pagination and sorting
    ({"limit": 10}, "limit_10"),
    ({"limit": 1}, "limit_1"),
    ({"offset": 5}, "offset_5"),
    ({"sort": "id"}, "sort_id"),
    ({"sort": "-size"}, "sort_size_desc"),
    ({"sort": "rulesCount"}, "sort_rulesCount"),
    # Search query
    ({"q": ".rules"}, "q_dot_rules"),
    ({"q": "emerging"}, "q_emerging"),
    ({"q": "nonexistentterm"}, "q_nonexistent"),
    # Filtering
    ({"filter[enabled]": "true"}, "filter_enabled_true"),
    ({"filter[enabled]": "false"}, "filter_enabled_false"),
    ({"filter[enabled]": "not-a-boolean"}, "filter_enabled_invalid"),
    # Combinations
    ({"limit": 5, "sort": "-rulesCount"}, "limit_5_sort_rulesCount_desc"),
    ({"offset": 10, "q": "ET", "filter[enabled]": "true"}, "offset_10_q_ET_filter_enabled_true"),
    # Edge cases
    ({"limit": 9999}, "limit_9999"),
    ({"offset": 99999}, "offset_99999"),
    ({"sort": "nonexistent_field"}, "sort_nonexistent"),
    # Robustness: unusual/invalid/empty params
    ({"limit": -1}, "limit_negative"),
    ({"offset": -1}, "offset_negative"),
    ({"limit": "abc"}, "limit_string"),
    ({"offset": "abc"}, "offset_string"),
    ({"q": ""}, "q_empty"),
    ({"filter[enabled]": ""}, "filter_enabled_empty"),
    ({"sort": ""}, "sort_empty"),
    ({"unexpected": "param"}, "unexpected_param"),
    ({"limit": 1, "q": "dos"}, "limit_1_q_dos"),
    ({"sort": "id", "q": "scan"}, "sort_id_q_scan"),
    ({"offset": 5, "q": "exploit"}, "offset_5_q_exploit"),
    ({"filter[size]": 0}, "filter_size_0"),
    ({"filter[rulesCount]": 0}, "filter_rulesCount_0"),
    ({"filter[rulesCount]": 100000}, "filter_rulesCount_high"),
    # Add more to ensure 35+
    ({"limit": 2, "offset": 2}, "limit_2_offset_2"),
    ({"sort": "-created"}, "sort_created_desc"),
    ({"sort": "-modified"}, "sort_modified_desc"),
    ({"q": "rules"}, "q_rules"),
    ({"filter[size]": 100}, "filter_size_100"),
    ({"filter[size]": -1}, "filter_size_negative"),
    ({"filter[size]": "abc"}, "filter_size_string"),
    ({"filter[rulesCount]": "abc"}, "filter_rulesCount_string"),
    ({"filter[enabled]": None}, "filter_enabled_none"),
]

@pytest.mark.ids
@pytest.mark.rules_groups
@pytest.mark.parametrize("params,test_id", ROBUSTNESS_PARAMS)
def test_rules_groups_filters(api_client, params, test_id, attach_curl_on_fail):
    with attach_curl_on_fail(f"/{ENDPOINT}", payload=params, method="GET"):
        response = api_client.get(f"/{ENDPOINT}", params=params)
        assert response.status_code == 200, f"Expected status 200 for params {params}, but got {response.status_code}."
        data = response.json()
        assert isinstance(data, list), f"API response for params {params} should be a list."
        for item in data:
            validate_schema(item)