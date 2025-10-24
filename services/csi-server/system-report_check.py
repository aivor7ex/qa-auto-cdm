import json
import pytest
from qa_constants import SERVICES

ENDPOINT = "/system-report/check"

# Схема ответа для успешного выполнения
SUCCESS_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "status": {"type": "string"},
        "ctime": {"type": "string"},
        "mtime": {"type": "string"},
        "size": {"type": "number"}
    },
    "required": ["status"]
}

def _check_types_recursive(obj, schema):
    """Рекурсивно проверяет типы данных по схеме"""
    if schema.get("type") == "object":
        assert isinstance(obj, dict), f"Expected object, got {type(obj)}"
        for key, prop in schema.get("properties", {}).items():
            if key in obj:
                _check_types_recursive(obj[key], prop)
        for req in schema.get("required", []):
            assert req in obj, f"Missing required field: {req}"
    elif schema.get("type") == "string":
        assert isinstance(obj, str), f"Expected string, got {type(obj)}"
    elif schema.get("type") == "number":
        assert isinstance(obj, (int, float)), f"Expected number, got {type(obj)}"
    elif schema.get("type") == "array":
        assert isinstance(obj, list), f"Expected array, got {type(obj)}"
        for item in obj:
            if "items" in schema:
                _check_types_recursive(item, schema["items"])

@pytest.mark.parametrize("auth_method,headers,expected_status", [
    # 1. С x-access-token заголовком (основной метод)
    ("x_access_token", {"x-access-token": "token_placeholder"}, [200]),
    
    # 2. Без аутентификации
    ("no_auth", {}, [401]),
    
    # 3. С дополнительными заголовками для логирования
    ("x_access_token_logging", {
        "x-access-token": "token_placeholder",
        "X-Request-ID": "unique-request-id",
        "User-Agent": "MyApp/1.0"
    }, [200])
])
def test_system_report_check_authentication_methods(
    api_client, 
    api_base_url, 
    auth_token, 
    attach_curl_on_fail,
    auth_method,
    headers,
    expected_status
):
    """
    Тест различных методов аутентификации для эндпоинта system-report/check.
    """
    url = f"{api_base_url}{ENDPOINT}"
    
    # Добавляем Content-Type заголовок
    headers["Content-Type"] = "application/json"
    
    # Обрабатываем специальные случаи аутентификации
    if auth_method in ["x_access_token", "x_access_token_logging"]:
        # Используем реальный токен из фикстуры
        headers["x-access-token"] = auth_token
    
    # Выполняем POST-запрос
    with attach_curl_on_fail(ENDPOINT, None, headers, "POST"):
        response = api_client.post(url, headers=headers)
        
        # Проверяем, что статус код соответствует ожидаемому
        assert response.status_code in expected_status, \
            f"Expected status code in {expected_status}, got {response.status_code}"
        
        # Если ответ успешный и содержит JSON, валидируем схему
        if response.status_code == 200 and response.content:
            response_data = response.json()
            _check_types_recursive(response_data, SUCCESS_RESPONSE_SCHEMA)

@pytest.mark.parametrize("invalid_token", [
    "invalid_token_123",
    "expired_token_456",
    "malformed_token_789",
    "",
    "null",
    "undefined"
])
def test_system_report_check_invalid_tokens(
    api_client, 
    api_base_url, 
    attach_curl_on_fail,
    invalid_token
):
    """
    Тест попыток доступа с недействительными токенами.
    """
    url = f"{api_base_url}{ENDPOINT}"
    headers = {
        "x-access-token": invalid_token,
        "Content-Type": "application/json"
    }
    
    with attach_curl_on_fail(ENDPOINT, None, headers, "POST"):
        response = api_client.post(url, headers=headers)
        
        # Проверяем, что запрос отклонен из-за недействительного токена
        assert response.status_code == 401, \
            f"Expected status code 401, got {response.status_code}"



