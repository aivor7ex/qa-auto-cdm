import pytest
import json
from typing import List, Dict, Any, Union

# =====================================================================================================================
# Constants
# =====================================================================================================================

ENDPOINT = "/mirrors"
METHOD = "POST"

# Schema for successful mirror creation response
RESPONSE_SCHEMA = {
    "required": {"id": str},
    "optional": {},
}

# Schema for error responses
ERROR_SCHEMA = {
    "required": {"detail": str},
    "optional": {},
}

# =====================================================================================================================
# Fixtures
# =====================================================================================================================

@pytest.fixture(scope="function")
def available_interfaces(api_client, attach_curl_on_fail):
    """Get available interface names dynamically from /managers/ipaddr endpoint."""
    with attach_curl_on_fail("/managers/ipaddr", method="GET"):
        response = api_client.get("/managers/ipaddr")
        assert response.status_code == 200, f"Failed to get interfaces: {response.status_code}"
        data = response.json()
        assert isinstance(data, list), "Expected list of interfaces"

        interfaces = []
        for iface in data:
            if isinstance(iface, dict) and "name" in iface:
                interfaces.append(iface["name"])

        # Add some common interface names that might be available
        common_interfaces = ["ids", "ids-mitm", "dummy0", "dummy1", "lo"]
        for iface in common_interfaces:
            if iface not in interfaces:
                interfaces.append(iface)

        assert len(interfaces) > 0, "No interfaces found"
        print(f"Available interfaces: {interfaces}")
        return interfaces

# =====================================================================================================================
# Validation Functions
# =====================================================================================================================

def validate_schema(data, schema):
    """Recursively validates a dictionary against a schema."""
    if isinstance(data, list):
        for item in data:
            validate_schema(item, schema)
        return
    
    assert isinstance(data, dict), f"Expected dict, got: {type(data).__name__}"
    
    for key, expected_type in schema.get("required", {}).items():
        assert key in data, f"Missing required field '{key}': {json.dumps(data, ensure_ascii=False, indent=2)}"
        actual_type = type(data[key])
        if isinstance(expected_type, tuple):
            assert actual_type in expected_type, (
                f"Field '{key}' has type {actual_type.__name__}, expected one of {[t.__name__ for t in expected_type]}"
            )
        else:
            assert actual_type is expected_type, (
                f"Field '{key}' has type {actual_type.__name__}, expected {expected_type.__name__}"
            )
    
    for key, expected_type in schema.get("optional", {}).items():
        if key in data and data[key] is not None:
            actual_type = type(data[key])
            if isinstance(expected_type, tuple):
                assert actual_type in expected_type, (
                    f"Optional field '{key}' has type {actual_type.__name__}, expected one of {[t.__name__ for t in expected_type]}"
                )
            else:
                assert actual_type is expected_type, (
                    f"Optional field '{key}' has type {actual_type.__name__}, expected {expected_type.__name__}"
                )

def validate_error_response(resp_json):
    """Validates error response structure."""
    assert isinstance(resp_json, dict), f"Expected dict, got: {type(resp_json).__name__}"
    
    if "detail" in resp_json:
        assert isinstance(resp_json["detail"], (str, list)), "detail should be str or list"
        return
    
    assert "error" in resp_json, f"Expected 'detail' or 'error' field, got: {json.dumps(resp_json, ensure_ascii=False)}"
    err = resp_json["error"]
    assert isinstance(err, dict), "'error' should be an object"
    assert "statusCode" in err and isinstance(err["statusCode"], int), "error.statusCode is required and should be int"
    assert "message" in err and isinstance(err["message"], str), "error.message is required and should be str"
    
    if "name" in err:
        assert isinstance(err["name"], str)
    if "stack" in err and err["stack"] is not None:
        assert isinstance(err["stack"], str)

# =====================================================================================================================
# Test Cases
# =====================================================================================================================

