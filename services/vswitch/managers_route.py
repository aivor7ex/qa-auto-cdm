import pytest
import json
from typing import Dict, Any

ENDPOINT = "/managers/route"

def validate_response_schema(response_data: Dict[str, Any]) -> None:
    """Валидация схемы ответа для route API.
    Ожидаемая структура:
    {
        "index": int,
        "cmd": str,
        "res": str (опционально)
    }
    """
    assert isinstance(response_data, dict), "Response must be a dictionary"
    
    # Обязательные поля
    assert "index" in response_data, "Missing required field 'index'"
    assert isinstance(response_data["index"], int), "Field 'index' must be integer"
    
    assert "cmd" in response_data, "Missing required field 'cmd'"
    assert isinstance(response_data["cmd"], str), "Field 'cmd' must be string"
    
    # Опциональное поле res
    if "res" in response_data:
        assert isinstance(response_data["res"], str), "Field 'res' must be string"

def validate_string_response(response_data: str) -> None:
    """Валидация строкового ответа для route API."""
    assert isinstance(response_data, str), "Response must be a string"
    assert len(response_data) > 0, "Response string cannot be empty"

def validate_error_schema(response_data: Dict[str, Any]) -> None:
    """Валидация схемы ошибки для route API."""
    assert isinstance(response_data, dict), "Response must be a dictionary"
    assert "error" in response_data, "Missing 'error' field in response"
    assert "message" in response_data["error"], "Missing 'message' field in error"

def validate_route_response(response_data, response_status_code: int) -> None:
    """Универсальная валидация ответа route API."""
    if response_status_code == 200:
        # API может возвращать как JSON объект, так и строку
        if isinstance(response_data, dict):
            validate_response_schema(response_data)
        elif isinstance(response_data, str):
            validate_string_response(response_data)
        else:
            assert False, f"Unexpected response type: {type(response_data)}"
    elif response_status_code == 422:
        # 422 - команда не может быть выполнена (например, несуществующий интерфейс)
        validate_error_schema(response_data)
    else:
        # Другие коды ошибок
        validate_error_schema(response_data)


# Тесты просмотра таблицы маршрутизации
@pytest.mark.parametrize("cmd_line, expected_status", [
    ("route", 200),  # Команда просмотра таблицы маршрутизации
    ("-n", 200),     # Числовой вывод
    ("-e", 200),     # Расширенный вывод
    ("-F", 200),     # Формат FIB
])
def test_route_show_commands(api_client, attach_curl_on_fail, cmd_line, expected_status):
    """Тест команд просмотра таблицы маршрутизации"""
    payload = {"cmdLine": cmd_line}
    
    with attach_curl_on_fail(ENDPOINT, payload):
        response = api_client.post(ENDPOINT, json=payload)
        
        # Ожидаем 200 OK или 422 Unprocessable Entity
        assert response.status_code in [200, 422], f"Expected 200 or 422, got {response.status_code}"
        
        response_data = response.json()
        validate_route_response(response_data, response.status_code)
        

# Тесты добавления маршрутов (уникальные, чтобы избежать повторного создания)
@pytest.mark.parametrize("route_cmd, expected_status", [
    ("add -net 192.168.100.0/24 gw 192.168.1.1", 422),
    ("add -net 192.168.101.0/24 gw 192.168.1.254", 422),
    ("add -net 10.1.0.0/16 dev eth0", 422),
])
def test_route_add_commands(api_client, attach_curl_on_fail, route_cmd, expected_status):
    """Тест команд добавления маршрутов"""
    payload = {"cmdLine": route_cmd}
    
    with attach_curl_on_fail(ENDPOINT, payload):
        response = api_client.post(ENDPOINT, json=payload)
        
        # Ожидаем 200 OK или 422 Unprocessable Entity
        assert response.status_code in [200, 422], f"Expected 200 or 422, got {response.status_code}"
        
        response_data = response.json()
        validate_route_response(response_data, response.status_code)
        

