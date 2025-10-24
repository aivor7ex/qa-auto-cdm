"""
Тесты для эндпоинта /licenses сервиса csi-server.

Проверяется:
- Статус-код 200 OK
- Соответствие структуры ответа схеме (объект лицензии)
- Валидация даты и времени
- Устойчивость к 35+ различным query-параметрам
- Вывод cURL-команды при ошибке в параметризованных тестах
"""
import pytest
import json
import re
from datetime import datetime
from collections.abc import Mapping, Sequence

ENDPOINT = "/licenses"

# Схема ответа для лицензии
LICENSE_SCHEMA = {
    "type": "object",
    "properties": {
        "licenseNumber": {"type": "string"},
        "expiresAt": {"type": "string"},
        "createdAt": {"type": "string"}
    },
    "required": ["licenseNumber", "expiresAt", "createdAt"],
}

def is_valid_datetime(date_string):
    """Проверяет, является ли строка валидной датой в формате ISO 8601."""
    if not isinstance(date_string, str):
        return False
    try:
        datetime.fromisoformat(date_string.replace('Z', '+00:00'))
        return True
    except ValueError:
        return False

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
        # Проверяем паттерн если он задан
        if "pattern" in schema:
            pattern = schema["pattern"]
            assert re.match(pattern, obj), f"Строка не соответствует паттерну {pattern}: {obj}"
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





def _format_curl_command(api_client, endpoint, params, auth_token=None):
    """Формирует и возвращает cURL-строку для воспроизведения запроса."""
    base_url = getattr(api_client, "base_url", "http://127.0.0.1")
    full_url = f"{base_url.rstrip('/')}/{endpoint.lstrip('/')}"
    
    # Формируем строку параметров
    param_str = "&".join([f"{k}={v}" for k, v in params.items() if v is not None])
    if param_str:
        full_url += f"?{param_str}"

    # Базовые заголовки
    headers = getattr(api_client, 'headers', {}).copy()
    
    # Добавляем заголовки авторизации если токен предоставлен
    if auth_token:
        headers['x-access-token'] = auth_token
        headers['token'] = auth_token
    
    headers_str = " \\\n  ".join([f"-H '{k}: {v}'" for k, v in headers.items()])
    
    curl_command = f"curl -X GET '{full_url}'"
    if headers_str:
        curl_command += f" \\\n  {headers_str}"
        
    return curl_command


# Осмысленная параметризация для тестирования эндпоинта /licenses
PARAMS = [
    # --- Базовые позитивные сценарии ---
    pytest.param({}, 200, id="P01: no_params"),
    pytest.param({"format": "json"}, 200, id="P02: format_json"),
    
    # --- Фильтрация по типу лицензии ---
    pytest.param({"type": "license"}, 200, id="P03: type_license"),
    pytest.param({"type": "trial"}, 200, id="P04: type_trial"),
    pytest.param({"type": "standard"}, 200, id="P05: type_standard"),
    pytest.param({"license_type": "trial"}, 200, id="P06: license_type_trial"),
    pytest.param({"license_type": "standard"}, 200, id="P07: license_type_standard"),
    pytest.param({"license_type": "premium"}, 200, id="P08: license_type_premium"),
    
    # --- Фильтрация по статусу ---
    pytest.param({"status": "active"}, 200, id="P09: status_active"),
    pytest.param({"status": "inactive"}, 200, id="P10: status_inactive"),
    pytest.param({"status": "expired"}, 200, id="P11: status_expired"),
    pytest.param({"status": "valid"}, 200, id="P12: status_valid"),
    
    # --- Фильтрация по датам ---
    pytest.param({"created_after": "2023-01-01"}, 200, id="P13: created_after_2023"),
    pytest.param({"created_before": "2024-12-31"}, 200, id="P14: created_before_2024"),
    pytest.param({"expires_after": "2024-01-01"}, 200, id="P15: expires_after_2024"),
    pytest.param({"expires_before": "2025-12-31"}, 200, id="P16: expires_before_2025"),
    
    # --- Комбинированные фильтры ---
    pytest.param({"type": "trial", "status": "active"}, 200, id="P17: trial_active"),
    pytest.param({"license_type": "standard", "status": "valid"}, 200, id="P18: standard_valid"),
    pytest.param({"format": "json", "type": "license"}, 200, id="P19: json_license"),
    pytest.param({"status": "active", "created_after": "2023-01-01"}, 200, id="P20: active_after_2023"),
    
    # --- Поиск и фильтрация ---
    pytest.param({"search": "license"}, 200, id="P21: search_license"),
    pytest.param({"search": "trial"}, 200, id="P22: search_trial"),
    pytest.param({"q": "number"}, 200, id="P23: query_number"),
    pytest.param({"filter": '{"status": "active"}'}, 200, id="P24: filter_active"),
    pytest.param({"filter": '{"license_type": "trial"}'}, 200, id="P25: filter_trial"),
    pytest.param({"filter": '{"licenseNumber": "trial"}'}, 200, id="P26: filter_trial_number"),
    
    # --- Сортировка ---
    pytest.param({"sort": "created"}, 200, id="P27: sort_by_created"),
    pytest.param({"sort": "-created"}, 200, id="P28: sort_by_created_desc"),
    pytest.param({"sort": "expires"}, 200, id="P29: sort_by_expires"),
    pytest.param({"sort": "-expires"}, 200, id="P30: sort_by_expires_desc"),
    pytest.param({"sort": "licenseNumber"}, 200, id="P31: sort_by_license_number"),
    
    # --- Постраничная навигация ---
    pytest.param({"limit": "10"}, 200, id="P32: pagination_limit_10"),
    pytest.param({"limit": "1"}, 200, id="P33: pagination_limit_1"),
    pytest.param({"offset": "5"}, 200, id="P34: pagination_offset_5"),
    pytest.param({"limit": "5", "offset": "2"}, 200, id="P35: pagination_limit_offset"),
]


