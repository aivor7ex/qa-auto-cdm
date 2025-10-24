"""
Local Rules API Tests - POST Method

This module contains comprehensive tests for the POST /api/localRules endpoint.
Tests validate request/response schema, error handling, and various payload combinations.

Key features:
- Dynamic interface selection from available interfaces
- Random port generation to avoid conflicts
- Comprehensive validation of API responses
- Proper error handling and curl command generation
"""

import pytest
import json
import random
from typing import List, Dict, Any, Union

# =====================================================================================================================
# Constants (R18: объявить ENDPOINT в начале файла)
# =====================================================================================================================

ENDPOINT = "/localRules"

# --- Response Schemas for GET and POST ---
response_schemas = {
    "GET": {
        "type": "array",
        "items": {
            "type": "object",
            "required": ["port", "id", "hash_portif"],
            "properties": {
                "port": {"type": "integer"},
                "id": {"type": "string"},
                "hash_portif": {"type": "string"},
                "interface": {"anyOf": [{"type": "string"}, {"type": "null"}]},
                "description": {"anyOf": [{"type": "string"}, {"type": "null"}]},
                "type": {"anyOf": [{"type": "string"}, {"type": "null"}]}
            },
            "additionalProperties": True
        }
    },
    "POST": {
        "type": "object",
        "required": ["port", "id", "hash_portif"],
        "properties": {
            "port": {"type": "integer"},
            "id": {"type": "string"},
            "hash_portif": {"type": "string"},
            "interface": {"anyOf": [{"type": "string"}, {"type": "null"}]},
            "description": {"anyOf": [{"type": "string"}, {"type": "null"}]},
            "type": {"anyOf": [{"type": "string"}, {"type": "null"}]}
        },
        "additionalProperties": True
    }
}

# Error response schema for validation failures
ERROR_RESPONSE_SCHEMA = {
    "type": "object",
    "required": ["error"],
    "properties": {
        "error": {
            "type": "object",
            "required": ["statusCode", "message"],
            "properties": {
                "statusCode": {"type": "integer"},
                "message": {"type": "string"},
                "name": {"type": "string"},
                "status": {"type": "integer"},
                "stack": {"type": "string"}
            },
            "additionalProperties": True
        }
    },
    "additionalProperties": True
}

# =====================================================================================================================
# Helper Functions
# =====================================================================================================================

def validate_schema(data, schema):
    """Recursively validates data against a JSON schema."""
    # Handle anyOf (union types)
    if "anyOf" in schema:
        for sub_schema in schema["anyOf"]:
            try:
                validate_schema(data, sub_schema)
                return  # If one validates successfully, we're good
            except AssertionError:
                continue
        # If none of the schemas validate, fail
        assert False, f"Data {data} doesn't match any of the anyOf schemas"
    
    if schema.get("type") == "array":
        assert isinstance(data, list), f"Expected array, got {type(data).__name__}"
        if "items" in schema and data:
            for item in data:
                validate_schema(item, schema["items"])
        return
    
    if schema.get("type") == "object":
        assert isinstance(data, dict), f"Expected object, got {type(data).__name__}"
        
        # Check required fields
        required_fields = schema.get("required", [])
        for field in required_fields:
            assert field in data, f"Missing required field '{field}'"
        
        # Validate properties
        properties = schema.get("properties", {})
        for field_name, field_schema in properties.items():
            if field_name in data:
                validate_schema(data[field_name], field_schema)
        return
    
    if schema.get("type") == "null":
        assert data is None, f"Expected null, got {type(data).__name__}"
        return
    
    # Handle primitive types
    expected_types = schema.get("type", [])
    if isinstance(expected_types, str):
        expected_types = [expected_types]
    
    if expected_types:
        type_mapping = {
            "string": str,
            "integer": int,
            "number": (int, float),
            "boolean": bool,
            "array": list,
            "object": dict,
            "null": type(None)
        }
        
        python_types = []
        for expected_type in expected_types:
            if expected_type in type_mapping:
                mapped_type = type_mapping[expected_type]
                if isinstance(mapped_type, tuple):
                    python_types.extend(mapped_type)
                else:
                    python_types.append(mapped_type)
        
        if python_types:
            assert isinstance(data, tuple(python_types)), \
                f"Expected type {expected_types}, got {type(data).__name__}"

