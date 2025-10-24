import pytest
from datetime import datetime

# --- Constants ---

ENDPOINT = "/security-report-cron-jobs"

SCHEMA = {
    "id": str,
    "name": str,
    "securityReportTemplateId": str,
    "to": list,
    "cronTemplate": str,
    "active": bool,
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
    ("search", "cron"),
    ("search", "job"),
    ("active", "true"),
    ("active", "false"),
    ("name_filter", "daily"),
    ("name_filter", "weekly"),
    ("name_filter", "monthly"),
    ("template_id", "template123"),
    ("template_id", "security456"),
    ("page", "1"),
    ("page", "2"),
    ("page_size", "20"),
    ("created_after", "2024-01-01"),
    ("created_before", "2024-12-31"),
    ("modified_after", "2024-06-01"),
    ("status", "enabled"),
    ("status", "disabled"),
    ("format", "json"),
    ("fields", "id,name,active"),
    ("fields", "id,name,cronTemplate"),
    ("expand", "template"),
    ("category", "security"),
    ("owner", "admin"),
    ("group", "default"),
    ("type", "scheduled"),
    ("timezone", "UTC"),
    ("locale", "en"),
    ("debug", "true"),
    ("include_inactive", "true"),
    ("include_inactive", "false"),
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

def is_valid_cron(s):
    """
    Checks if a string is a valid cron template (5 space-separated parts).
    This is a basic check and doesn't validate the value of each part.
    """
    if not isinstance(s, str):
        return False
    return len(s.split()) == 5


# --- Tests ---

@pytest.mark.parametrize("key, value", PARAMS)
def test_security_report_cron_jobs(api_client, key, value, attach_curl_on_fail):
    """
    Test for the /api/security-report-cron-jobs endpoint.

    This test verifies that the list of cron jobs is returned correctly.
    It uses parametrization with random query parameters to ensure the endpoint
    is stable. It validates the response structure, data types, and specific
    formats for cron and date-time fields.
    """
    # 1. Arrange
    params = {key: value}

    # 2. Act
    with attach_curl_on_fail(ENDPOINT, params, method="GET"):
        response = api_client.get(ENDPOINT, params=params)

        # 3. Assert
        assert response.status_code == 200, f"Expected status code 200, but got {response.status_code}"
        response_data = response.json()
        assert isinstance(response_data, list), f"Expected response to be a list, but got {type(response_data)}"

        if not response_data:
            # If the list is empty, the test is considered passed as there's nothing to validate.
            return

        # Validate each item in the response list
        for item in response_data:
            assert isinstance(item, dict), f"Expected item to be a dict, but got {type(item)}"

            # Check for presence and type of all fields in the schema
            for field, expected_type in SCHEMA.items():
                assert field in item, f"Mandatory key '{field}' is missing from the response item"
                assert isinstance(item[field], expected_type), \
                    f"For key '{field}', expected type {expected_type}, but got {type(item[field])}"

            # Special validations for specific fields
            assert all(isinstance(email, str) for email in item["to"]), "All items in 'to' list must be strings"
            assert is_valid_cron(item["cronTemplate"]), f"Field 'cronTemplate' has an invalid format: {item['cronTemplate']}"
            assert is_iso_datetime(item["createdAt"]), f"Field 'createdAt' has an invalid format: {item['createdAt']}"
            assert is_iso_datetime(item["modifiedAt"]), f"Field 'modifiedAt' has an invalid format: {item['modifiedAt']}" 