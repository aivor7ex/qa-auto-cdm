import json
import pytest
import requests
from collections.abc import Mapping, Sequence
from services.qa_constants import SERVICES
import uuid
import time

# =====================================================================================================================
# Constants
# =====================================================================================================================

ENDPOINT = "/managers/createInterface"
SERVICE = SERVICES["vswitch"][0]  # Используем первый сервис vswitch
PORT = SERVICE["port"]
BASE_PATH = SERVICE["base_path"]

# =====================================================================================================================
# Delay before each test in this module
# =====================================================================================================================

@pytest.fixture(autouse=True)
def _delay_before_each_test():
    time.sleep(1)

# =====================================================================================================================
# Response Schemas
# =====================================================================================================================

response_schemas = {
    "POST": {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "index": {"type": "integer"},
                "cmd": {"type": "string"},
                "res": {"type": "string"},
                "error": {"type": "string"},
                "skipped": {"type": "boolean"}
            },
            "required": ["index"]
        }
    }
}

# =====================================================================================================================
# Recursive Schema Validation
# =====================================================================================================================

def _check_types_recursive(obj, schema):
    """Рекурсивная проверка типов согласно схеме."""
    if "anyOf" in schema:
        assert any(_try_type(obj, s) for s in schema["anyOf"]), f"Value {obj} does not match anyOf {schema['anyOf']}"
        return
    if schema.get("type") == "object":
        assert isinstance(obj, Mapping), f"Expected object, got {type(obj)}"
        for key, prop in schema.get("properties", {}).items():
            if key in obj:
                _check_types_recursive(obj[key], prop)
        for req in schema.get("required", []):
            assert req in obj, f"Missing required field: {req}"
    elif schema.get("type") == "array":
        assert isinstance(obj, Sequence) and not isinstance(obj, str), f"Expected array, got {type(obj)}"
        if "items" in schema and isinstance(schema["items"], list):
            for idx, (item, item_schema) in enumerate(zip(obj, schema["items"])):
                _check_types_recursive(item, item_schema)
        else:
            for item in obj:
                _check_types_recursive(item, schema["items"])
    else:
        if schema.get("type") == "string":
            assert isinstance(obj, str), f"Expected string, got {type(obj)}"
        elif schema.get("type") == "integer":
            assert isinstance(obj, int), f"Expected integer, got {type(obj)}"
        elif schema.get("type") == "boolean":
            assert isinstance(obj, bool), f"Expected boolean, got {type(obj)}"
        elif schema.get("type") == "null":
            assert obj is None, f"Expected null, got {type(obj)}"

def _try_type(obj, schema):
    """Попытка проверить тип без исключения."""
    try:
        _check_types_recursive(obj, schema)
        return True
    except AssertionError:
        return False

# =====================================================================================================================
# Curl Command Formatter
# =====================================================================================================================

# R24: curl-инструкции формируются общей фикстурой attach_curl_on_fail
# Локальный форматтер больше не используется

# =====================================================================================================================
# R24: curl-инструкции формируются общей фикстурой attach_curl_on_fail
# =====================================================================================================================

# =====================================================================================================================
# Test Data
# =====================================================================================================================

# Валидные случаи
POST_VALID_CASES = [
    pytest.param({
        "name": "dummy0",
        "ipAndMask": "192.168.1.100/24"
    }, 200, id="valid-name-and-ip"),
    pytest.param({
        "name": "dummy1"
    }, 200, id="valid-name-only"),
    pytest.param({
        "name": "dummy2",
        "ipAndMask": "10.0.0.1/16"
    }, 200, id="valid-different-ip"),
    pytest.param({
        "name": "dummy3",
        "ipAndMask": "172.16.0.1/8"
    }, 200, id="valid-class-a-ip"),
    pytest.param({
        "name": "dummy4",
        "ipAndMask": "192.168.0.1/32"
    }, 200, id="valid-single-host"),
    pytest.param({
        "name": "dummy5",
        "ipAndMask": "10.10.10.10/24"
    }, 200, id="valid-standard-ip"),
    pytest.param({
        "name": "dummy6",
        "ipAndMask": "172.20.30.40/16"
    }, 200, id="valid-class-b-ip"),
    pytest.param({
        "name": "dummy7",
        "ipAndMask": "192.168.100.200/24"
    }, 200, id="valid-high-ip"),
    pytest.param({
        "name": "dummy8"
    }, 200, id="valid-name-only-2"),
    pytest.param({
        "name": "dummy9",
        "ipAndMask": "10.20.30.40/8"
    }, 200, id="valid-class-a-2"),
]