def test_system_report_check_malformed_headers(
    api_client, 
    api_base_url, 
    attach_curl_on_fail
):
    """
    Тест попыток доступа с некорректно сформированными заголовками x-access-token.
    """
    url = f"{api_base_url}{ENDPOINT}"
    
    test_cases = [
        # Некорректный x-access-token
        {"x-access-token": ""},
        {"x-access-token": "invalid"},
        {"x-access-token": "expired_token"},
    ]
    
    for headers in test_cases:
        headers["Content-Type"] = "application/json"
        with attach_curl_on_fail(ENDPOINT, None, headers, "POST"):
            response = api_client.post(url, headers=headers)
            
            # Проверяем, что запрос отклонен
            assert response.status_code == 401, \
                f"Expected status code 401 for headers {headers}, got {response.status_code}"

def test_system_report_check_content_type_validation(
    api_client, 
    api_base_url, 
    auth_token, 
    attach_curl_on_fail
):
    """
    Тест валидации Content-Type заголовка.
    """
    url = f"{api_base_url}{ENDPOINT}"
    
    test_cases = [
        # Отсутствует Content-Type
        {},
        
        # Неправильный Content-Type
        {"Content-Type": "text/plain"},
        {"Content-Type": "application/xml"},
        {"Content-Type": "multipart/form-data"},
        
        # Некорректный Content-Type
        {"Content-Type": "application/json; charset=utf-8"},
        {"Content-Type": "application/json; version=1.0"},
    ]
    
    for headers in test_cases:
        # Добавляем токен аутентификации
        headers["x-access-token"] = auth_token
        
        with attach_curl_on_fail(ENDPOINT, None, headers, "POST"):
            response = api_client.post(url, headers=headers)
            
            # API может принимать запросы с различными Content-Type заголовками
            # Проверяем, что запрос обработан (статус 200) или отклонен (401)
            assert response.status_code in [200, 401], \
                f"Unexpected status code {response.status_code} for Content-Type {headers.get('Content-Type', 'None')}"

def test_system_report_check_with_payload_data(
    api_client, 
    api_base_url, 
    auth_token, 
    attach_curl_on_fail
):
    """
    Тест с различными типами данных в payload.
    """
    url = f"{api_base_url}{ENDPOINT}"
    headers = {
        "x-access-token": auth_token,
        "Content-Type": "application/json"
    }
    
    test_payloads = [
        {"report_type": "system"},
        {"report_type": "security", "include_logs": True},
        {"report_type": "performance", "timeframe": "24h"},
        {"filters": {"severity": "high"}},
        {"options": {"format": "json", "compressed": False}}
    ]
    
    for payload in test_payloads:
        with attach_curl_on_fail(ENDPOINT, payload, headers, "POST"):
            response = api_client.post(url, headers=headers, json=payload)
            assert response.status_code == 200, \
                f"Expected status code 200 for payload {payload}, got {response.status_code}"
            
            if response.content:
                response_data = response.json()
                _check_types_recursive(response_data, SUCCESS_RESPONSE_SCHEMA)

def test_system_report_check_empty_payload(
    api_client, 
    api_base_url, 
    auth_token, 
    attach_curl_on_fail
):
    """
    Тест с пустым payload.
    """
    url = f"{api_base_url}{ENDPOINT}"
    headers = {
        "x-access-token": auth_token,
        "Content-Type": "application/json"
    }
    
    with attach_curl_on_fail(ENDPOINT, {}, headers, "POST"):
        response = api_client.post(url, headers=headers, json={})
        assert response.status_code == 200, \
            f"Expected status code 200 for empty payload, got {response.status_code}"
        
        if response.content:
            response_data = response.json()
            _check_types_recursive(response_data, SUCCESS_RESPONSE_SCHEMA)