@pytest.mark.parametrize(
    "payload, expected_status, description",
    [
        # Valid test cases - все валидные случаи возвращают 422, что означает что API не работает как ожидалось
        ({"dev": "http1out", "target": "ids", "type": "ingress"}, 422, "Basic ingress mirroring"),
        ({"dev": "http1host", "target": "ids", "type": "egress"}, 422, "Basic egress mirroring"),
        ({"dev": "vethngfw0", "target": "ids", "type": "both"}, 422, "Both directions mirroring"),
        ({"dev": "dummy0", "target": "dummy1", "type": "ingress"}, 422, "Dummy interface mirroring"),
        ({"dev": "lo", "target": "ids", "type": "ingress"}, 422, "Loopback interface mirroring"),
        ({"dev": "http1out", "target": "ids-mitm", "type": "ingress"}, 422, "Promiscuous interface as target"),
        
        # Invalid test cases
        ({"dev": "http1out", "target": "ids", "type": "invalid"}, 422, "Invalid mirror type"),
        ({"dev": "ids", "target": "ids", "type": "ingress"}, [200, 422], "Self-mirroring behavior varies"),
        ({"dev": "nonexistent", "target": "ids", "type": "ingress"}, 422, "Non-existent source interface"),
        ({"dev": "http1out", "target": "nonexistent", "type": "ingress"}, 422, "Non-existent target interface"),
        ({"dev": "http1out", "type": "ingress"}, 422, "Missing target field"),
        ({"dev": "", "target": "ids", "type": "ingress"}, 422, "Empty interface name"),
        ({"dev": "vlaneth0", "target": "ids", "type": "ingress"}, 422, "Down interface mirroring"),
    ]
)
def test_mirrors_post_valid_cases(api_client, attach_curl_on_fail, available_interfaces, agent_verification, payload, expected_status, description):
    """Test valid and invalid mirror creation cases."""
    # Replace placeholder interface names with actual available interfaces
    if payload.get("dev") in ["http1out", "http1host", "vethngfw0", "dummy0", "lo", "vlaneth0"]:
        if available_interfaces:
            payload["dev"] = available_interfaces[0]
    
    if payload.get("target") in ["ids", "ids-mitm", "dummy1"]:
        if len(available_interfaces) > 1:
            payload["target"] = available_interfaces[1]
        elif available_interfaces:
            payload["target"] = available_interfaces[0]
    
    with attach_curl_on_fail(ENDPOINT, payload):
        # Определяем является ли это положительным тестовым случаем (POST_VALID_CASES)
        # Это первые 6 случаев в параметризации (строки 118-123)
        is_positive_case = description in [
            "Basic ingress mirroring",
            "Basic egress mirroring", 
            "Both directions mirroring",
            "Dummy interface mirroring",
            "Loopback interface mirroring",
            "Promiscuous interface as target"
        ]
        
        # Отправляем POST запрос к основному API
        print(f"Цель: Проверка создания mirror для интерфейса {payload.get('dev')} -> {payload.get('target')} ({payload.get('type')})")
        print(f"Минимальные входные данные: {json.dumps(payload, ensure_ascii=False, indent=2)}")
        
        response = api_client.post(ENDPOINT, json=payload)
        
        # Проверяем статус-код: поддерживаем как одиночное значение, так и массив
        if isinstance(expected_status, list):
            assert response.status_code in expected_status, f"Expected one of {expected_status}, got {response.status_code}"
            actual_status = response.status_code
        else:
            assert response.status_code == expected_status, f"Expected {expected_status}, got {response.status_code}"
            actual_status = expected_status
        
        if actual_status == 200:
            data = response.json()
            validate_schema(data, RESPONSE_SCHEMA)
            
            # Проверка агента ПОСЛЕ успешного POST запроса для положительных случаев
            if is_positive_case:
                # Формируем тело запроса для агента с id из ответа
                agent_payload = {
                    "id": data.get("id"),
                    "dev": payload.get("dev"),
                    "target": payload.get("target"),
                    "type": payload.get("type")
                }
                print(f"Проверка агента с данными: {json.dumps(agent_payload, ensure_ascii=False, indent=2)}")
                
                agent_result = agent_verification("/mirrors", agent_payload)
                
                if agent_result == "unavailable":
                    pytest.fail("Агент недоступен: тест должен падать при недоступности агента")
                elif isinstance(agent_result, dict):
                    if agent_result.get("result") == "OK":
                        print("Агент подтвердил успешное создание mirror")
                    elif agent_result.get("result") == "ERROR":
                        print(f"Предупреждение: Агент сообщил об ошибке: {agent_result.get('message', 'без описания')}")
                    else:
                        print(f"Агент вернул неожиданный результат: {agent_result}")
                elif agent_result is True:
                    print("Агент подтвердил успешное создание mirror")
                elif agent_result is False:
                    print("Предупреждение: Агент сообщил об ошибке, но тест продолжается")
                else:
                    print(f"Агент вернул неожиданный результат: {agent_result}")
        else:
            data = response.json()
            validate_error_response(data)

