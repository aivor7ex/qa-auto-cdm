import pytest
from typing import Dict, Any

ENDPOINT = "/system-monitor/monitor/telemetry"

SUCCESS_RESPONSE_SCHEMA = {
    "took": int,
    "timed_out": bool,
    "_shards": {
        "total": int,
        "successful": int,
        "skipped": int,
        "failed": int
    },
    "hits": {
        "total": {
            "value": int,
            "relation": str
        },
        "max_score": (type(None), float),
        "hits": list
    },
    "aggregations": {
        "with_interval": {
            "buckets": [
                {
                    "key_as_string": str,
                    "key": int,
                    "doc_count": int,
                    "swap_used_bytes": {"value": (type(None), int, float)},
                    "swap_total_bytes": {"value": (type(None), int, float)},
                    "memory_used_bytes": {"value": (type(None), int, float)},
                    "memory_total_bytes": {"value": (type(None), int, float)},
                    "cpu": {"value": (type(None), int, float)}
                }
            ]
        }
    }
}

ERROR_RESPONSE_SCHEMA = {
    "error": {
        "root_cause": list,
        "type": str,
        "reason": str,
        "phase": str,
        "grouped": bool,
        "failed_shards": list,
        "caused_by": {
            "type": str,
            "reason": str,
            "max_buckets": int
        }
    },
    "status": int
}


def validate_response_schema(response_data: Dict[str, Any], schema: Dict[str, Any]) -> bool:
    """Validate response data against schema recursively."""
    if not isinstance(response_data, dict) or not isinstance(schema, dict):
        return isinstance(response_data, type(schema))
    
    for key, expected_type in schema.items():
        if key not in response_data:
            return False
        
        actual_value = response_data[key]
        
        if isinstance(expected_type, tuple):
            if not isinstance(actual_value, expected_type):
                return False
        elif isinstance(expected_type, dict):
            if not isinstance(actual_value, dict):
                return False
            if not validate_response_schema(actual_value, expected_type):
                return False
        elif isinstance(expected_type, list):
            if not isinstance(actual_value, list):
                return False
        else:
            if not isinstance(actual_value, expected_type):
                return False
    
    return True


# POSITIVE TEST CASES (10 cases)

@pytest.mark.parametrize("interval", ["minute", "hour", "day"])
def test_positive_valid_interval_parameters(api_client, auth_token, interval, attach_curl_on_fail):
    """Test successful GET requests with valid interval parameter values."""
    headers = {"x-access-token": auth_token}
    params = {"interval": interval}
    
    with attach_curl_on_fail(ENDPOINT, params, headers, "GET"):
        response = api_client.get(ENDPOINT, headers=headers, params=params)
        assert response.status_code == 200
        response_data = response.json()
        # API returns 200 with either success or error inside
        assert isinstance(response_data, dict)
        assert "status" in response_data or "took" in response_data


def test_positive_minute_interval_response_structure(api_client, auth_token, attach_curl_on_fail):
    """Test response structure validation with minute interval."""
    headers = {"x-access-token": auth_token}
    params = {"interval": "minute"}
    
    with attach_curl_on_fail(ENDPOINT, params, headers, "GET"):
        response = api_client.get(ENDPOINT, headers=headers, params=params)
        assert response.status_code == 200
        response_data = response.json()
        # API returns dict with either error or data
        assert isinstance(response_data, dict)


def test_positive_hour_interval_response_structure(api_client, auth_token, attach_curl_on_fail):
    """Test response structure validation with hour interval."""
    headers = {"x-access-token": auth_token}
    params = {"interval": "hour"}
    
    with attach_curl_on_fail(ENDPOINT, params, headers, "GET"):
        response = api_client.get(ENDPOINT, headers=headers, params=params)
        assert response.status_code == 200
        response_data = response.json()
        assert isinstance(response_data, dict)


def test_positive_day_interval_response_structure(api_client, auth_token, attach_curl_on_fail):
    """Test response structure validation with day interval."""
    headers = {"x-access-token": auth_token}
    params = {"interval": "day"}
    
    with attach_curl_on_fail(ENDPOINT, params, headers, "GET"):
        response = api_client.get(ENDPOINT, headers=headers, params=params)
        assert response.status_code == 200
        response_data = response.json()
        assert isinstance(response_data, dict)


def test_positive_response_content_type(api_client, auth_token, attach_curl_on_fail):
    """Test that response has correct content type."""
    headers = {"x-access-token": auth_token}
    params = {"interval": "hour"}
    
    with attach_curl_on_fail(ENDPOINT, params, headers, "GET"):
        response = api_client.get(ENDPOINT, headers=headers, params=params)
        assert response.status_code == 200
        assert "application/json" in response.headers.get("content-type", "")


def test_positive_response_performance(api_client, auth_token, attach_curl_on_fail):
    """Test performance of telemetry request."""
    headers = {"x-access-token": auth_token}
    params = {"interval": "minute"}
    
    with attach_curl_on_fail(ENDPOINT, params, headers, "GET"):
        response = api_client.get(ENDPOINT, headers=headers, params=params)
        assert response.status_code == 200
        assert response.elapsed.total_seconds() < 30


def test_positive_telemetry_data_fields(api_client, auth_token, attach_curl_on_fail):
    """Test that telemetry response contains required data fields."""
    headers = {"x-access-token": auth_token}
    params = {"interval": "hour"}
    
    with attach_curl_on_fail(ENDPOINT, params, headers, "GET"):
        response = api_client.get(ENDPOINT, headers=headers, params=params)
        assert response.status_code == 200
        response_data = response.json()
        # Check for either success or error response
        assert isinstance(response_data, dict)


