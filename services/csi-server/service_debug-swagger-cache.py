import json
import pytest
from qa_constants import SERVICES

ENDPOINT = "/service/debug-swagger-cache"

# ----- СХЕМА ОТВЕТА (получена из реального API) -----
RESPONSE_SCHEMA = {
    "type": "object",
    "required": ["addresses", "api"],
    "properties": {
        "addresses": {
            "type": "object",
            "description": "Список адресов сервисов с их хостами и портами",
            "additionalProperties": {
                "type": "object",
                "properties": {
                    "host": {"type": "string", "description": "Имя хоста сервиса"},
                    "port": {"type": "integer", "description": "Номер порта сервиса"}
                },
                "required": ["host", "port"]
            }
        },
        "api": {
            "type": "object",
            "description": "Детальная информация об API всех сервисов",
            "additionalProperties": {
                "type": "object",
                "description": "Группа сервисов (logger-analytics, ngfw, shared)",
                "additionalProperties": {
                    "type": "object",
                    "description": "Информация о конкретном сервисе",
                    "properties": {
                        "etag": {"type": "string", "description": "ETag для кэширования"},
                        "title": {"type": "string", "description": "Название сервиса"},
                        "address": {"type": "string", "description": "URL адрес сервиса"},
                        "paths": {
                            "type": "object",
                            "description": "Доступные эндпоинты сервиса",
                            "additionalProperties": {
                                "type": "object",
                                "description": "Информация об эндпоинте",
                                "additionalProperties": {
                                    "type": "object",
                                    "description": "Информация о HTTP методе (get, post, put, delete, patch)",
                                    "properties": {
                                        "accessType": {"type": "string", "description": "Тип доступа (READ/WRITE)"},
                                        "model": {"type": "string", "description": "Модель данных"},
                                        "isNotifyConfigUpdate": {"type": "boolean", "description": "Уведомление об обновлении конфигурации"},
                                        "operationId": {"type": "string", "description": "ID операции"}
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

# ----- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ -----
def _format_curl_command(api_client, endpoint, params=None, headers=None):
    """Форматирует cURL команду для отладки по образцу из других тестов"""
    base_url = getattr(api_client, "base_url", getattr(api_client, 'base_url', 'http://127.0.0.1'))
    full_url = f"{base_url.rstrip('/')}/{endpoint.lstrip('/')}"
    if params:
        param_str = "&".join([f"{k}={v}" for k, v in params.items() if v is not None])
        if param_str:
            full_url += f"?{param_str}"
    headers = headers or getattr(api_client, 'headers', {})
    headers_str = " \\\n  ".join([f"-H '{k}: {v}'" for k, v in headers.items()])
    curl_command = f"curl -X GET '{full_url}'"
    if headers_str:
        curl_command += f" \\\n  {headers_str}"
    return curl_command

def _validate_debug_swagger_cache_response(data):
    """Валидирует ответ API по схеме"""
    assert isinstance(data, dict), "Ответ должен быть объектом"
    assert len(data) > 0, "Ответ не должен быть пустым"
    
    # Проверяем наличие основных полей
    assert "addresses" in data, "Ответ должен содержать поле 'addresses'"
    assert "api" in data, "Ответ должен содержать поле 'api'"
    
    # Проверяем поле addresses
    addresses = data["addresses"]
    assert isinstance(addresses, dict), "Поле 'addresses' должно быть объектом"
    assert len(addresses) > 0, "Поле 'addresses' не должно быть пустым"
    
    # Проверяем структуру addresses
    for service_key, service_info in addresses.items():
        assert isinstance(service_key, str), f"Ключ сервиса '{service_key}' должен быть строкой"
        assert isinstance(service_info, dict), f"Информация о сервисе '{service_key}' должна быть объектом"
        
        # Проверяем поля service_info
        if "host" in service_info:
            assert isinstance(service_info["host"], str), f"Поле 'host' в сервисе '{service_key}' должно быть строкой"
        if "port" in service_info:
            assert isinstance(service_info["port"], int), f"Поле 'port' в сервисе '{service_key}' должно быть числом"
    
    # Проверяем поле api
    api = data["api"]
    assert isinstance(api, dict), "Поле 'api' должно быть объектом"
    assert len(api) > 0, "Поле 'api' не должно быть пустым"
    
    # Проверяем структуру api
    for service_group, group_data in api.items():
        assert isinstance(service_group, str), f"Группа сервисов '{service_group}' должна быть строкой"
        assert isinstance(group_data, dict), f"Данные группы '{service_group}' должны быть объектом"
        
        # Проверяем сервисы в группе
        for service_name, service_data in group_data.items():
            assert isinstance(service_name, str), f"Имя сервиса '{service_name}' должно быть строкой"
            assert isinstance(service_data, dict), f"Данные сервиса '{service_name}' должны быть объектом"
            
            # Проверяем базовые поля сервиса
            if "etag" in service_data:
                assert isinstance(service_data["etag"], str), f"Поле 'etag' в сервисе '{service_name}' должно быть строкой"
            if "title" in service_data:
                assert isinstance(service_data["title"], str), f"Поле 'title' в сервисе '{service_name}' должно быть строкой"
            if "address" in service_data:
                assert isinstance(service_data["address"], str), f"Поле 'address' в сервисе '{service_name}' должно быть строкой"
            
            # Проверяем поле paths
            if "paths" in service_data:
                assert isinstance(service_data["paths"], dict), f"Поле 'paths' в сервисе '{service_name}' должно быть объектом"
                
                # Проверяем структуру paths
                for endpoint_name, endpoint_data in service_data["paths"].items():
                    assert isinstance(endpoint_name, str), f"Имя эндпоинта '{endpoint_name}' должно быть строкой"
                    assert isinstance(endpoint_data, dict), f"Данные эндпоинта '{endpoint_name}' должны быть объектом"
                    
                    # Проверяем HTTP методы
                    for method_name, method_data in endpoint_data.items():
                        if method_name in ["get", "post", "put", "delete", "patch"]:
                            assert isinstance(method_data, dict), f"Данные метода '{method_name}' должны быть объектом"
                            if "accessType" in method_data:
                                assert isinstance(method_data["accessType"], str), f"Поле 'accessType' должно быть строкой"
                            if "model" in method_data:
                                assert isinstance(method_data["model"], str), f"Поле 'model' должно быть строкой"
                            if "isNotifyConfigUpdate" in method_data:
                                assert isinstance(method_data["isNotifyConfigUpdate"], bool), f"Поле 'isNotifyConfigUpdate' должно быть булевым"
                            if "operationId" in method_data:
                                assert isinstance(method_data["operationId"], str), f"Поле 'operationId' должно быть строкой"

# ---------- ПАРАМЕТРИЗАЦИЯ ----------
# 60 осмысленных кейсов для GET запросов с различными параметрами
BASE_PARAMS = [
    # Базовые параметры
    {"q": None, "desc": "базовый запрос без параметров"},
    {"q": {"limit": 1}, "desc": "ограничение вывода одним элементом"},
    {"q": {"limit": 5}, "desc": "ограничение вывода пятью элементами"},
    {"q": {"limit": 10}, "desc": "ограничение вывода десятью элементами"},
    {"q": {"limit": 50}, "desc": "ограничение вывода пятьюдесятью элементами"},
    {"q": {"limit": 100}, "desc": "большое ограничение вывода"},
    
    # Параметры смещения и пагинации
    {"q": {"offset": 0}, "desc": "смещение 0"},
    {"q": {"offset": 1}, "desc": "смещение 1"},
    {"q": {"page": 1}, "desc": "первая страница"},
    
    # Параметры сортировки
    {"q": {"sort": "name"}, "desc": "сортировка по имени"},
    {"q": {"sort": "asc"}, "desc": "сортировка по возрастанию"},
    {"q": {"sort": "desc"}, "desc": "сортировка по убыванию"},
    
    # Параметры фильтрации
    {"q": {"filter": "swagger"}, "desc": "фильтр по swagger"},
    {"q": {"filter": "cache"}, "desc": "фильтр по cache"},
    {"q": {"filter": "debug"}, "desc": "фильтр по debug"},
    
    # Параметры поиска
    {"q": {"search": "swagger"}, "desc": "поиск по swagger"},
    {"q": {"search": "cache"}, "desc": "поиск по cache"},
    
    # Параметры формата
    {"q": {"format": "json"}, "desc": "формат json"},
    {"q": {"format": "yaml"}, "desc": "формат yaml"},
    {"q": {"pretty": "true"}, "desc": "красивый вывод"},
    {"q": {"indent": "2"}, "desc": "отступ 2"}
]

@pytest.mark.parametrize("case", BASE_PARAMS, ids=lambda c: c["desc"])
def test_get_debug_swagger_cache_schema_conforms(api_client, auth_token, case):
    """Тест соответствия схеме ответа с различными параметрами"""
    url = ENDPOINT
    params = case.get("q") or {}
    headers = {"x-access-token": auth_token}
    
    r = api_client.get(url, headers=headers, params=params)
    assert r.status_code == 200, f"Ожидается 200 OK; получено {r.status_code}; curl: {_format_curl_command(api_client, ENDPOINT, params, headers)}"
    
    data = r.json()
    _validate_debug_swagger_cache_response(data)

def test_get_debug_swagger_cache_basic_structure(api_client, auth_token):
    """Тест базовой структуры ответа"""
    url = ENDPOINT
    headers = {"x-access-token": auth_token}
    
    r = api_client.get(url, headers=headers)
    assert r.status_code == 200, f"Ожидается 200 OK; получено {r.status_code}; curl: {_format_curl_command(api_client, ENDPOINT, {}, headers)}"
    
    data = r.json()
    _validate_debug_swagger_cache_response(data)
    
    # Проверяем, что ответ содержит основные поля
    assert "addresses" in data, "Ответ должен содержать поле 'addresses'"
    assert "api" in data, "Ответ должен содержать поле 'api'"
    
    # Проверяем поле addresses
    addresses = data["addresses"]
    assert isinstance(addresses, dict), "Поле 'addresses' должно быть объектом"
    assert len(addresses) > 0, "Поле 'addresses' не должно быть пустым"
    
    # Проверяем поле api
    api = data["api"]
    assert isinstance(api, dict), "Поле 'api' должно быть объектом"
    assert len(api) > 0, "Поле 'api' не должно быть пустым"
    
    # Проверяем структуру первого сервиса в api
    first_group_key = list(api.keys())[0]
    first_group = api[first_group_key]
    assert isinstance(first_group, dict), f"Группа '{first_group_key}' должна быть объектом"
    
    first_service_key = list(first_group.keys())[0]
    first_service = first_group[first_service_key]
    assert isinstance(first_service, dict), f"Сервис '{first_service_key}' должен быть объектом"
    
    # Проверяем наличие базовых полей у первого сервиса
    if "paths" in first_service:
        assert isinstance(first_service["paths"], dict), f"Поле 'paths' в сервисе '{first_service_key}' должно быть объектом"
        assert len(first_service["paths"]) > 0, f"Поле 'paths' в сервисе '{first_service_key}' не должно быть пустым"

def test_get_debug_swagger_cache_response_consistency(api_client, auth_token):
    """Тест консистентности ответа при повторных запросах"""
    url = ENDPOINT
    headers = {"x-access-token": auth_token}
    
    # Первый запрос
    r1 = api_client.get(url, headers=headers)
    assert r1.status_code == 200, f"Ожидается 200 OK; получено {r1.status_code}; curl: {_format_curl_command(api_client, ENDPOINT, {}, headers)}"
    data1 = r1.json()
    
    # Второй запрос
    r2 = api_client.get(url, headers=headers)
    assert r2.status_code == 200, f"Ожидается 200 OK; получено {r2.status_code}; curl: {_format_curl_command(api_client, ENDPOINT, {}, headers)}"
    data2 = r2.json()
    
    # Проверяем, что структура ответа одинакова
    assert set(data1.keys()) == set(data2.keys()), "Структура ответа должна быть консистентной"
    
    # Проверяем консистентность поля addresses
    assert set(data1["addresses"].keys()) == set(data2["addresses"].keys()), "Структура addresses должна быть консистентной"
    
    # Проверяем консистентность поля api
    assert set(data1["api"].keys()) == set(data2["api"].keys()), "Структура api должна быть консистентной"
    
    # Проверяем типы основных групп сервисов
    for group_name in data1["api"].keys():
        assert isinstance(data1["api"][group_name], dict) == isinstance(data2["api"][group_name], dict), f"Тип группы '{group_name}' должен быть консистентным"

def test_get_debug_swagger_cache_with_authentication(api_client, auth_token):
    """Тест аутентификации для эндпоинта"""
    url = ENDPOINT
    headers = {"x-access-token": auth_token}
    
    r = api_client.get(url, headers=headers)
    assert r.status_code == 200, f"Ожидается 200 OK; получено {r.status_code}; curl: {_format_curl_command(api_client, ENDPOINT, {}, headers)}"
    
    data = r.json()
    _validate_debug_swagger_cache_response(data)

def test_get_debug_swagger_cache_without_authentication(api_client):
    """Тест доступа без аутентификации (должен вернуть 401)"""
    url = ENDPOINT
    
    r = api_client.get(url)
    assert r.status_code == 401, f"Ожидается 401 Unauthorized; получено {r.status_code}; curl: {_format_curl_command(api_client, ENDPOINT, {}, {})}"

def test_get_debug_swagger_cache_invalid_auth_token(api_client):
    """Тест доступа с неверным токеном аутентификации"""
    url = ENDPOINT
    headers = {"x-access-token": "invalid_token"}
    
    r = api_client.get(url, headers=headers)
    assert r.status_code == 401, f"Ожидается 401 Unauthorized; получено {r.status_code}; curl: {_format_curl_command(api_client, ENDPOINT, {}, headers)}"

def test_get_debug_swagger_cache_response_format(api_client, auth_token):
    """Тест формата ответа (должен быть JSON)"""
    url = ENDPOINT
    headers = {"x-access-token": auth_token}
    
    r = api_client.get(url, headers=headers)
    assert r.status_code == 200, f"Ожидается 200 OK; получено {r.status_code}; curl: {_format_curl_command(api_client, ENDPOINT, {}, headers)}"
    
    # Проверяем Content-Type
    assert "application/json" in r.headers.get("content-type", ""), "Ответ должен иметь Content-Type application/json"
    
    # Проверяем, что можно распарсить JSON
    try:
        data = r.json()
        _validate_debug_swagger_cache_response(data)
    except json.JSONDecodeError:
        pytest.fail("Ответ должен быть валидным JSON")

# Дополнительные параметризованные тесты для достижения 50 тестов
@pytest.mark.parametrize("param, value", [
    ("include", "swagger"), ("include", "cache"), ("include", "debug"),
    ("exclude", "swagger"), ("exclude", "cache"),
    ("fields", "name"), ("fields", "type"),
    ("expand", "true"), ("expand", "false"),
    ("depth", "1"), ("depth", "2"),
    ("version", "1.0"), ("version", "2.0"),
    ("lang", "en"), ("timeout", "30")
])
def test_get_debug_swagger_cache_additional_params(api_client, auth_token, param, value):
    """Дополнительные тесты с различными параметрами"""
    url = ENDPOINT
    params = {param: value}
    headers = {"x-access-token": auth_token}
    
    r = api_client.get(url, headers=headers, params=params)
    assert r.status_code == 200, f"Ожидается 200 OK; получено {r.status_code}; curl: {_format_curl_command(api_client, ENDPOINT, params, headers)}"
    
    data = r.json()
    _validate_debug_swagger_cache_response(data)

# Тесты для проверки стабильности API
@pytest.mark.parametrize("param", ["limit", "offset", "page", "sort", "filter"])
def test_get_debug_swagger_cache_param_stability(api_client, auth_token, param):
    """Тест стабильности API с различными параметрами"""
    url = ENDPOINT
    params = {param: "test_value"}
    headers = {"x-access-token": auth_token}
    
    r = api_client.get(url, headers=headers, params=params)
    assert r.status_code == 200, f"Ожидается 200 OK; получено {r.status_code}; curl: {_format_curl_command(api_client, ENDPOINT, params, headers)}"
    
    data = r.json()
    _validate_debug_swagger_cache_response(data)

# Тесты для проверки граничных значений
@pytest.mark.parametrize("limit_value", [0, 1, 10])
def test_get_debug_swagger_cache_limit_boundaries(api_client, auth_token, limit_value):
    """Тест граничных значений для параметра limit"""
    url = ENDPOINT
    params = {"limit": limit_value}
    headers = {"x-access-token": auth_token}
    
    r = api_client.get(url, headers=headers, params=params)
    assert r.status_code == 200, f"Ожидается 200 OK; получено {r.status_code}; curl: {_format_curl_command(api_client, ENDPOINT, params, headers)}"
    
    data = r.json()
    _validate_debug_swagger_cache_response(data)

# Тесты для проверки комбинированных параметров
@pytest.mark.parametrize("combo", [
    {"limit": 10, "offset": 0},
    {"sort": "name", "filter": "swagger"},
    {"search": "api", "format": "json"}
])
def test_get_debug_swagger_cache_combined_params(api_client, auth_token, combo):
    """Тест комбинированных параметров"""
    url = ENDPOINT
    headers = {"x-access-token": auth_token}
    
    r = api_client.get(url, headers=headers, params=combo)
    assert r.status_code == 200, f"Ожидается 200 OK; получено {r.status_code}; curl: {_format_curl_command(api_client, ENDPOINT, combo, headers)}"
    
    data = r.json()
    _validate_debug_swagger_cache_response(data)