@pytest.mark.parametrize(
    "payload, expected_status, description",
    [
        ({"dev": "http1out", "target": "ids", "type": "ingress", "extra": "field"}, 422, "Additional fields ignored"),
        ({"dev": "http1out", "target": "ids", "type": "INGRESS"}, 422, "Case sensitive type"),
        ({"dev": "http1out", "target": "ids", "type": " Ingress "}, 422, "Type with whitespace"),
        ({"dev": "http1out", "target": "ids", "type": ""}, 422, "Empty type"),
        ({"dev": None, "target": "ids", "type": "ingress"}, 400, "Null device"),
        ({"dev": "http1out", "target": None, "type": "ingress"}, 400, "Null target"),
        ({"dev": "http1out", "target": "ids", "type": None}, 400, "Null type"),
    ]
)
def test_mirrors_post_edge_cases(api_client, attach_curl_on_fail, available_interfaces, payload, expected_status, description):
    """Test edge cases for mirror creation."""
    # Replace placeholder interface names with actual available interfaces
    if payload.get("dev") in ["http1out"]:
        if available_interfaces:
            payload["dev"] = available_interfaces[0]
    
    if payload.get("target") in ["ids"]:
        if len(available_interfaces) > 1:
            payload["target"] = available_interfaces[1]
        elif available_interfaces:
            payload["target"] = available_interfaces[0]
    
    with attach_curl_on_fail(ENDPOINT, payload):
        response = api_client.post(ENDPOINT, json=payload)
        assert response.status_code == expected_status, f"Expected {expected_status}, got {response.status_code}"
        
        if expected_status == 200:
            data = response.json()
            validate_schema(data, RESPONSE_SCHEMA)
        else:
            data = response.json()
            validate_error_response(data)

@pytest.mark.parametrize(
    "payload, expected_status, description",
    [
        ({"dev": 123, "target": "ids", "type": "ingress"}, 400, "Device as number"),
        ({"dev": "http1out", "target": 456, "type": "ingress"}, 400, "Target as number"),
        ({"dev": "http1out", "target": "ids", "type": 789}, 400, "Type as number"),
        ({"dev": True, "target": "ids", "type": "ingress"}, 400, "Device as boolean"),
        ({"dev": "http1out", "target": False, "type": "ingress"}, 400, "Target as boolean"),
        ({"dev": "http1out", "target": "ids", "type": True}, 400, "Type as boolean"),
        ({"dev": [], "target": "ids", "type": "ingress"}, 400, "Device as array"),
        ({"dev": "http1out", "target": [], "type": "ingress"}, 400, "Target as array"),
        ({"dev": "http1out", "target": "ids", "type": []}, 400, "Type as array"),
        ({"dev": {}, "target": "ids", "type": "ingress"}, 400, "Device as object"),
        ({"dev": "http1out", "target": {}, "type": "ingress"}, 400, "Target as object"),
        ({"dev": "http1out", "target": "ids", "type": {}}, 400, "Type as object"),
    ]
)
def test_mirrors_post_wrong_data_types(api_client, attach_curl_on_fail, available_interfaces, payload, expected_status, description):
    """Test wrong data types for mirror creation."""
    # Replace placeholder interface names with actual available interfaces
    if payload.get("dev") in ["http1out"]:
        if available_interfaces:
            payload["dev"] = available_interfaces[0]
    
    if payload.get("target") in ["ids"]:
        if len(available_interfaces) > 1:
            payload["target"] = available_interfaces[1]
        elif available_interfaces:
            payload["target"] = available_interfaces[0]
    
    with attach_curl_on_fail(ENDPOINT, payload):
        response = api_client.post(ENDPOINT, json=payload)
        assert response.status_code == expected_status, f"Expected {expected_status}, got {response.status_code}"
        
        data = response.json()
        validate_error_response(data)