def get_available_interfaces(api_client):
    """Fetches available interfaces from the API."""
    try:
        response = api_client.get("/managers/ipaddr")
        if response.status_code == 200:
            interfaces = response.json()
            interface_names = [iface["name"] for iface in interfaces if "name" in iface]
            return interface_names
        return ["eth0", "lo", "dummy0"]  # Fallback interfaces
    except:
        return ["eth0", "lo", "dummy0"]  # Fallback interfaces

def generate_random_port():
    """Генерирует случайный порт в допустимом диапазоне."""
    return random.randint(1024, 65535)

def generate_unique_description(base_description):
    """Генерирует уникальное описание с добавлением случайного суффикса."""
    suffix = random.randint(10000, 99999)
    return f"{base_description}_{suffix}"

# =====================================================================================================================
# Test Data Generation
# =====================================================================================================================

def generate_post_test_cases():
    """Generates comprehensive POST test cases for local rules creation."""
    
    test_cases = []
    
    # ===== POSITIVE CASES (Expected to work) =====
    
    # 1. Minimal request (only required parameter)
    test_cases.append(({
        "port": generate_random_port()
    }, [200, 404], "Minimal request with only port"))
    
    # 2. With interface
    test_cases.append(({
        "port": generate_random_port(),
        "interface": "eth0"
    }, [200, 404], "With interface parameter"))
    
    # 3. With description
    test_cases.append(({
        "port": generate_random_port(),
        "description": generate_unique_description("Web server port")
    }, [200, 404], "With description parameter"))
    
    # 4. With type
    test_cases.append(({
        "port": generate_random_port(),
        "type": "web"
    }, [200, 404], "With type parameter"))
    
    # 5. With interface and description
    test_cases.append(({
        "port": generate_random_port(),
        "interface": "lo",
        "description": generate_unique_description("Loopback rule")
    }, [200, 404], "With interface and description"))
    
    # 6. With interface and type
    test_cases.append(({
        "port": generate_random_port(),
        "interface": "dummy0",
        "type": "database"
    }, [200, 404], "With interface and type"))
    
    # 7. With description and type
    test_cases.append(({
        "port": generate_random_port(),
        "description": generate_unique_description("API server"),
        "type": "api"
    }, [200, 404], "With description and type"))
    
    # 8. Full request (all parameters)
    test_cases.append(({
        "port": generate_random_port(),
        "interface": "eth0",
        "type": "web",
        "description": generate_unique_description("Full configuration test")
    }, [200, 404], "Full request with all parameters"))
    
    # 9. Standard HTTP port
    test_cases.append(({
        "port": 80,
        "description": generate_unique_description("HTTP server")
    }, [200, 404], "Standard HTTP port"))
    
    # 10. Standard HTTPS port
    test_cases.append(({
        "port": 443,
        "description": generate_unique_description("HTTPS server")
    }, [200, 404], "Standard HTTPS port"))
    
    # 11. SSH port
    test_cases.append(({
        "port": 22,
        "description": generate_unique_description("SSH access")
    }, [200, 404], "SSH port"))
    
    # 12. Custom high port
    test_cases.append(({
        "port": 8080,
        "interface": "docker0",
        "description": generate_unique_description("Docker container port")
    }, [200, 404], "Custom high port with docker interface"))
    
    # 13. Database port
    test_cases.append(({
        "port": 3306,
        "type": "database",
        "description": generate_unique_description("MySQL database")
    }, [200, 404], "Database port with type"))
    
    # 14. API port
    test_cases.append(({
        "port": 3000,
        "type": "api",
        "description": generate_unique_description("REST API server")
    }, [200, 404], "API port with type"))
    
    # 15. Very high port number
    test_cases.append(({
        "port": 65535,
        "description": generate_unique_description("Maximum port number")
    }, [200, 404], "Maximum valid port"))
    
    # 16. Various interface types
    for interface in ["lo", "dummy0", "vethngfw0", "http1host"]:
        test_cases.append(({
            "port": generate_random_port(),
            "interface": interface,
            "description": generate_unique_description(f"Rule for {interface}")
        }, [200, 404], f"Interface {interface}"))
    
    # 17. Various service types
    for service_type in ["web", "api", "database", "cache", "proxy", "mail"]:
        test_cases.append(({
            "port": generate_random_port(),
            "type": service_type,
            "description": generate_unique_description(f"{service_type} service")
        }, [200, 404], f"Service type {service_type}"))
    
    # 18. Special characters in description
    test_cases.append(({
        "port": generate_random_port(),
        "description": generate_unique_description("Test with special chars @#$%^&*()")
    }, [200, 404], "Special characters in description"))
    
    # 19. Unicode characters in description
    test_cases.append(({
        "port": generate_random_port(),
        "description": generate_unique_description("Test с русскими символами")
    }, [200, 404], "Unicode characters in description"))
    
    # 20. Numbers in description
    test_cases.append(({
        "port": generate_random_port(),
        "description": f"Rule number {random.randint(1000, 9999)}"
    }, [200, 404], "Numbers in description"))
    
    # ===== NEGATIVE CASES (Expected to fail) =====
    
    # 21. Missing port (empty body)
    test_cases.append(({
    }, [422], "Empty request body"))
    
    # 22. Missing port with other parameters
    test_cases.append(({
        "interface": "eth0",
        "description": "Missing port test"
    }, [422], "Missing required port parameter"))
    
    # 23. Invalid port type (string)
    test_cases.append(({
        "port": "invalid"
    }, [422], "Invalid port type (string)"))
    
    # 24. Invalid port type (null)
    test_cases.append(({
        "port": None
    }, [422], "Invalid port type (null)"))
    
    # 25. Invalid port type (float)
    test_cases.append(({
        "port": 8080.5
    }, [422], "Invalid port type (float)"))
    
    # 26. Port too low (zero) - API now accepts port 0
    test_cases.append(({
        "port": 0
    }, [200, 404], "Port number too low (zero)"))
    
    # 27. Port too low (negative) - validation error
    test_cases.append(({
        "port": -1
    }, [422], "Port number negative"))
    
    # 28. Port too high - validation error
    test_cases.append(({
        "port": 99999
    }, [422], "Port number too high"))
    
    # 29. Interface as number (API converts to string)
    test_cases.append(({
        "port": generate_random_port(),
        "interface": 123
    }, [200, 404], "Interface as number (converted to string)"))
    
    # 30. Interface as null (API accepts it)
    test_cases.append(({
        "port": generate_random_port(),
        "interface": None
    }, [200, 404], "Interface as null"))
    
    # 31. Description as number (API converts to string)
    test_cases.append(({
        "port": generate_random_port(),
        "description": 123
    }, [200, 404], "Description as number"))
    
    # 32. Description as null (API accepts it)
    test_cases.append(({
        "port": generate_random_port(),
        "description": None
    }, [200, 404], "Description as null"))
    
    # 33. Type as number (API converts to string)
    test_cases.append(({
        "port": generate_random_port(),
        "type": 123
    }, [200, 404], "Type as number"))
    
    # 34. Type as null (API accepts it)
    test_cases.append(({
        "port": generate_random_port(),
        "type": None
    }, [200, 404], "Type as null"))
    
    # 35. Empty string description (API accepts it)
    test_cases.append(({
        "port": generate_random_port(),
        "description": ""
    }, [200, 404], "Empty string description"))
    
    # 36. Empty string interface (API accepts it)
    test_cases.append(({
        "port": generate_random_port(),
        "interface": ""
    }, [200, 404], "Empty string interface"))
    
    # 37. Empty string type (API accepts it)
    test_cases.append(({
        "port": generate_random_port(),
        "type": ""
    }, [200, 404], "Empty string type"))
    
    # 38. Very long description (API accepts it)
    test_cases.append(({
        "port": generate_random_port(),
        "description": "x" * 1000
    }, [200, 404], "Very long description"))
    
    # 39. Very long interface name (validation error)
    test_cases.append(({
        "port": generate_random_port(),
        "interface": "x" * 500
    }, [422], "Very long interface name"))
    
    # 40. Very long type name (API accepts it)
    test_cases.append(({
        "port": generate_random_port(),
        "type": "x" * 500
    }, [200, 404], "Very long type name"))
    
    # 41. Extra unknown fields (API rejects them)
    test_cases.append(({
        "port": generate_random_port(),
        "unknown_field": "should_be_ignored",
        "another_unknown": 123
    }, [422], "Extra unknown fields"))
    
    # 42. Duplicate port conflict test
    test_cases.append(({
        "port": 8080  # This might conflict with example in config
    }, [200, 404], "Potential port conflict"))
    
    return test_cases

