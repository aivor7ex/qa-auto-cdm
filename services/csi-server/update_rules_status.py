"""
Тесты для эндпоинта /update/rules/status сервиса csi-server.

Проверяется:
- Статус-код 200 OK
- Соответствие структуры ответа схеме (объект с информацией о статусе правил)
- Валидация дат и времени (date, createdAt, modifiedAt)
- Проверка обязательных полей и их типов
- Устойчивость к различным query-параметрам (API игнорирует все параметры)
- Вывод cURL-команды при ошибке в параметризованных тестах
"""
import pytest
import json
from collections.abc import Mapping, Sequence
from datetime import datetime
import re

ENDPOINT = "/update/rules/status"

# Схема ответа для update/rules/status на основе реального ответа API
UPDATE_RULES_STATUS_SCHEMA = {
    "type": "object",
    "properties": {
        "current": {
            "type": "object",
            "properties": {
                "id": {"type": "string"},
                "type": {"type": "string"},
                "name": {"type": "string"},
                "date": {"type": "string"},
                "channel": {"type": "string"},
                "files": {"type": "object"},
                "applied": {"type": "boolean"},
                "downloading": {"type": "boolean"},
                "downloaded": {"type": "boolean"},
                "local": {"type": "boolean"},
                "createdAt": {"type": "string"},
                "modifiedAt": {"type": "string"}
            },
            "required": ["id", "type", "name", "date", "channel", "files", "applied", "downloading", "downloaded", "local", "createdAt", "modifiedAt"]
        },
        "latest": {
            "anyOf": [
                {"type": "null"},
                {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "type": {"type": "string"},
                        "name": {"type": "string"},
                        "date": {"type": "string"},
                        "channel": {"type": "string"},
                        "files": {"type": "object"},
                        "applied": {"type": "boolean"},
                        "downloading": {"type": "boolean"},
                        "downloaded": {"type": "boolean"},
                        "local": {"type": "boolean"},
                        "createdAt": {"type": "string"},
                        "modifiedAt": {"type": "string"}
                    },
                    "required": ["id", "type", "name", "date", "channel", "files", "applied", "downloading", "downloaded", "local", "createdAt", "modifiedAt"]
                }
            ]
        }
    },
    "required": ["current", "latest"]
}

