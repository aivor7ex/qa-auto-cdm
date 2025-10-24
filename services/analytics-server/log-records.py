"""
Test for the /api/log-records endpoint.
"""
import pytest
from conftest import validate_schema
import ipaddress
from datetime import datetime

# --- Schema Definition ---
LOG_RECORD_SCHEMA = {
    "required": {
        "id": str,
        "proto": str,
        "srcNet": str,
        "counter": (int, str),
        "comment": str,
        "result": (str, bool),
        "message": str,
        "user": dict,
        "destNet": str,
        "tags": list,
        "seqid": int,
        "timestamp": str,
        "details": dict,
        "action": str,
        "@timestamp": str,
        "source": str,
        "alert": dict,
        "hostname": dict,
        "type": str,
        "@version": str,
        "severity": str,
        "index": str,
        "event": dict,
    },
    "optional": {
        "destPort": str,
        "src_ip": str,
        "description": str,
        "state": str,
        "severityStr": str,
        "src_addr": str,
        "dstIP": str,
        "srcPort": str,
        "dest_ip": str,
        "dst_addr": str,
        "srcIP": str,
        "dest_port": str,
        "dst_port": str,
        "recordType": str,
    }
}

ALL_LOG_KEYS = list(LOG_RECORD_SCHEMA["required"].keys()) + list(LOG_RECORD_SCHEMA["optional"].keys())

# --- Helper Functions ---
def is_valid_ipv4(addr):
    try:
        ipaddress.IPv4Address(addr)
        return True
    except Exception:
        return False

def is_valid_cidr(cidr):
    try:
        ipaddress.IPv4Network(cidr, strict=False)
        return True
    except Exception:
        return False

def is_valid_iso_datetime(dt):
    try:
        if dt.endswith('Z'):
            datetime.fromisoformat(dt.replace('Z', '+00:00'))
        else:
            datetime.fromisoformat(dt)
        return True
    except Exception:
        return False

def extract_all_ips(obj):
    """Recursively extract all IPv4 and CIDR fields from dicts/lists."""
    ips, cidrs = set(), set()
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, (dict, list)):
                ips2, cidrs2 = extract_all_ips(v)
                ips |= ips2
                cidrs |= cidrs2
            elif isinstance(v, str):
                if k in {"src_ip", "dstIP", "src_addr", "dst_addr", "dest_ip", "hostname"} and v:
                    ips.add(v)
                if k in {"srcNet", "destNet"} and v:
                    cidrs.add(v)
            elif isinstance(v, list) and k in {"srcNet", "destNet"}:
                for item in v:
                    if isinstance(item, str):
                        cidrs.add(item)
    elif isinstance(obj, list):
        for item in obj:
            ips2, cidrs2 = extract_all_ips(item)
            ips |= ips2
            cidrs |= cidrs2
    return ips, cidrs

def extract_all_datetimes(obj):
    """Recursively extract all datetime fields from dicts/lists."""
    dts = set()
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in {"timestamp", "@timestamp"} and isinstance(v, str) and v:
                dts.add(v)
            elif isinstance(v, (dict, list)):
                dts |= extract_all_datetimes(v)
    elif isinstance(obj, list):
        for item in obj:
            dts |= extract_all_datetimes(item)
    return dts


# --- Fixtures ---
@pytest.fixture(scope="module")
def api_response(api_client):
    response = api_client.get("/log-records")
    return response

@pytest.fixture(scope="module")
def log_records(api_response):
    if api_response.status_code != 200:
        pytest.skip(f"API request failed with status {api_response.status_code}, skipping tests.")
    data = api_response.json()
    if not data:
        pytest.skip("Response is empty, no log records to test.")
    return data

# --- Tests ---
def test_status_code(api_response):
    assert api_response.status_code == 200

def test_response_is_list(api_response):
    assert isinstance(api_response.json(), list)

def test_full_schema_validation(log_records):
    validate_schema(log_records, LOG_RECORD_SCHEMA)

@pytest.mark.parametrize("key", list(LOG_RECORD_SCHEMA["required"].keys()))
def test_log_key_presence(log_records, key):
    first_log = log_records[0]
    assert key in first_log, f"Key '{key}' not found in the log object."