# =====================================================================================================================
# POST Method Tests
# =====================================================================================================================

@pytest.mark.parametrize("payload, expected_status_codes, description", generate_post_test_cases())
def test_local_rules_post_comprehensive(api_client, attach_curl_on_fail, agent_verification, payload, expected_status_codes, description):
    """
    Comprehensive POST endpoint testing for local rules creation.
    
    Validates creation of local rules with various payload combinations,
    network port configurations, and error handling scenarios.
    Tests cover positive cases (expected to work) and negative cases (validation errors).
    """
    with attach_curl_on_fail(ENDPOINT, payload, method="POST"):
        response = api_client.post(ENDPOINT, json=payload)
        
        # Handle expected status codes (can be list or single value)
        if isinstance(expected_status_codes, list):
            assert response.status_code in expected_status_codes, \
                f"Expected status {expected_status_codes} for {description}, got {response.status_code}"
        else:
            assert response.status_code == expected_status_codes, \
                f"Expected status {expected_status_codes} for {description}, got {response.status_code}"
        
        data = response.json()
        
        if response.status_code == 200:
            # Success case - validate response schema
            validate_schema(data, response_schemas["POST"])
            
            # Verify required fields are present and correct
            assert data.get("port") == payload.get("port"), "Port mismatch in response"
            
            # Verify optional fields if provided (API may convert types to strings)
            if "interface" in payload:
                expected_interface = str(payload.get("interface")) if payload.get("interface") is not None else None
                actual_interface = data.get("interface")
                assert actual_interface == expected_interface, f"Interface mismatch: expected {expected_interface}, got {actual_interface}"
            if "description" in payload:
                expected_description = str(payload.get("description")) if payload.get("description") is not None else None
                actual_description = data.get("description")
                assert actual_description == expected_description, f"Description mismatch: expected {expected_description}, got {actual_description}"
            if "type" in payload:
                expected_type = str(payload.get("type")) if payload.get("type") is not None else None
                actual_type = data.get("type")
                assert actual_type == expected_type, f"Type mismatch: expected {expected_type}, got {actual_type}"
            
            # Verify generated fields
            assert isinstance(data.get("id"), str) and len(data.get("id")) > 0, "ID should be non-empty string"
            assert isinstance(data.get("hash_portif"), str) and len(data.get("hash_portif")) > 0, "Hash should be non-empty string"
            
            # Verify ID format (appears to be hex ObjectId-like)
            id_value = data.get("id", "")
            assert len(id_value) >= 20, "ID should be at least 20 characters long"
            
            # Verify hash format (appears to be hex hash)
            hash_value = data.get("hash_portif", "")
            assert len(hash_value) >= 32, "Hash should be at least 32 characters long"
            
            # Additional agent verification for successful POST requests (status 200)
            # Only execute for positive test cases that expect success
            if isinstance(expected_status_codes, list) and 200 in expected_status_codes:
                print(f"Starting agent verification for successful localRules creation: port {payload.get('port')}")
                
                # Create agent verification payload with minimal required data
                agent_payload = {
                    "port": payload.get("port"),
                    "interface": payload.get("interface"),
                    "description": payload.get("description"),
                    "type": payload.get("type")
                }
                
                # Remove None values from agent payload
                agent_payload = {k: v for k, v in agent_payload.items() if v is not None}
                
                # Call agent verification endpoint
                agent_result = agent_verification("/localRules", agent_payload)
                
                # Handle agent response according to the common fixture contract (dict or "unavailable")
                if agent_result == "unavailable":
                    pytest.fail(f"Agent verification: AGENT UNAVAILABLE - localRule for port {payload.get('port')} verification failed due to agent unavailability")
                elif isinstance(agent_result, dict) and agent_result.get("result") == "OK":
                    print(f"Agent verification: SUCCESS - localRule for port {payload.get('port')} was verified")
                elif isinstance(agent_result, dict) and agent_result.get("result") == "ERROR":
                    message = agent_result.get("message", "Unknown error")
                    pytest.fail(f"Agent verification: ERROR - localRule for port {payload.get('port')} verification failed: {message}")
                else:
                    pytest.fail(f"Agent verification: UNEXPECTED RESULT {agent_result} for port {payload.get('port')}")
                
        elif response.status_code == 404:
            # Rule already exists - validate error response schema
            validate_schema(data, ERROR_RESPONSE_SCHEMA)
            
            error = data["error"]
            assert error["statusCode"] == 404, "Error statusCode should be 404"
            assert isinstance(error["message"], str) and len(error["message"]) > 0, "Error message should be non-empty string"
            
            # Check for specific error message
            message = error["message"].lower()
            assert any(word in message for word in ["already", "exist", "combination"]), \
                f"404 error should mention rule already exists: {error['message']}"
                
        elif response.status_code in [400, 422]:
            # Error cases - validate error response schema
            validate_schema(data, ERROR_RESPONSE_SCHEMA)
            
            error = data["error"]
            assert error["statusCode"] == response.status_code, "Error statusCode mismatch"
            assert isinstance(error["message"], str) and len(error["message"]) > 0, "Error message should be non-empty string"
            
            # Check for specific error patterns based on test case
            message = error["message"].lower()
            
            if "missing" in description.lower() or "empty" in description.lower():
                # Missing or empty field errors
                assert any(word in message for word in ["undefined", "required", "missing", "invalid", "error"]), \
                    f"Missing/empty field error should mention validation issue: {error['message']}"
            elif "invalid" in description.lower():
                # Invalid value errors should mention validation, type conversion, or format issues
                assert any(word in message for word in ["invalid", "error", "iptables", "specified", "type"]), \
                    f"Invalid value error should mention validation: {error['message']}"
            elif "conflict" in description.lower():
                # Port conflict errors
                assert any(word in message for word in ["already", "exist", "conflict", "combination"]), \
                    f"Conflict error should mention existing rule: {error['message']}"
                    
        else:
            pytest.fail(f"Unexpected status code {response.status_code} for {description}")

