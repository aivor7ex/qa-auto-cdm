import pytest
import json
from typing import Dict, Any, List

ENDPOINT = "/managers/initScripts"

# Схема ответа на основе R0-запроса
RESPONSE_SCHEMA = {
    "required": {
        "index": int,
        "cmd": str,
        "res": str
    },
    "optional": {}
}

@pytest.mark.parametrize("payload,expected_status", [
    # Базовые случаи
    ({}, 200),
    ({"test": "value"}, 200),
    ({"data": None}, 200),
    
    # Пустые значения
    ({"empty_string": ""}, 200),
    ({"null_value": None}, 200),
    ({"empty_array": []}, 200),
    ({"empty_object": {}}, 200),
    
    # Различные типы данных
    ({"string": "test"}, 200),
    ({"number": 123}, 200),
    ({"float": 123.45}, 200),
    ({"boolean": True}, 200),
    ({"boolean_false": False}, 200),
    ({"array": [1, 2, 3]}, 200),
    ({"nested": {"key": "value"}}, 200),
    
    # Специальные символы
    ({"special_chars": "!@#$%^&*()"}, 200),
    ({"unicode": "тест"}, 200),
    ({"quotes": '""\'\''}, 200),
    ({"newlines": "line1\nline2"}, 200),
    ({"tabs": "tab\there"}, 200),
    
    # Длинные значения
    ({"long_string": "a" * 1000}, 200),
])
def test_init_scripts_basic(api_client, attach_curl_on_fail, payload, expected_status):
    """Тестирует базовые случаи для эндпоинта initScripts"""
    with attach_curl_on_fail(ENDPOINT, payload):
        response = api_client.post(ENDPOINT, json=payload)
        assert response.status_code == expected_status, f"Expected {expected_status}, got {response.status_code}"

@pytest.mark.parametrize("invalid_payload,expected_status", [
    # Невалидный JSON
    ("invalid json", 400),
    ("{invalid}", 400),
    ("[invalid]", 400),
])
def test_init_scripts_invalid_input(api_client, attach_curl_on_fail, invalid_payload, expected_status):
    """Тестирует обработку невалидного ввода"""
    with attach_curl_on_fail(ENDPOINT, invalid_payload):
        if isinstance(invalid_payload, str):
            response = api_client.post(ENDPOINT, data=invalid_payload)
        else:
            response = api_client.post(ENDPOINT, json=invalid_payload)
        assert response.status_code == expected_status

def test_init_scripts_response_structure(api_client, attach_curl_on_fail):
    """Проверяет структуру ответа эндпоинта initScripts"""
    with attach_curl_on_fail(ENDPOINT, {}):
        response = api_client.post(ENDPOINT, json={})
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list), f"Expected list, got {type(data)}"
        
        # Проверяем каждый элемент массива
        for i, item in enumerate(data):
            assert isinstance(item, dict), f"Item {i} is not a dict: {type(item)}"
            
            # Проверяем обязательные поля
            assert "index" in item, f"Missing 'index' field in item {i}"
            assert "cmd" in item, f"Missing 'cmd' field in item {i}"
            assert "res" in item, f"Missing 'res' field in item {i}"
            
            # Проверяем типы полей
            assert isinstance(item["index"], int), f"'index' field in item {i} is not int: {type(item['index'])}"
            assert isinstance(item["cmd"], str), f"'cmd' field in item {i} is not str: {type(item['cmd'])}"
            assert isinstance(item["res"], str), f"'res' field in item {i} is not str: {type(item['res'])}"

def test_init_scripts_response_content(api_client, attach_curl_on_fail):
    """Проверяет содержимое ответа эндпоинта initScripts"""
    with attach_curl_on_fail(ENDPOINT, {}):
        response = api_client.post(ENDPOINT, json={})
        assert response.status_code == 200
        
        data = response.json()
        assert len(data) > 0, "Response should contain at least one script"
        
        # Проверяем, что index начинается с 0 и увеличивается
        for i, item in enumerate(data):
            assert item["index"] == i, f"Expected index {i}, got {item['index']}"
            assert len(item["cmd"]) > 0, f"Command should not be empty in item {i}"
            assert len(item["res"]) > 0, f"Result should not be empty in item {i}"

def test_init_scripts_empty_payload(api_client, attach_curl_on_fail):
    """Тестирует эндпоинт с пустым payload"""
    with attach_curl_on_fail(ENDPOINT, {}):
        response = api_client.post(ENDPOINT, json={})
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)

def test_init_scripts_null_payload(api_client, attach_curl_on_fail):
    """Тестирует эндпоинт с null payload"""
    with attach_curl_on_fail(ENDPOINT, None):
        response = api_client.post(ENDPOINT, json=None)
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)

def test_init_scripts_large_payload(api_client, attach_curl_on_fail):
    """Тестирует эндпоинт с большим payload"""
    large_payload = {
        "large_field": "x" * 10000,
        "array_field": list(range(1000)),
        "nested_field": {"deep": {"nested": {"structure": "value"}}}
    }
    
    with attach_curl_on_fail(ENDPOINT, large_payload):
        response = api_client.post(ENDPOINT, json=large_payload)
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)

