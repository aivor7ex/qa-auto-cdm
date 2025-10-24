import json
import pytest
from qa_constants import SERVICES

ENDPOINT = "/update/rules/check-for-updates"

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

# 1. Успешные сценарии
@pytest.mark.parametrize("payload,expected_found", [
    ({"login": "test", "password": "JDlmRGPq", "channel": "release"}, True),
    ({"login": "test", "password": "JDlmRGPq", "channel": "release"}, False),
    ({"login": "test", "password": "JDlmRGPq", "channel": "beta"}, True),
    ({"login": "test", "password": "JDlmRGPq", "channel": "alpha"}, True),
    ({"login": "test", "password": "JDlmRGPq", "channel": "dev"}, True),
    ({"login": "test", "password": "JDlmRGPq"}, True),  # без channel (по умолчанию release)
], ids=[
    "валидные данные, канал release, найдены обновления",
    "валидные данные, канал release, обновлений нет", 
    "канал beta",
    "канал alpha",
    "канал dev",
    "без указания канала (по умолчанию release)"
])
def test_successful_check_for_updates(api_client, auth_token, api_base_url, payload, expected_found, attach_curl_on_fail):
    """Тестирует успешную проверку обновлений"""
    url = f"{api_base_url}{ENDPOINT}"
    headers = {"x-access-token": auth_token, "Content-Type": "application/json"}
    
    with attach_curl_on_fail(ENDPOINT, payload, headers, "POST"):
        response = api_client.post(url, json=payload, headers=headers)
        
        assert response.status_code == 200, f"Ожидается 200 OK; получено {response.status_code}"
        
        data = response.json()
        _validate_response_schema(data)
        assert isinstance(data["found"], bool), "Поле 'found' должно быть булевым значением"

# ----- ТЕСТЫ ДЛЯ ОШИБОК ВАЛИДАЦИИ ПАРАМЕТРОВ -----

# 2. Отсутствующие обязательные параметры
@pytest.mark.parametrize("payload", [
    {"password": "JDlmRGPq", "channel": "release"},  # отсутствует login
    {"login": "test", "channel": "release"},  # отсутствует password
    {"channel": "release"},  # отсутствуют login и password
    {}  # пустое тело запроса
], ids=[
    "отсутствует login",
    "отсутствует password", 
    "отсутствуют login и password",
    "пустое тело запроса"
])
def test_missing_required_parameters(api_client, auth_token, api_base_url, payload, attach_curl_on_fail):
    """Тестирует ошибки при отсутствии обязательных параметров"""
    url = f"{api_base_url}{ENDPOINT}"
    headers = {"x-access-token": auth_token, "Content-Type": "application/json"}
    
    with attach_curl_on_fail(ENDPOINT, payload, headers, "POST"):
        response = api_client.post(url, json=payload, headers=headers)
        
        assert response.status_code == 400, f"Ожидается 400; получено {response.status_code}"

# 3. Неверные типы данных
@pytest.mark.parametrize("payload", [
    {"login": 123, "password": "JDlmRGPq", "channel": "release"},  # login не строка
    {"login": "test", "password": 123, "channel": "release"},  # password не строка
    {"login": "test", "password": "JDlmRGPq", "channel": 123}  # channel не строка
], ids=[
    "login не строка",
    "password не строка",
    "channel не строка"
])
def test_invalid_parameter_types(api_client, auth_token, api_base_url, payload, attach_curl_on_fail):
    """Тестирует ошибки при неверных типах данных"""
    url = f"{api_base_url}{ENDPOINT}"
    headers = {"x-access-token": auth_token, "Content-Type": "application/json"}
    
    with attach_curl_on_fail(ENDPOINT, payload, headers, "POST"):
        response = api_client.post(url, json=payload, headers=headers)
        
        assert response.status_code == 400, f"Ожидается 400; получено {response.status_code}"

# 4. Пустые значения
@pytest.mark.parametrize("payload,expected_status", [
    ({"login": "", "password": "JDlmRGPq", "channel": "release"}, 400),  # пустой login
    ({"login": "test", "password": "", "channel": "release"}, 400),  # пустой password
    ({"login": "test", "password": "JDlmRGPq", "channel": ""}, 200)  # пустой channel
], ids=[
    "пустой login",
    "пустой password",
    "пустой channel"
])
def test_empty_parameter_values(api_client, auth_token, api_base_url, payload, expected_status, attach_curl_on_fail):
    """Тестирует ошибки при пустых значениях параметров"""
    url = f"{api_base_url}{ENDPOINT}"
    headers = {"x-access-token": auth_token, "Content-Type": "application/json"}
    
    with attach_curl_on_fail(ENDPOINT, payload, headers, "POST"):
        response = api_client.post(url, json=payload, headers=headers)
        
        assert response.status_code == expected_status, f"Ожидается {expected_status}; получено {response.status_code}"