# =====================================================================================================================
# Edge Cases and Content-Type Tests
# =====================================================================================================================

def test_local_rules_post_invalid_content_type(api_client, attach_curl_on_fail):
    """Test POST with invalid Content-Type header."""
    payload = {
        "port": generate_random_port()
    }
    
    headers = {"Content-Type": "text/plain"}
    
    with attach_curl_on_fail(ENDPOINT, payload, headers=headers, method="POST"):
        response = api_client.post(ENDPOINT, json=payload, headers=headers)
        assert response.status_code == 422, f"Expected 422 for invalid content type, got {response.status_code}"

def test_local_rules_post_missing_content_type(api_client, attach_curl_on_fail):
    """Test POST without Content-Type header."""
    payload = {
        "port": generate_random_port()
    }
    
    headers = {}
    
    with attach_curl_on_fail(ENDPOINT, payload, headers=headers, method="POST"):
        response = api_client.post(ENDPOINT, json=payload, headers=headers)
        # API accepts missing content type and may return success or conflict
        assert response.status_code in [200, 404], f"Unexpected status code: {response.status_code}"

def test_local_rules_post_malformed_json(api_client, attach_curl_on_fail):
    """Test POST with malformed JSON."""
    malformed_json = '{"port": 8080'  # Missing closing brace
    
    with attach_curl_on_fail(ENDPOINT, malformed_json, method="POST"):
        response = api_client.post(ENDPOINT, data=malformed_json, headers={"Content-Type": "application/json"})
        assert response.status_code == 400, f"Expected 400 for malformed JSON, got {response.status_code}"

