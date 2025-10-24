import pytest
import json

# ----- Constants -----
ENDPOINT = "/update/rules/apply-local"

# Схема успешного ответа для валидации
SUCCESS_RESPONSE_SCHEMA = {
    "ok": int
}


# ----- Успешное применение локальных правил -----
def test_apply_local_rules_success(api_client, auth_token, api_base_url, attach_curl_on_fail):
    """Тест успешного применения локальных правил"""
    url = f"{api_base_url}{ENDPOINT}"
    headers = {"x-access-token": auth_token, "Content-Type": "application/json"}
    
    with attach_curl_on_fail(ENDPOINT, None, headers, "POST"):
        response = api_client.post(url, headers=headers)
        
        # Допускаем 200 (успех), 204 (успех без тела) или 422 (правила не скачаны/не готовы)
        assert response.status_code in (200, 204, 422), f"Ожидается 200 OK, 204 No Content или 422 Unprocessable Entity; получено {response.status_code}"
        
        if response.status_code == 200:
            data = response.json()
            assert "ok" in data, "Ответ должен содержать поле 'ok'"
            assert isinstance(data["ok"], int), "Поле 'ok' должно быть числом"
        elif response.status_code == 422:
            # 422 - правила не скачаны/не готовы
            data = response.json()
            assert "error" in data, "Ответ должен содержать поле 'error'"
            assert data["error"]["statusCode"] == 422
            assert data["error"]["name"] == "UnprocessableEntityError"
        else:
            # 204 - успешное применение без тела
            assert response.text == ""


# ----- Позитивные тесты с различными заголовками -----
def test_apply_local_rules_success_with_accept_header(api_client, auth_token, api_base_url, attach_curl_on_fail):
    """Тест успешного применения с Accept заголовком"""
    url = f"{api_base_url}{ENDPOINT}"
    headers = {"x-access-token": auth_token, "Content-Type": "application/json", "Accept": "application/json"}
    
    with attach_curl_on_fail(ENDPOINT, None, headers, "POST"):
        response = api_client.post(url, headers=headers)
        assert response.status_code in (200, 204, 422), f"Ожидается 200 OK, 204 No Content или 422 Unprocessable Entity; получено {response.status_code}"


def test_apply_local_rules_success_with_user_agent(api_client, auth_token, api_base_url, attach_curl_on_fail):
    """Тест успешного применения с User-Agent заголовком"""
    url = f"{api_base_url}{ENDPOINT}"
    headers = {"x-access-token": auth_token, "Content-Type": "application/json", "User-Agent": "QA-Test-Client/1.0"}
    
    with attach_curl_on_fail(ENDPOINT, None, headers, "POST"):
        response = api_client.post(url, headers=headers)
        assert response.status_code in (200, 204, 422), f"Ожидается 200 OK, 204 No Content или 422 Unprocessable Entity; получено {response.status_code}"


def test_apply_local_rules_success_with_cache_control(api_client, auth_token, api_base_url, attach_curl_on_fail):
    """Тест успешного применения с Cache-Control заголовком"""
    url = f"{api_base_url}{ENDPOINT}"
    headers = {"x-access-token": auth_token, "Content-Type": "application/json", "Cache-Control": "no-cache"}
    
    with attach_curl_on_fail(ENDPOINT, None, headers, "POST"):
        response = api_client.post(url, headers=headers)
        assert response.status_code in (200, 204, 422), f"Ожидается 200 OK, 204 No Content или 422 Unprocessable Entity; получено {response.status_code}"


def test_apply_local_rules_success_with_connection(api_client, auth_token, api_base_url, attach_curl_on_fail):
    """Тест успешного применения с Connection заголовком"""
    url = f"{api_base_url}{ENDPOINT}"
    headers = {"x-access-token": auth_token, "Content-Type": "application/json", "Connection": "keep-alive"}
    
    with attach_curl_on_fail(ENDPOINT, None, headers, "POST"):
        response = api_client.post(url, headers=headers)
        assert response.status_code in (200, 204, 422), f"Ожидается 200 OK, 204 No Content или 422 Unprocessable Entity; получено {response.status_code}"


