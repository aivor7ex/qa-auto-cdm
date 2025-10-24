"""
Тесты для эндпоинта /config сервиса csi-server.

Проверяется:
- Статус-код 200 OK
- Соответствие структуры ответа схеме (массив объектов конфигурации)
- Устойчивость к 35+ различным query-параметрам
- Вывод cURL-команды при ошибке в параметризованных тестах
"""
import pytest
import json
from collections.abc import Mapping, Sequence

ENDPOINT = "/config"

# Схема ответа на основе предоставленного примера
CONFIG_SCHEMA = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "stackName": {"type": "string"},
            "serviceName": {"type": "string"},
            "config": {
                "type": "object",
                "properties": {
                    "SecuritySettings": {
                        "type": "array",
                        "items": {"type": "object"}
                    },
                    "NotificationStream": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string"},
                                "name": {"type": "string"},
                                "priority": {"type": "string"},
                                "userIds": {
                                    "type": "array",
                                    "items": {"type": "string"}
                                }
                            },
                            "required": ["id", "name", "priority", "userIds"]
                        }
                    }
                },
                "required": ["SecuritySettings", "NotificationStream"]
            }
        },
        "required": ["stackName", "serviceName", "config"]
    }
}

# Осмысленная параметризация для тестирования эндпоинта /config
PARAMS = [
    # --- Базовые позитивные сценарии ---
    pytest.param({}, 200, id="P01: no_params"),
    pytest.param({"format": "json"}, 200, id="P02: format_json"),
    pytest.param({"pretty": "true"}, 200, id="P03: pretty_true"),
    pytest.param({"pretty": "false"}, 200, id="P04: pretty_false"),
    pytest.param({"indent": "2"}, 200, id="P05: indent_2"),
    pytest.param({"indent": "4"}, 200, id="P06: indent_4"),
    
    # --- Фильтрация по стеку ---
    pytest.param({"stack": "csi"}, 200, id="P07: filter_stack_csi"),
    pytest.param({"stackName": "csi"}, 200, id="P08: filter_stackname_csi"),
    pytest.param({"service": "csi-server"}, 200, id="P09: filter_service_csi_server"),
    pytest.param({"serviceName": "csi-server"}, 200, id="P10: filter_servicename_csi_server"),
    
    # --- Фильтрация по компонентам конфигурации ---
    pytest.param({"include": "SecuritySettings"}, 200, id="P11: include_security_settings"),
    pytest.param({"include": "NotificationStream"}, 200, id="P12: include_notification_stream"),
    pytest.param({"include": "SecuritySettings,NotificationStream"}, 200, id="P13: include_multiple"),
    pytest.param({"exclude": "SecuritySettings"}, 200, id="P14: exclude_security_settings"),
    pytest.param({"exclude": "NotificationStream"}, 200, id="P15: exclude_notification_stream"),
    
    # --- Фильтрация по уведомлениям ---
    pytest.param({"notification_id": "alerts"}, 200, id="P16: filter_notification_alerts"),
    pytest.param({"notification_id": "information"}, 200, id="P17: filter_notification_information"),
    pytest.param({"notification_id": "warnings"}, 200, id="P18: filter_notification_warnings"),
    pytest.param({"notification_priority": "2"}, 200, id="P19: filter_priority_2"),
    pytest.param({"notification_priority": "3"}, 200, id="P20: filter_priority_3"),
    pytest.param({"notification_priority": "4"}, 200, id="P21: filter_priority_4"),
    
    # --- Поиск и фильтрация ---
    pytest.param({"search": "csi"}, 200, id="P22: search_csi"),
    pytest.param({"search": "server"}, 200, id="P23: search_server"),
    pytest.param({"q": "config"}, 200, id="P24: query_config"),
    pytest.param({"filter": '{"stackName": "csi"}'}, 200, id="P25: filter_json_stackname"),
    pytest.param({"filter": '{"serviceName": "csi-server"}'}, 200, id="P26: filter_json_servicename"),
    
    # --- Сортировка ---
    pytest.param({"sort": "stackName"}, 200, id="P27: sort_by_stackname"),
    pytest.param({"sort": "-stackName"}, 200, id="P28: sort_by_stackname_desc"),
    pytest.param({"sort": "serviceName"}, 200, id="P29: sort_by_servicename"),
    pytest.param({"sort": "-serviceName"}, 200, id="P30: sort_by_servicename_desc"),
    
    # --- Постраничная навигация ---
    pytest.param({"limit": "10"}, 200, id="P31: pagination_limit_10"),
    pytest.param({"limit": "1"}, 200, id="P32: pagination_limit_1"),
    pytest.param({"offset": "0"}, 200, id="P33: pagination_offset_0"),
    pytest.param({"limit": "5", "offset": "0"}, 200, id="P34: pagination_limit_offset"),
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

    headers = getattr(api_client, 'headers', {})
    if auth_token:
        headers['x-access-token'] = auth_token
        headers['token'] = auth_token
    headers_str = " \\\n  ".join([f"-H '{k}: {v}'" for k, v in headers.items()])
    
    curl_command = f"curl --location '{full_url}'"
    if headers_str:
        curl_command += f" \\\n  {headers_str}"
        
    return curl_command


@pytest.mark.parametrize("params, expected_status", PARAMS)
def test_config_parametrized(api_client, auth_token, params, expected_status):
    """
    Основной параметризованный тест для эндпоинта /config.
    1. Отправляет GET-запрос с указанными параметрами.
    2. Проверяет соответствие статус-кода ожидаемому.
    3. Для успешных ответов (200) валидирует схему JSON.
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
            assert isinstance(data, list), f"Тело ответа не является массивом JSON, получено: {type(data).__name__}"
            # Проверяем структуру каждого элемента конфигурации в ответе
            for config_item in data:
                _check_types_recursive(config_item, CONFIG_SCHEMA["items"])

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