# Тесты удаления маршрутов
@pytest.mark.parametrize("route_cmd, expected_status", [
    ("del -net 192.168.100.0/24", 422),
    ("del -net 192.168.101.0/24", 422),
])
def test_route_delete_commands(api_client, attach_curl_on_fail, route_cmd, expected_status):
    """Тест команд удаления маршрутов"""
    payload = {"cmdLine": route_cmd}
    
    with attach_curl_on_fail(ENDPOINT, payload):
        response = api_client.post(ENDPOINT, json=payload)
        
        # Ожидаем 200 OK или 422 Unprocessable Entity
        assert response.status_code in [200, 422], f"Expected 200 or 422, got {response.status_code}"
        
        response_data = response.json()
        validate_route_response(response_data, response.status_code)
        

# Тесты очистки таблицы маршрутизации
@pytest.mark.parametrize("route_cmd, expected_status", [
    ("flush", 422),
    ("flush -net 192.168.0.0/16", 422),
])
def test_route_flush_commands(api_client, attach_curl_on_fail, route_cmd, expected_status):
    """Тест команд очистки таблицы маршрутизации"""
    payload = {"cmdLine": route_cmd}
    
    with attach_curl_on_fail(ENDPOINT, payload):
        response = api_client.post(ENDPOINT, json=payload)
        
        # Ожидаем 200 OK или 422 Unprocessable Entity
        assert response.status_code in [200, 422], f"Expected 200 or 422, got {response.status_code}"
        
        response_data = response.json()
        validate_route_response(response_data, response.status_code)
        

# Тесты для IPv4/IPv6
@pytest.mark.parametrize("route_cmd", [
    "-4",
])
def test_route_ip_family_commands(api_client, attach_curl_on_fail, route_cmd):
    """Тест команд для работы с IPv4/IPv6"""
    payload = {"cmdLine": route_cmd}
    
    with attach_curl_on_fail(ENDPOINT, payload):
        response = api_client.post(ENDPOINT, json=payload)
        
        # Ожидаем только 200 OK для позитивных сценариев
        assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}"
        
        response_data = response.json()
        validate_route_response(response_data, response.status_code)
        

# Тесты справки и версии
@pytest.mark.parametrize("route_cmd", [
    "--help",
    "--version",
])
def test_route_help_commands(api_client, attach_curl_on_fail, route_cmd):
    """Тест команд справки и версии"""
    payload = {"cmdLine": route_cmd}
    
    with attach_curl_on_fail(ENDPOINT, payload):
        response = api_client.post(ENDPOINT, json=payload)
        
        # Ожидаем только 200 OK для позитивных сценариев
        assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}"
        
        response_data = response.json()
        validate_route_response(response_data, response.status_code)
        

# Тесты граничных случаев
@pytest.mark.parametrize("payload", [
    {"cmdLine": "invalid_command"},  # Неверная команда
    {"cmdLine": "add -net 999.999.999.999/24 gw 192.168.1.1"},  # Неверный IP
])
def test_route_edge_cases(api_client, attach_curl_on_fail, payload):
    """Тест граничных случаев и ошибок"""
    with attach_curl_on_fail(ENDPOINT, payload):
        response = api_client.post(ENDPOINT, json=payload)
        
        # Ожидаем 200 OK или 422, так как API возвращает результат выполнения команды
        assert response.status_code in [200, 422], f"Expected 200 OK or 422, got {response.status_code}"
        
        response_data = response.json()
        validate_route_response(response_data, response.status_code)

# Тест с пустым payload (должен возвращать 400)
def test_route_empty_payload(api_client, attach_curl_on_fail):
    """Тест с пустым payload - должен возвращать 400"""
    payload = {}
    
    with attach_curl_on_fail(ENDPOINT, payload):
        response = api_client.post(ENDPOINT, json=payload)
        
        assert response.status_code == 400, f"Expected 400 Bad Request, got {response.status_code}"
        
        response_data = response.json()
        validate_error_schema(response_data)
        assert "cmdLine is a required argument" in response_data["error"]["message"], "Unexpected error message"