def test_local_rules_post_empty_body(api_client, attach_curl_on_fail):
    """Test POST with empty request body."""
    with attach_curl_on_fail(ENDPOINT, {}, method="POST"):
        response = api_client.post(ENDPOINT, json={})
        assert response.status_code == 422, f"Expected 422 for empty body, got {response.status_code}"

def test_local_rules_post_null_body(api_client, attach_curl_on_fail):
    """Test POST with null request body."""
    with attach_curl_on_fail(ENDPOINT, None, method="POST"):
        response = api_client.post(ENDPOINT, json=None)
        assert response.status_code == 422, f"Expected 422 for null body, got {response.status_code}"

def test_local_rules_post_string_body(api_client, attach_curl_on_fail):
    """Test POST with string instead of JSON object."""
    with attach_curl_on_fail(ENDPOINT, "invalid", method="POST"):
        response = api_client.post(ENDPOINT, json="invalid")
        assert response.status_code == 400, f"Expected 400 for string body, got {response.status_code}"

def test_local_rules_post_number_body(api_client, attach_curl_on_fail):
    """Test POST with number instead of JSON object."""
    with attach_curl_on_fail(ENDPOINT, 123, method="POST"):
        response = api_client.post(ENDPOINT, json=123)
        assert response.status_code == 400, f"Expected 400 for number body, got {response.status_code}"

