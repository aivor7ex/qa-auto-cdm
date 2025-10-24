import pytest
from datetime import datetime


def is_iso_datetime(s):
    """
    Helper function to check if a string is a valid ISO 8601 datetime.
    The format from the example is ISO 8601 with 'Z' for UTC.
    Example: "2025-06-23T13:09:11.936Z"
    """
    if not isinstance(s, str):
        return False
    try:
        # datetime.fromisoformat handles timezone-aware strings ending in Z
        datetime.fromisoformat(s.replace('Z', '+00:00'))
        return True
    except (ValueError, TypeError):
        return False


def is_valid_time_interval(s):
    """
    Helper function to check if a string is a valid time interval.
    Example: '2025-06-23T16:08:00+03:00 - 2025-06-23T16:08:00+03:00'
    """
    if not isinstance(s, str):
        return False
    parts = s.split(' - ')
    if len(parts) != 2:
        return False
    try:
        # datetime.fromisoformat handles timezone-aware strings with +XX:XX offset
        datetime.fromisoformat(parts[0])
        datetime.fromisoformat(parts[1])
        return True
    except (ValueError, TypeError):
        return False


# Define the schema for mandatory and optional fields for the response items.
# This makes the expected structure clear and easy to maintain.
MANDATORY_SCHEMA = {
    "id": str,
    "name": str,
    "summaryChartDangers": bool,
    "differentialChartDangers": bool,
    "top10": bool,
    "createdRulesData": bool,
    "rulesInvocationsData": bool,
    "timeIntervalString": str,
    "timeIntervalMode": str,
    "createdAt": str,
    "modifiedAt": str,
}
OPTIONAL_SCHEMA = {
    "timeInterval": str,
}


# A list of static query parameters for parametrization.
# This list aims to test the endpoint's stability and resilience 
# against a variety of realistic inputs.
STATIC_PARAMS = [
    ("offset", 0),
    ("offset", 10),
    ("offset", 50),
    ("limit", 1),
    ("limit", 10),
    ("limit", 50),
    ("limit", 100),
    ("limit", 200),
    ("sort_by", "createdAt"),
    ("sort_by", "modifiedAt"),
    ("sort_by", "name"),
    ("sort_order", "asc"),
    ("sort_order", "desc"),
    ("from_date", "2024-01-01"),
    ("from_date", "2024-06-01"),
    ("to_date", "2024-12-31"),
    ("to_date", "2024-09-30"),
    ("search_query", "security"),
    ("search_query", "report"),
    ("search_query", "template"),
    ("template_id", "template123"),
    ("template_id", "security456"),
    ("template_name", "security_summary"),
    ("template_name", "daily_report"),
    ("template_name", "weekly_analysis"),
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
    ("invalid_parameter", "value_that_should_be_ignored"),
]

PARAMS = STATIC_PARAMS




@pytest.mark.parametrize("key, value", PARAMS)
def test_security_report_templates(api_client, key, value, attach_curl_on_fail):
    """
    Test for the /api/security-report-templates endpoint.

    This test sends a GET request with a variety of query parameters to ensure
    the endpoint is stable and always returns a structurally correct response.
    It validates the response schema, data types, and specific formats for
    date-time fields.
    """
    # 1. Arrange: Prepare the request
    endpoint = "/security-report-templates"
    params = {key: value}

    # 2. Act: Send the request to the API
    with attach_curl_on_fail(endpoint, params, method="GET"):
        response = api_client.get(endpoint, params=params)

        # 3. Assert: Validate the response
        assert response.status_code == 200, f"Expected status code 200, but got {response.status_code}"

        response_data = response.json()
        assert isinstance(response_data, list), f"Expected response to be a list, but got {type(response_data)}"

        # If the list is empty, the test passes as the structure is valid
        if not response_data:
            return

        # Validate each item in the response list
        for item in response_data:
            assert isinstance(item, dict), f"Expected item to be a dict, but got {type(item)}"

            # Check for presence and type of mandatory fields
            for field, expected_type in MANDATORY_SCHEMA.items():
                assert field in item, f"Mandatory key '{field}' is missing from the response item"
                assert isinstance(item[field], expected_type), \
                    f"For key '{field}', expected type {expected_type}, but got {type(item[field])}"

            # Check for type of optional fields if they exist
            for field, expected_type in OPTIONAL_SCHEMA.items():
                if field in item:
                    assert isinstance(item[field], expected_type), \
                        f"For optional key '{field}', expected type {expected_type}, but got {type(item[field])}"

            # Perform special validations for date and time formats
            assert is_iso_datetime(item["createdAt"]), f"Field 'createdAt' has an invalid ISO 8601 format: {item['createdAt']}"
            assert is_iso_datetime(item["modifiedAt"]), f"Field 'modifiedAt' has an invalid ISO 8601 format: {item['modifiedAt']}"
            if "timeInterval" in item:
                assert is_valid_time_interval(item["timeInterval"]), \
                    f"Field 'timeInterval' has an invalid format: {item['timeInterval']}" 