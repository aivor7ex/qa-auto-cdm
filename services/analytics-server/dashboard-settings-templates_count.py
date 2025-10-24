import pytest

# --- Constants ---

ENDPOINT = "/dashboard-settings-templates/count"

SCHEMA = {
    "count": int
}

# Static query parameters to test the endpoint's stability
PARAMS = [
    ("offset", "0"),
    ("limit", "10"),
    ("limit", "50"),
    ("limit", "100"),
    ("search", "template"),
    ("search", "dashboard"),
    ("eventsType", "security"),
    ("eventsType", "network"),
    ("eventsType", "system"),
    ("name_filter", "default"),
    ("name_filter", "custom"),
    ("include_inactive", "true"),
    ("include_inactive", "false"),
    ("created_after", "2024-01-01"),
    ("created_before", "2024-12-31"),
    ("modified_after", "2024-06-01"),
    ("filter", "active"),
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
    ("format", "json"),
    ("fields", "id,name"),
    ("expand", "rulesGroups"),
    ("sort_by", "name"),
    ("sort_by", "createdAt"),
    ("sort_order", "asc"),
    ("sort_order", "desc"),
    ("page", "1"),
    ("page", "2"),
    ("page_size", "20"),
    ("test_param", "value"),
    ("invalid_param", "ignored")
]

# --- Tests ---

@pytest.mark.parametrize("key, value", PARAMS)
def test_dashboard_settings_templates_count(api_client, key, value, attach_curl_on_fail):
    """
    Test for the /api/dashboard-settings-templates/count endpoint.

    This test verifies that the count endpoint is stable and consistently returns
    a valid response structure, regardless of the query parameters provided.
    It checks for a 200 OK status and ensures the response body contains a single
    'count' field with an integer value.
    """
    # 1. Arrange
    params = {key: value}
    
    with attach_curl_on_fail(ENDPOINT, payload=params, method="GET"):
    # 2. Act
        response = api_client.get(ENDPOINT, params=params)

    # 3. Assert
    assert response.status_code == 200, f"Expected status code 200, but got {response.status_code}"
    response_data = response.json()
    assert isinstance(response_data, dict), f"Expected response to be a dict, but got {type(response_data)}"

    # Validate schema
    for field, expected_type in SCHEMA.items():
        assert field in response_data, f"Mandatory key '{field}' is missing from the response"
        assert isinstance(response_data[field], expected_type), \
            f"For key '{field}', expected type {expected_type}, but got {type(response_data[field])}"

    # Ensure no extra keys are present
    assert len(response_data.keys()) == len(SCHEMA.keys()), "Response contains unexpected keys" 