# ----- ТЕСТЫ ДЛЯ ОШИБОК АУТЕНТИФИКАЦИИ -----

# 5. Неверные учетные данные
@pytest.mark.parametrize("payload", [
    {"login": "invalid_user", "password": "JDlmRGPq", "channel": "release"},  # неверный login
    {"login": "test", "password": "invalid_password", "channel": "release"},  # неверный password
    {"login": "invalid_user", "password": "invalid_password", "channel": "release"}  # неверные login и password
], ids=[
    "неверный login",
    "неверный password",
    "неверные login и password"
])
def test_invalid_credentials(api_client, auth_token, api_base_url, payload, attach_curl_on_fail):
    """Тестирует ошибки при неверных учетных данных"""
    url = f"{api_base_url}{ENDPOINT}"
    headers = {"x-access-token": auth_token, "Content-Type": "application/json"}
    
    with attach_curl_on_fail(ENDPOINT, payload, headers, "POST"):
        response = api_client.post(url, json=payload, headers=headers)
        
        assert response.status_code == 401, f"Ожидается 401; получено {response.status_code}"

# 6. Проблемы с токеном авторизации
@pytest.mark.parametrize("headers,payload", [
    ({"Content-Type": "application/json"}, {"login": "test", "password": "JDlmRGPq", "channel": "release"}),  # отсутствует токен
    ({"x-access-token": "invalid_token", "Content-Type": "application/json"}, {"login": "test", "password": "JDlmRGPq", "channel": "release"}),  # неверный токен
    ({"x-access-token": "expired_token", "Content-Type": "application/json"}, {"login": "test", "password": "JDlmRGPq", "channel": "release"})  # истекший токен
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
        
        assert response.status_code == 401, f"Ожидается 401; получено {response.status_code}"

# ----- ТЕСТЫ ДЛЯ ОШИБОК КОНФИГУРАЦИИ СЕРВЕРА -----

# 7. Проблемы с переменными окружения
@pytest.mark.parametrize("payload", [
    {"login": "test", "password": "JDlmRGPq", "channel": "release"}
], ids=["проблемы с конфигурацией сервера"])
def test_server_configuration_issues(api_client, auth_token, api_base_url, payload, attach_curl_on_fail):
    """Тестирует проблемы с конфигурацией сервера"""
    url = f"{api_base_url}{ENDPOINT}"
    headers = {"x-access-token": auth_token, "Content-Type": "application/json"}
    
    with attach_curl_on_fail(ENDPOINT, payload, headers, "POST"):
        response = api_client.post(url, json=payload, headers=headers)
        
        assert response.status_code == 200, f"Ожидается 200; получено {response.status_code}"

# ----- ТЕСТЫ ДЛЯ ОШИБОК СЕТИ И СЕРВЕРА ОБНОВЛЕНИЙ -----

# 8. Проблемы с доступностью сервера обновлений
@pytest.mark.parametrize("payload", [
    {"login": "test", "password": "JDlmRGPq", "channel": "release"},
    {"login": "test", "password": "JDlmRGPq", "channel": "nonexistent_channel"}
], ids=[
    "сервер обновлений недоступен",
    "сервер обновлений возвращает 404"
])
def test_update_server_issues(api_client, auth_token, api_base_url, payload, attach_curl_on_fail):
    """Тестирует проблемы с сервером обновлений"""
    url = f"{api_base_url}{ENDPOINT}"
    headers = {"x-access-token": auth_token, "Content-Type": "application/json"}
    
    with attach_curl_on_fail(ENDPOINT, payload, headers, "POST"):
        response = api_client.post(url, json=payload, headers=headers)
        
        assert response.status_code == 200, f"Ожидается 200; получено {response.status_code}"

# ----- ТЕСТЫ ДЛЯ ОШИБОК ВАЛИДАЦИИ МАНИФЕСТА -----

# 9. Неверный формат манифеста
@pytest.mark.parametrize("payload", [
    {"login": "test", "password": "JDlmRGPq", "channel": "release"}
], ids=[
    "проверка манифеста с валидными учетными данными"
])
def test_manifest_validation_errors(api_client, auth_token, api_base_url, payload, attach_curl_on_fail):
    """Тестирует ошибки валидации манифеста"""
    url = f"{api_base_url}{ENDPOINT}"
    headers = {"x-access-token": auth_token, "Content-Type": "application/json"}
    
    with attach_curl_on_fail(ENDPOINT, payload, headers, "POST"):
        response = api_client.post(url, json=payload, headers=headers)
        
        assert response.status_code == 200, f"Ожидается 200; получено {response.status_code}"

# ----- ТЕСТЫ ДЛЯ ГРАНИЧНЫХ СЛУЧАЕВ -----

# 10. Специальные символы в параметрах
@pytest.mark.parametrize("payload", [
    {"login": "test", "password": "JDlmRGPq", "channel": "release-v1.0"}  # специальные символы в channel
], ids=[
    "специальные символы в channel"
])
def test_special_characters_in_parameters(api_client, auth_token, api_base_url, payload, attach_curl_on_fail):
    """Тестирует специальные символы в параметрах"""
    url = f"{api_base_url}{ENDPOINT}"
    headers = {"x-access-token": auth_token, "Content-Type": "application/json"}
    
    with attach_curl_on_fail(ENDPOINT, payload, headers, "POST"):
        response = api_client.post(url, json=payload, headers=headers)
        
        assert response.status_code == 200, f"Ожидается 200; получено {response.status_code}"

# 11. Длинные значения
@pytest.mark.parametrize("payload", [
    {"login": "test", "password": "a" * 1000, "channel": "release"}  # очень длинный password
], ids=[
    "очень длинный password"
])
def test_long_parameter_values(api_client, auth_token, api_base_url, payload, attach_curl_on_fail):
    """Тестирует длинные значения параметров"""
    url = f"{api_base_url}{ENDPOINT}"
    headers = {"x-access-token": auth_token, "Content-Type": "application/json"}
    
    with attach_curl_on_fail(ENDPOINT, payload, headers, "POST"):
        response = api_client.post(url, json=payload, headers=headers)
        
        assert response.status_code == 401, f"Ожидается 401; получено {response.status_code}"

# ----- ТЕСТЫ ДЛЯ ОШИБОК HTTP ЗАГОЛОВКОВ -----

# 12. Неверные заголовки
@pytest.mark.parametrize("headers,payload,expected_status", [
    ({"Content-Type": "text/plain", "x-access-token": "valid_token"}, {"login": "test", "password": "JDlmRGPq", "channel": "release"}, 400),  # неверный Content-Type -> 400
    ({"x-access-token": "valid_token"}, {"login": "test", "password": "JDlmRGPq", "channel": "release"}, 200)  # отсутствует Content-Type -> 200
], ids=[
    "неверный Content-Type",
    "отсутствует Content-Type"
])
def test_invalid_headers(api_client, auth_token, api_base_url, headers, payload, expected_status, attach_curl_on_fail):
    """Тестирует неверные HTTP заголовки"""
    url = f"{api_base_url}{ENDPOINT}"
    # Заменяем placeholder на реальный токен
    if "valid_token" in headers.get("x-access-token", ""):
        headers["x-access-token"] = auth_token
    
    with attach_curl_on_fail(ENDPOINT, payload, headers, "POST"):
        response = api_client.post(url, json=payload, headers=headers)
        
        assert response.status_code == expected_status, f"Ожидается {expected_status}; получено {response.status_code}"

# ----- ТЕСТЫ ДЛЯ ОШИБОК МЕТОДА ЗАПРОСА -----

# 13. Неверный HTTP метод
@pytest.mark.parametrize("method,payload", [
    ("GET", {"login": "test", "password": "JDlmRGPq", "channel": "release"}),  # GET вместо POST
    ("PUT", {"login": "test", "password": "JDlmRGPq", "channel": "release"})  # PUT вместо POST
], ids=[
    "GET вместо POST",
    "PUT вместо POST"
])
def test_invalid_http_method(api_client, auth_token, api_base_url, method, payload, attach_curl_on_fail):
    """Тестирует неверные HTTP методы"""
    url = f"{api_base_url}{ENDPOINT}"
    headers = {"x-access-token": auth_token, "Content-Type": "application/json"}
    
    with attach_curl_on_fail(ENDPOINT, payload, headers, method):
        if method == "GET":
            response = api_client.get(url, headers=headers, params=payload)
        elif method == "PUT":
            response = api_client.put(url, json=payload, headers=headers)
        
        assert response.status_code == 404, f"Ожидается 404; получено {response.status_code}"

# ----- ТЕСТЫ ДЛЯ ОШИБОК БАЗЫ ДАННЫХ -----

# 14. Проблемы с доступом к БД
@pytest.mark.parametrize("payload", [
    {"login": "test", "password": "JDlmRGPq", "channel": "release"}
], ids=["проблемы с получением текущей версии из БД"])
def test_database_access_issues(api_client, auth_token, api_base_url, payload, attach_curl_on_fail):
    """Тестирует проблемы с доступом к базе данных"""
    url = f"{api_base_url}{ENDPOINT}"
    headers = {"x-access-token": auth_token, "Content-Type": "application/json"}
    
    with attach_curl_on_fail(ENDPOINT, payload, headers, "POST"):
        response = api_client.post(url, json=payload, headers=headers)
        
        assert response.status_code == 200, f"Ожидается 200; получено {response.status_code}"

# ----- ДОПОЛНИТЕЛЬНЫЕ ТЕСТЫ -----

# 15. Тест аутентификации
def test_authentication_required(api_client, api_base_url, attach_curl_on_fail):
    """Тестирует, что аутентификация обязательна"""
    url = f"{api_base_url}{ENDPOINT}"
    payload = {"login": "test", "password": "JDlmRGPq", "channel": "release"}
    
    with attach_curl_on_fail(ENDPOINT, payload, method="POST"):
        response = api_client.post(url, json=payload)
        
        assert response.status_code == 401, f"Ожидается 401 Unauthorized; получено {response.status_code}"

# 16. Тест валидации заголовков
def test_headers_validation(api_client, auth_token, api_base_url, attach_curl_on_fail):
    """Тестирует валидацию заголовков"""
    url = f"{api_base_url}{ENDPOINT}"
    payload = {"login": "test", "password": "JDlmRGPq", "channel": "release"}
    
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
        assert response.status_code == 200, f"Ожидается 200 OK; получено {response.status_code}"
        
        data = response.json()
        _validate_response_schema(data)


# ----- ДОПОЛНИТЕЛЬНАЯ ПРОВЕРКА ЧЕРЕЗ АГЕНТА -----

def test_agent_verification_check_for_updates(agent_verification, auth_token, api_base_url):
    """Дополнительная проверка через агента для POST /update/rules/check-for-updates.

    Требования:
    - Запрос к агенту выполняется в отдельном тесте
    - Тело запроса к агенту: { "x-access-token": <token> }
    - Обработка ответов агента:
        {"result":"OK"}  -> успех
        {"result":"ERROR","message":"..."} -> тест провален
        "unavailable" -> агент недоступен, тест не пропускать (провал)
    - После каждого шага — краткая валидация результата и решение о продолжении
    - Следуем шаблонам обработки ошибок/логированию проекта
    """

    # Шаг 1: Подготовка тела запроса к агенту
    agent_endpoint = "/update/rules/check-for-updates"
    agent_payload = {"x-access-token": auth_token}
    print("Шаг 1: Подготовка тела запроса — OK")

    # Шаг 2: Вызов агента
    result = agent_verification(agent_endpoint, agent_payload, timeout=180)
    print("Шаг 2: Отправка запроса агенту — OK")

    # Шаг 3: Валидация ответа агента
    if result == "unavailable":
        # Агент недоступен — тест не пропускаем, считаем провалом
        pytest.fail("Агент недоступен. Тест проваливается.")

    assert isinstance(result, dict), f"Ожидался JSON ответ агента, получено: {type(result)}"
    print("Шаг 3: Получен корректный JSON — OK")

    # Шаг 4: Интерпретация результата
    if result.get("result") == "OK":
        print("Шаг 4: Проверка агента успешна — продолжаем")
        return

    if result.get("result") == "ERROR":
        message = result.get("message", "Неизвестная ошибка")
        # Регистрируем предупреждение и валим тест
        print(f"Предупреждение: Агент вернул ошибку: {message}")
        pytest.fail(f"Проверка через агента провалена: {message}")

    # Непредвиденный формат — трактуем как ошибку
    pytest.fail(f"Неожиданный ответ агента: {result}")


# Гарантируем поднятие SSH-туннелей сервиса и агента ДО получения токена
@pytest.fixture(scope="module", autouse=True)
def _ensure_tunnels_initialized(api_base_url, agent_base_url):
    # Достаточно заинстанцировать фикстуры; побочных действий не требуется
    return None