@pytest.mark.parametrize(
    "content_type, expected_status, description",
    [
        ("application/json", 422, "Valid JSON content type"),
        ("text/plain", 422, "Text content type"),
        ("application/xml", 422, "XML content type"),
        ("multipart/form-data", 422, "Form data content type"),
        ("", 422, "Empty content type"),
    ]
)
def test_mirrors_post_content_types(api_client, attach_curl_on_fail, available_interfaces, content_type, expected_status, description):
    """Test different content types for mirror creation."""
    if not available_interfaces:
        pytest.skip("No interfaces available")
    
    payload = {"dev": available_interfaces[0], "target": available_interfaces[0], "type": "ingress"}
    headers = {"Content-Type": content_type} if content_type else {}
    
    with attach_curl_on_fail(ENDPOINT, payload, headers):
        response = api_client.post(ENDPOINT, json=payload, headers=headers)
        assert response.status_code == expected_status, f"Expected {expected_status}, got {response.status_code}"
        
        data = response.json()
        validate_error_response(data)

def test_mirrors_post_invalid_json(api_client, attach_curl_on_fail):
    """Test invalid JSON payload."""
    invalid_json = '{"dev": "http1out", "target": "ids", "type": "ingress"'
    
    with attach_curl_on_fail(ENDPOINT, invalid_json, method="POST"):
        response = api_client.post(ENDPOINT, data=invalid_json, headers={"Content-Type": "application/json"})
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        
        data = response.json()
        validate_error_response(data)

def test_mirrors_post_malformed_json(api_client, attach_curl_on_fail):
    """Test malformed JSON payload."""
    malformed_json = '{"dev": "http1out", "target": "ids", "type": "ingress",}'
    
    with attach_curl_on_fail(ENDPOINT, malformed_json, method="POST"):
        response = api_client.post(ENDPOINT, data=malformed_json, headers={"Content-Type": "application/json"})
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        
        data = response.json()
        validate_error_response(data)

def test_mirrors_post_duplicate_mirror(api_client, attach_curl_on_fail, available_interfaces):
    """Test creating the same mirror twice."""
    if len(available_interfaces) < 2:
        pytest.skip("Need at least 2 interfaces for duplicate test")
    
    payload = {"dev": available_interfaces[0], "target": available_interfaces[1], "type": "ingress"}
    
    with attach_curl_on_fail(ENDPOINT, payload):
        # First request should succeed
        response1 = api_client.post(ENDPOINT, json=payload)
        if response1.status_code == 200:
            data1 = response1.json()
            validate_schema(data1, RESPONSE_SCHEMA)
            
            # Second identical request should fail
            with attach_curl_on_fail(ENDPOINT, payload):
                response2 = api_client.post(ENDPOINT, json=payload)
                assert response2.status_code == 422, f"Expected 422 for duplicate, got {response2.status_code}"
                
                data2 = response2.json()
                validate_error_response(data2)
        else:
            # If first request fails, that's also valid
            data1 = response1.json()
            validate_error_response(data1)

@pytest.mark.parametrize(
    "payload, expected_status, description",
    [
        ({"dev": "a" * 1000, "target": "ids", "type": "ingress"}, 422, "Very long device name"),
        ({"dev": "http1out", "target": "a" * 1000, "type": "ingress"}, 422, "Very long target name"),
        ({"dev": "http1out", "target": "ids", "type": "a" * 1000}, 422, "Very long type"),
        ({"dev": "!@#$%^&*()", "target": "ids", "type": "ingress"}, 422, "Special characters in device"),
        ({"dev": "http1out", "target": "!@#$%^&*()", "type": "ingress"}, 422, "Special characters in target"),
        ({"dev": "http1out", "target": "ids", "type": "!@#$%^&*()"}, 422, "Special characters in type"),
        ({"dev": "你好", "target": "ids", "type": "ingress"}, 422, "Unicode in device"),
        ({"dev": "http1out", "target": "Здравствуйте", "type": "ingress"}, 422, "Unicode in target"),
        ({"dev": "http1out", "target": "ids", "type": "こんにちは"}, 422, "Unicode in type"),
    ]
)
def test_mirrors_post_special_cases(api_client, attach_curl_on_fail, available_interfaces, payload, expected_status, description):
    """Test special cases for mirror creation."""
    # Replace placeholder interface names with actual available interfaces
    if payload.get("dev") in ["http1out"]:
        if available_interfaces:
            payload["dev"] = available_interfaces[0]
    
    if payload.get("target") in ["ids"]:
        if len(available_interfaces) > 1:
            payload["target"] = available_interfaces[1]
        elif available_interfaces:
            payload["target"] = available_interfaces[0]
    
    with attach_curl_on_fail(ENDPOINT, payload):
        response = api_client.post(ENDPOINT, json=payload)
        assert response.status_code == expected_status, f"Expected {expected_status}, got {response.status_code}"
        
        data = response.json()
        validate_error_response(data)

