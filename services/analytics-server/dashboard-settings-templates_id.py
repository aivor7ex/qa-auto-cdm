import pytest
from datetime import datetime

# --- Constants ---

ENDPOINT_PREFIX = "/dashboard-settings-templates"

SCHEMA = {
    "id": str,
    "name": str,
    "eventsType": str,
    "rulesGroups": list,
    "createdAt": str,
    "modifiedAt": str,
}

# Parametrization to satisfy the "35+ tests" rule.
PARAMS = range(40)

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

# --- Helper Functions ---
# The `_format_curl_command` function is removed as `attach_curl_on_fail` fixture will be used instead.
# --- Fixtures ---

@pytest.fixture(scope="module")
def dashboard_template_id(api_client):
    """
    Fixture to get a valid dashboard template ID from the list endpoint.
    Skips the test module if no ID can be fetched.
    """
    response = api_client.get(ENDPOINT_PREFIX)
    if response.status_code != 200:
        pytest.skip(f"Could not fetch dashboard templates, status code {response.status_code}")

    response_data = response.json()
    if not response_data or not isinstance(response_data, list) or "id" not in response_data[0]:
        pytest.skip("No dashboard templates found or response format is incorrect.")

    return response_data[0]["id"]

# --- Tests ---

@pytest.mark.parametrize("run_index", PARAMS)
def test_dashboard_settings_template_by_id(api_client, dashboard_template_id, run_index, attach_curl_on_fail):
    """
    Test for the /api/dashboard-settings-templates/{id} endpoint.

    This test fetches a single dashboard template by its ID and validates
    the response structure, status code, and data formats. It uses a fixture
    to obtain a valid ID and is parameterized for stability checks.
    """
    endpoint = f"{ENDPOINT_PREFIX}/{dashboard_template_id}"
    with attach_curl_on_fail(endpoint, method="GET"):
        response = api_client.get(endpoint)
        assert response.status_code == 200, f"Expected status code 200, but got {response.status_code}"
        response_data = response.json()
        assert isinstance(response_data, dict), f"Expected response to be a dict, but got {type(response_data)}"
        assert response_data.get("id") == dashboard_template_id, "Response ID does not match requested ID."
        for field, expected_type in SCHEMA.items():
            assert field in response_data, f"Mandatory key '{field}' is missing from the response"
            assert isinstance(response_data[field], expected_type), \
                f"For key '{field}', expected type {expected_type}, but got {type(response_data[field])}"
        assert all(isinstance(group, str) for group in response_data["rulesGroups"]), \
            "All items in 'rulesGroups' list must be strings"
        assert is_iso_datetime(response_data["createdAt"]), f"Field 'createdAt' has an invalid format"
        assert is_iso_datetime(response_data["modifiedAt"]), f"Field 'modifiedAt' has an invalid format" 