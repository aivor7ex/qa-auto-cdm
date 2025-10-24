"""
Тесты для эндпоинта /licenses/valid сервиса csi-server.

Проверяется:
- Статус-код 200 OK
- Соответствие структуры ответа схеме (boolean)
- Устойчивость к различным query-параметрам
- Вывод cURL-команды при ошибке в параметризованных тестах
"""
import pytest
import json
from collections.abc import Mapping, Sequence

ENDPOINT = "/licenses/valid"

# Схема ответа для валидации лицензии
LICENSE_VALID_SCHEMA = {
    "type": "boolean"
}

# Осмысленная параметризация для тестирования эндпоинта /licenses/valid
PARAMS = [
    # --- Базовые позитивные сценарии ---
    pytest.param({}, 200, id="P01: no_params"),
    pytest.param({"check": "true"}, 200, id="P02: check_true"),
    pytest.param({"check": "false"}, 200, id="P03: check_false"),
    pytest.param({"validate": "true"}, 200, id="P04: validate_true"),
    pytest.param({"validate": "false"}, 200, id="P05: validate_false"),
    
    # --- Параметры фильтрации ---
    pytest.param({"filter": "active"}, 200, id="P06: filter_active"),
    pytest.param({"filter": "expired"}, 200, id="P07: filter_expired"),
    pytest.param({"filter": "valid"}, 200, id="P08: filter_valid"),
    pytest.param({"status": "active"}, 200, id="P09: status_active"),
    pytest.param({"status": "expired"}, 200, id="P10: status_expired"),
    
    # --- Параметры времени ---
    pytest.param({"time": "now"}, 200, id="P11: time_now"),
    pytest.param({"date": "today"}, 200, id="P12: date_today"),
    pytest.param({"timestamp": "now"}, 200, id="P13: timestamp_now"),
    
    # --- Параметры лицензии ---
    pytest.param({"license": "all"}, 200, id="P14: license_all"),
    pytest.param({"license": "current"}, 200, id="P15: license_current"),
    pytest.param({"type": "all"}, 200, id="P16: type_all"),
    
    # --- Параметры проверки ---
    pytest.param({"verify": "true"}, 200, id="P17: verify_true"),
    pytest.param({"debug": "true"}, 200, id="P18: debug_true"),
    
    # --- Параметры режима ---
    pytest.param({"mode": "strict"}, 200, id="P19: mode_strict"),
    pytest.param({"strict": "true"}, 200, id="P20: strict_true"),
]


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
    
    # Формируем строку заголовков
    headers_str = " \\\n  ".join([f"-H '{k}: {v}'" for k, v in headers.items()])
    
    curl_command = f"curl --location '{full_url}'"
    if headers_str:
        curl_command += f" \\\n  {headers_str}"
        
    return curl_command


@pytest.mark.parametrize("params, expected_status", PARAMS)
def test_licenses_valid_parametrized(api_client, auth_token, params, expected_status):
    """
    Основной параметризованный тест для эндпоинта /licenses/valid.
    1. Отправляет GET-запрос с указанными параметрами.
    2. Проверяет соответствие статус-кода ожидаемому.
    3. Для успешных ответов (200) валидирует схему JSON.
    4. В случае падения теста выводит полную cURL-команду для воспроизведения.
    """
    try:
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
            # Проверяем, что ответ является boolean
            _check_types_recursive(data, LICENSE_VALID_SCHEMA)
            
            # Дополнительная проверка: ответ должен быть именно true или false
            assert data in [True, False], f"Ответ должен быть boolean true или false, получено: {data}"

    except (AssertionError, json.JSONDecodeError) as e:
        # 3. Формирование и вывод детального отчета об ошибке
        curl_command = _format_curl_command(api_client, ENDPOINT, params, auth_token)
        
        error_message = (
            f"\nТест с параметрами {params} упал.\n"
            f"Ошибка: {e}\n\n"
            "================= Failed Test Request (cURL) ================\n"
            f"{curl_command}\n"
            "============================================================="
        )
        pytest.fail(error_message, pytrace=False)









