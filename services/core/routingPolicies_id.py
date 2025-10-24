import pytest
from jsonschema import validate
import shlex
import json

ROUTING_POLICIES_ENDPOINT = "/routingPolicies"

ROUTING_POLICY_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "toNetwork": {"type": "string"},
        "fromNetwork": {"type": "string"},
        "table": {"type": "integer"},
        "priority": {"type": "integer"},
        "interfaceId": {"type": "string"},
        "active": {"type": "boolean"},
        "id": {"type": "string"},
    },
    "required": ["name", "toNetwork", "fromNetwork", "table", "priority", "interfaceId", "active", "id"],
    "additionalProperties": False,
}

INVALID_ID_PARAMS = [
    ("nonexistent", "6152deb79793730008d8a895", [404]),
    ("invalid_format", "not-a-valid-id", [400, 404]),
    ("integer", 123, [400, 404]),
    ("zero", 0, [400, 404]),
    ("negative", -1, [400, 404]),
    ("float", 1.23, [400, 404]),
    ("scientific_notation", "1e3", [400, 404]),
    ("null_string", "null", [400, 404]),
    ("true_string", "true", [400, 404]),
    ("false_string", "false", [400, 404]),
    ("empty_string", "", [200]),
    ("space", " ", [400, 404]),
    ("multiple_spaces", "   ", [400, 404]),
    ("newline", "\n", [200]),
    ("tab", "\t", [200]),
    ("long_numeric", "123456789012345678901234567890", [400, 404]),
    ("long_string", "a" * 100, [400, 404]),
    ("long_hex", "f" * 100, [400, 404]),
    ("special_chars_1", "!@#$%^", [400, 404]),
    ("special_chars_2", "()_+-=", [400, 404]),
    ("special_chars_3", "[]{}", [400, 404]),
    ("special_chars_4", "';:", [400, 404]),
    ("special_chars_5", "<>,.?/", [400, 404]),
    ("path_traversal", "../..", [400, 404]),
    ("path_traversal_2", "etc/passwd", [400, 404]),
    ("sql_injection", "' OR 1=1 --", [400, 404]),
    ("xss_attempt", "<script>alert(1)</script>", [400, 404]),
    ("utf8_chars", "тест", [400, 404]),
    ("leading_zeros", "0000000", [400, 404]),
    ("hex_prefix", "0x123", [400, 404]),
    ("double_slash", "//", [200]),
    ("trailing_slash", "some-id/", [404]),
    ("id_with_query", "some-id?param=val", [400, 404]),
    ("unicode_id", "¨¨", [400, 404]),
    ("undefined_string", "undefined", [400, 404]),
    ("array_string", "[]", [400, 404]),
    ("object_string", "{}", [400, 404]),
]

def _format_curl_command(request):
    """Формирует и возвращает cURL-строку для воспроизведения запроса."""
    method = getattr(request, 'method', 'GET')
    url = getattr(request, 'url', None)
    headers = getattr(request, 'headers', {})
    body = getattr(request, 'body', None)

    curl_lines = [f"curl -X {method} '{url}'"]
    for k, v in headers.items():
        curl_lines.append(f"  -H '{k}: {v}'")
    if body:
        if isinstance(body, bytes):
            body = body.decode('utf-8')
        curl_lines.append(f"  -d '{body}'")
    return '\n'.join(curl_lines)

def test_get_routing_policies_list(api_client):
    """
    Verify that the routing policies list endpoint returns a valid JSON array.
    This test works even when the list is empty.
    """
    try:
        response = api_client.get(ROUTING_POLICIES_ENDPOINT)
        assert response.status_code == 200, f"Expected status code 200, got {response.status_code}"
        
        data = response.json()
        assert isinstance(data, list), f"Expected JSON array, got {type(data).__name__}"
        
        # If there are policies, validate the first one
        if len(data) > 0:
            validate(instance=data[0], schema=ROUTING_POLICY_SCHEMA)
            
    except (AssertionError, json.JSONDecodeError) as e:
        curl_command = _format_curl_command(getattr(response, 'request', None))
        error_message = (
            f"\nТест получения списка routing policies упал.\n"
            f"Ошибка: {e}\n\n"
            "================= Failed Test Request (cURL) ================\n"
            f"{curl_command}\n"
            "============================================================="
        )
        pytest.fail(error_message, pytrace=False)

def test_get_routing_policy_by_id_when_exists(api_client):
    """
    Verify successful retrieval of a routing policy by its valid ID and schema validation.
    This test only runs if there are existing policies.
    """
    # First check if there are any policies
    response = api_client.get(ROUTING_POLICIES_ENDPOINT)
    assert response.status_code == 200
    policies = response.json()
    
    # Skip this test if no policies exist
    if len(policies) == 0:
        pytest.skip("No routing policies exist. Skipping individual policy test.")
    
    # Get the first policy ID
    policy_id = policies[0].get("id")
    assert policy_id is not None, "First policy in the list does not have an 'id' field."
    
    try:
        response = api_client.get(f"{ROUTING_POLICIES_ENDPOINT}/{policy_id}")
        assert response.status_code == 200
        validate(instance=response.json(), schema=ROUTING_POLICY_SCHEMA)
    except (AssertionError, json.JSONDecodeError) as e:
        curl_command = _format_curl_command(getattr(response, 'request', None))
        error_message = (
            f"\nТест с ID '{policy_id}' упал.\n"
            f"Ошибка: {e}\n\n"
            "================= Failed Test Request (cURL) ================\n"
            f"{curl_command}\n"
            "============================================================="
        )
        pytest.fail(error_message, pytrace=False)