def test_init_scripts_special_characters(api_client, attach_curl_on_fail):
    """Тестирует эндпоинт с специальными символами в payload"""
    special_payload = {
        "unicode": "тест с кириллицей",
        "special": "!@#$%^&*()_+-=[]{}|;':\",./<>?",
        "quotes": '""\'\'``',
        "newlines": "line1\nline2\r\nline3",
        "tabs": "tab\there\tand\there"
    }
    
    with attach_curl_on_fail(ENDPOINT, special_payload):
        response = api_client.post(ENDPOINT, json=special_payload)
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)

def test_init_scripts_numeric_values(api_client, attach_curl_on_fail):
    """Тестирует эндпоинт с различными числовыми значениями"""
    numeric_payload = {
        "zero": 0,
        "positive": 123,
        "negative": -456,
        "float": 3.14159,
        "large": 999999999999,
        "scientific": 1.23e10,
        "hex": 0xABCD,
        "binary": 0b1010
    }
    
    with attach_curl_on_fail(ENDPOINT, numeric_payload):
        response = api_client.post(ENDPOINT, json=numeric_payload)
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)

def test_init_scripts_boolean_values(api_client, attach_curl_on_fail):
    """Тестирует эндпоинт с булевыми значениями"""
    boolean_payload = {
        "true_value": True,
        "false_value": False,
        "mixed": {"bool": True, "string": "test", "number": 123}
    }
    
    with attach_curl_on_fail(ENDPOINT, boolean_payload):
        response = api_client.post(ENDPOINT, json=boolean_payload)
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)

def test_init_scripts_array_values(api_client, attach_curl_on_fail):
    """Тестирует эндпоинт с массивами в payload"""
    array_payload = {
        "empty_array": [],
        "string_array": ["a", "b", "c"],
        "number_array": [1, 2, 3, 4, 5],
        "mixed_array": [1, "string", True, None, {"key": "value"}],
        "nested_array": [[1, 2], [3, 4], [5, 6]]
    }
    
    with attach_curl_on_fail(ENDPOINT, array_payload):
        response = api_client.post(ENDPOINT, json=array_payload)
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)

def test_init_scripts_nested_objects(api_client, attach_curl_on_fail):
    """Тестирует эндпоинт с вложенными объектами"""
    nested_payload = {
        "level1": {
            "level2": {
                "level3": {
                    "level4": {
                        "value": "deep_nested"
                    }
                }
            }
        },
        "mixed": {
            "string": "test",
            "number": 123,
            "boolean": True,
            "null": None,
            "array": [1, 2, 3],
            "object": {"key": "value"}
        }
    }
    
    with attach_curl_on_fail(ENDPOINT, nested_payload):
        response = api_client.post(ENDPOINT, json=nested_payload)
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)

def test_init_scripts_response_consistency(api_client, attach_curl_on_fail):
    """Проверяет консистентность ответов при повторных запросах"""
    with attach_curl_on_fail(ENDPOINT, {}):
        # Первый запрос
        response1 = api_client.post(ENDPOINT, json={})
        assert response1.status_code == 200
        data1 = response1.json()
        
        # Второй запрос
        response2 = api_client.post(ENDPOINT, json={})
        assert response2.status_code == 200
        data2 = response2.json()
        
        # Ответы должны быть одинаковыми
        assert data1 == data2, "Responses should be consistent between requests"

def test_init_scripts_headers_validation(api_client, attach_curl_on_fail):
    """Проверяет валидацию заголовков"""
    with attach_curl_on_fail(ENDPOINT, {}):
        # Запрос с правильными заголовками
        response = api_client.post(ENDPOINT, json={})
        assert response.status_code == 200
        
        # Проверяем, что Content-Type установлен правильно
        assert "application/json" in response.headers.get("content-type", "")

def test_init_scripts_error_handling(api_client, attach_curl_on_fail):
    """Тестирует обработку ошибок"""
    # Тест с невалидным JSON
    with attach_curl_on_fail(ENDPOINT, "invalid json"):
        response = api_client.post(ENDPOINT, data="invalid json")
        assert response.status_code in [400, 422], f"Expected 400 or 422, got {response.status_code}"

def test_init_scripts_method_not_allowed(api_client, attach_curl_on_fail):
    """Проверяет, что другие HTTP методы не поддерживаются"""
    # GET запрос должен вернуть 404 Not Found
    with attach_curl_on_fail(ENDPOINT, None, method="GET"):
        response = api_client.get(ENDPOINT)
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"

def test_init_scripts_put_not_allowed(api_client, attach_curl_on_fail):
    """Проверяет, что PUT метод не поддерживается"""
    with attach_curl_on_fail(ENDPOINT, {}, method="PUT"):
        response = api_client.put(ENDPOINT, json={})
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"

def test_init_scripts_delete_not_allowed(api_client, attach_curl_on_fail):
    """Проверяет, что DELETE метод не поддерживается"""
    with attach_curl_on_fail(ENDPOINT, None, method="DELETE"):
        response = api_client.delete(ENDPOINT)
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"

def test_init_scripts_patch_not_allowed(api_client, attach_curl_on_fail):
    """Проверяет, что PATCH метод не поддерживается"""
    with attach_curl_on_fail(ENDPOINT, {}, method="PATCH"):
        response = api_client.patch(ENDPOINT, json={})
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
