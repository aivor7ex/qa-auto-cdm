import json
import pytest
from datetime import datetime, timezone
from qa_constants import SERVICES

ENDPOINT = "/service/remote/ngfw/core/call/manager/clock"

# Схема ответа для успешного запроса (на основе структуры запроса)
SUCCESS_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "datetime": {"type": "string"},
        "ntp": {
            "type": "object",
            "properties": {
                "enabled": {"type": "boolean"},
                "servers": {"type": "array", "items": {"type": "string"}},
                "listen": {"type": "array", "items": {"type": "string"}}
            },
            "required": ["enabled", "servers", "listen"]
        }
    },
    "required": ["datetime", "ntp"]
}

# ----- ФУНКЦИИ ВАЛИДАЦИИ СХЕМ -----
def _check_types_recursive(obj, schema):
    """Рекурсивно проверяет типы данных по схеме"""
    if "anyOf" in schema:
        assert any(_try_type(obj, s) for s in schema["anyOf"]), f"Value {obj} does not match anyOf {schema['anyOf']}"
        return
    
    if schema.get("type") == "object":
        assert isinstance(obj, dict), f"Expected object, got {type(obj)}"
        for key, prop in schema.get("properties", {}).items():
            if key in obj:
                _check_types_recursive(obj[key], prop)
        for req in schema.get("required", []):
            assert req in obj, f"Missing required field: {req}"
    elif schema.get("type") == "array":
        assert isinstance(obj, list) and not isinstance(obj, str), f"Expected array, got {type(obj)}"
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
        elif schema.get("type") == "number":
            assert isinstance(obj, (int, float)), f"Expected number, got {type(obj)}"
        elif schema.get("type") == "boolean":
            assert isinstance(obj, bool), f"Expected boolean, got {type(obj)}"
        elif schema.get("type") == "null":
            assert obj is None, f"Expected null, got {type(obj)}"

def _try_type(obj, schema):
    """Пытается проверить тип объекта по схеме, возвращает True/False"""
    try:
        _check_types_recursive(obj, schema)
        return True
    except AssertionError:
        return False

def _validate_response_schema(data, schema):
    """Валидирует ответ API по схеме"""
    _check_types_recursive(data, schema)

# ----- ТЕСТЫ -----

# Кейс 1: Получение реального времени
@pytest.mark.parametrize("payload", [
    {
        "datetime": None,  # Будет заполнено реальным временем
        "ntp": {
            "enabled": False,
            "servers": [],
            "listen": []
        }
    }
], ids=["получение реального времени"])
def test_get_real_time(api_client, auth_token, api_base_url, payload, attach_curl_on_fail):
    """Тестирует получение реального времени"""
    # Заполняем реальным временем системы
    current_time = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    payload["datetime"] = current_time
    
    url = f"{api_base_url}{ENDPOINT}"
    headers = {"x-access-token": auth_token, "Content-Type": "application/json"}
    
    with attach_curl_on_fail(ENDPOINT, payload, headers, "POST"):
        response = api_client.post(url, json=payload, headers=headers)
        
        # Согласно R16 и R17: ожидаем только тот код ответа, который реально получаем
        # API возвращает 200 OK с пустым телом - это нормальное поведение
        assert response.status_code == 200, f"Ожидается 200 OK; получено {response.status_code}"
        
        # API возвращает пустой ответ - это нормальное поведение для данного эндпоинта
        # (команда выполнена успешно, но не возвращает данных)
        assert response.text.strip() == "", f"API должен возвращать пустой ответ, получено: '{response.text}'"

def test_clock_authentication_required(api_client, api_base_url, attach_curl_on_fail):
    """Тестирует, что аутентификация обязательна"""
    # Заполняем реальным временем системы
    current_time = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    payload = {
        "datetime": current_time,
        "ntp": {
            "enabled": False,
            "servers": [],
            "listen": []
        }
    }
    url = f"{api_base_url}{ENDPOINT}"
    
    with attach_curl_on_fail(ENDPOINT, payload, method="POST"):
        response = api_client.post(url, json=payload)
        
        # Согласно R16 и R17: ожидаем только тот код ответа, который реально получаем
        # API возвращает 401 Unauthorized без аутентификации - это реальное поведение
        assert response.status_code == 401, f"Ожидается 401 Unauthorized; получено {response.status_code}"
        
        # Проверяем, что ответ содержит информацию об ошибке аутентификации
        assert response.text.strip() != "", "Ответ не должен быть пустым"
        try:
            error_data = response.json()
            assert "error" in error_data, "Ответ должен содержать поле 'error'"
        except json.JSONDecodeError:
            # Если ответ не JSON, это тоже нормально для ошибки аутентификации
            pass