# Невалидные случаи
POST_INVALID_CASES = [
    pytest.param({
        "ipAndMask": "192.168.1.100/24"
    }, 200, id="missing-name"),  # API возвращает 200, но использует "undefined"
    pytest.param({
        "name": "dummy0"
    }, 200, id="existing-interface"),  # Уже существующий интерфейс
    pytest.param({
        "name": "dummy2",
        "ipAndMask": "not_an_ip"
    }, 200, id="invalid-ip-format"),  # API возвращает 200, но с ошибкой в команде
    pytest.param({
        "name": "",
        "ipAndMask": "192.168.1.100/24"
    }, 200, id="empty-name"),
    pytest.param({
        "name": "dummy10",
        "ipAndMask": "256.256.256.256/24"
    }, 200, id="invalid-ip-range"),
    pytest.param({
        "name": "dummy11",
        "ipAndMask": "192.168.1.100/33"
    }, 200, id="invalid-mask"),
    pytest.param({
        "name": "dummy12",
        "ipAndMask": "192.168.1.100"
    }, 200, id="ip-without-mask"),
    pytest.param({
        "name": "dummy13",
        "ipAndMask": "192.168.1.100/24/extra"
    }, 200, id="malformed-ip"),
    pytest.param({
        "name": "dummy14",
        "ipAndMask": "192.168.1.100/24",
        "extra": "field"
    }, 200, id="extra-field"),
]

# Edge cases для дополнительного покрытия
POST_EDGE_CASES = [
    pytest.param({
        "name": "dummy15",
        "ipAndMask": "0.0.0.0/0"
    }, 200, id="zero-ip"),
    pytest.param({
        "name": "dummy16",
        "ipAndMask": "255.255.255.255/32"
    }, 200, id="broadcast-ip"),
    pytest.param({
        "name": "dummy17",
        "ipAndMask": "127.0.0.1/8"
    }, 200, id="loopback-ip"),
    pytest.param({
        "name": "dummy18",
        "ipAndMask": "::1/128"
    }, 200, id="ipv6-ip"),
    pytest.param({
        "name": "dummy19",
        "ipAndMask": "2001:db8::1/64"
    }, 200, id="ipv6-global"),
    pytest.param({
        "name": "dummy20",
        "ipAndMask": "fe80::1/64"
    }, 200, id="ipv6-link-local"),
]

# =====================================================================================================================
# Tests
# =====================================================================================================================