def test_local_rules_post_boolean_body(api_client, attach_curl_on_fail):
    """Test POST with boolean instead of JSON object."""
    with attach_curl_on_fail(ENDPOINT, True, method="POST"):
        response = api_client.post(ENDPOINT, json=True)
        assert response.status_code == 400, f"Expected 400 for boolean body, got {response.status_code}"

def test_local_rules_post_with_available_interfaces(api_client, attach_curl_on_fail):
    """Test POST with dynamically fetched available interfaces."""
    available_interfaces = get_available_interfaces(api_client)
    
    # Test with first available interface
    if available_interfaces:
        interface = available_interfaces[0]
        payload = {
            "port": generate_random_port(),
            "interface": interface,
            "description": generate_unique_description(f"Dynamic interface test {interface}")
        }
        
        with attach_curl_on_fail(ENDPOINT, payload, method="POST"):
            response = api_client.post(ENDPOINT, json=payload)
            assert response.status_code == 200, f"Expected 200 for available interface {interface}, got {response.status_code}"
            
            data = response.json()
            assert data.get("interface") == interface, f"Interface mismatch in response"

def test_local_rules_post_boundary_ports(api_client, attach_curl_on_fail):
    """Test POST with boundary port values."""
    boundary_cases = [
        (1, "Minimum valid port"),
        (1023, "Just below unprivileged range"),
        (1024, "Start of unprivileged range"),
        (65534, "Just below maximum"),
        (65535, "Maximum valid port")
    ]
    
    for port, desc in boundary_cases:
        payload = {
            "port": port,
            "description": generate_unique_description(desc)
        }
        
        with attach_curl_on_fail(ENDPOINT, payload, method="POST"):
            response = api_client.post(ENDPOINT, json=payload)
            # All these ports should be valid, expecting success or rule exists
            assert response.status_code in [200, 404], f"Expected 200/404 for port {port}, got {response.status_code}"

# =====================================================================================================================
# GET Method Tests
# =====================================================================================================================

def test_local_rules_get_success(api_client, attach_curl_on_fail):
    """Test GET request to retrieve all local rules."""
    with attach_curl_on_fail(ENDPOINT, {}, method="GET"):
        response = api_client.get(ENDPOINT)
        assert response.status_code == 200, f"Expected 200 for GET request, got {response.status_code}"
        
        data = response.json()
        
        # Validate response schema
        validate_schema(data, response_schemas["GET"])
        
        # Check that it's an array
        assert isinstance(data, list), "Response should be an array"
        
        # If there are items, validate each one
        for item in data:
            assert isinstance(item.get("port"), int), "Port should be integer"
            assert isinstance(item.get("id"), str) and len(item.get("id", "")) > 0, "ID should be non-empty string"
            assert isinstance(item.get("hash_portif"), str) and len(item.get("hash_portif", "")) > 0, "Hash should be non-empty string"
            
            # Optional fields validation (can be string or null)
            if "interface" in item and item["interface"] is not None:
                assert isinstance(item["interface"], str), "Interface should be string or null"
            if "description" in item and item["description"] is not None:
                assert isinstance(item["description"], str), "Description should be string or null"  
            if "type" in item and item["type"] is not None:
                assert isinstance(item["type"], str), "Type should be string or null"

def test_local_rules_get_with_invalid_params(api_client, attach_curl_on_fail):
    """Test GET request with invalid query parameters."""
    invalid_params = [
        {"invalid_param": "test"},
        {"port": "invalid"},
        {"limit": "abc"},
        {"offset": -1}
    ]
    
    for params in invalid_params:
        with attach_curl_on_fail(ENDPOINT, params, method="GET"):
            response = api_client.get(ENDPOINT, params=params)
            # GET endpoints typically ignore unknown parameters
            assert response.status_code == 200, f"Expected 200 for params {params}, got {response.status_code}"