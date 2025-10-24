"""
Тесты для эндпоинта /manager/restoreConfigStatus сервиса csi-server.

Проверяется:
- Статус-код 200 OK и 400 Bad Request
- Соответствие структуры ответа схеме
- Валидация обязательных полей и их типов
- Устойчивость к различным query-параметрам
- Вывод cURL-команды при ошибке
- Возможные ответы API:
  * {"error": "unable to find run status"} - восстановление не запускалось
  * {"message": "OK"} - восстановление прошло успешно
  * {"message": "updating"} - происходит процесс восстановления
"""
import pytest
import json
import time
from collections.abc import Mapping, Sequence
from datetime import datetime
import re

ENDPOINT = "/manager/restoreConfigStatus"

# Схема ответа для /manager/restoreConfigStatus на основе реального ответа API
RESTORE_CONFIG_STATUS_SCHEMA_200 = {
    "type": "object",
    "properties": {
        "message": {"type": "string"}
    },
    "required": ["message"]
}

RESTORE_CONFIG_STATUS_SCHEMA_400 = {
    "type": "object",
    "properties": {
        "error": {"type": "string"}
    },
    "required": ["error"]
}

# Осмысленная параметризация для тестирования реальной функциональности API
PARAMS = [
    # --- Базовые позитивные сценарии ---
    pytest.param({}, [200, 400], id="P01: no_params"),
    
    # --- Тестирование устойчивости к параметрам (API игнорирует все параметры) ---
    pytest.param({"any_param": "any_value"}, [200, 400], id="P02: single_param_ignored"),
    pytest.param({"unknown": "value"}, [200, 400], id="P03: unknown_param_ignored"),
    pytest.param({"multiple": "params", "another": "value"}, [200, 400], id="P04: multiple_params_ignored"),
    
    # --- Параметры, которые логично могли бы существовать, но API их игнорирует ---
    pytest.param({"status": "check"}, [200, 400], id="P05: status_param_ignored"),
    pytest.param({"mode": "restore"}, [200, 400], id="P06: mode_param_ignored"),
    pytest.param({"config": "backup"}, [200, 400], id="P07: config_param_ignored"),
    pytest.param({"restore": "true"}, [200, 400], id="P08: restore_param_ignored"),
    
    # --- Временные параметры (API игнорирует) ---
    pytest.param({"timeout": "30"}, [200, 400], id="P09: timeout_param_ignored"),
    pytest.param({"delay": "5"}, [200, 400], id="P10: delay_param_ignored"),
    pytest.param({"wait": "true"}, [200, 400], id="P11: wait_param_ignored"),
    
    # --- Поисковые параметры (API игнорирует) ---
    pytest.param({"search": "config"}, [200, 400], id="P12: search_param_ignored"),
    pytest.param({"q": "restore"}, [200, 400], id="P13: query_param_ignored"),
    pytest.param({"filter": "active"}, [200, 400], id="P14: filter_param_ignored"),
    
    # --- Параметры сортировки (API игнорирует) ---
    pytest.param({"sort": "date"}, [200, 400], id="P15: sort_param_ignored"),
    pytest.param({"order": "desc"}, [200, 400], id="P16: order_param_ignored"),
    pytest.param({"limit": "10"}, [200, 400], id="P17: limit_param_ignored"),
    
    # --- Параметры пагинации (API игнорирует) ---
    pytest.param({"page": "1"}, [200, 400], id="P18: page_param_ignored"),
    pytest.param({"per_page": "20"}, [200, 400], id="P19: per_page_param_ignored"),
    pytest.param({"offset": "0"}, [200, 400], id="P20: offset_param_ignored"),
    
    # --- Параметры версионирования (API игнорирует) ---
    pytest.param({"version": "1.0"}, [200, 400], id="P21: version_param_ignored"),
    pytest.param({"api_version": "v2"}, [200, 400], id="P22: api_version_param_ignored"),
    pytest.param({"format": "json"}, [200, 400], id="P23: format_param_ignored"),
    
    # --- Параметры локализации (API игнорирует) ---
    pytest.param({"locale": "en"}, [200, 400], id="P24: locale_param_ignored"),
    pytest.param({"lang": "ru"}, [200, 400], id="P25: language_param_ignored"),
    pytest.param({"timezone": "UTC"}, [200, 400], id="P26: timezone_param_ignored"),
    
    # --- Параметры логирования (API игнорирует) ---
    pytest.param({"debug": "true"}, [200, 400], id="P27: debug_param_ignored"),
    pytest.param({"verbose": "1"}, [200, 400], id="P28: verbose_param_ignored"),
    pytest.param({"log_level": "info"}, [200, 400], id="P29: log_level_param_ignored"),
    
    # --- Параметры кэширования (API игнорирует) ---
    pytest.param({"cache": "false"}, [200, 400], id="P30: cache_param_ignored"),
    pytest.param({"no_cache": "true"}, [200, 400], id="P31: no_cache_param_ignored"),
    pytest.param({"cache_ttl": "300"}, [200, 400], id="P32: cache_param_ignored"),
    
    # --- Параметры безопасности (API игнорирует) ---
    pytest.param({"secure": "true"}, [200, 400], id="P33: secure_param_ignored"),
    pytest.param({"auth": "required"}, [200, 400], id="P34: auth_param_ignored"),
    pytest.param({"permission": "read"}, [200, 400], id="P35: permission_param_ignored"),
    
    # --- Негативные сценарии ---
    pytest.param({"invalid_token": "fake_token"}, [200, 400, 401], id="N01: invalid_token_param"),
    pytest.param({"malformed": "value'with'quotes"}, [200, 400], id="N02: malformed_param_value"),
    pytest.param({"very_long_param": "x" * 1000}, [200, 400], id="N03: very_long_param_value"),
    pytest.param({"special_chars": "!@#$%^&*()"}, [200, 400], id="N04: special_chars_in_param"),
    pytest.param({"unicode": "тест"}, [200, 400], id="N05: unicode_param_value"),
    pytest.param({"null_value": None}, [200, 400], id="N06: null_param_value"),
    pytest.param({"empty_value": ""}, [200, 400], id="N07: empty_param_value"),
    pytest.param({"numeric": 123}, [200, 400], id="N08: numeric_param_value"),
    pytest.param({"boolean": True}, [200, 400], id="N09: boolean_param_value"),
    pytest.param({"array": ["value1", "value2"]}, [200, 400], id="N10: array_param_value")
]

