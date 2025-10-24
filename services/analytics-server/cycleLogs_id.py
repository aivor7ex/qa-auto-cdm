import pytest
import random
import string
import re
from datetime import datetime

# --- Constants ---

ENDPOINT_TEMPLATE = "/cycleLogs/{}"

# --- Schemas ---
# Schemas are defined based on the structure of a single log record.

USER_SCHEMA = {"name": str}
ALERT_SCHEMA = {"signature": str}
HOSTNAME_SCHEMA = {"ip": str}
EVENT_SCHEMA = {"original": str}

LOG_MESSAGES_SCHEMA = {
    "action": str,
    "destNet": list,
    "all_time_counter": int,
    "ruleId": str,
    "proto": str,
    "counter": int,
    "srcNet": list,
}

# The 'details' object can have a variable structure.
# We define all possible fields and check for their presence before validation.
DETAILS_SCHEMA = {
    "methodBody": str,
    "code": (str, int),
    "logMessages": list,
    "action": str,
    "service": str,
    "accessType": str,
    "url": str,
    "model": str,
    "method": str,
    "methodParams": dict,
    "content": str,
    "error": dict,
}

# Based on real data, some fields are mandatory, others are optional.
MANDATORY_SCHEMA = {
    "id": str, "severity": str, "tags": list, "timestamp": str,
    "message": str, "index": str, "seqid": int,
    "details": dict,
    "@version": str, "source": str,
    "event": dict, "hostname": dict, "type": str,
    "@timestamp": str,
}

OPTIONAL_SCHEMA = {
    "proto": str, "dstIP": str, "src_ip": str, "destPort": str,
    "recordType": str, "state": str, "severityStr": str, "srcIP": str,
    "description": str, "destNet": str, "action": str, "counter": (int, str),
    "src_addr": str, "dst_addr": str, "dst_port": str, "dest_port": str,
    "dest_ip": str, "src_port": str, "dstPort": str, "comment": str,
    "result": (str, bool), "srcNet": str, "srcPort": str,
    "user": dict, "alert": dict
}

# --- Parameters for Test ---
# We parameterize the test to run 35 times to ensure endpoint stability with different logs.
PARAMS = [
    (f"random_run_{i}", i)
    for i in range(35)
]

# --- Helper Functions ---

def is_iso_datetime(s):
    """Checks if a string is a valid ISO 8601 datetime."""
    if not isinstance(s, str): return False
    try:
        datetime.fromisoformat(s.replace('Z', '+00:00'))
        return True
    except (ValueError, TypeError): return False

def is_quoted_iso_datetime(s):
    """Checks if a string is a valid quoted ISO 8601 datetime."""
    if not isinstance(s, str) or not (s.startswith('"') and s.endswith('"')): return False
    return is_iso_datetime(s.strip('"'))

def is_valid_ip_or_empty(ip_str):
    """Checks if a string is a valid IPv4 address, empty, or None."""
    if ip_str is None: return True
    if ip_str == "": return True
    if not isinstance(ip_str, str): return False
    return bool(re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", ip_str))


# --- Tests ---

@pytest.mark.parametrize("name, run_index", PARAMS)
def test_cycle_log_by_id(api_client, name, run_index, attach_curl_on_fail):
    """
    Tests the /cycleLogs/{id} endpoint by fetching a valid log ID
    and performing a deep validation of the response structure.
    """
    # 1. Fetch logs to get a valid ID
    logs_response = api_client.get("/cycleLogs")
    assert logs_response.status_code == 200, f"Expected 200 OK, got {logs_response.status_code}"
    logs_data = logs_response.json()
    assert isinstance(logs_data, list)
    assert logs_data, "Could not retrieve any logs to test for existence."

    # 2. Pick a random log and get its ID
    log_item = random.choice(logs_data)
    assert "id" in log_item, "Log item is missing 'id' field."
    log_id = log_item["id"]

    # 3. Request the specific log by its ID
    endpoint = ENDPOINT_TEMPLATE.format(log_id)
    with attach_curl_on_fail(endpoint, method="GET"):
        response = api_client.get(endpoint)
        assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}"
        item = response.json()
        assert isinstance(item, dict)

        # 4. Validate the response schema
        for field, f_type in MANDATORY_SCHEMA.items():
            assert field in item, f"Mandatory key '{field}' is missing"
            assert isinstance(item[field], f_type), f"Key '{field}' has wrong type"
        for field, f_type in OPTIONAL_SCHEMA.items():
            if field in item:
                assert isinstance(item[field], f_type), f"Optional key '{field}' has wrong type"
        assert is_iso_datetime(item['timestamp'])
        assert is_quoted_iso_datetime(item['@timestamp'])
        assert all(is_valid_ip_or_empty(item.get(ip_field)) for ip_field in ["dstIP", "src_ip", "srcIP", "dst_addr", "dest_ip", "src_addr"])
        for field, schema in [("hostname", HOSTNAME_SCHEMA), ("event", EVENT_SCHEMA)]:
            nested_item = item.get(field)
            assert isinstance(nested_item, dict)
            for sub_field, sub_type in schema.items():
                assert sub_field in nested_item, f"Mandatory key '{sub_field}' missing in '{field}'"
                assert isinstance(nested_item[sub_field], sub_type), f"Key '{sub_field}' in '{field}' has wrong type"
        
        # Validate optional nested objects if they exist
        for field, schema in [("user", USER_SCHEMA), ("alert", ALERT_SCHEMA)]:
            nested_item = item.get(field)
            if nested_item is not None:
                assert isinstance(nested_item, dict)
                for sub_field, sub_type in schema.items():
                    if sub_field in nested_item:
                        assert isinstance(nested_item[sub_field], sub_type), f"Key '{sub_field}' in '{field}' has wrong type"
        details_item = item.get("details")
        if details_item:
            assert isinstance(details_item, dict)
            for sub_field, sub_type in DETAILS_SCHEMA.items():
                if sub_field in details_item:
                    assert isinstance(details_item[sub_field], sub_type), f"Key '{sub_field}' in 'details' has wrong type"
        if details_item and "logMessages" in details_item:
            log_messages = details_item.get("logMessages", [])
            assert isinstance(log_messages, list)
            for msg in log_messages:
                assert isinstance(msg, dict)
                for field, f_type in LOG_MESSAGES_SCHEMA.items():
                    if field in msg:
                        assert isinstance(msg[field], f_type), f"Key '{field}' in logMessage has wrong type"
                if "destNet" in msg:
                    assert all(isinstance(net, str) for net in msg["destNet"])
                if "srcNet" in msg:
                    assert all(isinstance(net, str) for net in msg["srcNet"]) 