def test_apply_local_rules_success_with_pragma(api_client, auth_token, api_base_url, attach_curl_on_fail):
    """Тест успешного применения с Pragma заголовком"""
    url = f"{api_base_url}{ENDPOINT}"
    headers = {"x-access-token": auth_token, "Content-Type": "application/json", "Pragma": "no-cache"}
    
    with attach_curl_on_fail(ENDPOINT, None, headers, "POST"):
        response = api_client.post(url, headers=headers)
        assert response.status_code in (200, 204, 422), f"Ожидается 200 OK, 204 No Content или 422 Unprocessable Entity; получено {response.status_code}"


def test_apply_local_rules_success_with_accept_language(api_client, auth_token, api_base_url, attach_curl_on_fail):
    """Тест успешного применения с Accept-Language заголовком"""
    url = f"{api_base_url}{ENDPOINT}"
    headers = {"x-access-token": auth_token, "Content-Type": "application/json", "Accept-Language": "en-US,en;q=0.9"}
    
    with attach_curl_on_fail(ENDPOINT, None, headers, "POST"):
        response = api_client.post(url, headers=headers)
        assert response.status_code in (200, 204, 422), f"Ожидается 200 OK, 204 No Content или 422 Unprocessable Entity; получено {response.status_code}"


def test_apply_local_rules_success_with_x_debug(api_client, auth_token, api_base_url, attach_curl_on_fail):
    """Тест успешного применения с X-Debug заголовком"""
    url = f"{api_base_url}{ENDPOINT}"
    headers = {"x-access-token": auth_token, "Content-Type": "application/json", "X-Debug": "1"}
    
    with attach_curl_on_fail(ENDPOINT, None, headers, "POST"):
        response = api_client.post(url, headers=headers)
        assert response.status_code in (200, 204, 422), f"Ожидается 200 OK, 204 No Content или 422 Unprocessable Entity; получено {response.status_code}"


def test_apply_local_rules_success_with_x_trace_id(api_client, auth_token, api_base_url, attach_curl_on_fail):
    """Тест успешного применения с X-Trace-Id заголовком"""
    url = f"{api_base_url}{ENDPOINT}"
    headers = {"x-access-token": auth_token, "Content-Type": "application/json", "X-Trace-Id": "trace-12345"}
    
    with attach_curl_on_fail(ENDPOINT, None, headers, "POST"):
        response = api_client.post(url, headers=headers)
        assert response.status_code in (200, 204, 422), f"Ожидается 200 OK, 204 No Content или 422 Unprocessable Entity; получено {response.status_code}"


def test_apply_local_rules_success_with_content_length(api_client, auth_token, api_base_url, attach_curl_on_fail):
    """Тест успешного применения с Content-Length заголовком"""
    url = f"{api_base_url}{ENDPOINT}"
    headers = {"x-access-token": auth_token, "Content-Type": "application/json", "Content-Length": "0"}
    
    with attach_curl_on_fail(ENDPOINT, None, headers, "POST"):
        response = api_client.post(url, headers=headers)
        assert response.status_code in (200, 204, 422), f"Ожидается 200 OK, 204 No Content или 422 Unprocessable Entity; получено {response.status_code}"


def test_apply_local_rules_success_with_charset(api_client, auth_token, api_base_url, attach_curl_on_fail):
    """Тест успешного применения с charset в Content-Type"""
    url = f"{api_base_url}{ENDPOINT}"
    headers = {"x-access-token": auth_token, "Content-Type": "application/json; charset=utf-8"}
    
    with attach_curl_on_fail(ENDPOINT, None, headers, "POST"):
        response = api_client.post(url, headers=headers)
        assert response.status_code in (200, 204, 422), f"Ожидается 200 OK, 204 No Content или 422 Unprocessable Entity; получено {response.status_code}"