def validate_schema_recursive(data, schema):
    """
    Рекурсивно валидирует данные по схеме.
    Проверяет типы, обязательные поля и вложенные структуры.
    """
    if isinstance(data, list):
        # Для массивов проверяем каждый элемент
        for item in data:
            validate_schema_recursive(item, schema)
        return
    
    if isinstance(data, dict):
        # Проверяем обязательные поля
        for required_field in schema.get("required", []):
            assert required_field in data, f"Отсутствует обязательное поле '{required_field}'"
            field_type = type(data[required_field])
            expected_type = schema["properties"][required_field]["type"]
            
            if expected_type == "string":
                assert field_type is str, f"Поле '{required_field}' должно быть строкой, получено: {field_type.__name__}"
            elif expected_type == "boolean":
                assert field_type is bool, f"Поле '{required_field}' должно быть булевым, получено: {field_type.__name__}"
            elif expected_type == "number":
                assert field_type in (int, float), f"Поле '{required_field}' должно быть числом, получено: {field_type.__name__}"
            elif expected_type == "object":
                assert field_type is dict, f"Поле '{required_field}' должно быть объектом, получено: {field_type.__name__}"
            elif expected_type == "array":
                assert field_type is list, f"Поле '{required_field}' должно быть массивом, получено: {field_type.__name__}"
        
        # Проверяем необязательные поля при их наличии
        for field_name, field_schema in schema.get("properties", {}).items():
            if field_name in data and data[field_name] is not None:
                field_type = type(data[field_name])
                expected_type = field_schema["type"]
                
                if expected_type == "string":
                    assert field_type is str, f"Поле '{field_name}' должно быть строкой, получено: {field_type.__name__}"
                elif expected_type == "boolean":
                    assert field_type is bool, f"Поле '{field_name}' должно быть булевым, получено: {field_type.__name__}"
                elif expected_type == "number":
                    assert field_type in (int, float), f"Поле '{field_name}' должно быть числом, получено: {field_type.__name__}"
                elif expected_type == "object":
                    assert field_type is dict, f"Поле '{field_name}' должно быть объектом, получено: {field_type.__name__}"
                elif expected_type == "array":
                    assert field_type is list, f"Поле '{field_name}' должно быть массивом, получено: {field_type.__name__}"

def _check_response_status(response, expected_statuses, auth_token, endpoint_url):
    """Общая функция для проверки статуса ответа"""
    assert response.status_code in expected_statuses, (
        f"Ожидался один из статусов {expected_statuses}, получен {response.status_code}. "
        f"cURL-запрос для воспроизведения: curl --location '{endpoint_url}' "
        f"--header 'x-access-token: {auth_token}'"
    )

def _validate_json_response(response, auth_token, endpoint_url):
    """Общая функция для валидации JSON ответа"""
    try:
        data = response.json()
    except json.JSONDecodeError as e:
        pytest.fail(
            f"Ответ не является валидным JSON: {e}. "
            f"cURL-запрос для воспроизведения: curl --location '{endpoint_url}' "
            f"--header 'x-access-token: {auth_token}'"
        )
    return data