# Осмысленная параметризация для тестирования реальной функциональности API
PARAMS = [
    # --- Базовые позитивные сценарии ---
    pytest.param({}, 200, id="P01: no_params"),
    
    # --- Тестирование устойчивости к параметрам (API игнорирует все параметры) ---
    pytest.param({"any_param": "any_value"}, 200, id="P02: single_param_ignored"),
    pytest.param({"unknown": "value"}, 200, id="P03: unknown_param_ignored"),
    pytest.param({"multiple": "params", "another": "value"}, 200, id="P04: multiple_params_ignored"),
    
    # --- Параметры, которые логично могли бы существовать, но API их игнорирует ---
    pytest.param({"id": "rules_release_2025-03-26"}, 200, id="P05: id_param_ignored"),
    pytest.param({"name": "2025-03-26"}, 200, id="P06: name_param_ignored"),
    pytest.param({"type": "rules"}, 200, id="P07: type_param_ignored"),
    pytest.param({"channel": "release"}, 200, id="P08: channel_param_ignored"),
    
    # --- Статусные параметры (API игнорирует) ---
    pytest.param({"applied": "true"}, 200, id="P09: applied_param_ignored"),
    pytest.param({"downloaded": "true"}, 200, id="P10: downloaded_param_ignored"),
    pytest.param({"downloading": "false"}, 200, id="P11: downloading_param_ignored"),
    pytest.param({"local": "false"}, 200, id="P12: local_param_ignored"),
    
    # --- Временные параметры (API игнорирует) ---
    pytest.param({"date": "2025-03-26"}, 200, id="P13: date_param_ignored"),
    pytest.param({"date_from": "2025-03-01"}, 200, id="P14: date_from_param_ignored"),
    pytest.param({"date_to": "2025-03-31"}, 200, id="P15: date_to_param_ignored"),
    pytest.param({"created_after": "2025-07-01T00:00:00Z"}, 200, id="P16: created_after_param_ignored"),
    pytest.param({"modified_before": "2025-08-31T23:59:59Z"}, 200, id="P17: modified_before_param_ignored"),
    
    # --- Поисковые параметры (API игнорирует) ---
    pytest.param({"search": "rules"}, 200, id="P18: search_param_ignored"),
    pytest.param({"q": "update"}, 200, id="P19: query_param_ignored"),
    pytest.param({"filter": "value"}, 200, id="P20: filter_param_ignored"),
    
    # --- Параметры сортировки (API игнорирует) ---
    pytest.param({"sort": "name"}, 200, id="P21: sort_param_ignored"),
    pytest.param({"order": "desc"}, 200, id="P22: order_param_ignored"),
    
    # --- Параметры пагинации (API игнорирует) ---
    pytest.param({"limit": "10"}, 200, id="P23: limit_param_ignored"),
    pytest.param({"offset": "0"}, 200, id="P24: offset_param_ignored"),
    pytest.param({"page": "1"}, 200, id="P25: page_param_ignored"),
    
    # --- Комбинированные параметры (API игнорирует все) ---
    pytest.param({"sort": "name", "limit": "5"}, 200, id="P26: sort_and_limit_ignored"),
    pytest.param({"filter": "value", "sort": "date"}, 200, id="P27: filter_and_sort_ignored"),
    pytest.param({"search": "rules", "limit": "3"}, 200, id="P28: search_and_limit_ignored"),
    
    # --- Граничные значения параметров (API игнорирует) ---
    pytest.param({"limit": "0"}, 200, id="P29: zero_limit_ignored"),
    pytest.param({"limit": "-1"}, 200, id="P30: negative_limit_ignored"),
    pytest.param({"offset": "-5"}, 200, id="P31: negative_offset_ignored"),
    
    # --- Специальные параметры (API игнорирует) ---
    pytest.param({"version": "latest"}, 200, id="P32: version_param_ignored"),
    pytest.param({"status": "active"}, 200, id="P33: status_param_ignored"),
    pytest.param({"environment": "production"}, 200, id="P34: environment_param_ignored"),
    pytest.param({"deployment": "stable"}, 200, id="P35: deployment_param_ignored"),
    
    # --- Дополнительные параметры (API игнорирует) ---
    pytest.param({"force": "true"}, 200, id="P36: force_param_ignored"),
    pytest.param({"dry_run": "true"}, 200, id="P37: dry_run_param_ignored"),
    pytest.param({"verbose": "true"}, 200, id="P38: verbose_param_ignored"),
    pytest.param({"debug": "false"}, 200, id="P39: debug_param_ignored"),
    pytest.param({"cache": "true"}, 200, id="P40: cache_param_ignored"),
    
    # --- Временные параметры (API игнорирует) ---
    pytest.param({"timeout": "30"}, 200, id="P41: timeout_param_ignored"),
    pytest.param({"retry": "3"}, 200, id="P42: retry_param_ignored"),
    pytest.param({"delay": "5"}, 200, id="P43: delay_param_ignored"),
    pytest.param({"interval": "10"}, 200, id="P44: interval_param_ignored"),
    
    # --- Версионные параметры (API игнорирует) ---
    pytest.param({"min_version": "1.0.0"}, 200, id="P45: min_version_param_ignored"),
    pytest.param({"max_version": "2.0.0"}, 200, id="P46: max_version_param_ignored"),
    pytest.param({"exact_version": "1.5.0"}, 200, id="P47: exact_version_param_ignored"),
    
    # --- Сложные комбинации параметров (API игнорирует все) ---
    pytest.param({"filter": '{"applied": true, "downloaded": true}', "sort": "date", "limit": "5"}, 200, id="P48: complex_params_ignored"),
    pytest.param({"search": "rules", "filter": '{"channel": "release"}', "sort": "-name"}, 200, id="P49: search_filter_sort_ignored"),
    pytest.param({"q": "update", "filter": '{"local": false}', "limit": "10", "offset": "0"}, 200, id="P50: query_filter_pagination_ignored"),
]


def _validate_date_format(date_string, field_name):
    """Проверяет корректность формата даты ISO 8601."""
    try:
        # Проверяем, что строка соответствует формату ISO 8601
        datetime.fromisoformat(date_string.replace('Z', '+00:00'))
        return True
    except ValueError:
        return False


def _validate_date_fields(data):
    """Проверяет валидность всех полей с датами в ответе."""
    date_fields = ["date", "createdAt", "modifiedAt"]
    
    for field in date_fields:
        if field in data:
            assert _validate_date_format(data[field], field), \
                f"Поле '{field}' содержит некорректный формат даты: {data[field]}"


