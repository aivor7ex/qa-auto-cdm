import pytest
from datetime import datetime

# --- Constants ---

ENDPOINT = "/dashboard-settings-templates"

SCHEMA = {
    "id": str,
    "name": str,
    "eventsType": str,
    "rulesGroups": list,
    "createdAt": str,
    "modifiedAt": str,
}

# Static query parameters to test the endpoint's stability
PARAMS = [
    ("offset", "0"),
    ("limit", "10"),
    ("limit", "50"),
    ("limit", "100"),
    ("sort_by", "name"),
    ("sort_by", "createdAt"),
    ("sort_by", "modifiedAt"),
    ("sort_order", "asc"),
    ("sort_order", "desc"),
    ("search", "template"),
    ("search", "dashboard"),
    ("eventsType", "security"),
    ("eventsType", "network"),
    ("eventsType", "system"),
    ("name_filter", "default"),
    ("name_filter", "custom"),
    ("page", "1"),
    ("page", "2"),
    ("page_size", "20"),
    ("include_inactive", "true"),
    ("include_inactive", "false"),
    ("created_after", "2024-01-01"),
    ("created_before", "2024-12-31"),
    ("modified_after", "2024-06-01"),
    ("format", "json"),
    ("fields", "id,name"),
    ("fields", "id,name,eventsType"),
    ("expand", "rulesGroups"),
    ("category", "security"),
    ("category", "analytics"),
    ("status", "enabled"),
    ("status", "disabled"),
    ("owner", "admin"),
    ("group", "default"),
    ("type", "standard"),
    ("version", "v1"),
    ("locale", "en"),
    ("timezone", "UTC"),
    ("debug", "true"),
    ("test_param", "value")
]

# --- Helper Functions ---

def is_iso_datetime(s):
    """Helper function to check if a string is a valid ISO 8601 datetime."""
    if not isinstance(s, str):
        return False
    try:
        datetime.fromisoformat(s.replace('Z', '+00:00'))
        return True
    except (ValueError, TypeError):
        return False


# --- Tests ---

@pytest.mark.parametrize("key, value", PARAMS)
def test_dashboard_settings_templates(api_client, key, value, attach_curl_on_fail):
    """
    Test for the /api/dashboard-settings-templates endpoint.

    This test verifies that the list of dashboard settings templates is returned correctly.
    It uses parametrization with random query parameters to ensure the endpoint is stable.
    It validates the response structure, data types, and specific formats for date-time fields.
    """
    params = {key: value}
    with attach_curl_on_fail(ENDPOINT, params, method="GET"):
        response = api_client.get(ENDPOINT, params=params)
        assert response.status_code == 200, f"Expected status code 200, but got {response.status_code}"
        response_data = response.json()
        assert isinstance(response_data, list), f"Expected response to be a list, but got {type(response_data)}"
        if not response_data:
            return
        for item in response_data:
            assert isinstance(item, dict), f"Expected item to be a dict, but got {type(item)}"
            for field, expected_type in SCHEMA.items():
                assert field in item, f"Mandatory key '{field}' is missing from the response item"
                assert isinstance(item[field], expected_type), \
                    f"For key '{field}', expected type {expected_type}, but got {type(item[field])}"
            assert all(isinstance(group, str) for group in item["rulesGroups"]), \
                "All items in 'rulesGroups' list must be strings"
            assert is_iso_datetime(item["createdAt"]), f"Field 'createdAt' has an invalid format: {item['createdAt']}"
            assert is_iso_datetime(item["modifiedAt"]), f"Field 'modifiedAt' has an invalid format: {item['modifiedAt']}" 