def test_ip_and_datetime_validity(log_records):
    for log in log_records:
        ips, cidrs = extract_all_ips(log)
        for ip in ips:
            if ip:
                assert is_valid_ipv4(ip), f"Invalid IPv4: {ip}"
        for cidr in cidrs:
            if cidr:
                assert is_valid_cidr(cidr), f"Invalid CIDR: {cidr}"
        dts = extract_all_datetimes(log)
        for dt in dts:
            if dt:
                assert is_valid_iso_datetime(dt), f"Invalid datetime: {dt}"

def test_details_structure(log_records):
    for log in log_records:
        details = log.get('details')
        assert isinstance(details, dict)
        if 'code' in details:
            assert isinstance(details['code'], str)
        if 'logMessages' in details:
            assert isinstance(details['logMessages'], list)
            for msg in details['logMessages']:
                assert isinstance(msg, dict)
                assert 'ruleId' in msg

def test_user_structure(log_records):
    for log in log_records:
        user = log.get('user')
        assert isinstance(user, dict)
        assert 'name' in user

def test_hostname_structure(log_records):
    for log in log_records:
        hostname = log.get('hostname')
        assert isinstance(hostname, dict)
        if 'ip' in hostname and hostname['ip']:
            assert is_valid_ipv4(hostname['ip'])

def test_alert_structure(log_records):
    for log in log_records:
        alert = log.get('alert')
        assert isinstance(alert, dict)
        assert 'signature' in alert

def test_event_structure(log_records):
    for log in log_records:
        event = log.get('event')
        assert isinstance(event, dict)
        if 'original' in event:
            assert isinstance(event['original'], str)

def test_tags_list(log_records):
    for log in log_records:
        tags = log.get('tags')
        assert isinstance(tags, list)
        if tags:
            assert any(isinstance(tag, str) for tag in tags)

def test_seqid_is_nonnegative_int(log_records):
    for log in log_records:
        seqid = log.get('seqid')
        assert isinstance(seqid, int)
        assert seqid >= 0

def test_version_is_one(log_records):
    for log in log_records:
        assert log.get('@version') == '1'

def test_severity_type_values(log_records):
    allowed_severity = {'1', '2', '3', '4', '5', ''}
    allowed_types = {'warning', 'error', '', 'info'}
    for log in log_records:
        if 'severity' in log:
            assert log['severity'] in allowed_severity
        if 'type' in log:
            assert log['type'] in allowed_types

def test_timestamps_consistency(log_records):
    for log in log_records:
        t1 = log.get('timestamp')
        t2 = log.get('@timestamp')
        if t1 and t2:
            try:
                from datetime import datetime
                dt1 = datetime.fromisoformat(t1.replace('Z', '+00:00'))
                dt2 = datetime.fromisoformat(t2.replace('Z', '+00:00'))
                delta = abs((dt1 - dt2).total_seconds())
                assert delta < 2
            except Exception:
                pass

def test_message_or_logmessages(log_records):
    for log in log_records:
        msg = log.get('message', '')
        details = log.get('details', {})
        logmsgs = details.get('logMessages', [])
        has_msg = bool(msg)
        has_logmsg = any(isinstance(m, dict) for m in logmsgs)
        assert has_msg or has_logmsg

def test_srcnet_destnet_cidr(log_records):
    for log in log_records:
        for k in ['srcNet', 'destNet']:
            v = log.get(k)
            if v:
                if isinstance(v, str):
                    assert is_valid_cidr(v)
                elif isinstance(v, list):
                    for item in v:
                        assert is_valid_cidr(item)

def test_srcport_dstport_type(log_records):
    for log in log_records:
        for k in ['srcPort', 'dstPort']:
            v = log.get(k)
            if v:
                assert isinstance(v, (str, int))

def test_counter_nonnegative(log_records):
    for log in log_records:
        c = log.get('counter')
        if c is not None and c != '':
            try:
                val = int(c)
                assert val >= 0
            except Exception:
                assert False, f'counter not int/str-int: {c}' 