def test_system_report_check_large_payload(
    api_client, 
    api_base_url, 
    auth_token, 
    attach_curl_on_fail
):
    """
    Тест с большим payload.
    """
    url = f"{api_base_url}{ENDPOINT}"
    headers = {
        "x-access-token": auth_token,
        "Content-Type": "application/json"
    }
    
    large_payload = {
        "report_type": "comprehensive",
        "filters": {
            "severity": ["low", "medium", "high", "critical"],
            "categories": ["system", "security", "performance", "network", "storage"],
            "time_range": {
                "start": "2024-01-01T00:00:00.000Z",
                "end": "2024-12-31T23:59:59.999Z"
            }
        },
        "options": {
            "format": "json",
            "compressed": True,
            "include_metadata": True,
            "include_raw_data": False
        }
    }
    
    with attach_curl_on_fail(ENDPOINT, large_payload, headers, "POST"):
        response = api_client.post(url, headers=headers, json=large_payload)
        assert response.status_code == 200, \
            f"Expected status code 200 for large payload, got {response.status_code}"
        
        if response.content:
            response_data = response.json()
            _check_types_recursive(response_data, SUCCESS_RESPONSE_SCHEMA)

def test_system_report_check_malformed_json(
    api_client, 
    api_base_url, 
    auth_token, 
    attach_curl_on_fail
):
    """
    Тест с некорректным JSON в payload.
    """
    url = f"{api_base_url}{ENDPOINT}"
    headers = {
        "x-access-token": auth_token,
        "Content-Type": "application/json"
    }
    
    malformed_payloads = [
        '{"invalid": json}',
        '{"missing": "quote}',
        '{"extra": "comma",}',
        '{"null": null, "undefined": undefined}'
    ]
    
    for payload in malformed_payloads:
        with attach_curl_on_fail(ENDPOINT, payload, headers, "POST"):
            response = api_client.post(url, headers=headers, data=payload)
            # API должен вернуть ошибку для некорректного JSON
            assert response.status_code in [400, 422], \
                f"Expected status code 400 or 422 for malformed JSON, got {response.status_code}"

def test_system_report_check_unicode_payload(
    api_client, 
    api_base_url, 
    auth_token, 
    attach_curl_on_fail
):
    """
    Тест с Unicode символами в payload.
    """
    url = f"{api_base_url}{ENDPOINT}"
    headers = {
        "x-access-token": auth_token,
        "Content-Type": "application/json"
    }
    
    unicode_payload = {
        "description": "Системный отчет с кириллицей",
        "tags": ["система", "безопасность", "производительность"],
        "notes": "Тест с русскими символами: ёёё ъъъ ыыы"
    }
    
    with attach_curl_on_fail(ENDPOINT, unicode_payload, headers, "POST"):
        response = api_client.post(url, headers=headers, json=unicode_payload)
        assert response.status_code == 200, \
            f"Expected status code 200 for unicode payload, got {response.status_code}"
        
        if response.content:
            response_data = response.json()
            _check_types_recursive(response_data, SUCCESS_RESPONSE_SCHEMA)

def test_system_report_check_special_characters(
    api_client, 
    api_base_url, 
    auth_token, 
    attach_curl_on_fail
):
    """
    Тест со специальными символами в payload.
    """
    url = f"{api_base_url}{ENDPOINT}"
    headers = {
        "x-access-token": auth_token,
        "Content-Type": "application/json"
    }
    
    special_chars_payload = {
        "name": "report_!@#$%^&*()_+-=[]{}|;':\",./<>?",
        "path": "/var/log/system/!@#$%^&*()_+-=[]{}|;':\",./<>?",
        "description": "Report with special chars: !@#$%^&*()_+-=[]{}|;':\",./<>?"
    }
    
    with attach_curl_on_fail(ENDPOINT, special_chars_payload, headers, "POST"):
        response = api_client.post(url, headers=headers, json=special_chars_payload)
        assert response.status_code == 200, \
            f"Expected status code 200 for special chars payload, got {response.status_code}"
        
        if response.content:
            response_data = response.json()
            _check_types_recursive(response_data, SUCCESS_RESPONSE_SCHEMA)

