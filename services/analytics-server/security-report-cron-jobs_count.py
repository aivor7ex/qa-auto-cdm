import pytest

# --- Constants ---

ENDPOINT = "/security-report-cron-jobs/count"

SCHEMA = {
    "count": int
}

# Static query parameters to test the endpoint's stability
PARAMS = [
    ("offset", "0"),
    ("limit", "10"),
    ("limit", "50"),
    ("limit", "100"),
    ("search", "cron"),
    ("search", "job"),
    ("active", "true"),
    ("active", "false"),
    ("name_filter", "daily"),
    ("name_filter", "weekly"),
    ("name_filter", "monthly"),
    ("template_id", "template123"),
    ("template_id", "security456"),
    ("created_after", "2024-01-01"),
    ("created_before", "2024-12-31"),
    ("modified_after", "2024-06-01"),
    ("status", "enabled"),
    ("status", "disabled"),
    ("format", "json"),
    ("filter", "active_jobs"),
    ("category", "security"),
    ("owner", "admin"),
    ("group", "default"),
    ("type", "scheduled"),
    ("timezone", "UTC"),
    ("locale", "en"),
    ("debug", "true"),
    ("include_inactive", "true"),
    ("include_inactive", "false"),
    ("sort_by", "name"),
    ("sort_by", "createdAt"),
    ("sort_order", "asc"),
    ("sort_order", "desc"),
    ("page", "1"),
    ("page", "2"),
    ("page_size", "20"),
    ("fields", "id,name,active"),
    ("expand", "template"),
    ("test_param", "value"),
    ("invalid_param", "ignored")
]

# --- Tests ---
# The `_format_curl_command` function is removed as `attach_curl_on_fail` fixture will be used instead.

@pytest.mark.parametrize("key, value", PARAMS)
def test_security_report_cron_jobs_count(api_client, key, value, attach_curl_on_fail):
    """
    Test for the /api/security-report-cron-jobs/count endpoint.

    This test verifies that the count endpoint is stable and consistently returns
    a valid response structure, regardless of the query parameters provided.
    It checks for a 200 OK status and ensures the response body contains a single
    'count' field with an integer value.
    """
    # 1. Arrange
    params = {key: value}

    # 2. Act
    with attach_curl_on_fail(ENDPOINT, payload=params, method="GET"):
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