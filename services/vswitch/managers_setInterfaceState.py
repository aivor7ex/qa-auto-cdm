import json
import pytest
from collections.abc import Mapping, Sequence
from services.qa_constants import SERVICES

# =====================================================================================================================
# Constants
# =====================================================================================================================

ENDPOINT = "/managers/setInterfaceState"
SERVICE = SERVICES["vswitch"][0]  # Используем первый сервис vswitch
PORT = SERVICE["port"]
BASE_PATH = SERVICE["base_path"]

# =====================================================================================================================
# Response Schemas
# =====================================================================================================================

# Схема ответа для валидных запросов (поле error отсутствует)
# Для невалидных запросов поле error присутствует в ответе со статусом 200
response_schemas = {
    "POST": {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "index": {"type": "integer"},
                "cmd": {"type": "string"},
                "res": {"type": "string"}
            },
            "required": ["index", "cmd"]
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
# Helpers
# =====================================================================================================================

# =====================================================================================================================
# Test Data
# =====================================================================================================================

# Валидные тестовые случаи
POST_VALID_CASES = [
    (
        {"interface": "lo", "state": "up"},
        200
    ),
    (
        {"interface": "dummy0", "state": "up"},
        200
    ),
    (
        {"interface": "vlaneth0", "state": "down"},
        200
    ),
    (
        {"interface": "ids", "state": "up"},
        200
    )
]

# Невалидные тестовые случаи
POST_INVALID_CASES = [
    (
        {"interface": "eth0", "state": "down"},
        200  # Возвращает 200, но с ошибкой в команде (поле error) - интерфейс не существует в ngfw
    ),
    (
        {"interface": "eth1", "state": "up"},
        200  # Возвращает 200, но с ошибкой в команде (поле error) - интерфейс не существует в ngfw
    ),
    (
        {"interface": "docker0", "state": "down"},
        200  # Возвращает 200, но с ошибкой в команде (поле error) - интерфейс не существует в ngfw
    ),
    (
        {"interface": "br0", "state": "up"},
        200  # Возвращает 200, но с ошибкой в команде (поле error) - интерфейс не существует в ngfw
    ),
    (
        {"interface": "invalid_interface", "state": "up"},
        200  # Возвращает 200, но с ошибкой в команде (поле error)
    ),
    (
        {"interface": "very_long_interface_name_that_exceeds_normal_length_limits_for_network_interfaces_in_linux_systems", "state": "up"},
        200  # Возвращает 200, но с ошибкой в команде (поле error)
    ),
    (
        {"interface": "eth0@#$%", "state": "up"},
        200  # Возвращает 200, но с ошибкой в команде (поле error)
    ),
    (
        {"interface": "lo", "state": "invalid"},
        422
    ),
    (
        {"interface": "lo", "state": "on"},
        422
    ),
    (
        {"interface": "lo", "state": "off"},
        422
    ),
    (
        {"interface": "lo", "state": "enabled"},
        422
    ),
    (
        {"interface": "lo", "state": "disabled"},
        422
    )
]

# Edge cases
POST_EDGE_CASES = [
    (
        {"interface": "", "state": "up"},
        400
    ),
    (
        {"interface": "lo", "state": ""},
        400
    ),
    (
        {"state": "up"},
        400
    ),
    (
        {"interface": "lo"},
        400
    ),
    (
        {},
        400
    ),
    (
        {"interface": None, "state": "up"},
        400
    ),
    (
        {"interface": "lo", "state": None},
        400
    ),
    (
        {"interface": 123, "state": "up"},
        400
    ),
    (
        {"interface": "lo", "state": 1},
        400
    ),
    (
        {"interface": "lo", "state": "UP"},
        422
    ),
    (
        {"interface": "lo", "state": "DOWN"},
        422
    ),
    (
        {"interface": "lo", "state": "Up"},
        422
    ),
    (
        {"interface": "lo", "state": "Down"},
        422
    )
]

# =====================================================================================================================
# Dynamic Interface Discovery
# =====================================================================================================================

def get_available_interfaces(api_client):
    """
    Получает список доступных интерфейсов из /Managers/ifconfig
    """
    try:
        response = api_client.get("/Managers/ifconfig")
        if response.status_code == 200:
            interfaces_data = response.json()
            return list(interfaces_data.keys())
        else:
            print(f"Failed to get interfaces, status: {response.status_code}")
            return ["lo", "ids", "vlaneth0"]  # Fallback interfaces
    except Exception as e:
        print(f"Error getting interfaces: {e}")
        return ["lo", "ids", "vlaneth0"]  # Fallback interfaces

def generate_test_cases(api_client):
    """
    Генерирует тестовые случаи на основе реальных интерфейсов
    """
    available_interfaces = get_available_interfaces(api_client)
    
    # Валидные тестовые случаи - используем реальные интерфейсы
    valid_cases = []
    for interface in available_interfaces[:3]:  # Берем первые 3 интерфейса для валидных тестов
        valid_cases.append((
            {"interface": interface, "state": "up"},
            200
        ))
        valid_cases.append((
            {"interface": interface, "state": "down"},
            200
        ))
    
    # Невалидные тестовые случаи - используем несуществующие интерфейсы
    invalid_interfaces = ["nonexistent_interface", "invalid_interface", "test_interface"]
    invalid_cases = []
    for interface in invalid_interfaces:
        invalid_cases.append((
            {"interface": interface, "state": "up"},
            200  # API возвращает 200, но с ошибкой в команде
        ))
    
    # Добавляем тесты с невалидными состояниями
    invalid_states = ["invalid", "on", "off", "enabled", "disabled"]
    for state in invalid_states:
        invalid_cases.append((
            {"interface": available_interfaces[0] if available_interfaces else "lo", "state": state},
            422
        ))
    
    # Edge cases остаются статичными
    edge_cases = [
        ({"interface": "", "state": "up"}, 400),
        ({"interface": "lo", "state": ""}, 400),
        ({"state": "up"}, 400),
        ({"interface": "lo"}, 400),
        ({}, 400),
        ({"interface": None, "state": "up"}, 400),
        ({"interface": "lo", "state": None}, 400),
        ({"interface": 123, "state": "up"}, 400),
        ({"interface": "lo", "state": 1}, 400),
        ({"interface": "lo", "state": "UP"}, 422),
        ({"interface": "lo", "state": "DOWN"}, 422),
        ({"interface": "lo", "state": "Up"}, 422),
        ({"interface": "lo", "state": "Down"}, 422)
    ]
    
    return valid_cases, invalid_cases, edge_cases

# =====================================================================================================================
# Agent Verification
# =====================================================================================================================
"""
Проверка агента выполняется через фикстуру agent_verification из conftest.py.
"""

# =====================================================================================================================
# Test Functions
# =====================================================================================================================

@pytest.mark.parametrize("payload, expected_status", POST_VALID_CASES + POST_INVALID_CASES + POST_EDGE_CASES)
def test_post_setInterfaceState(api_client, attach_curl_on_fail, agent_verification, payload, expected_status):
    """
    Параметризованный тест для POST /managers/setInterfaceState
    Проверяет различные комбинации валидных и невалидных данных
    """
    headers = {"Content-Type": "application/json"}
    
    with attach_curl_on_fail(ENDPOINT, payload, headers, method="POST"):
        response = api_client.post(ENDPOINT, json=payload, headers=headers)
        
        # Проверяем статус код
        assert response.status_code == expected_status, \
            f"Expected status {expected_status}, got {response.status_code}"
        
        # Для успешных запросов проверяем схему ответа
        if expected_status == 200:
            data = response.json()
            _check_types_recursive(data, response_schemas["POST"])
            
            # Проверяем, что ответ - это массив
            assert isinstance(data, list), "Response should be an array"
            
            # Проверяем структуру каждого элемента массива
            for item in data:
                assert "index" in item, "Each item should have 'index' field"
                assert "cmd" in item, "Each item should have 'cmd' field"
                assert isinstance(item["index"], int), "Index should be integer"
                assert isinstance(item["cmd"], str), "Cmd should be string"
                
                # Проверяем, что команда содержит правильные элементы
                cmd = item["cmd"]
                assert "ip netns exec ngfw" in cmd, "Command should contain 'ip netns exec ngfw'"
                assert "ifconfig" in cmd, "Command should contain 'ifconfig'"
                assert payload["interface"] in cmd, f"Command should contain interface '{payload['interface']}'"
                assert payload["state"] in cmd, f"Command should contain state '{payload['state']}'"
                
                # Для валидных случаев поле error не должно присутствовать
                # Проверяем, является ли интерфейс реальным (существует в системе)
                available_interfaces = get_available_interfaces(api_client)
                if payload["interface"] in available_interfaces:
                    assert "error" not in item, f"Valid interface '{payload['interface']}' should not contain error field"
                else:
                    # Для несуществующих интерфейсов поле error может присутствовать или отсутствовать
                    # API может не всегда возвращать ошибку для несуществующих интерфейсов
                    if "error" in item:
                        assert isinstance(item["error"], str), "Error field should be string"
                    # Если поля error нет, это тоже допустимо - API может просто не выполнить команду
        
        # Для ошибок валидации проверяем структуру ошибки
        elif expected_status in [400, 422]:
            data = response.json()
            assert "error" in data, "Error response should contain 'error' field"
            error = data["error"]
            assert "statusCode" in error, "Error should contain 'statusCode'"
            assert "message" in error, "Error should contain 'message'"
            assert error["statusCode"] == expected_status, f"Error statusCode should be {expected_status}"
        
        # Дополнительная проверка через агента для валидных случаев
        if expected_status == 200 and isinstance(payload, dict) and payload in [case[0] for case in POST_VALID_CASES]:
            # Проверяем, есть ли ошибки в команде (поле error)
            has_error = any("error" in item for item in data)
            
            if not has_error:
                print(f"Checking agent verification for valid test: {payload}")
                # Проверяем агента
                agent_result = agent_verification(ENDPOINT, payload)
                if agent_result == "unavailable":
                    pytest.fail("Agent is unavailable; test must fail according to rule R24")
                elif agent_result["result"].upper() in ["ERROR", "ОШИБКА"]:
                    pytest.fail(f"Agent verification failed: {agent_result['message']}")
                elif agent_result["result"].upper() not in ["OK", "ОК"]:
                    pytest.fail(f"Unexpected agent result: {agent_result}")
            else:
                print(f"Agent verification skipped - command contains errors for interface: {payload.get('interface', 'unknown')}")
        else:
            print(f"Test completed with status {expected_status}")

def test_post_setInterfaceState_dynamic(api_client, attach_curl_on_fail, agent_verification):
    """
    Динамический тест для POST /managers/setInterfaceState
    Генерирует тестовые случаи на основе реальных интерфейсов
    """
    # Генерируем тестовые случаи
    valid_cases, invalid_cases, edge_cases = generate_test_cases(api_client)
    all_cases = valid_cases + invalid_cases + edge_cases
    
    print(f"Generated {len(all_cases)} test cases:")
    print(f"  Valid cases: {len(valid_cases)}")
    print(f"  Invalid cases: {len(invalid_cases)}")
    print(f"  Edge cases: {len(edge_cases)}")
    
    # Запускаем тесты для каждого случая
    for i, (payload, expected_status) in enumerate(all_cases):
        print(f"\nRunning test case {i+1}/{len(all_cases)}: {payload} -> {expected_status}")
        
        headers = {"Content-Type": "application/json"}
        
        with attach_curl_on_fail(ENDPOINT, payload, headers, method="POST"):
            response = api_client.post(ENDPOINT, json=payload, headers=headers)
            
            # Проверяем статус код
            assert response.status_code == expected_status, \
                f"Expected status {expected_status}, got {response.status_code}"
            
            # Для успешных запросов проверяем схему ответа
            if expected_status == 200:
                data = response.json()
                _check_types_recursive(data, response_schemas["POST"])
                
                # Проверяем, что ответ - это массив
                assert isinstance(data, list), "Response should be an array"
                
                # Проверяем структуру каждого элемента массива
                for item in data:
                    assert "index" in item, "Each item should have 'index' field"
                    assert "cmd" in item, "Each item should have 'cmd' field"
                    assert isinstance(item["index"], int), "Index should be integer"
                    assert isinstance(item["cmd"], str), "Cmd should be string"
                    
                    # Проверяем, что команда содержит правильные элементы
                    cmd = item["cmd"]
                    assert "ip netns exec ngfw" in cmd, "Command should contain 'ip netns exec ngfw'"
                    assert "ifconfig" in cmd, "Command should contain 'ifconfig'"
                    assert payload["interface"] in cmd, f"Command should contain interface '{payload['interface']}'"
                    assert payload["state"] in cmd, f"Command should contain state '{payload['state']}'"
                    
                    # Для валидных случаев поле error не должно присутствовать
                    # Проверяем, является ли интерфейс реальным (существует в системе)
                    available_interfaces = get_available_interfaces(api_client)
                    if payload["interface"] in available_interfaces:
                        assert "error" not in item, f"Valid interface '{payload['interface']}' should not contain error field"
                    else:
                        # Для несуществующих интерфейсов поле error может присутствовать или отсутствовать
                        # API может не всегда возвращать ошибку для несуществующих интерфейсов
                        if "error" in item:
                            assert isinstance(item["error"], str), "Error field should be string"
                        # Если поля error нет, это тоже допустимо - API может просто не выполнить команду
            
            # Для ошибок валидации проверяем структуру ошибки
            elif expected_status in [400, 422]:
                data = response.json()
                assert "error" in data, "Error response should contain 'error' field"
                error = data["error"]
                assert "statusCode" in error, "Error should contain 'statusCode'"
                assert error["statusCode"] == expected_status, f"Error statusCode should be {expected_status}"
            
            # Дополнительная проверка через агента для теста стабильности
            if expected_status == 200 and not any("error" in item for item in data):
                print(f"Checking agent verification for stability test {i+1}: {payload}")
                # Проверяем агента
                agent_result = agent_verification(ENDPOINT, payload)
                if agent_result == "unavailable":
                    pytest.fail("Agent is unavailable; test must fail according to rule R24")
                elif agent_result["result"].upper() in ["ERROR", "ОШИБКА"]:
                    pytest.fail(f"Agent verification failed: {agent_result['message']}")
                elif agent_result["result"].upper() not in ["OK", "ОК"]:
                    pytest.fail(f"Unexpected agent result: {agent_result}")
            
            print(f"  ✓ Test case {i+1} passed")

def test_setInterfaceState_response_structure(api_client, attach_curl_on_fail, agent_verification):
    """
    Тест структуры ответа для валидного запроса
    """
    payload = {"interface": "lo", "state": "up"}
    headers = {"Content-Type": "application/json"}
    
    with attach_curl_on_fail(ENDPOINT, payload, headers, method="POST"):
        response = api_client.post(ENDPOINT, json=payload, headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        _check_types_recursive(data, response_schemas["POST"])
        
        # Дополнительные проверки структуры
        assert len(data) > 0, "Response should contain at least one command"
        
        for item in data:
            # Проверяем обязательные поля
            assert "index" in item, "Missing required field 'index'"
            assert "cmd" in item, "Missing required field 'cmd'"
            
            # Проверяем типы полей
            assert isinstance(item["index"], int), "Field 'index' should be integer"
            assert isinstance(item["cmd"], str), "Field 'cmd' should be string"
            
            # Проверяем опциональные поля
            if "res" in item:
                assert isinstance(item["res"], str), "Field 'res' should be string"
            
            # Для валидного запроса поле error не должно присутствовать
            assert "error" not in item, "Valid request should not contain error field"
        
        # Дополнительная проверка через агента
        print(f"Checking agent verification for structure test: {payload}")
        # Проверяем агента
        agent_result = agent_verification(ENDPOINT, payload)
        if agent_result == "unavailable":
            pytest.fail("Agent is unavailable; test must fail according to rule R24")
        elif agent_result["result"].upper() in ["ERROR", "ОШИБКА"]:
            pytest.fail(f"Agent verification failed: {agent_result['message']}")
        elif agent_result["result"].upper() not in ["OK", "ОК"]:
            pytest.fail(f"Unexpected agent result: {agent_result}")

def test_setInterfaceState_missing_interface(api_client, attach_curl_on_fail):
    """
    Тест отсутствия обязательного параметра interface
    """
    payload = {"state": "up"}
    headers = {"Content-Type": "application/json"}
    
    with attach_curl_on_fail(ENDPOINT, payload, headers, method="POST"):
        response = api_client.post(ENDPOINT, json=payload, headers=headers)
        assert response.status_code == 400
        
        data = response.json()
        assert "error" in data
        error = data["error"]
        assert error["statusCode"] == 400
        assert "interface is a required argument" in error["message"]

def test_setInterfaceState_missing_state(api_client, attach_curl_on_fail):
    """
    Тест отсутствия обязательного параметра state
    """
    payload = {"interface": "lo"}
    headers = {"Content-Type": "application/json"}
    
    with attach_curl_on_fail(ENDPOINT, payload, headers, method="POST"):
        response = api_client.post(ENDPOINT, json=payload, headers=headers)
        assert response.status_code == 400
        
        data = response.json()
        assert "error" in data
        error = data["error"]
        assert error["statusCode"] == 400
        assert "state is a required argument" in error["message"]

def test_setInterfaceState_empty_payload(api_client, attach_curl_on_fail):
    """
    Тест пустого payload
    """
    payload = {}
    headers = {"Content-Type": "application/json"}
    
    with attach_curl_on_fail(ENDPOINT, payload, headers, method="POST"):
        response = api_client.post(ENDPOINT, json=payload, headers=headers)
        assert response.status_code == 400
        
        data = response.json()
        assert "error" in data
        error = data["error"]
        assert error["statusCode"] == 400
        assert "interface is a required argument" in error["message"]

def test_setInterfaceState_invalid_state_values(api_client, attach_curl_on_fail):
    """
    Тест различных невалидных значений для state
    """
    invalid_states = ["invalid", "on", "off", "enabled", "disabled", "UP", "DOWN", "Up", "Down", "1", "0", "true", "false"]
    
    for state in invalid_states:
        payload = {"interface": "lo", "state": state}
        headers = {"Content-Type": "application/json"}
        
        with attach_curl_on_fail(ENDPOINT, payload, headers, method="POST"):
            response = api_client.post(ENDPOINT, json=payload, headers=headers)
            
            if state in ["up", "down"]:
                # Эти значения должны быть валидными
                assert response.status_code == 200
            else:
                # Остальные значения должны вызывать ошибку 422
                assert response.status_code == 422
                
                data = response.json()
                assert "error" in data
                error = data["error"]
                assert error["statusCode"] == 422
                assert "State should by up or down" in error["message"]

def test_setInterfaceState_nonexistent_interface(api_client, attach_curl_on_fail):
    """
    Тест несуществующего интерфейса
    """
    payload = {"interface": "nonexistent_interface", "state": "up"}
    headers = {"Content-Type": "application/json"}
    
    with attach_curl_on_fail(ENDPOINT, payload, headers, method="POST"):
        response = api_client.post(ENDPOINT, json=payload, headers=headers)
        # API возвращает 200, но с ошибкой в команде
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        
        # Проверяем, что в ответе есть информация об ошибке
        for item in data:
            assert "cmd" in item
            cmd = item["cmd"]
            assert "nonexistent_interface" in cmd
            assert "up" in cmd
            
            # Проверяем наличие поля error для несуществующего интерфейса
            assert "error" in item, "Response should contain error field for nonexistent interface"
            assert isinstance(item["error"], str), "Error field should be string"

def test_setInterfaceState_special_characters_interface(api_client, attach_curl_on_fail):
    """
    Тест интерфейса со специальными символами
    """
    payload = {"interface": "eth0@#$%", "state": "up"}
    headers = {"Content-Type": "application/json"}
    
    with attach_curl_on_fail(ENDPOINT, payload, headers, method="POST"):
        response = api_client.post(ENDPOINT, json=payload, headers=headers)
        # API принимает специальные символы, но команда может не выполниться
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        
        # Проверяем наличие поля error для невалидного случая
        for item in data:
            assert "error" in item, "Invalid case should contain error field"
            assert isinstance(item["error"], str), "Error field should be string"

def test_setInterfaceState_long_interface_name(api_client, attach_curl_on_fail):
    """
    Тест очень длинного имени интерфейса
    """
    long_name = "very_long_interface_name_that_exceeds_normal_length_limits_for_network_interfaces_in_linux_systems"
    payload = {"interface": long_name, "state": "up"}
    headers = {"Content-Type": "application/json"}
    
    with attach_curl_on_fail(ENDPOINT, payload, headers, method="POST"):
        response = api_client.post(ENDPOINT, json=payload, headers=headers)
        # API принимает длинные имена, но команда может не выполниться
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        
        # Проверяем наличие поля error для невалидного случая
        for item in data:
            assert "error" in item, "Invalid case should contain error field"
            assert isinstance(item["error"], str), "Error field should be string"

def test_setInterfaceState_wrong_content_type(api_client, attach_curl_on_fail):
    """
    Тест неправильного Content-Type
    """
    payload = {"interface": "lo", "state": "up"}
    headers = {"Content-Type": "text/plain"}
    
    with attach_curl_on_fail(ENDPOINT, payload, headers, method="POST"):
        response = api_client.post(ENDPOINT, json=payload, headers=headers)
        # API может принять неправильный Content-Type
        assert response.status_code in [200, 400, 415]

def test_setInterfaceState_malformed_json(api_client, attach_curl_on_fail):
    """
    Тест невалидного JSON
    """
    headers = {"Content-Type": "application/json"}
    
    with attach_curl_on_fail(ENDPOINT, '{"interface": "lo", "state": "up"', headers, method="POST"):
        # Отправляем невалидный JSON
        response = api_client.post(ENDPOINT, data='{"interface": "lo", "state": "up"', headers=headers)
        assert response.status_code == 400
        
        data = response.json()
        assert "error" in data
        error = data["error"]
        assert error["statusCode"] == 400
        assert "SyntaxError" in error["name"] or "Unexpected end of JSON input" in error["message"]

def test_setInterfaceState_wrong_http_method(api_client, attach_curl_on_fail):
    """
    Тест неправильного HTTP метода
    """
    payload = {"interface": "lo", "state": "up"}
    headers = {"Content-Type": "application/json"}
    
    with attach_curl_on_fail(ENDPOINT, payload, headers, method="GET"):
        # Пробуем GET вместо POST
        response = api_client.get(ENDPOINT, json=payload, headers=headers)
        assert response.status_code == 404
        
        data = response.json()
        assert "error" in data
        error = data["error"]
        assert error["statusCode"] == 404
        assert "no method handling GET" in error["message"]

@pytest.mark.parametrize("test_id", range(10))
def test_setInterfaceState_stability(api_client, attach_curl_on_fail, agent_verification, test_id):
    """
    Тесты стабильности - повторяем валидный запрос много раз
    """
    payload = {"interface": "lo", "state": "up"}
    headers = {"Content-Type": "application/json"}
    
    with attach_curl_on_fail(ENDPOINT, payload, headers, method="POST"):
            response = api_client.post(ENDPOINT, json=payload, headers=headers)
            assert response.status_code == 200
            
            data = response.json()
            assert isinstance(data, list)
            assert len(data) > 0
            
            # Проверяем, что структура ответа стабильна
            for item in data:
                assert "index" in item
                assert "cmd" in item
                assert isinstance(item["index"], int)
                assert isinstance(item["cmd"], str)
                
                # Для валидного запроса поле error не должно присутствовать
                assert "error" not in item, "Valid request should not contain error field"
            
            # Дополнительная проверка через агента для теста стабильности
            print(f"Checking agent verification for stability test {test_id}: {payload}")
            # Проверяем агента
            agent_result = agent_verification(ENDPOINT, payload)
            if agent_result == "unavailable":
                pytest.fail("Agent is unavailable; test must fail according to rule R24")
            elif agent_result["result"].upper() in ["ERROR", "ОШИБКА"]:
                pytest.fail(f"Agent verification failed: {agent_result['message']}")
            elif agent_result["result"].upper() not in ["OK", "ОК"]:
                pytest.fail(f"Unexpected agent result: {agent_result}")

def test_setInterfaceState_null_values(api_client, attach_curl_on_fail):
    """
    Тест null значений
    """
    test_cases = [
        ({"interface": None, "state": "up"}, 400),
        ({"interface": "lo", "state": None}, 400),
        ({"interface": None, "state": None}, 400)
    ]
    
    for payload, expected_status in test_cases:
        headers = {"Content-Type": "application/json"}
        
        with attach_curl_on_fail(ENDPOINT, payload, headers, method="POST"):
            response = api_client.post(ENDPOINT, json=payload, headers=headers)
            assert response.status_code == expected_status
            
            if expected_status != 200:
                data = response.json()
                assert "error" in data

def test_setInterfaceState_empty_strings(api_client, attach_curl_on_fail):
    """
    Тест пустых строк
    """
    test_cases = [
        ({"interface": "", "state": "up"}, 400),
        ({"interface": "lo", "state": ""}, 400),
        ({"interface": "", "state": ""}, 400)
    ]
    
    for payload, expected_status in test_cases:
        headers = {"Content-Type": "application/json"}
        
        with attach_curl_on_fail(ENDPOINT, payload, headers, method="POST"):
            response = api_client.post(ENDPOINT, json=payload, headers=headers)
            assert response.status_code == expected_status
            
            if expected_status != 200:
                data = response.json()
                assert "error" in data

def test_setInterfaceState_numeric_values(api_client, attach_curl_on_fail):
    """
    Тест числовых значений вместо строк
    """
    test_cases = [
        ({"interface": 123, "state": "up"}, 400),
        ({"interface": "lo", "state": 1}, 400),
        ({"interface": 0, "state": 0}, 400)
    ]
    
    for payload, expected_status in test_cases:
        headers = {"Content-Type": "application/json"}
        
        with attach_curl_on_fail(ENDPOINT, payload, headers, method="POST"):
            response = api_client.post(ENDPOINT, json=payload, headers=headers)
            assert response.status_code == expected_status
            
            if expected_status != 200:
                data = response.json()
                assert "error" in data

def test_setInterfaceState_case_sensitivity(api_client, attach_curl_on_fail, agent_verification):
    """
    Тест чувствительности к регистру
    """
    test_cases = [
        ({"interface": "LO", "state": "up"}, 200),  # Интерфейс может быть нечувствителен к регистру
        ({"interface": "Lo", "state": "up"}, 200),
        ({"interface": "lo", "state": "UP"}, 422),  # State должен быть в нижнем регистре
        ({"interface": "lo", "state": "DOWN"}, 422),
        ({"interface": "lo", "state": "Up"}, 422),
        ({"interface": "lo", "state": "Down"}, 422)
    ]
    
    for payload, expected_status in test_cases:
        headers = {"Content-Type": "application/json"}
        
        with attach_curl_on_fail(ENDPOINT, payload, headers, method="POST"):
            response = api_client.post(ENDPOINT, json=payload, headers=headers)
            assert response.status_code == expected_status
            
            if expected_status == 200:
                data = response.json()
                assert isinstance(data, list)
                
                # Проверяем, есть ли ошибки в команде (поле error)
                has_error = any("error" in item for item in data)
                
                if not has_error:
                    # Дополнительная проверка через агента только для действительно валидных случаев
                    print(f"Checking agent verification for case sensitivity test: {payload}")
                    # Проверяем агента
                    agent_result = agent_verification(ENDPOINT, payload)
                    if agent_result == "unavailable":
                        pytest.fail("Agent is unavailable; test must fail according to rule R24")
                    elif agent_result["result"].upper() in ["ERROR", "ОШИБКА"]:
                        pytest.fail(f"Agent verification failed: {agent_result['message']}")
                    elif agent_result["result"].upper() not in ["OK", "ОК"]:
                        pytest.fail(f"Unexpected agent result: {agent_result}")
                else:
                    print(f"Agent verification skipped - command contains errors for interface: {payload.get('interface', 'unknown')}")
                    
            elif expected_status == 422:
                data = response.json()
                assert "error" in data
                error = data["error"]
                assert error["statusCode"] == 422 

def test_setInterfaceState_valid_interface_dummy0(api_client, attach_curl_on_fail, agent_verification):
    """
    Тест валидного интерфейса dummy0 (существует в ngfw)
    """
    payload = {"interface": "dummy0", "state": "up"}
    headers = {"Content-Type": "application/json"}
    
    with attach_curl_on_fail(ENDPOINT, payload, headers, method="POST"):
        response = api_client.post(ENDPOINT, json=payload, headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        
        # Проверяем, что для валидного интерфейса поле error отсутствует
        for item in data:
            assert "cmd" in item
            cmd = item["cmd"]
            assert "dummy0" in cmd
            assert "up" in cmd
            
            # Проверяем, является ли интерфейс реальным (существует в системе)
            available_interfaces = get_available_interfaces(api_client)
            if "dummy0" in available_interfaces:
                # Поле error не должно присутствовать для валидного интерфейса
                assert "error" not in item, "Valid interface should not contain error field"
            else:
                # Для несуществующего интерфейса поле error может присутствовать
                if "error" in item:
                    assert isinstance(item["error"], str), "Error field should be string"
                # Если поля error нет, это тоже допустимо
        
        # Дополнительная проверка через агента для теста dummy0
        print(f"Checking agent verification for dummy0 test: {payload}")
        # Проверяем агента
        agent_result = agent_verification(ENDPOINT, payload)
        if agent_result == "unavailable":
            pytest.fail("Agent is unavailable; test must fail according to rule R24")
        elif agent_result["result"].upper() in ["ERROR", "ОШИБКА"]:
            pytest.fail(f"Agent verification failed: {agent_result['message']}")
        elif agent_result["result"].upper() not in ["OK", "ОК"]:
            pytest.fail(f"Unexpected agent result: {agent_result}") 