def test_system_report_check_numeric_values(
    api_client, 
    api_base_url, 
    auth_token, 
    attach_curl_on_fail
):
    """
    Тест с различными числовыми значениями.
    """
    url = f"{api_base_url}{ENDPOINT}"
    headers = {
        "x-access-token": auth_token,
        "Content-Type": "application/json"
    }
    
    numeric_payloads = [
        {"priority": 1},
        {"priority": 0},
        {"priority": -1},
        {"priority": 999999},
        {"priority": 3.14159},
        {"priority": 1e6}
    ]
    
    for payload in numeric_payloads:
        with attach_curl_on_fail(ENDPOINT, payload, headers, "POST"):
            response = api_client.post(url, headers=headers, json=payload)
            assert response.status_code == 200, \
                f"Expected status code 200 for numeric payload {payload}, got {response.status_code}"
            
            if response.content:
                response_data = response.json()
                _check_types_recursive(response_data, SUCCESS_RESPONSE_SCHEMA)

def test_system_report_check_boolean_values(
    api_client, 
    api_base_url, 
    auth_token, 
    attach_curl_on_fail
):
    """
    Тест с булевыми значениями.
    """
    url = f"{api_base_url}{ENDPOINT}"
    headers = {
        "x-access-token": auth_token,
        "Content-Type": "application/json"
    }
    
    boolean_payloads = [
        {"enabled": True},
        {"enabled": False},
        {"verbose": True, "quiet": False},
        {"include_debug": False, "include_info": True}
    ]
    
    for payload in boolean_payloads:
        with attach_curl_on_fail(ENDPOINT, payload, headers, "POST"):
            response = api_client.post(url, headers=headers, json=payload)
            assert response.status_code == 200, \
                f"Expected status code 200 for boolean payload {payload}, got {response.status_code}"
            
            if response.content:
                response_data = response.json()
                _check_types_recursive(response_data, SUCCESS_RESPONSE_SCHEMA)

def test_system_report_check_array_values(
    api_client, 
    api_base_url, 
    auth_token, 
    attach_curl_on_fail
):
    """
    Тест с массивами в payload.
    """
    url = f"{api_base_url}{ENDPOINT}"
    headers = {
        "x-access-token": auth_token,
        "Content-Type": "application/json"
    }
    
    array_payloads = [
        {"tags": []},
        {"tags": ["system"]},
        {"tags": ["system", "security", "performance"]},
        {"numbers": [1, 2, 3, 4, 5]},
        {"mixed": ["string", 123, True, None]}
    ]
    
    for payload in array_payloads:
        with attach_curl_on_fail(ENDPOINT, payload, headers, "POST"):
            response = api_client.post(url, headers=headers, json=payload)
            assert response.status_code == 200, \
                f"Expected status code 200 for array payload {payload}, got {response.status_code}"
            
            if response.content:
                response_data = response.json()
                _check_types_recursive(response_data, SUCCESS_RESPONSE_SCHEMA)

def test_system_report_check_nested_objects(
    api_client, 
    api_base_url, 
    auth_token, 
    attach_curl_on_fail
):
    """
    Тест с вложенными объектами в payload.
    """
    url = f"{api_base_url}{ENDPOINT}"
    headers = {
        "x-access-token": auth_token,
        "Content-Type": "application/json"
    }
    
    nested_payloads = [
        {"config": {"level": "debug"}},
        {"config": {"level": "info", "output": {"format": "json"}}},
        {"filters": {"time": {"start": "2024-01-01", "end": "2024-12-31"}}},
        {"options": {"format": "json", "compression": {"enabled": True, "level": 9}}}
    ]
    
    for payload in nested_payloads:
        with attach_curl_on_fail(ENDPOINT, payload, headers, "POST"):
            response = api_client.post(url, headers=headers, json=payload)
            assert response.status_code == 200, \
                f"Expected status code 200 for nested payload {payload}, got {response.status_code}"
            
            if response.content:
                response_data = response.json()
                _check_types_recursive(response_data, SUCCESS_RESPONSE_SCHEMA)

