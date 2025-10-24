import pytest
from qa_constants import SERVICES
import urllib.parse
import re

# --- Constants ---
ENDPOINT = "managers/status"
BASE_PATH_FOR_CURL = "/api/ids/"
SERVICE_PORT = SERVICES["ids"]["port"]

# --- Schema Definition ---
SCHEMA = {
    "active": bool,
    "time": str
}

# --- Helper Functions ---
def validate_schema(data):
    """Validates the response data against the schema."""
    assert isinstance(data, dict), f"Response is not a dictionary."
    for key, expected_type in SCHEMA.items():
        assert key in data, f"Field '{key}' is missing from response."
        assert isinstance(data[key], expected_type), f"Field '{key}' has wrong type."
    
    # Validate that 'time' is a string representing a duration (e.g., "12345s")
    time_format_ok = isinstance(data.get("time"), str) and data["time"].endswith("s") and data["time"][:-1].isdigit()
    assert time_format_ok, f"Field 'time' has an invalid format: {data.get('time')}."

# --- Fixtures ---
@pytest.fixture
def service_data(api_client, attach_curl_on_fail):
    """Fetches manager status once per module."""
    with attach_curl_on_fail(f"/{ENDPOINT}", method="GET"):
        response = api_client.get(f"/{ENDPOINT}")
        assert response.status_code == 200, f"Failed to fetch data. Status {response.status_code}."
        data = response.json()
        return data

# --- Test Cases ---
@pytest.mark.ids
def test_schema_validation(service_data):
    """Validates the schema of the manager status response."""
    data = service_data
    validate_schema(data)

@pytest.mark.ids
@pytest.mark.parametrize("params, headers, test_id", [
    (None, None, "no_params_no_headers"),
    ({}, {}, "empty_params_empty_headers"),
    # Add 33 more robust test cases
    ({"cache": "false"}, None, "param_cache_false"),
    (None, {"Accept": "application/json"}, "header_accept_json"),
    ({"unused": "param"}, {"X-Request-ID": "123"}, "param_and_header"),
    ({"a": 1}, None, "param_a_1"),
    ({"b": "2"}, None, "param_b_2"),
    ({"c": True}, None, "param_c_true"),
    ({"d": ""}, None, "param_d_empty"),
    ({"e": None}, None, "param_e_none"),
    (None, {"h1": "v1"}, "header_h1_v1"),
    (None, {"h2": ""}, "header_h2_empty"),
    (None, {"h3": "long_value_"*10}, "header_h3_long"),
    ({"p1": "v1"}, {"h1": "v1"}, "p1_h1"),
    ({"p2": "v2", "p3": "v3"}, None, "multiple_params"),
    (None, {"h4": "v4", "h5": "v5"}, "multiple_headers"),
    ({"p4": "v4"}, {"h6": "v6"}, "p4_h6"),
    ({"p5": "v5"}, {"h7": "v7", "h8": "v8"}, "p5_multiple_headers"),
    ({"p6": "v6", "p7": "v7"}, {"h9": "v9"}, "multiple_params_h9"),
    ({"long_param": "long_value_"*20}, None, "long_param"),
    (None, {"long_header_name_"*10: "v10"}, "long_header_name"),
    ({"_": 12345}, None, "cache_bust_param"),
    ({"a.b": "c"}, None, "param_with_dot"),
    (None, {"X_Header": "val"}, "header_with_underscore"),
    ({"a b": "c d"}, None, "param_with_space"),
    ({"%20": "%20"}, None, "encoded_space_param"),
    (None, {"User-Agent": "Test/1.0"}, "user_agent_header"),
    ({"list_param": ["a", "b"]}, None, "list_param"),
    ({"dict_param": {"k": "v"}}, None, "dict_param"),
    (None, {"Cookie": "a=b; c=d"}, "cookie_header"),
    ({"utf8": "✓"}, None, "utf8_param"),
])
def test_robustness(api_client, params, headers, test_id, attach_curl_on_fail):
    """Tests endpoint robustness against various unexpected parameters and headers."""
    with attach_curl_on_fail(f"/{ENDPOINT}", payload=params, headers=headers, method="GET"):
        response = api_client.get(f"/{ENDPOINT}", params=params, headers=headers)
        assert response.status_code == 200, f"Expected status 200, got {response.status_code}."
        data = response.json()
        validate_schema(data)