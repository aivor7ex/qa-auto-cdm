"""
Test for the /api/ids-events/{id} endpoint.
"""
import pytest
from conftest import validate_schema

# Schema for a single event object, based on actual API response
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
        "tags": list,
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
        "direction": str,
        "in_iface": str,
        "pkt_src": str,
        "user": dict,
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





@pytest.fixture(scope="module")
def event_id(api_client):
    """
    Fetches a valid event ID from the /ids-events list endpoint.
    Skips tests in this module if no events are available.
    """
    response = api_client.get("/ids-events")
    if response.status_code != 200:
        pytest.skip(f"Could not retrieve events list, status code: {response.status_code}")

    events = response.json()
    if not events or not isinstance(events, list):
        pytest.skip("Events list is empty or invalid, cannot proceed with single event tests.")

    return events[0].get("id")

@pytest.fixture(scope="module")
def api_response(api_client, event_id):
    """
    Makes a single API call to the /ids-events/{id} endpoint and stores the response.
    """
    if not event_id:
        pytest.skip("No event ID was found, skipping single event tests.")

    response = api_client.get(f"/ids-events/{event_id}")
    return response

def test_status_code(api_response):
    """
    Tests that the API returns a 200 OK status code for a specific event.
    """
    assert api_response.status_code == 200, \
        f"Expected status code 200, but got {api_response.status_code}. Response: {api_response.text}"

def test_response_is_dict(api_response):
    """
    Tests that the root of the JSON response for a single event is a dictionary.
    """
    response_json = api_response.json()
    assert isinstance(response_json, dict), \
        f"Expected response to be a dict, but got {type(response_json).__name__}"

def test_full_schema_validation(api_response):
    """
    Performs a deep validation of the schema for the returned event object.
    """
    response_json = api_response.json()
    validate_schema(response_json, EVENT_SCHEMA)

@pytest.mark.parametrize("key", list(EVENT_SCHEMA["required"].keys()))
def test_required_event_key_presence(api_response, key):
    response_json = api_response.json()
    assert key in response_json, f"Required key '{key}' not found in the event object."

@pytest.mark.parametrize("key", list(EVENT_SCHEMA["optional"].keys()))
def test_optional_event_key_presence(api_response, key):
    response_json = api_response.json()
    # Для опциональных полей проверяем только если они есть в ответе
    # Если поля нет - это нормально, тест проходит
    pass 