def test_system_report_check_null_values(
    api_client, 
    api_base_url, 
    auth_token, 
    attach_curl_on_fail
):
    """
    Тест с null значениями в payload.
    """
    url = f"{api_base_url}{ENDPOINT}"
    headers = {
        "x-access-token": auth_token,
        "Content-Type": "application/json"
    }
    
    null_payloads = [
        {"optional_field": None},
        {"field1": None, "field2": "value"},
        {"nested": {"field": None}},
        {"array": [None, "value", None]}
    ]
    
    for payload in null_payloads:
        with attach_curl_on_fail(ENDPOINT, payload, headers, "POST"):
            response = api_client.post(url, headers=headers, json=payload)
            assert response.status_code == 200, \
                f"Expected status code 200 for null payload {payload}, got {response.status_code}"
            
            if response.content:
                response_data = response.json()
                _check_types_recursive(response_data, SUCCESS_RESPONSE_SCHEMA)

def test_system_report_check_very_long_strings(
    api_client, 
    api_base_url, 
    auth_token, 
    attach_curl_on_fail
):
    """
    Тест с очень длинными строками.
    """
    url = f"{api_base_url}{ENDPOINT}"
    headers = {
        "x-access-token": auth_token,
        "Content-Type": "application/json"
    }
    
    long_string_payloads = [
        {"description": "A" * 1000},
        {"description": "B" * 10000},
        {"path": "/very/long/path/" + "x" * 500},
        {"comment": "Long comment " * 100}
    ]
    
    for payload in long_string_payloads:
        with attach_curl_on_fail(ENDPOINT, payload, headers, "POST"):
            response = api_client.post(url, headers=headers, json=payload)
            # API может принять длинные строки или вернуть ошибку
            assert response.status_code in [200, 400, 413], \
                f"Unexpected status code {response.status_code} for long string payload"
            
            if response.status_code == 200 and response.content:
                response_data = response.json()
                _check_types_recursive(response_data, SUCCESS_RESPONSE_SCHEMA)

def test_system_report_check_very_large_numbers(
    api_client, 
    api_base_url, 
    auth_token, 
    attach_curl_on_fail
):
    """
    Тест с очень большими числами.
    """
    url = f"{api_base_url}{ENDPOINT}"
    headers = {
        "x-access-token": auth_token,
        "Content-Type": "application/json"
    }
    
    large_number_payloads = [
        {"id": 999999999999999999},
        {"timestamp": 1704067200000},
        {"size": 1e15},
        {"count": 2**63 - 1}
    ]
    
    for payload in large_number_payloads:
        with attach_curl_on_fail(ENDPOINT, payload, headers, "POST"):
            response = api_client.post(url, headers=headers, json=payload)
            assert response.status_code == 200, \
                f"Expected status code 200 for large number payload {payload}, got {response.status_code}"
            
            if response.content:
                response_data = response.json()
                _check_types_recursive(response_data, SUCCESS_RESPONSE_SCHEMA)

def test_system_report_check_date_formats(
    api_client, 
    api_base_url, 
    auth_token, 
    attach_curl_on_fail
):
    """
    Тест с различными форматами дат.
    """
    url = f"{api_base_url}{ENDPOINT}"
    headers = {
        "x-access-token": auth_token,
        "Content-Type": "application/json"
    }
    
    date_payloads = [
        {"start_date": "2024-01-01"},
        {"start_date": "2024-01-01T00:00:00Z"},
        {"start_date": "2024-01-01T00:00:00.000Z"},
        {"start_date": "2024-01-01T00:00:00+00:00"},
        {"start_date": "2024-01-01T00:00:00.000+00:00"}
    ]
    
    for payload in date_payloads:
        with attach_curl_on_fail(ENDPOINT, payload, headers, "POST"):
            response = api_client.post(url, headers=headers, json=payload)
            assert response.status_code == 200, \
                f"Expected status code 200 for date payload {payload}, got {response.status_code}"
            
            if response.content:
                response_data = response.json()
                _check_types_recursive(response_data, SUCCESS_RESPONSE_SCHEMA)