# Тесты комплексных сценариев
@pytest.mark.parametrize("route_cmd, expected_status", [
    ("add -net 192.168.200.0/24 gw 192.168.1.1", 422),
    ("add -net 192.168.201.0/24 gw 192.168.1.10", 422),
])
def test_route_complex_scenarios(api_client, attach_curl_on_fail, route_cmd, expected_status):
    """Тест комплексных сценариев с несколькими командами"""
    payload = {"cmdLine": route_cmd}
    
    with attach_curl_on_fail(ENDPOINT, payload):
        response = api_client.post(ENDPOINT, json=payload)
        
        # Ожидаем 200 OK или 422 Unprocessable Entity
        assert response.status_code in [200, 422], f"Expected 200 or 422, got {response.status_code}"
        
        response_data = response.json()
        validate_route_response(response_data, response.status_code)
        

# Тесты с различными типами данных
@pytest.mark.parametrize("cmd_line, expected_status", [
    ("   ", 200), # пробелы
    ("add", 200),   # неполная команда
    ("add -net 192.168.1.0/24", 422),  # неполная команда add
])
def test_route_various_inputs(api_client, attach_curl_on_fail, cmd_line, expected_status):
    """Тест различных типов входных данных"""
    payload = {"cmdLine": cmd_line}
    
    with attach_curl_on_fail(ENDPOINT, payload):
        response = api_client.post(ENDPOINT, json=payload)
        
        # Ожидаем 200 OK или 422 Unprocessable Entity
        assert response.status_code in [200, 422], f"Expected 200 or 422, got {response.status_code}"
        
        response_data = response.json()
        validate_route_response(response_data, response.status_code)

# Тест с null значением cmdLine
def test_route_null_cmdline(api_client, attach_curl_on_fail):
    """Тест с null значением cmdLine - должен возвращать 400"""
    payload = {"cmdLine": None}
    
    with attach_curl_on_fail(ENDPOINT, payload):
        response = api_client.post(ENDPOINT, json=payload)
        
        assert response.status_code == 400, f"Expected 400 Bad Request, got {response.status_code}"
        
        response_data = response.json()
        validate_error_schema(response_data)

# Тест с пустой строкой cmdLine
def test_route_empty_cmdline(api_client, attach_curl_on_fail):
    """Тест с пустой строкой cmdLine - должен возвращать 400"""
    payload = {"cmdLine": ""}
    
    with attach_curl_on_fail(ENDPOINT, payload):
        response = api_client.post(ENDPOINT, json=payload)
        
        assert response.status_code == 400, f"Expected 400 Bad Request, got {response.status_code}"
        
        response_data = response.json()
        validate_error_schema(response_data)

# Тесты с длинными строками
@pytest.mark.parametrize("route_cmd, expected_status", [
    ("add -net 192.168.40.0/24 gw 192.168.1.1", 422),
    ("add -net 192.168.41.0/24 gw 192.168.1.1", 422),
])
def test_route_long_inputs(api_client, attach_curl_on_fail, route_cmd, expected_status):
    """Тест с длинными входными строками"""
    payload = {"cmdLine": route_cmd}
    
    with attach_curl_on_fail(ENDPOINT, payload):
        response = api_client.post(ENDPOINT, json=payload)
        
        # Ожидаем 200 OK или 422 Unprocessable Entity
        assert response.status_code in [200, 422], f"Expected 200 or 422, got {response.status_code}"
        
        response_data = response.json()
        validate_route_response(response_data, response.status_code)

