"""Tests for the /router/routes endpoint."""
import pytest
from jsonschema import validate, ValidationError
import json

# The API endpoint under test.
ENDPOINT = "/router/routes"

# JSON schema for a single route item.
# The 'mask' field is validated using a regex pattern for CIDR notation.
ROUTE_ITEM_SCHEMA = {
    "type": "object",
    "properties": {
        "mask": {
            "type": ["string", "null"],
            "pattern": r"^(?:[0-9]{1,3}\.){3}[0-9]{1,3}/[0-9]{1,2}$"
        },
        "distance": {"type": ["integer", "null"]},
        "metric": {"type": ["integer", "null"]},
        "local": {"type": "boolean"},
        "kernel": {"type": "boolean"},
        "connected": {"type": "boolean"},
        "static": {"type": "boolean"},
        "rip": {"type": "boolean"},
        "ospf": {"type": "boolean"},
        "isIs": {"type": "boolean"},
        "bgp": {"type": "boolean"},
        "pim": {"type": "boolean"},
        "babel": {"type": "boolean"},
        "nhrp": {"type": "boolean"},
        "selected": {"type": "boolean"},
        "fib": {"type": "boolean"},
        "connectedThrough": {"type": ["string", "null"]},
        "interface": {"type": ["string", "null"]},
        "lastUpdate": {"type": ["string", "null"]},
        "active": {"type": "boolean"},
        "weight": {"type": ["integer", "null"]}
    },
    "required": [
        "local", "kernel", "connected", "static", "rip", "ospf", "isIs",
        "bgp", "pim", "babel", "nhrp", "selected", "fib", "active"
    ]
}

# JSON schema for the root of the response.
ROOT_SCHEMA = {
    "type": "array",
    "items": ROUTE_ITEM_SCHEMA
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
    - Validates the response against the JSON schema, including the 'mask' pattern.
    """
    response = api_client.get(ENDPOINT)
    try:
        assert response.status_code == 200
        validate(instance=response.json(), schema=ROOT_SCHEMA)
    except (AssertionError, ValidationError) as e:
        curl_command = _get_curl_command(getattr(api_client, 'last_request', None))
        pytest.fail(f"Base request failed. Error: {e}\n{curl_command}")

# Scenarios that should result in a 200 OK response.
SUCCESS_PARAMS = [
    ("limit", "10"),
    ("offset", "10"),
    ("filter", '{"mask": "0.0.0.0/0"}'),
    ("filter", '{"metric": 0}'),
    ("filter", '{"non_existent_field": "value"}'),
    ("filter", ""),
    ("filter", '{"mask": "1.2.3.4"}'),  # Valid JSON, but ignored filter value (no CIDR)
    ("random_param", "random_value"),
    ("long_param", "a" * 500),
    ("sql_injection", "' OR 1=1 --"),
    ("xss_param", "<script>alert(1)</script>")
]

# Scenarios that should result in a 400 Bad Request response.
FAILURE_PARAMS = [
    ("filter", "{'mask': '0.0.0.0/0'}"),  # Invalid JSON (single quotes)
    ("filter", "not_a_json_string"),
]

@pytest.mark.parametrize("param, value", SUCCESS_PARAMS)
def test_successful_parameterized_requests(api_client, param, value):
    """
    Tests that various valid and ignored parameters return 200 OK and a valid schema.
    """
    params = {param: value}
    response = api_client.get(ENDPOINT, params=params)
    try:
        assert response.status_code == 200
        validate(instance=response.json(), schema=ROOT_SCHEMA)
    except (AssertionError, ValidationError) as e:
        curl_command = _get_curl_command(getattr(api_client, 'last_request', None))
        pytest.fail(f"Success test failed for {param}={value}. Error: {e}\n{curl_command}")

@pytest.mark.parametrize("param, value", FAILURE_PARAMS)
def test_failure_parameterized_requests(api_client, param, value):
    """
    Tests that malformed or invalid parameters return a 400 Bad Request.
    """
    params = {param: value}
    response = api_client.get(ENDPOINT, params=params)
    try:
        assert response.status_code == 400
    except AssertionError as e:
        curl_command = _get_curl_command(getattr(api_client, 'last_request', None))
        pytest.fail(
            f"Failure test expected 400 but got {response.status_code} "
            f"for {param}={value}. Error: {e}\n{curl_command}"
        ) 