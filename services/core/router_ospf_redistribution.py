"""Tests for the /router/ospf/redistribution endpoint."""
import pytest
from jsonschema import validate, ValidationError
import json

# The API endpoint under test.
ENDPOINT = "/router/ospf/redistribution"

# JSON schema for an item in the response array.
ITEM_SCHEMA = {
    "type": "object",
    "properties": {
        "proto": {"type": "string"},
        "metricType": {"type": ["string", "null"]},
        "metric": {"type": ["integer", "null"]},
        "id": {"type": "integer"}
    },
    "required": ["proto", "metricType", "metric", "id"]
}

# JSON schema for the root of the response.
ROOT_SCHEMA = {
    "type": "array",
    "items": ITEM_SCHEMA
}

def _get_curl_command(last_request):
    """Formats a curl command from a PreparedRequest object for debugging."""
    if not last_request:
        return "Could not retrieve request details for curl command."

    parts = [f"curl -X {last_request.method} '{last_request.url}'"]
    for k, v in last_request.headers.items():
        parts.append(f"  -H '{k}: {v}'")

    command = " \\\n".join(parts)

    return (
        f"\n================= Failed Test Request (curl) =================\n"
        f"{command}\n"
        f"============================================================="
    )

def test_base_request(api_client):
    """
    Tests the endpoint's basic functionality with no parameters.
    - Verifies the status code is 200.
    - Validates the response against the JSON schema.
    """
    response = api_client.get(ENDPOINT)
    try:
        assert response.status_code == 200
        validate(instance=response.json(), schema=ROOT_SCHEMA)
    except (AssertionError, ValidationError) as e:
        curl_command = _get_curl_command(getattr(api_client, 'last_request', None))
        pytest.fail(f"Base request failed. Error: {e}\n{curl_command}")

# A diverse set of over 35 parameters to test endpoint robustness.
# This endpoint is expected to ignore all of them and return a valid response.
PARAM_SCENARIOS = [
    ("filter", '{"proto": "connected"}'), ("sort", "id"), ("order", "desc"),
    ("limit", "10"), ("offset", "20"), ("page", "2"), ("q", "search"),
    ("id", "some-id"), ("name", "some-name"), ("_id", "object-id"),
    ("param1", ""), ("param2", "null"), ("param3", "undefined"),
    ("param4", "true"), ("param5", "false"), ("param6", "0"),
    ("param7", "!@#$%^&*()"), ("param8", "<script>alert('xss')</script>"),
    ("utf8_param", "тест"), ("emoji_param", "👍"),
    ("long_param", "p" * 300), ("long_value", "v" * 300),
    ("select", "proto,metric"), ("populate", "some_relation"),
    ("distinct", "proto"), ("count", "false"),
    ("format", "yaml"), ("callback", "jsonp_handler"),
    ("filter", '{"metric": {"$gt": 10}}'),
    ("filter", '{"non_existent_field": 1}'),
    ("filter", ""),
    ("another_param", "another_value"),
    ("p_with_space", "v with space"),
    ("p_with_leading_zero", "007"),
    ("p_with_trailing_space", "value   "),
    ("p_sql_injection", "1' OR '1'='1"),
    ("p_null_byte", "a\0b")
]

@pytest.mark.parametrize("param, value", PARAM_SCENARIOS)
def test_parameterized_ignored_params(api_client, param, value):
    """
    Verifies that the endpoint ignores various query parameters,
    always returning a 200 status and a valid response body.
    """
    params = {param: value}
    response = api_client.get(ENDPOINT, params=params)

    try:
        assert response.status_code == 200
        validate(instance=response.json(), schema=ROOT_SCHEMA)
    except (AssertionError, ValidationError) as e:
        curl_command = _get_curl_command(getattr(api_client, 'last_request', None))
        pytest.fail(
            f"Test with ignored param failed for {param}={value}. "
            f"Error: {e}\n{curl_command}"
        ) 