def test_system_report_check_duplicate_keys(
    api_client, 
    api_base_url, 
    auth_token, 
    attach_curl_on_fail
):
    """
    Тест с дублирующимися ключами в JSON.
    """
    url = f"{api_base_url}{ENDPOINT}"
    headers = {
        "x-access-token": auth_token,
        "Content-Type": "application/json"
    }
    
    # JSON с дублирующимися ключами (последний должен перезаписать предыдущий)
    duplicate_keys_payload = '{"key": "first", "key": "second", "key": "final"}'
    
    with attach_curl_on_fail(ENDPOINT, duplicate_keys_payload, headers, "POST"):
        response = api_client.post(url, headers=headers, data=duplicate_keys_payload)
        # API может принять такой JSON или вернуть ошибку
        assert response.status_code in [200, 400, 422], \
            f"Unexpected status code {response.status_code} for duplicate keys payload"
        
        if response.status_code == 200 and response.content:
            response_data = response.json()
            _check_types_recursive(response_data, SUCCESS_RESPONSE_SCHEMA)

def test_system_report_check_extra_headers(
    api_client, 
    api_base_url, 
    auth_token, 
    attach_curl_on_fail
):
    """
    Тест с дополнительными заголовками.
    """
    url = f"{api_base_url}{ENDPOINT}"
    headers = {
        "x-access-token": auth_token,
        "Content-Type": "application/json",
        "X-Custom-Header": "custom-value",
        "X-Request-ID": "test-12345",
        "X-Client-Version": "1.0.0",
        "Accept-Language": "en-US,en;q=0.9",
        "Cache-Control": "no-cache"
    }
    
    with attach_curl_on_fail(ENDPOINT, None, headers, "POST"):
        response = api_client.post(url, headers=headers)
        assert response.status_code == 200, \
            f"Expected status code 200 with extra headers, got {response.status_code}"
        
        if response.content:
            response_data = response.json()
            _check_types_recursive(response_data, SUCCESS_RESPONSE_SCHEMA)

def test_system_report_check_response_time(
    api_client, 
    api_base_url, 
    auth_token, 
    attach_curl_on_fail
):
    """
    Тест времени ответа API.
    """
    url = f"{api_base_url}{ENDPOINT}"
    headers = {
        "x-access-token": auth_token,
        "Content-Type": "application/json"
    }
    
    import time
    
    with attach_curl_on_fail(ENDPOINT, None, headers, "POST"):
        start_time = time.time()
        response = api_client.post(url, headers=headers)
        end_time = time.time()
        
        response_time = end_time - start_time
        
        assert response.status_code == 200, \
            f"Expected status code 200, got {response.status_code}"
        
        # Проверяем, что ответ получен в разумное время (менее 30 секунд)
        assert response_time < 30, \
            f"Response time {response_time:.2f}s is too slow (expected < 30s)"
        
        if response.content:
            response_data = response.json()
            _check_types_recursive(response_data, SUCCESS_RESPONSE_SCHEMA)

def test_system_report_check_concurrent_requests(
    api_client, 
    api_base_url, 
    auth_token, 
    attach_curl_on_fail
):
    """
    Тест с одновременными запросами.
    """
    url = f"{api_base_url}{ENDPOINT}"
    headers = {
        "x-access-token": auth_token,
        "Content-Type": "application/json"
    }
    
    import threading
    import time
    
    results = []
    errors = []
    
    def make_request():
        try:
            response = api_client.post(url, headers=headers)
            results.append(response.status_code)
        except Exception as e:
            errors.append(str(e))
    
    with attach_curl_on_fail(ENDPOINT, None, headers, "POST"):
        # Создаем 5 потоков для одновременных запросов
        threads = []
        for i in range(5):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()
        
        # Ждем завершения всех потоков
        for thread in threads:
            thread.join()
        
        # Проверяем, что все запросы выполнены
        assert len(results) == 5, f"Expected 5 responses, got {len(results)}"
        assert len(errors) == 0, f"Expected no errors, got {errors}"
        
        # Проверяем, что все ответы успешны
        for status_code in results:
            assert status_code == 200, f"Expected status code 200, got {status_code}"



# -------------------- New parameterized POST tests (add-only) --------------------