@pytest.mark.parametrize("params,expected_statuses", PARAMS)
def test_restore_config_status_success(api_client, auth_token, params, expected_statuses):
    """
    Тест успешного получения статуса восстановления конфигурации.
    Проверяет различные комбинации параметров и валидирует структуру ответа.
    
    Возможные ответы API:
    - {"error": "unable to find run status"} - режим восстановления не запущен (статус 400)
    - {"message": "OK"} - восстановление прошло успешно (статус 200)
    - {"message": "updating"} - процесс восстановления происходит (статус 200)
    """
    headers = {
        'x-access-token': auth_token
    }
    
    response = api_client.get(ENDPOINT, params=params, headers=headers)
    
    # Проверяем статус-код (допустимы оба: 200 и 400)
    _check_response_status(response, expected_statuses, auth_token, response.url)
    
    # Проверяем, что ответ - валидный JSON
    data = _validate_json_response(response, auth_token, response.url)
    
    # Валидируем структуру ответа по соответствующей схеме
    if response.status_code == 200:
        validate_schema_recursive(data, RESTORE_CONFIG_STATUS_SCHEMA_200)
        # Дополнительные проверки для поля message при статусе 200
        assert "message" in data, "В ответе отсутствует поле 'message'"
        assert isinstance(data["message"], str), "Поле 'message' должно быть строкой"
        assert data["message"] in ["OK", "updating"], f"Неожиданное значение поля 'message': {data['message']}"
    elif response.status_code == 400:
        validate_schema_recursive(data, RESTORE_CONFIG_STATUS_SCHEMA_400)
        # Дополнительные проверки для поля error при статусе 400
        assert "error" in data, "В ответе отсутствует поле 'error'"
        assert isinstance(data["error"], str), "Поле 'error' должно быть строкой"
        # При некоторых конфигурациях бэкенд возвращает "exit 1" вместо сообщения об отсутствии статуса
        assert any(substr in data["error"] for substr in ["unable to find run status", "exit 1"]), (
            f"Неожиданное значение поля 'error': {data['error']}"
        )

def test_restore_config_status_with_auth_headers(api_client, auth_token):
    """
    Тест проверки работы с различными заголовками авторизации.
    """
    headers = {
        'x-access-token': auth_token,
        'Authorization': f'Bearer {auth_token}',
        'X-API-Key': auth_token
    }
    
    response = api_client.get(ENDPOINT, headers=headers)
    
    # Проверяем, что получили ответ (может быть 200 или 400)
    _check_response_status(response, [200, 400], auth_token, response.url)

def test_restore_config_status_response_time(api_client, auth_token, request_timeout):
    """
    Тест времени отклика API.
    """
    import time
    
    headers = {
        'x-access-token': auth_token
    }
    
    start_time = time.time()
    response = api_client.get(ENDPOINT, headers=headers)
    end_time = time.time()
    
    response_time = end_time - start_time
    
    # Проверяем статус-код
    _check_response_status(response, [200, 400], auth_token, response.url)
    
    # Проверяем, что время отклика разумное (используем таймаут из конфига)
    max_expected_time = request_timeout * 0.8  # 80% от таймаута
    assert response_time < max_expected_time, f"Время отклика слишком большое: {response_time:.2f} секунд (максимум {max_expected_time:.2f})"

def test_restore_config_status_concurrent_requests(api_client, auth_token):
    """
    Тест обработки нескольких одновременных запросов.
    """
    import concurrent.futures
    import threading
    
    headers = {
        'x-access-token': auth_token
    }
    
    def make_request():
        return api_client.get(ENDPOINT, headers=headers)
    
    # Делаем 3 одновременных запроса
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(make_request) for _ in range(3)]
        responses = [future.result() for future in futures]
    
    # Проверяем, что все запросы вернули корректные статусы
    for i, response in enumerate(responses):
        _check_response_status(response, [200, 400], auth_token, response.url)

# Дополнительные негативные тесты
def test_restore_config_status_without_auth(api_client):
    """
    Тест без авторизации - должен вернуть 401.
    """
    response = api_client.get(ENDPOINT)
    
    assert response.status_code == 401, (
        f"Ожидался статус 401 без авторизации, получен {response.status_code}. "
        f"cURL-запрос для воспроизведения: curl --location '{response.url}'"
    )

def test_restore_config_status_invalid_token(api_client):
    """
    Тест с невалидным токеном авторизации.
    """
    headers = {
        'x-access-token': 'invalid_token_12345'
    }
    
    response = api_client.get(ENDPOINT, headers=headers)
    
    assert response.status_code in [401], (
        f"Ожидался статус 401 с невалидным токеном, получен {response.status_code}. "
        f"cURL-запрос для воспроизведения: curl --location '{response.url}' "
        f"--header 'x-access-token: invalid_token_12345'"
    )

def test_restore_config_status_malformed_headers(api_client, auth_token):
    """
    Тест с некорректными заголовками.
    """
    headers = {
        'x-access-token': auth_token,
        'Content-Type': 'invalid/content-type',
        'Accept': 'invalid/accept'
    }
    
    response = api_client.get(ENDPOINT, headers=headers)
    
    # API должен корректно обработать некорректные заголовки
    _check_response_status(response, [200, 400], auth_token, response.url)