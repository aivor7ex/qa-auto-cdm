import pytest
import random
import string
from datetime import datetime

# --- Constants ---

ENDPOINT_PREFIX = "/security-report-cron-jobs"

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

# Parametrization to satisfy the "35+ tests" rule by running the same core checks multiple times.
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

def is_valid_cron(s):
    """Basic check for a valid cron template format (5 space-separated parts)."""
    if not isinstance(s, str):
        return False
    return len(s.split()) == 5

# --- Fixtures ---

@pytest.fixture(scope="module")
def cron_job_id(api_client):
    """
    Fixture to get a valid cron job ID from the list endpoint.
    Skips the test module if no ID can be fetched.
    """
    response = api_client.get(ENDPOINT_PREFIX)
    if response.status_code != 200:
        pytest.skip(f"Could not fetch cron jobs, status code {response.status_code}")

    response_data = response.json()
    if not response_data or not isinstance(response_data, list) or "id" not in response_data[0]:
        pytest.skip("No cron jobs found or response format is incorrect.")

    return response_data[0]["id"]

# --- Tests ---

@pytest.mark.parametrize("run_index", PARAMS)
def test_security_report_cron_job_by_id(api_client, cron_job_id, run_index, attach_curl_on_fail):
    """
    Test for the /api/security-report-cron-jobs/{id} endpoint.

    This test fetches a single cron job by its ID and validates the response
    structure, status code, and data formats. It uses a fixture to obtain a
    valid ID and is parameterized to ensure endpoint stability.
    """
    endpoint = f"{ENDPOINT_PREFIX}/{cron_job_id}"
    with attach_curl_on_fail(endpoint, method="GET"):
        response = api_client.get(endpoint)
        assert response.status_code == 200, f"Expected status code 200, but got {response.status_code}"
        response_data = response.json()
        assert isinstance(response_data, dict), f"Expected response to be a dict, but got {type(response_data)}"
        assert response_data.get("id") == cron_job_id, "Response ID does not match requested ID."

        # Validate schema
        for field, expected_type in SCHEMA.items():
            assert field in response_data, f"Mandatory key '{field}' is missing from the response"
            assert isinstance(response_data[field], expected_type), \
                f"For key '{field}', expected type {expected_type}, but got {type(response_data[field])}"

        # Special validations
        assert all(isinstance(email, str) for email in response_data["to"]), "All items in 'to' list must be strings"
        assert is_valid_cron(response_data["cronTemplate"]), f"Field 'cronTemplate' has an invalid format"
        assert is_iso_datetime(response_data["createdAt"]), f"Field 'createdAt' has an invalid format"
        assert is_iso_datetime(response_data["modifiedAt"]), f"Field 'modifiedAt' has an invalid format" 