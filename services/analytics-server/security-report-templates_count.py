import pytest

# --- Constants ---

ENDPOINT = "/security-report-templates/count"

SCHEMA = {
    "count": int
}

# Static query parameters to test the endpoint's stability
# and ensure it correctly handles or ignores unexpected inputs.
PARAMS = [
    ("offset", "0"),
    ("offset", "10"),
    ("offset", "50"),
    ("limit", "1"),
    ("limit", "10"),
    ("limit", "50"),
    ("limit", "100"),
    ("limit", "200"),
    ("search_query", "security"),
    ("search_query", "report"),
    ("search_query", "template"),
    ("template_id", "template123"),
    ("template_id", "security456"),
    ("template_name", "security_summary"),
    ("template_name", "daily_report"),
    ("template_name", "weekly_analysis"),
    ("from_date", "2024-01-01"),
    ("from_date", "2024-06-01"),
    ("to_date", "2024-12-31"),
    ("to_date", "2024-09-30"),
    ("mode", "last"),
    ("mode", "interval"),
    ("user_id", "user-123"),
    ("user_id", "admin"),
    ("status_filter", "active"),
    ("status_filter", "inactive"),
    ("report_type", "summary"),
    ("report_type", "detailed"),
    ("category", "security"),
    ("category", "analytics"),
    ("format", "json"),
    ("timezone", "UTC"),
    ("locale", "en"),
    ("debug", "true"),
    ("sort_by", "createdAt"),
    ("sort_by", "modifiedAt"),
    ("sort_by", "name"),
    ("sort_order", "asc"),
    ("sort_order", "desc"),
    ("test_param", "value"),
    ("invalid_parameter", "value_that_should_be_ignored")
]

# --- Tests ---

@pytest.mark.parametrize("key, value", PARAMS)
def test_security_report_templates_count(api_client, key, value, attach_curl_on_fail):
    """
    Test for the /api/security-report-templates/count endpoint.

    This test verifies that the count endpoint is stable and consistently returns
    a valid response structure, regardless of the query parameters provided.
    It checks for a 200 OK status and ensures the response body contains a single
    'count' field with an integer value.
    """
    # 1. Arrange
    params = {key: value}

    # 2. Act
    with attach_curl_on_fail(ENDPOINT, params, method="GET"):
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