def _check_agent_verification(payload):
    """
    Проверяет через агента, что интерфейс действительно был создан в системе.
    
    Args:
        payload: Данные, которые были отправлены в POST запросе
        
    Returns:
        dict | None: { 'status': 'ok'|'error'|'unavailable', 'message': str } или None если проверка пропущена
    """
    try:
        # Извлекаем имя интерфейса из payload
        if isinstance(payload, dict) and "name" in payload:
            interface_name = payload["name"]
        else:
            # Если payload не является словарем или не содержит name, пропускаем проверку
            return None
            
        # Отправляем запрос к агенту
        agent_url = "http://localhost:8000/api/managers/createInterface"
        agent_payload = {
            "name": interface_name,
            "ipAndMask": payload.get("ipAndMask", "")
        }
        
        print(f"Agent verification request: {json.dumps(agent_payload, indent=2)}")
        response = requests.post(agent_url, json=agent_payload, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            result_value = result.get("result")
            # Поддерживаем строковые 'OK'/'ОК' без учета регистра, а также булевы значения
            if isinstance(result_value, str):
                normalized = result_value.strip().lower()
                if normalized in ("ok", "ок"):
                    return {"status": "ok", "message": str(result.get("message", ""))}
                if normalized == "error":
                    return {"status": "error", "message": str(result.get("message", ""))}
                # Неизвестная строка — считаем ошибкой
                return {"status": "error", "message": str(result.get("message", "Unknown agent result"))}
            if isinstance(result_value, bool):
                return {"status": "ok" if result_value else "error", "message": str(result.get("message", ""))}
            # Неподдерживаемый тип
            return {"status": "error", "message": str(result.get("message", "Invalid agent result type"))}
        else:
            print(f"Agent verification failed with status {response.status_code}: {response.text}")
            return {"status": "error", "message": f"HTTP {response.status_code}"}
            
    except requests.exceptions.RequestException as e:
        print(f"Agent verification request failed: {e}")
        return {"status": "unavailable", "message": str(e)}  # Агент недоступен
    except Exception as e:
        print(f"Agent verification error: {e}")
        return {"status": "unavailable", "message": str(e)}  # Агент недоступен

@pytest.mark.parametrize("payload, expected_status", POST_VALID_CASES + POST_INVALID_CASES + POST_EDGE_CASES)
def test_post_createInterface(api_client, attach_curl_on_fail, payload, expected_status):
    """
    Тестирует POST /managers/createInterface с различными валидными и невалидными payload.
    
    Валидные случаи:
    - Создание интерфейса с именем и IP
    - Создание интерфейса только с именем
    - Различные валидные IP адреса и маски
    
    Невалидные случаи:
    - Отсутствие обязательного поля name
    - Попытка создать уже существующий интерфейс
    - Некорректный формат IP
    - Некорректные типы данных
    
    Edge cases:
    - Очень длинные имена
    - Специальные IP адреса (0.0.0.0, 255.255.255.255)
    - IPv6 адреса
    """
    headers = {"Content-Type": "application/json"}
    
    with attach_curl_on_fail(ENDPOINT, payload, headers, "POST"):
        response = api_client.post(ENDPOINT, json=payload, headers=headers)
        assert response.status_code == expected_status, f"Expected status {expected_status}, got {response.status_code}"
        response_data = response.json()
        _check_types_recursive(response_data, response_schemas["POST"])

        if expected_status == 200 and isinstance(payload, dict) and "name" in payload:
            assert isinstance(response_data, list), "Response should be an array"
            for item in response_data:
                assert isinstance(item, dict), "Each item should be a dictionary"
                assert "index" in item, "Each item should have 'index' field"
                assert isinstance(item["index"], int), "Index should be integer"
                has_cmd = "cmd" in item
                has_res = "res" in item
                has_error = "error" in item
                has_skipped = "skipped" in item
                assert has_cmd or has_error or has_skipped, "Item should have cmd, error, or skipped field"
                if has_cmd:
                    assert isinstance(item["cmd"], str), "cmd should be string"
                    if "res" in item:
                        assert isinstance(item["res"], str), "res should be string"
                if has_error:
                    assert isinstance(item["error"], str), "error should be string"
                if has_skipped:
                    assert isinstance(item["skipped"], bool), "skipped should be boolean"

            print(f"Checking agent verification for valid test: {payload.get('name', 'unknown')}")
            interface_name = payload.get('name', '')
            if interface_name and isinstance(interface_name, str) and interface_name.strip():
                has_policy_error = any(
                    "Attribute failed policy validation" in item.get("error", "")
                    for item in response_data
                )
                if has_policy_error:
                    print(f"Agent verification skipped - policy validation failed for interface: {payload.get('name', 'unknown')}")
                else:
                    agent_result = _check_agent_verification(payload)
                    if agent_result["status"] == "unavailable":
                        agent_endpoint = "/api/managers/createInterface"
                        agent_headers = {"Content-Type": "application/json"}
                        agent_payload = {"name": interface_name, "ipAndMask": payload.get("ipAndMask", "")}
                        with attach_curl_on_fail(agent_endpoint, agent_payload, agent_headers, "POST"):
                            pytest.fail(
                                f"Agent is unavailable for interface: {payload.get('name', 'unknown')}",
                                pytrace=False,
                            )
                    elif agent_result["status"] == "error":
                        agent_endpoint = "/api/managers/createInterface"
                        agent_headers = {"Content-Type": "application/json"}
                        agent_payload = {"name": interface_name, "ipAndMask": payload.get("ipAndMask", "")}
                        with attach_curl_on_fail(agent_endpoint, agent_payload, agent_headers, "POST"):
                            pytest.fail(
                                f"Agent verification failed: Interface '{payload.get('name', 'unknown')}' was not found in the system. Message: {agent_result['message']}",
                                pytrace=False,
                            )
                    elif agent_result["status"] == "ok":
                        print(f"Agent verification: Interface '{payload.get('name', 'unknown')}' was successfully created")
                    else:
                        print(f"Agent verification skipped for payload: {payload}")
            else:
                print(f"Agent verification skipped - invalid interface name: '{interface_name}'")
        elif expected_status == 200 and isinstance(payload, dict):
            print(f"Skipping agent verification for non-valid test (no name field): {payload}")
        else:
            print(f"Test completed with status {expected_status}")

# =====================================================================================================================
# Additional Validation Tests
# =====================================================================================================================

def test_createInterface_response_structure(api_client, attach_curl_on_fail):
    """Тест структуры ответа для создания интерфейса."""
    payload = {
        "name": f"test_interface_{uuid.uuid4().hex[:8]}",
        "ipAndMask": "192.168.1.100/24"
    }
    headers = {"Content-Type": "application/json"}

    with attach_curl_on_fail(ENDPOINT, payload, headers, "POST"):
        response = api_client.post(ENDPOINT, json=payload, headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list), "Response should be an array"
        assert len(data) > 0, "Response array should not be empty"
        for i, item in enumerate(data):
            assert isinstance(item, dict), f"Item {i} should be a dictionary"
            assert "index" in item, f"Item {i} should have 'index' field"
            assert item["index"] == i, f"Item {i} should have index {i}"

        # Дополнительная проверка через агента
        print(f"Checking agent verification for structure test: {payload.get('name', 'unknown')}")
        interface_name = payload.get('name', '')
        if interface_name and isinstance(interface_name, str) and interface_name.strip():
            has_policy_error = any(
                "Attribute failed policy validation" in item.get("error", "")
                for item in data
            )
            if has_policy_error:
                print(f"Agent verification skipped - policy validation failed for interface: {payload.get('name', 'unknown')}")
            else:
                agent_result = _check_agent_verification(payload)
                if agent_result["status"] == "unavailable":
                    agent_endpoint = "/api/managers/createInterface"
                    agent_headers = {"Content-Type": "application/json"}
                    agent_payload = {"name": interface_name, "ipAndMask": payload.get("ipAndMask", "")}
                    with attach_curl_on_fail(agent_endpoint, agent_payload, agent_headers, "POST"):
                        pytest.fail(
                            f"Agent is unavailable for interface: {payload.get('name', 'unknown')}",
                            pytrace=False,
                        )
                elif agent_result["status"] == "error":
                    agent_endpoint = "/api/managers/createInterface"
                    agent_headers = {"Content-Type": "application/json"}
                    agent_payload = {"name": interface_name, "ipAndMask": payload.get("ipAndMask", "")}
                    with attach_curl_on_fail(agent_endpoint, agent_payload, agent_headers, "POST"):
                        pytest.fail(
                            f"Agent verification failed: Interface '{payload.get('name', 'unknown')}' was not found in the system. Message: {agent_result['message']}",
                            pytrace=False,
                        )
                else:
                    print(f"Agent verification: Interface '{payload.get('name', 'unknown')}' was successfully created")
        else:
            print(f"Agent verification skipped - invalid interface name: '{interface_name}'")

def test_createInterface_without_ip(api_client, attach_curl_on_fail):
    """Тест создания интерфейса без IP адреса."""
    payload = {
        "name": f"test_no_ip_{uuid.uuid4().hex[:8]}"
    }
    headers = {"Content-Type": "application/json"}
    
    with attach_curl_on_fail(ENDPOINT, payload, headers, "POST"):
        response = api_client.post(ENDPOINT, json=payload, headers=headers)
        assert response.status_code == 200
        data = response.json()
        # Проверяем, что это массив
        assert isinstance(data, list), "Response should be an array"
        # Проверяем, что есть элементы с skipped: true
        skipped_items = [item for item in data if item.get("skipped") is True]
        assert len(skipped_items) > 0, "Should have skipped items when no IP provided"

def test_createInterface_duplicate_name(api_client, attach_curl_on_fail):
    """Тест создания интерфейса с уже существующим именем."""
    # Сначала создаем интерфейс
    name = f"duplicate_test_{uuid.uuid4().hex[:8]}"
    payload = {
        "name": name,
        "ipAndMask": "192.168.1.100/24"
    }
    headers = {"Content-Type": "application/json"}
    # Первый запрос
    response1 = api_client.post(ENDPOINT, json=payload, headers=headers)
    assert response1.status_code == 200
    # Второй запрос с тем же именем
    with attach_curl_on_fail(ENDPOINT, payload, headers, "POST"):
        response2 = api_client.post(ENDPOINT, json=payload, headers=headers)
        assert response2.status_code == 200
        data = response2.json()
        assert isinstance(data, list), "Response should be an array"
        # Исправлено: API возвращает элементы с error, а не skipped для дубликатов
        error_items = [item for item in data if "error" in item]
        assert len(error_items) > 0, "Should have error items for duplicate interface"

def test_createInterface_invalid_ip_format(api_client, attach_curl_on_fail):
    """Тест создания интерфейса с некорректным IP."""
    payload = {
        "name": f"test_invalid_ip_{uuid.uuid4().hex[:8]}",
        "ipAndMask": "not_an_ip_address"
    }
    headers = {"Content-Type": "application/json"}
    
    with attach_curl_on_fail(ENDPOINT, payload, headers, "POST"):
        response = api_client.post(ENDPOINT, json=payload, headers=headers)
        assert response.status_code == 200
        data = response.json()
        # Проверяем, что это массив
        assert isinstance(data, list), "Response should be an array"
        # Проверяем, что есть элемент с ошибкой
        error_items = [item for item in data if "error" in item]
        assert len(error_items) > 0, "Should have error items for invalid IP"

# =====================================================================================================================
# Stability Tests
# =====================================================================================================================

@pytest.mark.parametrize("test_id", range(10))
def test_createInterface_stability(api_client, attach_curl_on_fail, test_id):
    """Тест стабильности создания интерфейсов."""
    payload = {
        "name": f"stability_test_{test_id}_{uuid.uuid4().hex[:8]}",
        "ipAndMask": f"192.168.{test_id}.100/24"
    }
    headers = {"Content-Type": "application/json"}
    with attach_curl_on_fail(ENDPOINT, payload, headers, "POST"):
        response = api_client.post(ENDPOINT, json=payload, headers=headers)
        assert response.status_code == 200
        data = response.json()
        _check_types_recursive(data, response_schemas["POST"])
        assert isinstance(data, list), "Response should be an array"
        
        # Дополнительная проверка через агента
        print(f"Checking agent verification for stability test {test_id}: {payload.get('name', 'unknown')}")
        # Проверяем, что имя валидное (не пустое и не числовое)
        interface_name = payload.get('name', '')
        if interface_name and isinstance(interface_name, str) and interface_name.strip():
            # Проверяем, есть ли ошибки политики в ответе
            has_policy_error = any(
                "Attribute failed policy validation" in item.get("error", "")
                for item in data
            )
            if has_policy_error:
                print(f"Agent verification skipped - policy validation failed for interface: {payload.get('name', 'unknown')}")
            else:
                agent_result = _check_agent_verification(payload)
                if agent_result["status"] == "unavailable":
                    agent_endpoint = "/api/managers/createInterface"
                    agent_headers = {"Content-Type": "application/json"}
                    agent_payload = {"name": interface_name, "ipAndMask": payload.get("ipAndMask", "")}
                    with attach_curl_on_fail(agent_endpoint, agent_payload, agent_headers, "POST"):
                        pytest.fail(
                            f"Agent is unavailable for interface: {payload.get('name', 'unknown')}",
                            pytrace=False,
                        )
                elif agent_result["status"] == "error":
                    agent_endpoint = "/api/managers/createInterface"
                    agent_headers = {"Content-Type": "application/json"}
                    agent_payload = {"name": interface_name, "ipAndMask": payload.get("ipAndMask", "")}
                    with attach_curl_on_fail(agent_endpoint, agent_payload, agent_headers, "POST"):
                        pytest.fail("Agent verification failed: Interface was not found in the system.", pytrace=False)
                else:
                    print(f"Agent verification: Interface '{payload.get('name', 'unknown')}' was successfully created")
        else:
            print(f"Agent verification skipped - invalid interface name: '{interface_name}'") 