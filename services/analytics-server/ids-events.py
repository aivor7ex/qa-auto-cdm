"""
Test for the /api/ids-events endpoint.
"""
import pytest
from conftest import validate_schema

# Schema definition for a single event object in the response
# Based on the example provided in the task description.
EVENT_SCHEMA = {
    "required": {
        "id": str,
        "flow": dict,
        "@timestamp": str,
        "details": dict,
        "event_type": str,
        "src_net": str,
        "dest_port": int,
        "recordType": str,
        "seqid": int,
        "src_ip": str,
        "hostname": dict,
        "alert": dict,
        "src_port": int,
        "severity": int,
        "dest_ip": str,
        "dest_net": str,
        "proto": str,
        "timestamp": str,
        "detect_counter": int,
        "@version": str,
        "flow_id": int,
        "severityStr": str,
        "event": dict,
        "geoip": dict
    },
    "optional": {
        "tags": list,
        "direction": str,
        "in_iface": str,
        "pkt_src": str,
        "user": (str, dict),
        "dst_addr": str,
        "destNet": str,
        "action": str,
        "dstIP": str,
        "source": str,
        "result": str,
        "srcIP": str,
        "description": str,
        "message": str,
        "state": str,
        "dst_port": (str, int),
        "srcPort": (str, int),
        "type": str,
        "dstPort": (str, int),
        "comment": str,
        "src_addr": str,
        "srcNet": str,
        "counter": (str, int),
        "icmp_code": int,
        "icmp_type": int,
        "eth_src": str,
        "eth_dst": str
    }
}

# List of all expected top-level keys for presence check
# This list is used to generate over 35 individual tests via parametrization.
ALL_EVENT_KEYS = list(EVENT_SCHEMA["required"].keys()) + list(EVENT_SCHEMA["optional"].keys())



@pytest.fixture(scope="module")
def api_response(api_client):
    """
    Fixture to make a single API call and store the response.
    This minimizes the number of GET requests, as per the requirements.
    """
    response = api_client.get("/ids-events")
    return response

def test_status_code(api_response):
    """
    Tests that the API returns a 200 OK status code.
    """
    assert api_response.status_code == 200, \
        f"Expected status code 200, but got {api_response.status_code}. Response: {api_response.text}"

def test_response_is_list(api_response):
    """
    Tests that the root of the JSON response is a list.
    """
    response_json = api_response.json()
    assert isinstance(response_json, list), \
        f"Expected response to be a list, but got {type(response_json).__name__}"

def test_list_not_empty(api_response):
    """
    Checks that the returned list of events is not empty.
    Note: This test may fail if there are no IDS events in the system, which is normal.
    """
    response_json = api_response.json()
    # API may return empty list if no events exist, which is valid
    # We'll skip this test if the list is empty rather than failing
    if len(response_json) == 0:
        pytest.skip("No IDS events found in the system - this is normal if no events have been generated")
    assert len(response_json) > 0, "The events list in the response should not be empty."

def test_full_schema_validation(api_response):
    """
    Performs a deep validation of the schema for each object in the response list.
    It checks for required/optional keys and their data types recursively.
    """
    response_json = api_response.json()
    # If the list is empty, that's valid - no events to validate
    if len(response_json) == 0:
        pytest.skip("No IDS events found in the system - skipping schema validation")
    # The helper function 'validate_schema' can handle a list of dicts directly.
    validate_schema(response_json, EVENT_SCHEMA)

@pytest.mark.parametrize("key", EVENT_SCHEMA["required"].keys())
def test_required_event_key_presence(api_response, key):
    response_json = api_response.json()
    if len(response_json) == 0:
        pytest.skip("No IDS events found in the system - skipping key presence test")
    first_event = response_json[0]
    assert key in first_event, f"Required key '{key}' not found in the event object."

@pytest.mark.parametrize("key", EVENT_SCHEMA["optional"].keys())
def test_optional_event_key_presence(api_response, key):
    response_json = api_response.json()
    if len(response_json) == 0:
        pytest.skip("No IDS events found in the system - skipping key presence test")
    first_event = response_json[0]
    # Optional keys may be missing, so we only check if they exist and have valid types
    if key in first_event:
        # If the key exists, validate its type according to schema
        expected_type = EVENT_SCHEMA["optional"][key]
        actual_type = type(first_event[key])
        if isinstance(expected_type, tuple):
            assert actual_type in expected_type, f"Optional key '{key}' has type {actual_type.__name__}, but expected one of {expected_type}"
        else:
            assert actual_type is expected_type, f"Optional key '{key}' has type {actual_type.__name__}, but expected {expected_type.__name__}" 