def test_get_multiple_routing_policies_by_id(api_client):
    """
    Test getting multiple routing policies by their IDs.
    Dynamically fetches real IDs from the API and tests each one.
    """
    # Get all policies
    response = api_client.get(ROUTING_POLICIES_ENDPOINT)
    assert response.status_code == 200
    policies = response.json()
    
    # Skip if no policies exist
    if len(policies) == 0:
        pytest.skip("No routing policies exist. Skipping multiple policy test.")
    
    # Test each policy (limit to first 3 to avoid too many tests)
    for i, policy in enumerate(policies[:3]):
        policy_id = policy.get("id")
        assert policy_id is not None, f"Policy {i} does not have an 'id' field."
        
        try:
            response = api_client.get(f"{ROUTING_POLICIES_ENDPOINT}/{policy_id}")
            assert response.status_code == 200, f"Failed to get policy {i} with ID {policy_id}"
            
            data = response.json()
            validate(instance=data, schema=ROUTING_POLICY_SCHEMA)
            
            # Additional checks for specific fields
            assert data.get("id") == policy_id, f"Returned policy ID doesn't match requested ID"
            assert "name" in data, "Policy should have a name field"
            assert "toNetwork" in data, "Policy should have a toNetwork field"
            assert "fromNetwork" in data, "Policy should have a fromNetwork field"
            assert "table" in data, "Policy should have a table field"
            assert "priority" in data, "Policy should have a priority field"
            assert "interfaceId" in data, "Policy should have an interfaceId field"
            assert "active" in data, "Policy should have an active field"
            
        except (AssertionError, json.JSONDecodeError) as e:
            curl_command = _format_curl_command(getattr(response, 'request', None))
            error_message = (
                f"\nТест с ID '{policy_id}' (policy {i}) упал.\n"
                f"Ошибка: {e}\n\n"
                "================= Failed Test Request (cURL) ================\n"
                f"{curl_command}\n"
                "============================================================="
            )
            pytest.fail(error_message, pytrace=False)

def test_get_routing_policy_with_query_params(api_client):
    """
    Test getting routing policies with various query parameters.
    Uses real policy IDs from the API.
    """
    # Get a policy ID
    response = api_client.get(ROUTING_POLICIES_ENDPOINT)
    assert response.status_code == 200
    policies = response.json()
    
    if len(policies) == 0:
        pytest.skip("No routing policies exist. Skipping query params test.")
    
    policy_id = policies[0].get("id")
    assert policy_id is not None, "First policy does not have an 'id' field."
    
    # Test with various query parameters
    query_params_tests = [
        ({}, "no_params"),
        ({"format": "json"}, "with_format"),
        ({"verbose": "true"}, "with_verbose"),
        ({"details": "true"}, "with_details"),
        ({"include": "all"}, "with_include"),
        ({"expand": "true"}, "with_expand"),
        ({"format": "json", "verbose": "true"}, "with_format_and_verbose"),
    ]
    
    for params, test_name in query_params_tests:
        try:
            response = api_client.get(f"{ROUTING_POLICIES_ENDPOINT}/{policy_id}", params=params)
            # Most query params should be ignored for individual policy requests
            assert response.status_code == 200, f"Test '{test_name}' failed. Expected 200, got {response.status_code}"
            
            data = response.json()
            validate(instance=data, schema=ROUTING_POLICY_SCHEMA)
            
        except (AssertionError, json.JSONDecodeError) as e:
            curl_command = _format_curl_command(getattr(response, 'request', None))
            error_message = (
                f"\nТест '{test_name}' с ID '{policy_id}' упал.\n"
                f"Ошибка: {e}\n\n"
                "================= Failed Test Request (cURL) ================\n"
                f"{curl_command}\n"
                "============================================================="
            )
            pytest.fail(error_message, pytrace=False)

@pytest.mark.parametrize("id_type, junk_id, expected_statuses", INVALID_ID_PARAMS)
def test_get_routing_policy_with_invalid_id(api_client, id_type, junk_id, expected_statuses):
    """
    Verify that the API handles invalid routing policy IDs correctly,
    returning a 4xx status code.
    """
    try:
        response = api_client.get(f"{ROUTING_POLICIES_ENDPOINT}/{junk_id}")
        assert response.status_code in expected_statuses, f"Test '{id_type}' failed. Expected one of {expected_statuses}, but got {response.status_code} for ID: {junk_id}"
    except (AssertionError, json.JSONDecodeError) as e:
        # 3. Формирование и вывод детального отчета об ошибке
        curl_command = _format_curl_command(getattr(response, 'request', None))
        error_message = (
            f"\nТест с параметрами ... упал.\n"
            f"Ошибка: {e}\n\n"
            "================= Failed Test Request (cURL) ================\n"
            f"{curl_command}\n"
            "============================================================="
        )
        pytest.fail(error_message, pytrace=False) 