@pytest.mark.parametrize("payload", [
    pytest.param({"report_type": "system"}, id="type-system"),
    pytest.param({"report_type": "security", "include_logs": True}, id="type-security-with-logs"),
    pytest.param({"report_type": "performance", "timeframe": "1h"}, id="type-performance-1h"),
    pytest.param({"filters": {"severity": "low"}}, id="filters-severity-low"),
    pytest.param({"filters": {"severity": "high", "component": "network"}}, id="filters-severity-high-network"),
    pytest.param({"options": {"format": "json"}}, id="options-format-json"),
    pytest.param({"options": {"format": "json", "compressed": False}}, id="options-format-json-uncompressed"),
    pytest.param({"metadata": {"request_id": "req-123", "source": "qa"}}, id="metadata-basic"),
    pytest.param({"filters": {"time": {"start": "2024-01-01", "end": "2024-01-31"}}}, id="filters-time-range"),
    pytest.param({"tags": ["system", "security"]}, id="tags-array"),
])
def test_system_report_check_positive_cases(api_client, api_base_url, auth_token, attach_curl_on_fail, agent_verification, payload):
    url = f"{api_base_url}{ENDPOINT}"
    headers = {"x-access-token": auth_token, "Content-Type": "application/json"}
    with attach_curl_on_fail(ENDPOINT, payload, headers, "POST"):
        response = api_client.post(url, headers=headers, json=payload)
        assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}"
        print("Validation: main API returned 200 OK — proceeding to agent verification")
        if response.content:
            data = response.json()
            _check_types_recursive(data, SUCCESS_RESPONSE_SCHEMA)
            print("Validation: response schema OK — continue")

        # Дополнительная проверка через агента: отправляем то же тело, что и в основной API
        agent_result = agent_verification(ENDPOINT, payload)
        if agent_result == "unavailable":
            print("Warning: агент недоступен — тест не пропускается и должен упасть")
            pytest.fail("Agent verification: AGENT UNAVAILABLE - system-report/check verification failed due to agent unavailability")
        elif isinstance(agent_result, dict) and agent_result.get("result") == "OK":
            print("Agent verification: SUCCESS — OK")
        elif isinstance(agent_result, dict) and agent_result.get("result") == "ERROR":
            message = agent_result.get("message", "Unknown error")
            pytest.fail(f"Agent verification: ERROR - system-report/check verification failed: {message}")
        else:
            pytest.fail(f"Agent verification: UNEXPECTED RESULT {agent_result}")


@pytest.mark.parametrize("payload,headers,expected_status,id_str", [
    # no auth token
    pytest.param({"report_type": "system"}, {"Content-Type": "application/json"}, 401, "no-auth-token", id="no-auth-token"),
    # invalid JSON strings
    pytest.param('{"broken": }', {"Content-Type": "application/json"}, 400, "invalid-json-1", id="invalid-json-1"),
    pytest.param('{"a":"b",}', {"Content-Type": "application/json"}, 400, "invalid-json-2", id="invalid-json-2"),
    # non-JSON bodies
    pytest.param('just text', {"Content-Type": "application/json"}, 400, "plain-text-body", id="plain-text-body"),
    pytest.param('', {"Content-Type": "application/json"}, 401, "empty-body", id="empty-body"),
    # wrong content-type
    pytest.param({"report_type": "system"}, {"x-access-token": "token_placeholder", "Content-Type": "text/plain"}, 200, "wrong-content-type", id="wrong-content-type"),
    # top-level array instead of object
    pytest.param(["not", "an", "object"], {"Content-Type": "application/json"}, 401, "array-body", id="array-body-no-auth"),
    # null as body
    pytest.param('null', {"Content-Type": "application/json"}, 400, "null-body", id="null-body"),
])
def test_system_report_check_negative_cases(api_client, api_base_url, auth_token, attach_curl_on_fail, payload, headers, expected_status, id_str):
    url = f"{api_base_url}{ENDPOINT}"
    # Inject real token where placeholder is used
    if headers.get("x-access-token") == "token_placeholder":
        headers["x-access-token"] = auth_token
    with attach_curl_on_fail(ENDPOINT, payload, headers, "POST"):
        if isinstance(payload, str) or isinstance(payload, list):
            response = api_client.post(url, headers=headers, data=payload if isinstance(payload, str) else json.dumps(payload))
        else:
            response = api_client.post(url, headers=headers, json=payload)
        assert response.status_code == expected_status, f"Expected {expected_status}, got {response.status_code}"