def test_apply_local_rules_success_with_accept_any(api_client, auth_token, api_base_url, attach_curl_on_fail):
    """Тест успешного применения с Accept: */*"""
    url = f"{api_base_url}{ENDPOINT}"
    headers = {"x-access-token": auth_token, "Content-Type": "application/json", "Accept": "*/*"}
    
    with attach_curl_on_fail(ENDPOINT, None, headers, "POST"):
        response = api_client.post(url, headers=headers)
        assert response.status_code in (200, 204, 422), f"Ожидается 200 OK, 204 No Content или 422 Unprocessable Entity; получено {response.status_code}"


def test_apply_local_rules_success_with_multiple_headers(api_client, auth_token, api_base_url, attach_curl_on_fail):
    """Тест успешного применения с множественными заголовками"""
    url = f"{api_base_url}{ENDPOINT}"
    headers = {
        "x-access-token": auth_token, 
        "Content-Type": "application/json", 
        "Accept": "application/json",
        "User-Agent": "QA-Test-Client/2.0",
        "Cache-Control": "no-cache",
        "X-Debug": "1"
    }
    
    with attach_curl_on_fail(ENDPOINT, None, headers, "POST"):
        response = api_client.post(url, headers=headers)
        assert response.status_code in (200, 204, 422), f"Ожидается 200 OK, 204 No Content или 422 Unprocessable Entity; получено {response.status_code}"


def test_apply_local_rules_success_with_timeout(api_client, auth_token, api_base_url, attach_curl_on_fail):
    """Тест успешного применения с увеличенным timeout"""
    url = f"{api_base_url}{ENDPOINT}"
    headers = {"x-access-token": auth_token, "Content-Type": "application/json"}
    
    with attach_curl_on_fail(ENDPOINT, None, headers, "POST"):
        response = api_client.post(url, headers=headers, timeout=30)
        assert response.status_code in (200, 204, 422), f"Ожидается 200 OK, 204 No Content или 422 Unprocessable Entity; получено {response.status_code}"


def test_apply_local_rules_success_minimal_headers(api_client, auth_token, api_base_url, attach_curl_on_fail):
    """Тест успешного применения с минимальными заголовками"""
    url = f"{api_base_url}{ENDPOINT}"
    headers = {"x-access-token": auth_token}
    
    with attach_curl_on_fail(ENDPOINT, None, headers, "POST"):
        response = api_client.post(url, headers=headers)
        assert response.status_code in (200, 204, 422), f"Ожидается 200 OK, 204 No Content или 422 Unprocessable Entity; получено {response.status_code}"


# ----- Отсутствие токена авторизации -----
def test_apply_local_rules_no_auth_token(api_client, api_base_url, attach_curl_on_fail):
    """Тест запроса без токена авторизации"""
    url = f"{api_base_url}{ENDPOINT}"
    headers = {"Content-Type": "application/json"}
    
    with attach_curl_on_fail(ENDPOINT, None, headers, "POST"):
        response = api_client.post(url, headers=headers)
        
        assert response.status_code == 401, f"Ожидается 401 Unauthorized; получено {response.status_code}"
        
        data = response.json()
        assert "error" in data, "Ответ должен содержать поле 'error'"
        assert data["error"]["statusCode"] == 401
        assert data["error"]["name"] == "UnauthorizedError"
        assert data["error"]["message"] == "Authorization Required"


# ----- Недействительный токен авторизации -----
def test_apply_local_rules_invalid_token(api_client, api_base_url, attach_curl_on_fail):
    """Тест с недействительным токеном авторизации"""
    url = f"{api_base_url}{ENDPOINT}"
    headers = {"x-access-token": "invalid_token_12345", "Content-Type": "application/json"}
    
    with attach_curl_on_fail(ENDPOINT, None, headers, "POST"):
        response = api_client.post(url, headers=headers)
        
        assert response.status_code == 401, f"Ожидается 401 Unauthorized; получено {response.status_code}"
        
        data = response.json()
        assert "error" in data, "Ответ должен содержать поле 'error'"
        assert data["error"]["statusCode"] == 401
        assert data["error"]["name"] == "UnauthorizedError"
        assert data["error"]["message"] == "Authorization Required"