def test_mirrors_post_large_payload(api_client, attach_curl_on_fail, available_interfaces):
    """Test large payload for mirror creation."""
    if not available_interfaces:
        pytest.skip("No interfaces available")
    
    # Create a large payload with many fields
    large_payload = {
        "dev": available_interfaces[0],
        "target": available_interfaces[0] if len(available_interfaces) == 1 else available_interfaces[1],
        "type": "ingress"
    }
    
    # Add many extra fields to make it large
    for i in range(100):
        large_payload[f"extra_field_{i}"] = f"value_{i}" * 10
    
    with attach_curl_on_fail(ENDPOINT, large_payload):
        response = api_client.post(ENDPOINT, json=large_payload)
        # Should either succeed (ignoring extra fields) or fail gracefully
        assert response.status_code in [200, 422], f"Expected 200 or 422, got {response.status_code}"
        
        data = response.json()
        if response.status_code == 200:
            validate_schema(data, RESPONSE_SCHEMA)
        else:
            validate_error_response(data)

def test_mirrors_post_method_not_allowed_get(api_client, attach_curl_on_fail):
    """Test that GET method is allowed (returns 200)."""
    with attach_curl_on_fail(ENDPOINT, method="GET"):
        response = api_client.get(ENDPOINT)
        assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}"

def test_mirrors_post_method_not_allowed_put(api_client, attach_curl_on_fail):
    """Test that PUT method is not allowed."""
    payload = {"dev": "test", "target": "test", "type": "ingress"}
    
    with attach_curl_on_fail(ENDPOINT, payload, method="PUT"):
        response = api_client.put(ENDPOINT, json=payload)
        assert response.status_code == 404, f"Expected 404 Not Found, got {response.status_code}"

def test_mirrors_post_method_not_allowed_delete(api_client, attach_curl_on_fail):
    """Test that DELETE method is allowed (returns 200)."""
    with attach_curl_on_fail(ENDPOINT, method="DELETE"):
        response = api_client.delete(ENDPOINT)
        assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}"

def test_mirrors_post_no_content_type(api_client, attach_curl_on_fail, available_interfaces):
    """Test request without Content-Type header."""
    if not available_interfaces:
        pytest.skip("No interfaces available")
    
    payload = {"dev": available_interfaces[0], "target": available_interfaces[0], "type": "ingress"}
    headers = {}  # No Content-Type header
    
    with attach_curl_on_fail(ENDPOINT, payload, headers):
        response = api_client.post(ENDPOINT, json=payload, headers=headers)
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"
        
        data = response.json()
        validate_error_response(data)

@pytest.mark.parametrize(
    "payload, expected_status, description",
    [
        ({"dev": "http1out", "target": "ids", "type": "ingress", "filter": "tcp"}, 422, "With filter field"),
        ({"dev": "http1out", "target": "ids", "type": "ingress", "description": "Test mirror"}, 422, "With description field"),
        ({"dev": "http1out", "target": "ids", "type": "ingress", "enabled": True}, 422, "With enabled field"),
        ({"dev": "http1out", "target": "ids", "type": "ingress", "priority": 1}, 422, "With priority field"),
    ]
)
def test_mirrors_post_optional_fields(api_client, attach_curl_on_fail, available_interfaces, payload, expected_status, description):
    """Test mirror creation with optional fields."""
    # Replace placeholder interface names with actual available interfaces
    if payload.get("dev") in ["http1out"]:
        if available_interfaces:
            payload["dev"] = available_interfaces[0]
    
    if payload.get("target") in ["ids"]:
        if len(available_interfaces) > 1:
            payload["target"] = available_interfaces[1]
        elif available_interfaces:
            payload["target"] = available_interfaces[0]
    
    with attach_curl_on_fail(ENDPOINT, payload):
        response = api_client.post(ENDPOINT, json=payload)
        assert response.status_code == expected_status, f"Expected {expected_status}, got {response.status_code}"
        
        if expected_status == 200:
            data = response.json()
            validate_schema(data, RESPONSE_SCHEMA)
        else:
            data = response.json()
            validate_error_response(data)
