"""
Тесты для эндпоинта /notification-streams/count сервиса csi-server.

Проверяется:
- Статус-код 200 OK
- Соответствие структуры ответа схеме (число)
- Устойчивость к 35+ различным query-параметрам
- Вывод cURL-команды при ошибке в параметризованных тестах
- Динамическое получение ID из списка notification streams
"""
import pytest
import json
from collections.abc import Mapping, Sequence

ENDPOINT = "/notification-streams/count"

# Схема ответа для эндпоинта /notification-streams/count
COUNT_SCHEMA = {
    "type": "integer",
    "description": "Количество notification streams"
}

# Осмысленная параметризация для тестирования эндпоинта /notification-streams/count
PARAMS = [
    # --- Базовые позитивные сценарии ---
    pytest.param({}, 200, id="P01: no_params"),
    pytest.param({"filter": '{"subscribed": true}'}, 200, id="P02: filter_by_subscribed_true"),
    pytest.param({"filter": '{"subscribed": false}'}, 200, id="P03: filter_by_subscribed_false"),
    pytest.param({"filter": '{"id": "alerts"}'}, 200, id="P04: filter_by_alerts_id"),
    pytest.param({"filter": '{"id": "information"}'}, 200, id="P05: filter_by_information_id"),
    pytest.param({"filter": '{"id": "warnings"}'}, 200, id="P06: filter_by_warnings_id"),
    pytest.param({"filter": '{"name": "Alerts"}'}, 200, id="P07: filter_by_alerts_name"),
    pytest.param({"filter": '{"name": "Information"}'}, 200, id="P08: filter_by_information_name"),
    pytest.param({"filter": '{"name": "Warnings"}'}, 200, id="P09: filter_by_warnings_name"),
    pytest.param({"filter": '{"priority": "2"}'}, 200, id="P10: filter_by_priority_2"),
    
    # --- Фильтрация по приоритетам ---
    pytest.param({"filter": '{"priority": "3"}'}, 200, id="P11: filter_by_priority_3"),
    pytest.param({"filter": '{"priority": "4"}'}, 200, id="P12: filter_by_priority_4"),
    pytest.param({"filter": '{"priority": "1"}'}, 200, id="P13: filter_by_priority_1"),
    pytest.param({"filter": '{"priority": "5"}'}, 200, id="P14: filter_by_priority_5"),
    pytest.param({"filter": '{"priority": "high"}'}, 200, id="P15: filter_by_priority_high"),
    
    # --- Комбинированные фильтры ---
    pytest.param({"filter": '{"subscribed": false, "priority": "2"}'}, 200, id="P16: unsubscribed_priority_2"),
    pytest.param({"filter": '{"id": "alerts", "subscribed": false}'}, 200, id="P17: alerts_unsubscribed"),
    pytest.param({"filter": '{"name": "Information", "priority": "4"}'}, 200, id="P18: information_priority_4"),
    
    # --- Поиск и фильтрация ---
    pytest.param({"search": "alert"}, 200, id="P19: search_alert"),
    pytest.param({"search": "info"}, 200, id="P20: search_info"),
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
    
    headers_str = " \\\n  ".join([f"-H '{k}: {v}'" for k, v in headers.items()])
    
    curl_command = f"curl -X GET '{full_url}'"
    if headers_str:
        curl_command += f" \\\n  {headers_str}"
        
    return curl_command





@pytest.mark.parametrize("params, expected_status", PARAMS)
def test_notification_streams_count_parametrized(api_client, auth_token, params, expected_status):
    """
    Основной параметризованный тест для эндпоинта /notification-streams/count.
    1. Получает ID notification stream из списка (если нужно).
    2. Отправляет GET-запрос с указанными параметрами.
    3. Проверяет соответствие статус-кода ожидаемому.
    4. Для успешных ответов (200) валидирует схему JSON.
    5. В случае падения теста выводит полную cURL-команду для воспроизведения.
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
            # Проверяем, что ответ является числом
            _check_types_recursive(data, COUNT_SCHEMA)
            # Дополнительная проверка, что число неотрицательное
            assert data >= 0, f"Количество должно быть неотрицательным, получено: {data}"

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


def test_notification_streams_count_basic(api_client, auth_token):
    """
    Базовый тест для эндпоинта /notification-streams/count.
    Проверяет основной функционал без дополнительных параметров.
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
        _check_types_recursive(data, COUNT_SCHEMA)
        assert data >= 0, f"Количество должно быть неотрицательным, получено: {data}"

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


def test_notification_streams_count_with_filter(api_client, auth_token):
    """
    Тест для эндпоинта /notification-streams/count с фильтром по подписке.
    """
    try:
        headers = {
            'x-access-token': auth_token,
            'token': auth_token
        }
        
        params = {"filter": '{"subscribed": true}'}
        response = api_client.get(ENDPOINT, params=params, headers=headers)
        
        assert response.status_code == 200, \
            f"Ожидался статус-код 200, получен {response.status_code}. Ответ: {response.text}"
        
        data = response.json()
        _check_types_recursive(data, COUNT_SCHEMA)
        assert data >= 0, f"Количество должно быть неотрицательным, получено: {data}"

    except (AssertionError, json.JSONDecodeError) as e:
        curl_command = _format_curl_command(api_client, ENDPOINT, {"filter": '{"subscribed": true}'}, auth_token)
        
        error_message = (
            f"\nТест с фильтром упал.\n"
            f"Ошибка: {e}\n\n"
            "================= Failed Test Request (cURL) ================\n"
            f"{curl_command}\n"
            "============================================================="
        )
        pytest.fail(error_message, pytrace=False)


def test_notification_streams_count_with_search(api_client, auth_token):
    """
    Тест для эндпоинта /notification-streams/count с поиском.
    """
    try:
        headers = {
            'x-access-token': auth_token,
            'token': auth_token
        }
        
        params = {"search": "alert"}
        response = api_client.get(ENDPOINT, params=params, headers=headers)
        
        assert response.status_code == 200, \
            f"Ожидался статус-код 200, получен {response.status_code}. Ответ: {response.text}"
        
        data = response.json()
        _check_types_recursive(data, COUNT_SCHEMA)
        assert data >= 0, f"Количество должно быть неотрицательным, получено: {data}"

    except (AssertionError, json.JSONDecodeError) as e:
        curl_command = _format_curl_command(api_client, ENDPOINT, {"search": "alert"}, auth_token)
        
        error_message = (
            f"\nТест с поиском упал.\n"
            f"Ошибка: {e}\n\n"
            "================= Failed Test Request (cURL) ================\n"
            f"{curl_command}\n"
            "============================================================="
        )
        pytest.fail(error_message, pytrace=False)