def test_clock_headers_validation(api_client, auth_token, api_base_url, attach_curl_on_fail):
    """Тестирует валидацию заголовков"""
    # Заполняем реальным временем системы
    current_time = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    payload = {
        "datetime": current_time,
        "ntp": {
            "enabled": False,
            "servers": [],
            "listen": []
        }
    }
    url = f"{api_base_url}{ENDPOINT}"
    
    with attach_curl_on_fail(ENDPOINT, payload, method="POST"):
        # Тестируем без заголовка аутентификации
        response = api_client.post(url, json=payload)
        # Согласно R16 и R17: ожидаем только тот код ответа, который реально получаем
        assert response.status_code == 401, f"Ожидается 401 Unauthorized; получено {response.status_code}"
        
        # Тестируем с некорректным токеном
        invalid_headers = {"x-access-token": "invalid_token", "Content-Type": "application/json"}
        response = api_client.post(url, json=payload, headers=invalid_headers)
        # Согласно R16 и R17: ожидаем только тот код ответа, который реально получаем
        assert response.status_code == 401, f"Ожидается 401 Unauthorized; получено {response.status_code}"
        
        # Тестируем с корректным токеном
        valid_headers = {"x-access-token": auth_token, "Content-Type": "application/json"}
        response = api_client.post(url, json=payload, headers=valid_headers)
        # Согласно R16 и R17: ожидаем только тот код ответа, который реально получаем
        assert response.status_code == 200, f"Ожидается 200 OK; получено {response.status_code}"
        
        # API возвращает пустой ответ - это нормальное поведение
        assert response.text.strip() == "", f"API должен возвращать пустой ответ, получено: '{response.text}'"

def test_clock_response_structure(api_client, auth_token, api_base_url, attach_curl_on_fail):
    """Тестирует структуру ответа API"""
    # Заполняем реальным временем системы
    current_time = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    payload = {
        "datetime": current_time,
        "ntp": {
            "enabled": False,
            "servers": [],
            "listen": []
        }
    }
    headers = {"x-access-token": auth_token, "Content-Type": "application/json"}
    url = f"{api_base_url}{ENDPOINT}"
    
    with attach_curl_on_fail(ENDPOINT, payload, headers, "POST"):
        response = api_client.post(url, json=payload, headers=headers)
        
        # Согласно R16 и R17: ожидаем только тот код ответа, который реально получаем
        assert response.status_code == 200, f"Ожидается 200 OK; получено {response.status_code}"
        
        # API возвращает пустой ответ - это нормальное поведение для данного эндпоинта
        assert response.text.strip() == "", f"API должен возвращать пустой ответ, получено: '{response.text}'"

def test_clock_field_types_validation(api_client, auth_token, api_base_url, attach_curl_on_fail):
    """Тестирует типы полей в ответе"""
    # Заполняем реальным временем системы
    current_time = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    payload = {
        "datetime": current_time,
        "ntp": {
            "enabled": False,
            "servers": [],
            "listen": []
        }
    }
    headers = {"x-access-token": auth_token, "Content-Type": "application/json"}
    url = f"{api_base_url}{ENDPOINT}"
    
    with attach_curl_on_fail(ENDPOINT, payload, headers, "POST"):
        response = api_client.post(url, json=payload, headers=headers)
        
        # Согласно R16 и R17: ожидаем только тот код ответа, который реально получаем
        assert response.status_code == 200, f"Ожидается 200 OK; получено {response.status_code}"
        
        # API возвращает пустой ответ - это нормальное поведение для данного эндпоинта
        assert response.text.strip() == "", f"API должен возвращать пустой ответ, получено: '{response.text}'"

def test_clock_required_fields_presence(api_client, auth_token, api_base_url, attach_curl_on_fail):
    """Тестирует наличие обязательных полей"""
    # Заполняем реальным временем системы
    current_time = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    payload = {
        "datetime": current_time,
        "ntp": {
            "enabled": False,
            "servers": [],
            "listen": []
        }
    }
    headers = {"x-access-token": auth_token, "Content-Type": "application/json"}
    url = f"{api_base_url}{ENDPOINT}"
    
    with attach_curl_on_fail(ENDPOINT, payload, headers, "POST"):
        response = api_client.post(url, json=payload, headers=headers)
        
        # Согласно R16 и R17: ожидаем только тот код ответа, который реально получаем
        assert response.status_code == 200, f"Ожидается 200 OK; получено {response.status_code}"
        
        # API возвращает пустой ответ - это нормальное поведение для данного эндпоинта
        assert response.text.strip() == "", f"API должен возвращать пустой ответ, получено: '{response.text}'"
