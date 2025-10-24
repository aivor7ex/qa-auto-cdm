import pytest

# --- Schema Definition ---
SCHEMA = {
    "id": str,
    "source": str,
    "description": str,
    "active": bool,
    "link": bool,
}

# --- Fixtures ---
@pytest.fixture
def rule_sources_data(api_client, attach_curl_on_fail):
    """ Fetches all rule sources once per module. """
    with attach_curl_on_fail("ruleSources", payload=None, method="GET"):
        response = api_client.get("ruleSources")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        return data

# --- Test Data for Parameterization ---
FILTER_CASES = [
    {"limit": 1},
    {"offset": 1},
    {"sort": "id"},
    {"sort": "-source"},
    {"q": "emergingthreats"},
    {"filter[active]": "true"},
    {"filter[active]": "false"},
    {"limit": 1, "sort": "id", "filter[active]": "true"},
    {"limit": 999},
    {"offset": 9999},
    {"sort": "nonexistent_field"},
    {"q": "nonexistentsearchterm"},
]

ROBUSTNESS_PARAMS = (
    [pytest.param(p, id=f"param_{list(p.keys())[0]}_{list(p.values())[0]}") for p in FILTER_CASES] +
    [pytest.param({"limit": i}, id=f"limit_robust_{i}") for i in range(20)]
)

# --- Core Tests ---
@pytest.mark.ids
def test_rule_sources_schema(rule_sources_data):
    """ Validates the schema for each rule source in the response. """
    assert rule_sources_data, "Test requires at least one rule source to be present"
    for item in rule_sources_data:
        for key, expected_type in SCHEMA.items():
            assert key in item, f"Key '{key}' missing in item {item.get('id')}"
            assert isinstance(item[key], expected_type), f"Key '{key}' in {item.get('id')} has wrong type"

@pytest.mark.ids
def test_rule_sources_unique_ids(rule_sources_data):
    """ Ensures that all rule source IDs are unique. """
    ids = [item["id"] for item in rule_sources_data]
    assert len(ids) == len(set(ids)), "Found duplicate rule source IDs"

# --- Parameterized Tests ---
@pytest.mark.ids
@pytest.mark.parametrize("params", ROBUSTNESS_PARAMS)
def test_rule_sources_filters(api_client, params, attach_curl_on_fail):
    """
    Tests various filtering and pagination parameters.
    Only checks for a successful response (200) and that the body is a list.
    """
    with attach_curl_on_fail("ruleSources", payload=params, method="GET"):
        response = api_client.get("ruleSources", params=params)
        assert response.status_code == 200
        assert isinstance(response.json(), list)