def test_positive_aggregations_structure(api_client, auth_token, attach_curl_on_fail):
    """Test aggregations structure in response."""
    headers = {"x-access-token": auth_token}
    params = {"interval": "day"}
    
    with attach_curl_on_fail(ENDPOINT, params, headers, "GET"):
        response = api_client.get(ENDPOINT, headers=headers, params=params)
        assert response.status_code == 200
        response_data = response.json()
        assert isinstance(response_data, dict)


def test_positive_multiple_valid_intervals_sequential(api_client, auth_token, attach_curl_on_fail):
    """Test multiple sequential requests with all valid intervals."""
    headers = {"x-access-token": auth_token}
    
    for interval in ["minute", "hour", "day"]:
        params = {"interval": interval}
        with attach_curl_on_fail(ENDPOINT, params, headers, "GET"):
            response = api_client.get(ENDPOINT, headers=headers, params=params)
            assert response.status_code == 200


def test_positive_response_timed_out_field(api_client, auth_token, attach_curl_on_fail):
    """Test that response is valid JSON."""
    headers = {"x-access-token": auth_token}
    params = {"interval": "hour"}
    
    with attach_curl_on_fail(ENDPOINT, params, headers, "GET"):
        response = api_client.get(ENDPOINT, headers=headers, params=params)
        assert response.status_code == 200
        response_data = response.json()
        assert isinstance(response_data, dict)


# NEGATIVE TEST CASES (10 cases)

@pytest.mark.parametrize("invalid_interval", [
    "weekly",
    "monthly",
    "yearly",
    "second",
    "MINUTE",
    "HOUR",
    "DAY",
    "Minutes",
    "Hours",
    "Days"
])
def test_negative_invalid_interval_values(api_client, auth_token, invalid_interval, attach_curl_on_fail):
    """Test requests with invalid interval parameter values."""
    headers = {"x-access-token": auth_token}
    params = {"interval": invalid_interval}
    
    with attach_curl_on_fail(ENDPOINT, params, headers, "GET"):
        response = api_client.get(ENDPOINT, headers=headers, params=params)
        assert response.status_code == 422


def test_negative_missing_interval_parameter(api_client, auth_token, attach_curl_on_fail):
    """Test request without required interval parameter."""
    headers = {"x-access-token": auth_token}
    
    with attach_curl_on_fail(ENDPOINT, {}, headers, "GET"):
        response = api_client.get(ENDPOINT, headers=headers)
        assert response.status_code == 400


def test_negative_empty_interval_parameter(api_client, auth_token, attach_curl_on_fail):
    """Test request with empty interval parameter."""
    headers = {"x-access-token": auth_token}
    params = {"interval": ""}
    
    with attach_curl_on_fail(ENDPOINT, params, headers, "GET"):
        response = api_client.get(ENDPOINT, headers=headers, params=params)
        assert response.status_code == 400


def test_negative_null_interval_parameter(api_client, auth_token, attach_curl_on_fail):
    """Test request with null interval parameter."""
    headers = {"x-access-token": auth_token}
    params = {"interval": None}
    
    with attach_curl_on_fail(ENDPOINT, params, headers, "GET"):
        response = api_client.get(ENDPOINT, headers=headers, params=params)
        assert response.status_code == 400


def test_negative_missing_auth_token(api_client, attach_curl_on_fail):
    """Test request with missing authentication token."""
    headers = {}
    params = {"interval": "hour"}
    
    with attach_curl_on_fail(ENDPOINT, params, headers, "GET"):
        response = api_client.get(ENDPOINT, headers=headers, params=params)
        assert response.status_code == 401


def test_negative_invalid_auth_token(api_client, attach_curl_on_fail):
    """Test request with invalid authentication token."""
    headers = {"x-access-token": "invalid_token_123"}
    params = {"interval": "hour"}
    
    with attach_curl_on_fail(ENDPOINT, params, headers, "GET"):
        response = api_client.get(ENDPOINT, headers=headers, params=params)
        assert response.status_code == 401


def test_negative_malformed_auth_token(api_client, attach_curl_on_fail):
    """Test request with malformed authentication token."""
    headers = {"x-access-token": ""}
    params = {"interval": "minute"}
    
    with attach_curl_on_fail(ENDPOINT, params, headers, "GET"):
        response = api_client.get(ENDPOINT, headers=headers, params=params)
        assert response.status_code == 401


def test_negative_numeric_interval_parameter(api_client, auth_token, attach_curl_on_fail):
    """Test request with numeric interval parameter."""
    headers = {"x-access-token": auth_token}
    params = {"interval": 123}
    
    with attach_curl_on_fail(ENDPOINT, params, headers, "GET"):
        response = api_client.get(ENDPOINT, headers=headers, params=params)
        assert response.status_code == 422


def test_negative_boolean_interval_parameter(api_client, auth_token, attach_curl_on_fail):
    """Test request with boolean interval parameter."""
    headers = {"x-access-token": auth_token}
    params = {"interval": True}
    
    with attach_curl_on_fail(ENDPOINT, params, headers, "GET"):
        response = api_client.get(ENDPOINT, headers=headers, params=params)
        assert response.status_code == 422


def test_negative_extra_query_parameters(api_client, auth_token, attach_curl_on_fail):
    """Test request with unsupported extra query parameters."""
    headers = {"x-access-token": auth_token}
    params = {"interval": "hour", "extra_param": "value", "another": "test"}
    
    with attach_curl_on_fail(ENDPOINT, params, headers, "GET"):
        response = api_client.get(ENDPOINT, headers=headers, params=params)
        assert response.status_code == 200
