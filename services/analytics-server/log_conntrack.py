"""
Test for the /api/log_conntrack endpoint.
"""
import pytest
from conftest import validate_schema
import ipaddress
from datetime import datetime

# --- Schema Definition ---
# Based on the example, defining required fields (with values) and optional (empty).
LOG_CONNTRACK_SCHEMA = {
    "required": {
        "dst_addr": str,
        "bytes": (int, str),
        "details": dict,
        "user": dict,
        "dst_port": (int, str),
        "proto": (int, str),
        "action": str,
        "recordType": str,
        "@version": str,
        "seqid": int,
        "hostname": dict,
        "packets": (int, str),
        "src_addr": str,
        "ether_type": str,
        "src_port": (int, str),
        "alert": dict,
    },
    "optional": {
        "timestamp": str,
        "@timestamp": str,
        "id": str,
        "description": str,
        "severity": str,
        "message": str,
        "state": str,
        "destNet": str,
        "dest_ip": str,
        "dest_port": str,
        "dstIP": str,
        "source": str,
        "srcPort": str,
        "src_ip": str,
        "type": str,
        "result": str,
        "dstPort": str,
        "severityStr": str,
        "srcNet": str,
        "comment": str,
        "srcIP": str,
        "counter": str,
    }
}

ALL_LOG_KEYS = list(LOG_CONNTRACK_SCHEMA["required"].keys()) + list(LOG_CONNTRACK_SCHEMA["optional"].keys())

# --- Helper Functions for Special Validation ---

def is_valid_ip(address):
    """Checks if a string is a valid IPv4 or IPv6 address."""
    try:
        ipaddress.ip_address(address)
        return True
    except ValueError:
        return False

def is_valid_iso_timestamp(ts_string):
    """Checks if a string is a valid ISO 8601 timestamp with 'Z' suffix."""
    try:
        # Python 3.11+ `fromisoformat` directly supports 'Z'
        if ts_string.endswith('Z'):
            datetime.fromisoformat(ts_string.replace('Z', '+00:00'))
        else:
            datetime.fromisoformat(ts_string)
        return True
    except (ValueError, TypeError):
        return False



# --- Fixtures ---

@pytest.fixture(scope="module")
def api_response(api_client):
    """Fetches the API response once for all tests in the module."""
    response = api_client.get("/log_conntrack")
    return response

@pytest.fixture(scope="module")
def conntrack_logs(api_response):
    """
    Parses the JSON from the API response and skips tests if the list is empty.
    """
    if api_response.status_code != 200:
        pytest.skip(f"API request failed with status {api_response.status_code}, skipping tests.")
    
    logs = api_response.json()
    if not logs:
        pytest.skip("Response is empty, no logs to test.")
    return logs

# --- Test Cases ---

def test_status_code(api_response, attach_curl_on_fail):
    """Tests that the API returns a 200 OK status code."""
    with attach_curl_on_fail("/log_conntrack", method="GET"):
        assert api_response.status_code == 200

def test_response_is_list(api_response, attach_curl_on_fail):
    """Tests that the root of the JSON response is a list."""
    with attach_curl_on_fail("/log_conntrack", method="GET"):
        assert isinstance(api_response.json(), list)

def test_full_schema_validation(conntrack_logs, attach_curl_on_fail):
    endpoint = "/log_conntrack"
    with attach_curl_on_fail(endpoint, method="GET"):
        validate_schema(conntrack_logs, LOG_CONNTRACK_SCHEMA)

def test_special_fields_are_valid(conntrack_logs, attach_curl_on_fail):
    """
    Validates the format of special fields: timestamps and IP addresses.
    """
    endpoint = "/log_conntrack"
    with attach_curl_on_fail(endpoint, method="GET"):
        for log in conntrack_logs:
            assert is_valid_iso_timestamp(log.get("@timestamp")), f"Invalid @timestamp format: {log.get('@timestamp')}"
            assert is_valid_iso_timestamp(log.get("timestamp")), f"Invalid timestamp format: {log.get('timestamp')}"
            
            if log.get("src_addr"):
                assert is_valid_ip(log["src_addr"]), f"Invalid src_addr IP format: {log['src_addr']}"
            if log.get("dst_addr"):
                assert is_valid_ip(log["dst_addr"]), f"Invalid dst_addr IP format: {log['dst_addr']}"

@pytest.mark.parametrize("key", ALL_LOG_KEYS)
def test_log_key_presence(conntrack_logs, key, attach_curl_on_fail):
    endpoint = "/log_conntrack"
    with attach_curl_on_fail(endpoint, method="GET"):
        first_log = conntrack_logs[0]
        assert key in first_log, f"Key '{key}' not found in the log object." 