@pytest.mark.parametrize("params, expected_status", PARAMS)
def test_licenses_parametrized(api_client, auth_token, params, expected_status):
    """
    Основной параметризованный тест для эндпоинта /licenses.
    1. Отправляет GET-запрос с указанными параметрами.
    2. Проверяет соответствие статус-кода ожидаемому.
    3. Для успешных ответов (200) валидирует схему JSON и даты.
    4. В случае падения теста выводит полную cURL-команду для воспроизведения.
    """
    try:
        # Добавляем заголовки авторизации
        headers = {
            'x-access-token': auth_token,
            'token': auth_token
        }
        
        response = api_client.get(ENDPOINT, params=params, headers=headers)
        
        # 1. Проверка статус-кода
        assert response.status_code == expected_status, \
            f"Ожидался статус-код {expected_status}, получен {response.status_code}. Ответ: {response.text}"

        # 2. Валидация схемы ответа
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, dict), f"Тело ответа не является объектом JSON, получено: {type(data).__name__}"
            
            # Проверяем структуру лицензии
            _check_types_recursive(data, LICENSE_SCHEMA)
            
            # 3. Валидация дат и времени
            if "expiresAt" in data:
                assert is_valid_datetime(data["expiresAt"]), f"Поле expiresAt содержит невалидную дату: {data['expiresAt']}"
            
            if "createdAt" in data:
                assert is_valid_datetime(data["createdAt"]), f"Поле createdAt содержит невалидную дату: {data['createdAt']}"

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





def test_licenses_basic(api_client, auth_token):
    """
    Базовый тест для эндпоинта /licenses без параметров.
    Проверяет основную функциональность и структуру ответа.
    """
    try:
        headers = {
            'x-access-token': auth_token,
            'token': auth_token
        }
        
        response = api_client.get(ENDPOINT, headers=headers)
        
        # Проверяем статус-код
        assert response.status_code == 200, \
            f"Ожидался статус-код 200, получен {response.status_code}. Ответ: {response.text}"

        # Валидируем схему ответа
        data = response.json()
        assert isinstance(data, dict), f"Тело ответа не является объектом JSON, получено: {type(data).__name__}"
        
        # Проверяем структуру лицензии
        _check_types_recursive(data, LICENSE_SCHEMA)
        
        # Валидируем даты
        if "expiresAt" in data:
            assert is_valid_datetime(data["expiresAt"]), f"Поле expiresAt содержит невалидную дату: {data['expiresAt']}"
        
        if "createdAt" in data:
            assert is_valid_datetime(data["createdAt"]), f"Поле createdAt содержит невалидную дату: {data['createdAt']}"

    except (AssertionError, json.JSONDecodeError) as e:
        curl_command = _format_curl_command(api_client, ENDPOINT, {}, auth_token)
        
        error_message = (
            f"\nБазовый тест упал.\n"
            f"Ошибка: {e}\n\n"
            "================= Failed Test Request (cURL) ================\n"
            f"{curl_command}\n"
            "============================================================="
        )
        pytest.fail(error_message, pytrace=False)


def test_licenses_date_validation(api_client, auth_token):
    """
    Специальный тест для валидации дат и времени в ответе.
    Проверяет корректность формата ISO 8601 для полей expiresAt и createdAt.
    """
    try:
        headers = {
            'x-access-token': auth_token,
            'token': auth_token
        }
        
        response = api_client.get(ENDPOINT, headers=headers)
        
        assert response.status_code == 200, \
            f"Ожидался статус-код 200, получен {response.status_code}. Ответ: {response.text}"

        data = response.json()
        
        # Проверяем наличие обязательных полей с датами
        assert "expiresAt" in data, "Поле expiresAt отсутствует в ответе"
        assert "createdAt" in data, "Поле createdAt отсутствует в ответе"
        
        # Валидируем формат дат
        expires_at = data["expiresAt"]
        created_at = data["createdAt"]
        
        assert is_valid_datetime(expires_at), f"Поле expiresAt содержит невалидную дату: {expires_at}"
        assert is_valid_datetime(created_at), f"Поле createdAt содержит невалидную дату: {created_at}"
        
        # Проверяем логику дат (createdAt должно быть раньше expiresAt)
        try:
            expires_dt = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
            created_dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            
            assert created_dt <= expires_dt, \
                f"Дата создания ({created_at}) должна быть раньше или равна дате истечения ({expires_at})"
                
        except ValueError as e:
            pytest.fail(f"Ошибка парсинга дат: {e}")

    except (AssertionError, json.JSONDecodeError) as e:
        curl_command = _format_curl_command(api_client, ENDPOINT, {}, auth_token)
        
        error_message = (
            f"\nТест валидации дат упал.\n"
            f"Ошибка: {e}\n\n"
            "================= Failed Test Request (cURL) ================\n"
            f"{curl_command}\n"
            "============================================================="
        )
        pytest.fail(error_message, pytrace=False)