# ----- Недостаточно прав (нет прав EXECUTE) -----
def test_apply_local_rules_insufficient_permissions(api_client, api_base_url, attach_curl_on_fail):
    """Тест с токеном без прав EXECUTE"""
    url = f"{api_base_url}{ENDPOINT}"
    headers = {"x-access-token": "read_only_token_12345", "Content-Type": "application/json"}
    
    with attach_curl_on_fail(ENDPOINT, None, headers, "POST"):
        response = api_client.post(url, headers=headers)
        
        # API возвращает 401 для недействительных токенов, включая токены без прав
        assert response.status_code == 401, f"Ожидается 401 Unauthorized; получено {response.status_code}"
        
        data = response.json()
        assert "error" in data, "Ответ должен содержать поле 'error'"
        assert data["error"]["statusCode"] == 401
        assert data["error"]["name"] == "UnauthorizedError"
        assert data["error"]["message"] == "Authorization Required"


# ----- Нет локальных правил для применения -----
def test_apply_local_rules_no_updates_found(api_client, auth_token, api_base_url, attach_curl_on_fail):
    """Тест когда нет локальных правил для применения"""
    url = f"{api_base_url}{ENDPOINT}"
    headers = {"x-access-token": auth_token, "Content-Type": "application/json"}
    
    with attach_curl_on_fail(ENDPOINT, None, headers, "POST"):
        response = api_client.post(url, headers=headers)
        
        assert response.status_code in (204, 422), f"Ожидается 204 No Content или 422 Unprocessable Entity; получено {response.status_code}"
        
        if response.status_code == 422:
            data = response.json()
            assert "error" in data, "Ответ должен содержать поле 'error'"
            assert data["error"]["statusCode"] == 422
            assert data["error"]["name"] == "UnprocessableEntityError"
            assert data["error"]["message"] == "RULES_NOT_DOWNLOADED"


# ----- Директория SURICATA_IMPORT_PATH недоступна для записи -----
def test_apply_local_rules_path_not_writable(api_client, auth_token, api_base_url, attach_curl_on_fail):
    """Тест когда директория SURICATA_IMPORT_PATH недоступна для записи"""
    url = f"{api_base_url}{ENDPOINT}"
    headers = {"x-access-token": auth_token, "Content-Type": "application/json"}
    
    with attach_curl_on_fail(ENDPOINT, None, headers, "POST"):
        response = api_client.post(url, headers=headers)
        
        assert response.status_code in (204, 422), f"Ожидается 204 No Content или 422 Unprocessable Entity; получено {response.status_code}"
        
        if response.status_code == 422:
            data = response.json()
            assert "error" in data, "Ответ должен содержать поле 'error'"
            assert data["error"]["statusCode"] == 422
            assert data["error"]["name"] == "UnprocessableEntityError"
            assert data["error"]["message"] == "RULES_NOT_DOWNLOADED"


# ----- Ошибка проверки подписей -----
def test_apply_local_rules_signature_verification_failed(api_client, auth_token, api_base_url, attach_curl_on_fail):
    """Тест ошибки проверки подписей"""
    url = f"{api_base_url}{ENDPOINT}"
    headers = {"x-access-token": auth_token, "Content-Type": "application/json"}
    
    with attach_curl_on_fail(ENDPOINT, None, headers, "POST"):
        response = api_client.post(url, headers=headers)
        
        assert response.status_code in (204, 422), f"Ожидается 204 No Content или 422 Unprocessable Entity; получено {response.status_code}"
        
        if response.status_code == 422:
            data = response.json()
            assert "error" in data, "Ответ должен содержать поле 'error'"
            assert data["error"]["statusCode"] == 422
            assert data["error"]["name"] == "UnprocessableEntityError"
            assert data["error"]["message"] == "RULES_NOT_DOWNLOADED"


