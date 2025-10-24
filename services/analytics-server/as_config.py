"""
Test for the /api/config endpoint.
"""
import pytest
import random
import string
from datetime import datetime
from conftest import validate_schema

# --- Schema Definitions ---

# Schema for the objects inside the 'SecurityReportTemplate' list
SECURITY_REPORT_TEMPLATE_SCHEMA = {
    "required": {
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
    },
    "optional": {
        "timeInterval": str,
    }
}

# --- Helper Functions for Date/Time Validation ---

def is_valid_iso_datetime(dt_string):
    """
    Validates if a string is a valid ISO 8601 timestamp.
    Handles both 'Z' and +HH:MM timezone formats.
    """
    if not isinstance(dt_string, str):
        return False
    try:
        # Python's fromisoformat is powerful enough for this.
        if 'Z' in dt_string and dt_string.endswith('Z'):
             datetime.fromisoformat(dt_string.replace('Z', '+00:00'))
        else:
             datetime.fromisoformat(dt_string)
        return True
    except (ValueError, TypeError):
        return False

def is_valid_time_interval(interval_string):
    """
    Validates the custom time interval string format.
    e.g., "2025-06-23T16:08:00+03:00 - 2025-06-23T16:08:00+03:00"
    """
    if not isinstance(interval_string, str):
        return False
    parts = interval_string.split(" - ")
    if len(parts) != 2:
        return False
    return is_valid_iso_datetime(parts[0]) and is_valid_iso_datetime(parts[1])


# --- Fixtures ---

@pytest.fixture(scope="module")
def api_response(api_client):
    """Fetches the API response once for all tests."""
    return api_client.get("/config")

@pytest.fixture(scope="module")
def config_data(api_response):
    """Parses JSON response and ensures it's a dictionary."""
    assert api_response.status_code == 200
    data = api_response.json()
    assert isinstance(data, dict), "Root response should be a dictionary."
    return data

# --- Core Structure and Validation Tests ---

def test_status_code(api_response):
    assert api_response.status_code == 200

def test_top_level_keys_and_types(config_data):
    """Checks for the presence and list type of top-level keys."""
    expected_keys = [
        "DashboardSettingsTemplate",
        "SecurityReportCronJob",
        "SecurityReportTemplate",
    ]
    for key in expected_keys:
        assert key in config_data, f"Top-level key '{key}' is missing."
        assert isinstance(config_data[key], list), f"Top-level key '{key}' should be a list."

def test_security_report_template_schema(config_data):
    """Performs deep schema validation for each report template."""
    report_templates = config_data.get("SecurityReportTemplate")
    if report_templates:  # Only test if the list is not empty
        validate_schema(report_templates, SECURITY_REPORT_TEMPLATE_SCHEMA)

def test_datetime_fields_are_valid(config_data):
    """
    Validates the format of all date/time fields in each report template.
    """
    report_templates = config_data.get("SecurityReportTemplate", [])
    for template in report_templates:
        assert is_valid_iso_datetime(template.get("createdAt")), \
            f"Invalid 'createdAt' format: {template.get('createdAt')}"
        assert is_valid_iso_datetime(template.get("modifiedAt")), \
            f"Invalid 'modifiedAt' format: {template.get('modifiedAt')}"
        
        if "timeInterval" in template:
            assert is_valid_time_interval(template["timeInterval"]), \
                f"Invalid 'timeInterval' format: {template['timeInterval']}"

# --- Parametrized Robustness Test ---

def generate_random_string(length=8):
    """Generates a random string for parameter names and values."""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

robustness_params = [
    {"alpha": "abc123"},
    {"numeric": "987654"},
    {"empty": ""},
    {"special": "!@#"},
    {"long": "x" * 30},
    {"short": "y"},
    {"unicode": "тест"},
    {"upper": "ABCDEF"},
    {"lower": "abcdef"},
    {"mixed": "A1b2C3"},
]

@pytest.mark.parametrize("params", robustness_params)
def test_endpoint_handles_unexpected_params(api_client, params, attach_curl_on_fail):
    with attach_curl_on_fail("/config", params, method="GET"):
        response = api_client.get("/config", params=params)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert "SecurityReportTemplate" in data 