@pytest.mark.parametrize("payload", [
    pytest.param({"report_type": "health", "details": True}, id="type-health-details"),
    pytest.param({"options": {"format": "json", "compressed": True, "pretty": True}}, id="options-format-json-compressed-pretty"),
    pytest.param({"filters": {"component": "storage", "severity": ["medium", "high"]}}, id="filters-component-storage-severity-list"),
    pytest.param({"report_type": "audit", "user": "qa-bot"}, id="type-audit-user"),
    pytest.param({"context": {"env": "staging", "trace_id": "abc-123"}}, id="context-env-trace"),
])
def test_system_report_check_more_positive_cases(api_client, api_base_url, auth_token, attach_curl_on_fail, agent_verification, payload):
    url = f"{api_base_url}{ENDPOINT}"
    headers = {"x-access-token": auth_token, "Content-Type": "application/json"}
    with attach_curl_on_fail(ENDPOINT, payload, headers, "POST"):
        response = api_client.post(url, headers=headers, json=payload)
        assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}"
        print("Validation: main API returned 200 OK — proceeding to agent verification")
        if response.content:
            data = response.json()
            _check_types_recursive(data, SUCCESS_RESPONSE_SCHEMA)
            print("Validation: response schema OK — continue")

        # Дополнительная проверка через агента: отправляем то же тело, что и в основной API
        agent_result = agent_verification(ENDPOINT, payload)
        if agent_result == "unavailable":
            print("Warning: агент недоступен — тест не пропускается и должен упасть")
            pytest.fail("Agent verification: AGENT UNAVAILABLE - system-report/check verification failed due to agent unavailability")
        elif isinstance(agent_result, dict) and agent_result.get("result") == "OK":
            print("Agent verification: SUCCESS — OK")
        elif isinstance(agent_result, dict) and agent_result.get("result") == "ERROR":
            message = agent_result.get("message", "Unknown error")
            pytest.fail(f"Agent verification: ERROR - system-report/check verification failed: {message}")
        else:
            pytest.fail(f"Agent verification: UNEXPECTED RESULT {agent_result}")


@pytest.mark.parametrize("payload,headers,expected_status,id_str", [
    pytest.param('{}', {"Content-Type": "text/plain"}, 401, "json-in-text-ct", id="json-in-text-ct"),
    pytest.param('123', {"Content-Type": "application/json"}, 400, "numeric-body", id="numeric-body"),
    pytest.param('[1,2,3]', {"x-access-token": "token_placeholder", "Content-Type": "application/json"}, 200, "array-body-auth", id="array-body-auth"),
    pytest.param({"report_type": "system"}, {"x-access-token": "invalid_token!!", "Content-Type": "application/json"}, 401, "bad-token-format", id="bad-token-format"),
    pytest.param({"report_type": "x"}, {"x-access-token": "token_placeholder", "Content-Type": "application/octet-stream"}, 200, "octet-stream", id="octet-stream"),
    pytest.param('{"report_type":}', {"x-access-token": "token_placeholder", "Content-Type": "application/json"}, 400, "missing-value", id="missing-value"),
    pytest.param('"string"', {"x-access-token": "token_placeholder", "Content-Type": "application/json"}, 400, "string-body", id="string-body"),
])
def test_system_report_check_more_negative_cases(api_client, api_base_url, auth_token, attach_curl_on_fail, payload, headers, expected_status, id_str):
    url = f"{api_base_url}{ENDPOINT}"
    if headers.get("x-access-token") == "token_placeholder":
        headers["x-access-token"] = auth_token
    with attach_curl_on_fail(ENDPOINT, payload, headers, "POST"):
        if isinstance(payload, str) or isinstance(payload, list):
            response = api_client.post(url, headers=headers, data=payload if isinstance(payload, str) else json.dumps(payload))
        else:
            response = api_client.post(url, headers=headers, json=payload)
        assert response.status_code == expected_status, f"Expected {expected_status}, got {response.status_code}"