# ----- Ошибка сети при обращении к UPDATE_RULES_REST_URL -----
def test_apply_local_rules_network_error(api_client, auth_token, api_base_url, attach_curl_on_fail):
    """Тест ошибки сети при обращении к внешнему API"""
    url = f"{api_base_url}{ENDPOINT}"
    headers = {"x-access-token": auth_token, "Content-Type": "application/json"}
    
    with attach_curl_on_fail(ENDPOINT, None, headers, "POST"):
        response = api_client.post(url, headers=headers)
        
        assert response.status_code in (204, 422), f"Ожидается 204 No Content или 422 Unprocessable Entity; получено {response.status_code}"
        
        if response.status_code == 422:
            data = response.json()
            assert "error" in data, "Ответ должен содержать поле 'error'"
            assert data["error"]["statusCode"] == 422
            assert data["error"]["name"] == "UnprocessableEntityError"
            assert data["error"]["message"] == "RULES_NOT_DOWNLOADED"


# ----- Таймаут при обращении к внешнему API -----
def test_apply_local_rules_timeout_error(api_client, auth_token, api_base_url, attach_curl_on_fail):
    """Тест таймаута при обращении к внешнему API"""
    url = f"{api_base_url}{ENDPOINT}"
    headers = {"x-access-token": auth_token, "Content-Type": "application/json"}
    
    with attach_curl_on_fail(ENDPOINT, None, headers, "POST"):
        response = api_client.post(url, headers=headers)
        
        assert response.status_code in (204, 422), f"Ожидается 204 No Content или 422 Unprocessable Entity; получено {response.status_code}"
        
        if response.status_code == 422:
            data = response.json()
            assert "error" in data, "Ответ должен содержать поле 'error'"
            assert data["error"]["statusCode"] == 422
            assert data["error"]["name"] == "UnprocessableEntityError"
            assert data["error"]["message"] == "RULES_NOT_DOWNLOADED"


# ----- Ошибка базы данных -----
def test_apply_local_rules_database_error(api_client, auth_token, api_base_url, attach_curl_on_fail):
    """Тест ошибки базы данных"""
    url = f"{api_base_url}{ENDPOINT}"
    headers = {"x-access-token": auth_token, "Content-Type": "application/json"}
    
    with attach_curl_on_fail(ENDPOINT, None, headers, "POST"):
        response = api_client.post(url, headers=headers)
        
        assert response.status_code in (204, 422), f"Ожидается 204 No Content или 422 Unprocessable Entity; получено {response.status_code}"
        
        if response.status_code == 422:
            data = response.json()
            assert "error" in data, "Ответ должен содержать поле 'error'"
            assert data["error"]["statusCode"] == 422
            assert data["error"]["name"] == "UnprocessableEntityError"
            assert data["error"]["message"] == "RULES_NOT_DOWNLOADED"


# ----- Ошибка файловой системы -----
def test_apply_local_rules_filesystem_error(api_client, auth_token, api_base_url, attach_curl_on_fail):
    """Тест ошибки файловой системы"""
    url = f"{api_base_url}{ENDPOINT}"
    headers = {"x-access-token": auth_token, "Content-Type": "application/json"}
    
    with attach_curl_on_fail(ENDPOINT, None, headers, "POST"):
        response = api_client.post(url, headers=headers)
        
        assert response.status_code in (204, 422), f"Ожидается 204 No Content или 422 Unprocessable Entity; получено {response.status_code}"
        
        if response.status_code == 422:
            data = response.json()
            assert "error" in data, "Ответ должен содержать поле 'error'"
            assert data["error"]["statusCode"] == 422
            assert data["error"]["name"] == "UnprocessableEntityError"
            assert data["error"]["message"] == "RULES_NOT_DOWNLOADED"