def _check_types_recursive(obj, schema):
    """Рекурсивно проверяет типы данных в объекте на соответствие схеме."""
    if "anyOf" in schema:
        assert any(_try_type(obj, s) for s in schema["anyOf"]), f"Тип {type(obj)} не соответствует ни одной из схем в anyOf"
        return

    schema_type = schema.get("type")
    if schema_type == "object":
        assert isinstance(obj, Mapping), f"Ожидался объект (dict), получено: {type(obj).__name__}"
        for key, prop_schema in schema.get("properties", {}).items():
            if key in obj:
                _check_types_recursive(obj[key], prop_schema)
        for required_key in schema.get("required", []):
            assert required_key in obj, f"Обязательное поле '{required_key}' отсутствует в объекте"
    elif schema_type == "array":
        assert isinstance(obj, Sequence) and not isinstance(obj, str), f"Ожидался список (list/tuple), получено: {type(obj).__name__}"
        for item in obj:
            _check_types_recursive(item, schema["items"])
    elif schema_type == "string":
        assert isinstance(obj, str), f"Поле должно быть строкой (string), получено: {type(obj).__name__}"
    elif schema_type == "integer":
        assert isinstance(obj, int), f"Поле должно быть целым числом (integer), получено: {type(obj).__name__}"
    elif schema_type == "boolean":
        assert isinstance(obj, bool), f"Поле должно быть булевым (boolean), получено: {type(obj).__name__}"
    elif schema_type == "null":
        assert obj is None, "Поле должно быть null"


def _try_type(obj, schema):
    """Вспомогательная функция для проверки типа в 'anyOf'."""
    try:
        _check_types_recursive(obj, schema)
        return True
    except AssertionError:
        return False


def _validate_update_rules_status_response(data):
    """Валидирует ответ API update/rules/status."""
    # Проверяем основную структуру
    _check_types_recursive(data, UPDATE_RULES_STATUS_SCHEMA)
    
    # Проверяем валидность дат в current объекте
    if "current" in data and data["current"]:
        _validate_date_fields(data["current"])
    
    # Проверяем валидность дат в latest объекте (если не null)
    if "latest" in data and data["latest"] is not None:
        _validate_date_fields(data["latest"])


def _format_curl_command(api_client, endpoint, params, auth_token):
    """Формирует и возвращает cURL-строку для воспроизведения запроса."""
    base_url = getattr(api_client, "base_url", "http://127.0.0.1:2999")
    full_url = f"{base_url.rstrip('/')}/{endpoint.lstrip('/')}"
    
    # Формируем строку параметров
    param_str = "&".join([f"{k}={v}" for k, v in params.items() if v is not None])
    if param_str:
        full_url += f"?{param_str}"

    curl_command = f"curl --location '{full_url}' \\\n--header 'x-access-token: {auth_token}' \\\n--header 'token: {auth_token}'"
        
    return curl_command


@pytest.mark.parametrize("params, expected_status", PARAMS)
def test_update_rules_status_parametrized(api_client, auth_token, params, expected_status):
    """
    Основной параметризованный тест для эндпоинта /update/rules/status.
    1. Отправляет GET-запрос с указанными параметрами.
    2. Проверяет соответствие статус-кода ожидаемому.
    3. Для успешных ответов (200) валидирует схему JSON.
    4. Проверяет, что API игнорирует все параметры (возвращает одинаковый ответ).
    5. В случае падения теста выводит полную cURL-команду для воспроизведения.
    """
    try:
        # Добавляем заголовки авторизации
        headers = {
            "x-access-token": auth_token,
            "token": auth_token
        }
        
        response = api_client.get(ENDPOINT, params=params, headers=headers)
        
        # 1. Проверка статус-кода
        assert response.status_code == expected_status, \
            f"Ожидался статус-код {expected_status}, получен {response.status_code}. Ответ: {response.text}"

        # 2. Валидация схемы ответа
        if response.status_code == 200:
            data = response.json()
            _validate_update_rules_status_response(data)
            
            # 3. Проверяем, что API игнорирует все параметры
            # Для этого сравниваем ответ с базовым запросом без параметров
            if params:  # Если есть параметры
                base_response = api_client.get(ENDPOINT, headers=headers)
                base_data = base_response.json()
                
                # API должен возвращать одинаковый ответ независимо от параметров
                assert data == base_data, \
                    f"API должен игнорировать параметры {params}. Ответы должны быть идентичными."

    except (AssertionError, json.JSONDecodeError) as e:
        # 4. Формирование и вывод детального отчета об ошибке
        curl_command = _format_curl_command(api_client, ENDPOINT, params, auth_token)
        
        error_message = (
            f"\nТест с параметрами {params} упал.\n"
            f"Ошибка: {e}\n\n"
            "================= Failed Test Request (cURL) ================\n"
            f"{curl_command}\n"
            "============================================================="
        )
        pytest.fail(error_message, pytrace=False)
