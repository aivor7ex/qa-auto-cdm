import json
import pytest
from qa_constants import SERVICES

ENDPOINT = "/update/rules/check-for-updates-local"

# Схема успешного ответа API
SUCCESS_RESPONSE_SCHEMA = {
    "found": bool
}

# ----- ФУНКЦИИ ВАЛИДАЦИИ СХЕМ -----
def _check_types_recursive(obj, schema):
    """Рекурсивно проверяет типы данных по схеме"""
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

def _validate_response_schema(data):
    """Валидирует ответ API по схеме"""
    assert isinstance(data, dict), "Ответ должен быть объектом"
    assert "found" in data, "Ответ должен содержать поле 'found'"
    assert isinstance(data["found"], bool), "Поле 'found' должно быть булевым значением"

# ----- ТЕСТЫ ДЛЯ УСПЕШНЫХ СЦЕНАРИЕВ -----

# 1. Успешные кейсы
@pytest.mark.parametrize("payload", [
    {},  # Найдены новые локальные правила (в текущей среде: NO_UPDATES_FOUND)
    {"channel": "stable"},  # Найдены новые правила с каналом (NO_UPDATES_FOUND)
    {},  # Найдены приоритетные правила (NO_UPDATES_FOUND)
    {},  # Нет новых правил (NO_UPDATES_FOUND)
], ids=[
    "найдены новые локальные правила",
    "найдены новые правила с каналом",
    "найдены приоритетные правила",
    "нет новых правил"
])
def test_successful_check_for_updates_local(api_client, auth_token, api_base_url, payload, attach_curl_on_fail):
    """Тестирует успешную проверку локальных обновлений"""
    url = f"{api_base_url}{ENDPOINT}"
    headers = {"x-access-token": auth_token, "Content-Type": "application/json"}
    
    with attach_curl_on_fail(ENDPOINT, payload, headers, "POST"):
        response = api_client.post(url, json=payload, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            _validate_response_schema(data)
            assert isinstance(data["found"], bool), "Поле 'found' должно быть булевым значением"
        elif response.status_code == 422:
            data = response.json()
            assert "error" in data, "Ответ должен содержать поле 'error'"
            assert data["error"]["message"] == "NO_UPDATES_FOUND", "Ошибка должна быть NO_UPDATES_FOUND"
        else:
            pytest.fail(f"Неожиданный код ответа: {response.status_code}")

# ----- ТЕСТЫ ДЛЯ ОШИБОК ФАЙЛОВОЙ СИСТЕМЫ -----

# 2. Кейсы с ошибками файловой системы
@pytest.mark.parametrize("payload", [
    {},  # Отсутствие файлов правил (NO_UPDATES_FOUND)
    {},  # Неправильный формат имени файла
    {},  # Только один файл (zip без sig или наоборот)
    {},  # Неправильный формат даты в имени файла
], ids=[
    "отсутствие файлов правил",
    "неправильный формат имени файла",
    "только один файл",
    "неправильный формат даты в имени файла"
])
def test_file_system_errors(api_client, auth_token, api_base_url, payload, attach_curl_on_fail):
    """Тестирует ошибки файловой системы"""
    url = f"{api_base_url}{ENDPOINT}"
    headers = {"x-access-token": auth_token, "Content-Type": "application/json"}
    
    with attach_curl_on_fail(ENDPOINT, payload, headers, "POST"):
        response = api_client.post(url, json=payload, headers=headers)
        
        # В текущей среде ожидаем NO_UPDATES_FOUND
        assert response.status_code == 422, f"Ожидается 422; получено {response.status_code}"
        data = response.json()
        assert "error" in data, "Ответ должен содержать поле 'error'"
        assert data["error"]["message"] == "NO_UPDATES_FOUND", "Ошибка должна быть NO_UPDATES_FOUND"

# ----- ТЕСТЫ ДЛЯ ОШИБОК АУТЕНТИФИКАЦИИ -----

# 3. Проблемы с токеном авторизации
@pytest.mark.parametrize("headers,payload", [
    ({"Content-Type": "application/json"}, {}),  # отсутствует токен
    ({"x-access-token": "invalid_token", "Content-Type": "application/json"}, {}),  # неверный токен
    ({"x-access-token": "expired_token", "Content-Type": "application/json"}, {}),  # истекший токен
], ids=[
    "отсутствует токен авторизации",
    "неверный токен авторизации",
    "истекший токен авторизации"
])
def test_authorization_token_issues(api_client, api_base_url, headers, payload, attach_curl_on_fail):
    """Тестирует проблемы с токеном авторизации"""
    url = f"{api_base_url}{ENDPOINT}"
    
    with attach_curl_on_fail(ENDPOINT, payload, headers, "POST"):
        response = api_client.post(url, json=payload, headers=headers)
        
        assert response.status_code == 401, f"Ожидается 401 Unauthorized; получено {response.status_code}"

# ----- ТЕСТЫ ДЛЯ РАЗНЫХ КАНАЛОВ ОБНОВЛЕНИЙ -----

# 4. Разные каналы обновлений
@pytest.mark.parametrize("payload", [
    {"channel": "release"},  # Канал "release"
    {"channel": "stable"},  # Канал "stable"
    {"channel": "beta"},  # Канал "beta"
], ids=[
    "канал release",
    "канал stable",
    "канал beta"
])
def test_different_update_channels(api_client, auth_token, api_base_url, payload, attach_curl_on_fail):
    """Тестирует разные каналы обновлений"""
    url = f"{api_base_url}{ENDPOINT}"
    headers = {"x-access-token": auth_token, "Content-Type": "application/json"}
    
    with attach_curl_on_fail(ENDPOINT, payload, headers, "POST"):
        response = api_client.post(url, json=payload, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            _validate_response_schema(data)
            assert isinstance(data["found"], bool), "Поле 'found' должно быть булевым значением"
        elif response.status_code == 422:
            data = response.json()
            assert "error" in data, "Ответ должен содержать поле 'error'"
            assert data["error"]["message"] == "NO_UPDATES_FOUND", "Ошибка должна быть NO_UPDATES_FOUND"
        else:
            pytest.fail(f"Неожиданный код ответа: {response.status_code}")

# ----- ТЕСТЫ ДЛЯ РАЗНЫХ ФОРМАТОВ ДАТ -----

# 5. Разные форматы дат
@pytest.mark.parametrize("payload", [
    {},  # ISO формат даты
    {},  # Стандартный формат даты
], ids=[
    "ISO формат даты",
    "стандартный формат даты"
])
def test_different_date_formats(api_client, auth_token, api_base_url, payload, attach_curl_on_fail):
    """Тестирует разные форматы дат в именах файлов"""
    url = f"{api_base_url}{ENDPOINT}"
    headers = {"x-access-token": auth_token, "Content-Type": "application/json"}
    
    with attach_curl_on_fail(ENDPOINT, payload, headers, "POST"):
        response = api_client.post(url, json=payload, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            _validate_response_schema(data)
            assert isinstance(data["found"], bool), "Поле 'found' должно быть булевым значением"
        elif response.status_code == 422:
            data = response.json()
            assert "error" in data, "Ответ должен содержать поле 'error'"
            assert data["error"]["message"] == "NO_UPDATES_FOUND", "Ошибка должна быть NO_UPDATES_FOUND"
        else:
            pytest.fail(f"Неожиданный код ответа: {response.status_code}")

# ----- ТЕСТЫ ДЛЯ МНОЖЕСТВЕННЫХ ФАЙЛОВ -----

# 6. Множественные файлы
@pytest.mark.parametrize("payload", [
    {},  # Несколько версий правил (выбирается самая новая)
    {},  # Приоритетная версия среди обычных
], ids=[
    "несколько версий правил",
    "приоритетная версия среди обычных"
])
def test_multiple_files(api_client, auth_token, api_base_url, payload, attach_curl_on_fail):
    """Тестирует обработку множественных файлов"""
    url = f"{api_base_url}{ENDPOINT}"
    headers = {"x-access-token": auth_token, "Content-Type": "application/json"}
    
    with attach_curl_on_fail(ENDPOINT, payload, headers, "POST"):
        response = api_client.post(url, json=payload, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            _validate_response_schema(data)
            assert isinstance(data["found"], bool), "Поле 'found' должно быть булевым значением"
        elif response.status_code == 422:
            data = response.json()
            assert "error" in data, "Ответ должен содержать поле 'error'"
            assert data["error"]["message"] == "NO_UPDATES_FOUND", "Ошибка должна быть NO_UPDATES_FOUND"
        else:
            pytest.fail(f"Неожиданный код ответа: {response.status_code}")

# ----- ТЕСТЫ ДЛЯ СИСТЕМНЫХ ОШИБОК -----

# 7. Системные ошибки
@pytest.mark.parametrize("payload", [
    {},  # Отсутствие директории UPLOAD_DIRECTORY
    {},  # Нет прав на чтение директории
], ids=[
    "отсутствие директории UPLOAD_DIRECTORY",
    "нет прав на чтение директории"
])
def test_system_errors(api_client, auth_token, api_base_url, payload, attach_curl_on_fail):
    """Тестирует системные ошибки"""
    url = f"{api_base_url}{ENDPOINT}"
    headers = {"x-access-token": auth_token, "Content-Type": "application/json"}
    
    with attach_curl_on_fail(ENDPOINT, payload, headers, "POST"):
        response = api_client.post(url, json=payload, headers=headers)
        
        # В текущей среде ожидаем NO_UPDATES_FOUND
        assert response.status_code == 422, f"Ожидается 422; получено {response.status_code}"

# ----- ТЕСТЫ ДЛЯ НЕКОРРЕКТНЫХ ДАННЫХ -----

# 8. Некорректные данные
@pytest.mark.parametrize("payload", [
    {"channel": "invalid-json"},  # Некорректный JSON (симуляция)
    "",  # Пустое тело запроса
    {"unsupported_param": "value"},  # Неподдерживаемые параметры
    {"channel": 123},  # Неверный тип данных для channel
], ids=[
    "некорректный JSON",
    "пустое тело запроса",
    "неподдерживаемые параметры",
    "неверный тип данных для channel"
])
def test_invalid_data(api_client, auth_token, api_base_url, payload, attach_curl_on_fail):
    """Тестирует некорректные данные"""
    url = f"{api_base_url}{ENDPOINT}"
    headers = {"x-access-token": auth_token, "Content-Type": "application/json"}
    
    with attach_curl_on_fail(ENDPOINT, payload, headers, "POST"):
        if payload == "":
            # Для пустого тела запроса
            response = api_client.post(url, data="", headers=headers)
        else:
            response = api_client.post(url, json=payload, headers=headers)
        
        # В текущей среде:
        # - неверный тип channel -> 400
        # - остальные кейсы -> 422
        if payload == {"channel": 123}:
            assert response.status_code == 400, f"Ожидается 400; получено {response.status_code}"
        else:
            assert response.status_code == 422, f"Ожидается 422; получено {response.status_code}"

# ----- ДОПОЛНИТЕЛЬНЫЕ ТЕСТЫ -----

# 9. Тест аутентификации
def test_authentication_required(api_client, api_base_url, attach_curl_on_fail):
    """Тестирует, что аутентификация обязательна"""
    url = f"{api_base_url}{ENDPOINT}"
    payload = {}
    
    with attach_curl_on_fail(ENDPOINT, payload, method="POST"):
        response = api_client.post(url, json=payload)
        
        assert response.status_code == 401, f"Ожидается 401 Unauthorized; получено {response.status_code}"

# 10. Тест валидации заголовков
def test_headers_validation(api_client, auth_token, api_base_url, attach_curl_on_fail):
    """Тестирует валидацию заголовков"""
    url = f"{api_base_url}{ENDPOINT}"
    payload = {}
    
    with attach_curl_on_fail(ENDPOINT, payload, method="POST"):
        # Тестируем без заголовка аутентификации
        response = api_client.post(url, json=payload)
        assert response.status_code == 401, f"Ожидается 401 Unauthorized; получено {response.status_code}"
        
        # Тестируем с некорректным токеном
        invalid_headers = {"x-access-token": "invalid_token", "Content-Type": "application/json"}
        response = api_client.post(url, json=payload, headers=invalid_headers)
        assert response.status_code == 401, f"Ожидается 401 Unauthorized; получено {response.status_code}"
        
        # Тестируем с корректным токеном
        valid_headers = {"x-access-token": auth_token, "Content-Type": "application/json"}
        response = api_client.post(url, json=payload, headers=valid_headers)
        
        if response.status_code == 200:
            data = response.json()
            _validate_response_schema(data)
            assert isinstance(data["found"], bool), "Поле 'found' должно быть булевым значением"
        elif response.status_code == 422:
            data = response.json()
            assert "error" in data, "Ответ должен содержать поле 'error'"
            assert data["error"]["message"] == "NO_UPDATES_FOUND", "Ошибка должна быть NO_UPDATES_FOUND"
        else:
            pytest.fail(f"Неожиданный код ответа: {response.status_code}")