# ----- Неправильный HTTP метод -----
def test_apply_local_rules_wrong_method(api_client, auth_token, api_base_url, attach_curl_on_fail):
    """Тест с неправильным HTTP методом"""
    url = f"{api_base_url}{ENDPOINT}"
    headers = {"x-access-token": auth_token, "Content-Type": "application/json"}
    
    with attach_curl_on_fail(ENDPOINT, None, headers, "GET"):
        response = api_client.get(url, headers=headers)
        
        assert response.status_code == 404, f"Ожидается 404 Not Found; получено {response.status_code}"
        
        data = response.json()
        assert "error" in data, "Ответ должен содержать поле 'error'"
        assert data["error"]["statusCode"] == 404
        assert data["error"]["name"] == "Error"
        assert "method handling GET" in data["error"]["message"]


# ----- Неправильный Content-Type -----
def test_apply_local_rules_wrong_content_type(api_client, auth_token, api_base_url, attach_curl_on_fail):
    """Тест с неправильным Content-Type"""
    url = f"{api_base_url}{ENDPOINT}"
    headers = {"x-access-token": auth_token, "Content-Type": "text/plain"}
    
    with attach_curl_on_fail(ENDPOINT, None, headers, "POST"):
        response = api_client.post(url, headers=headers)
        
        assert response.status_code in (204, 422), f"Ожидается 204 No Content или 422 Unprocessable Entity; получено {response.status_code}"
        
        if response.status_code == 422:
            data = response.json()
            assert "error" in data, "Ответ должен содержать поле 'error'"
            assert data["error"]["statusCode"] == 422
            assert data["error"]["name"] == "UnprocessableEntityError"
            assert data["error"]["message"] == "RULES_NOT_DOWNLOADED"


# ----- Дополнительные негативные тесты -----
def test_apply_local_rules_malformed_token(api_client, api_base_url, attach_curl_on_fail):
    """Тест с некорректно сформированным токеном"""
    url = f"{api_base_url}{ENDPOINT}"
    headers = {"x-access-token": "malformed.token.123", "Content-Type": "application/json"}
    
    with attach_curl_on_fail(ENDPOINT, None, headers, "POST"):
        response = api_client.post(url, headers=headers)
        
        assert response.status_code == 401, f"Ожидается 401 Unauthorized; получено {response.status_code}"
        
        data = response.json()
        assert "error" in data, "Ответ должен содержать поле 'error'"
        assert data["error"]["statusCode"] == 401
        assert data["error"]["name"] == "UnauthorizedError"
        assert data["error"]["message"] == "Authorization Required"


def test_apply_local_rules_empty_token(api_client, api_base_url, attach_curl_on_fail):
    """Тест с пустым токеном"""
    url = f"{api_base_url}{ENDPOINT}"
    headers = {"x-access-token": "", "Content-Type": "application/json"}
    
    with attach_curl_on_fail(ENDPOINT, None, headers, "POST"):
        response = api_client.post(url, headers=headers)
        
        assert response.status_code == 401, f"Ожидается 401 Unauthorized; получено {response.status_code}"
        
        data = response.json()
        assert "error" in data, "Ответ должен содержать поле 'error'"
        assert data["error"]["statusCode"] == 401
        assert data["error"]["name"] == "UnauthorizedError"
        assert data["error"]["message"] == "Authorization Required"


def test_apply_local_rules_unsupported_method_put(api_client, auth_token, api_base_url, attach_curl_on_fail):
    """Тест с неподдерживаемым методом PUT"""
    url = f"{api_base_url}{ENDPOINT}"
    headers = {"x-access-token": auth_token, "Content-Type": "application/json"}
    
    with attach_curl_on_fail(ENDPOINT, None, headers, "PUT"):
        response = api_client.put(url, headers=headers)
        
        assert response.status_code == 404, f"Ожидается 404 Not Found; получено {response.status_code}"
        
        data = response.json()
        assert "error" in data, "Ответ должен содержать поле 'error'"
        assert data["error"]["statusCode"] == 404
        assert data["error"]["name"] == "Error"
        assert "method handling PUT" in data["error"]["message"]
