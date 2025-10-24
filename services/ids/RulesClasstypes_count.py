import pytest
from qa_constants import SERVICES
import urllib.parse

# --- Constants ---
ENDPOINT = "RulesClasstypes/count"
BASE_PATH_FOR_CURL = "/api/ids/"
SERVICE_PORT = SERVICES["ids"]["port"]

# --- Schema Definition ---
SCHEMA = {
    "count": int,
}

# --- Helper Functions ---
def validate_schema(data):
    """Validates the response data against the schema."""
    assert isinstance(data, dict), f"Response is not a dictionary."
    assert "count" in data, f"Field 'count' is missing from response."
    count_value = data["count"]
    assert isinstance(count_value, int), f"'count' field has wrong type."
    assert count_value >= 0, f"'count' must be a non-negative integer, got {count_value}."

# --- Fixtures ---
@pytest.fixture
def service_data(api_client, attach_curl_on_fail):
    """Fetches the count of rule classtypes once per module."""
    with attach_curl_on_fail(f"/{ENDPOINT}", method="GET"):
        response = api_client.get(f"/{ENDPOINT}")
        assert response.status_code == 200, f"Failed to fetch data. Status {response.status_code}."
        data = response.json()
        return data

# --- Test Cases ---
@pytest.mark.ids
def test_schema_validation(service_data):
    """Validates the schema of the count response."""
    data = service_data
    validate_schema(data)

@pytest.mark.ids
@pytest.mark.parametrize("params, headers, test_id", [
    (None, None, "no_params_no_headers"),
    ({}, {}, "empty_params_empty_headers"),
    # Filtering parameters that should be ignored by the /count endpoint
    ({"q": "trojan"}, None, "filter_q"),
    ({"filter[id]": "policy-violation"}, None, "filter_id"),
    ({"limit": 10}, None, "param_limit"),
    ({"offset": 5}, None, "param_offset"),
    ({"sort": "id"}, None, "param_sort"),
    # Random headers
    (None, {"X-Custom-Header": "value"}, "header_custom"),
    (None, {"Accept": "application/xml"}, "header_accept_xml"),
    # Combinations of ignored params and headers
    ({"q": "web", "limit": 5}, {"X-Request-ID": "abc-123"}, "params_and_headers"),
    # Add 25 more robustness cases
    ({"a": 1}, None, "robust_a_1"),
    (None, {"b": "2"}, "robust_b_2"),
    ({"c": True}, {"d": "false"}, "robust_c_true_d_false"),
    ({"e": ""}, None, "robust_e_empty"),
    (None, {"f": ""}, "robust_f_empty"),
    ({"g": " "}, None, "robust_g_space"),
    # (None, {"h": " "}, "robust_h_space"),  # requests library disallows this
    ({"i": "long_val_"*10}, None, "robust_i_long"),
    (None, {"j_key_"*10: "val"}, "robust_j_long_key"),
    ({"k": ["1", "2"]}, None, "robust_k_list"),
    ({"l": {"m": "n"}}, None, "robust_l_dict"),
    ({"%20": "%20"}, None, "robust_encoded_space"),
    ({"filter[nonexistent]": "value"}, None, "robust_filter_nonexistent"),
    ({"sort": "nonexistent,id"}, None, "robust_sort_nonexistent"),
    (None, {"Cookie": "a=b"}, "robust_cookie"),
    (None, {"User-Agent": "test-agent"}, "robust_user_agent"),
    ({"p1": 1}, {"h1": "1"}, "robust_p1_h1_int"),
    ({"p2": 1.1}, None, "robust_p2_float"),
    (None, {"h2": "1.1"}, "robust_h2_float"),
    ({"p3": None}, None, "robust_p3_none"),
    (None, {"h3": ""}, "robust_h3_none_str"), # Changed None to "" for header
    ({"p4": "a,b,c"}, None, "robust_p4_comma"),
    (None, {"h4": "a,b,c"}, "robust_h4_comma"),
    ({"p5": "a=b"}, None, "robust_p5_equals"),
    (None, {"h5": "a=b"}, "robust_h5_equals"),
    ({"p6": "a&b"}, None, "robust_p6_ampersand"),
    (None, {"h6": "a&b"}, "robust_h6_ampersand"),
    ({"p7": "a?b"}, None, "robust_p7_question"),
    (None, {"h7": "a?b"}, "robust_h7_question"),
    ({"p8": "a#b"}, None, "robust_p8_hash"),
    (None, {"h8": "a#b"}, "robust_h8_hash"),
])
def test_robustness(api_client, service_data, params, headers, test_id, attach_curl_on_fail):
    """
    Tests endpoint robustness. The /count endpoint should ignore all parameters
    and headers, always returning the total count.
    """
    initial_data = service_data
    initial_count = initial_data["count"]

    expected_status = 406 if test_id == "header_accept_xml" else 200

    with attach_curl_on_fail(f"/{ENDPOINT}", payload=params, headers=headers, method="GET"):
        response = api_client.get(f"/{ENDPOINT}", params=params, headers=headers)
        
        assert response.status_code == expected_status, f"Expected status {expected_status}, got {response.status_code}."

        if expected_status == 200:
            data = response.json()
            validate_schema(data)
            
            assert data["count"] == initial_count, (
                f"Count should not change with params. "
                f"Initial: {initial_count}, Got: {data['count']}."
            ) 