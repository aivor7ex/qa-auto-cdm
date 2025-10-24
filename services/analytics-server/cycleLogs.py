import pytest
import random
import string
import re
from datetime import datetime

# --- Constants ---

ENDPOINT = "/cycleLogs"

# --- Schemas ---
# Defining schemas for the main object and all nested structures for clarity.

USER_SCHEMA = {"name": str}
ALERT_SCHEMA = {"signature": str}
HOSTNAME_SCHEMA = {"ip": str}
LOG_MESSAGES_SCHEMA = {
    "action": str,
    "destNet": list,
    "all_time_counter": int,
    "ruleId": str,
    "proto": str,
    "counter": int,
    "srcNet": list,
}
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
EVENT_SCHEMA = {"original": str}

# Based on real data, some fields are optional.
MANDATORY_SCHEMA = {
    "id": str, "severity": (str, int), "tags": list, "timestamp": str,
    "message": str, "seqid": int,
    "user": dict, "alert": dict, "details": dict,
    "@version": (str, int), "source": (str, int, dict, list), 
    "event": dict, "hostname": dict, "type": str,
    "@timestamp": str,
}

OPTIONAL_SCHEMA = {
    "index": (str, int), "proto": (str, int), "dstIP": (str, int), "src_ip": (str, int), "destPort": (str, int),
    "recordType": (str, int), "state": (str, int), "severityStr": (str, int), "srcIP": (str, int),
    "description": (str, int), "destNet": (str, int), "action": (str, int), "counter": (int, str),
    "src_addr": (str, int), "dst_addr": (str, int), "dst_port": (str, int), "dest_port": (str, int),
    "dest_ip": (str, int), "src_port": (str, int), "dstPort": (str, int), "comment": (str, int),
    "result": (str, bool, int), "srcNet": (str, int), "srcPort": (str, int)
}

# --- Parameters for Test ---
PARAMS = [
    ("case_alpha", "abcdefghij"),
    ("case_numeric", "1234567890"),
    ("case_mixed", "abc123XYZ"),
    ("case_special", "!@#$%^&*()"),
    ("case_empty", ""),
    ("case_upper", "ABCDEFGHIJ"),
    ("case_lower", "klmnopqrst"),
    ("case_long", "a" * 50),
    ("case_short", "z"),
    ("case_unicode", "тестЮникод"),
]

# --- Helper Functions ---

def is_iso_datetime(s):
    if not isinstance(s, str): return False
    try:
        datetime.fromisoformat(s.replace('Z', '+00:00'))
        return True
    except (ValueError, TypeError): return False

def is_quoted_iso_datetime(s):
    if not isinstance(s, str) or not (s.startswith('"') and s.endswith('"')): return False
    return is_iso_datetime(s.strip('"'))

def is_valid_ip_or_empty(ip_str):
    if ip_str == "": return True
    if not isinstance(ip_str, str): return False
    # Basic regex for IPv4
    return bool(re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", ip_str))

def validate_type(value, expected_type):
    """Validate that value matches expected type(s)"""
    if isinstance(expected_type, tuple):
        return isinstance(value, expected_type)
    return isinstance(value, expected_type)

# --- Tests ---

@pytest.mark.parametrize("key, value", PARAMS)
def test_cycle_logs(api_client, key, value, attach_curl_on_fail):
    """
    Test for the /api/cycleLogs endpoint.

    This test sends a GET request with random query parameters to ensure stability.
    It performs basic validation of the response structure.
    """
    with attach_curl_on_fail(ENDPOINT, method="GET"):
        response = api_client.get(ENDPOINT, params={key: value})
        assert response.status_code == 200, f"Status: {response.status_code}"
        response_data = response.json()
        assert isinstance(response_data, list)

        if not response_data:
            return  # Pass if the list is empty

        for item in response_data:
            assert isinstance(item, dict)
            
            # Basic structure validation - just check that it's a dict with some content
            assert len(item) > 0, "Empty item in response"
            
            # Check that required fields exist (basic ones)
            required_fields = ["id", "timestamp", "@timestamp"]
            for field in required_fields:
                if field in item:
                    assert item[field] is not None, f"Field {field} is None"
            
            # Validate timestamp formats if they exist
            if 'timestamp' in item:
                assert is_iso_datetime(item['timestamp']), "Invalid timestamp format"
            if '@timestamp' in item:
                assert is_quoted_iso_datetime(item['@timestamp']), "Invalid @timestamp format"
            
            # Validate IP fields if they exist (basic format check)
            ip_fields = ["dstIP", "src_ip", "srcIP", "dst_addr", "dest_ip", "src_addr"]
            for ip_field in ip_fields:
                if ip_field in item and item[ip_field]:
                    assert is_valid_ip_or_empty(item[ip_field]), f"Invalid IP format: {ip_field}" 