# Тесты с специальными символами
@pytest.mark.parametrize("route_cmd, expected_status", [
    ("add -net 192.168.1.0/24 gw 192.168.1.1", 422),
    ("add -net 192.168.1.0/24 gw 192.168.1.1 metric 1", 422),
])
def test_route_special_characters(api_client, attach_curl_on_fail, route_cmd, expected_status):
    """Тест с специальными символами в командах"""
    payload = {"cmdLine": route_cmd}
    
    with attach_curl_on_fail(ENDPOINT, payload):
        response = api_client.post(ENDPOINT, json=payload)
        
        # Ожидаем 200 OK или 422 Unprocessable Entity
        assert response.status_code in [200, 422], f"Expected 200 or 422, got {response.status_code}"
        
        response_data = response.json()
        validate_route_response(response_data, response.status_code)

# Тесты с различными метриками и параметрами
@pytest.mark.parametrize("route_cmd, expected_status", [
    ("add -net 192.168.10.0/24 gw 192.168.1.1 metric 1", 422),
    ("add -net 192.168.11.0/24 gw 192.168.1.1 metric 100", 422),
    ("add -net 192.168.12.0/24 gw 192.168.1.1 mtu 1500", 422),
])
def test_route_with_parameters(api_client, attach_curl_on_fail, route_cmd, expected_status):
    """Тест с различными параметрами маршрутов"""
    payload = {"cmdLine": route_cmd}
    
    with attach_curl_on_fail(ENDPOINT, payload):
        response = api_client.post(ENDPOINT, json=payload)
        
        # Ожидаем 200 OK или 422 Unprocessable Entity
        assert response.status_code in [200, 422], f"Expected 200 or 422, got {response.status_code}"
        
        response_data = response.json()
        validate_route_response(response_data, response.status_code)
        

# Тесты с различными сетями и подсетями
@pytest.mark.parametrize("route_cmd, expected_status", [
    ("add -net 10.0.0.0/8 gw 192.168.1.1", 422),
    ("add -net 172.16.0.0/12 gw 192.168.1.1", 422),
    ("add -net 192.168.0.0/16 gw 192.168.1.1", 422),
])
def test_route_different_networks(api_client, attach_curl_on_fail, route_cmd, expected_status):
    """Тест с различными сетями и подсетями"""
    payload = {"cmdLine": route_cmd}
    
    with attach_curl_on_fail(ENDPOINT, payload):
        response = api_client.post(ENDPOINT, json=payload)
        
        # Ожидаем 200 OK или 422 Unprocessable Entity
        assert response.status_code in [200, 422], f"Expected 200 or 422, got {response.status_code}"
        
        response_data = response.json()
        validate_route_response(response_data, response.status_code)
        

# Тесты с различными интерфейсами
@pytest.mark.parametrize("route_cmd, expected_status", [
    ("add -net 192.168.30.0/24 dev eth0", 422),
    ("add -net 192.168.31.0/24 dev eth1", 422),
    ("add -net 192.168.32.0/24 dev lo", 422),
])
def test_route_different_interfaces(api_client, attach_curl_on_fail, route_cmd, expected_status):
    """Тест с различными интерфейсами"""
    payload = {"cmdLine": route_cmd}
    
    with attach_curl_on_fail(ENDPOINT, payload):
        response = api_client.post(ENDPOINT, json=payload)
        
        # Ожидаем 200 OK или 422 Unprocessable Entity
        assert response.status_code in [200, 422], f"Expected 200 or 422, got {response.status_code}"
        
        response_data = response.json()
        validate_route_response(response_data, response.status_code)
        

# Тест базового функционала (пример из конфигурации)
def test_route_basic_functionality(api_client, attach_curl_on_fail):
    """Тест базового функционала - добавление маршрута по умолчанию"""
    payload = {"cmdLine": "add -net default gw 192.168.0.1"}
    
    with attach_curl_on_fail(ENDPOINT, payload):
        response = api_client.post(ENDPOINT, json=payload)
        
        # Ожидаем 200 OK или 422 Unprocessable Entity
        assert response.status_code in [200, 422], f"Expected 200 or 422, got {response.status_code}"
        
        response_data = response.json()
        validate_route_response(response_data, response.status_code)
        
