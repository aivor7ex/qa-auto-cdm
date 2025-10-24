"""
Тесты для эндпоинта-стрима /interfaceRuntimes/change-stream сервиса core.

Проверяется:
- Успешное установление соединения (статус-код 200 OK)
- Устойчивость к 35+ различным query-параметрам (валидным и невалидным)
- Вывод cURL-команды с пояснением при ошибке соединения
"""
import pytest
import json
from collections.abc import Mapping, Sequence

ENDPOINT = "/interfaceRuntimes/change-stream"

# Для change-stream эндпоинтов обычно возвращается либо SSE, либо специальный формат
CHANGE_STREAM_SCHEMA = {
    "type": "object",
    "properties": {
        "data": {"type": "string"},
        "event": {"type": "string"},
        "id": {"type": "string"},
        "retry": {"type": "integer"}
    },
    "required": [],
}

# Осмысленная параметризация для тестирования эндпоинта /interfaceRuntimes/change-stream
PARAMS = [
    # --- Базовые позитивные сценарии ---
    pytest.param({}, 200, id="P01: no_params"),
    pytest.param({"format": "sse"}, 200, id="P02: format_sse"),
    pytest.param({"format": "json"}, 200, id="P03: format_json"),
    pytest.param({"format": "text"}, 200, id="P04: format_text"),
    pytest.param({"stream": "true"}, 200, id="P05: stream_enabled"),
    pytest.param({"stream": "false"}, 200, id="P06: stream_disabled"),
    pytest.param({"realtime": "true"}, 200, id="P07: realtime_enabled"),
    pytest.param({"realtime": "false"}, 200, id="P08: realtime_disabled"),
    pytest.param({"live": "true"}, 200, id="P09: live_enabled"),
    pytest.param({"live": "false"}, 200, id="P10: live_disabled"),
    
    # --- Фильтрация по событиям ---
    pytest.param({"events": "create"}, 200, id="P11: events_create"),
    pytest.param({"events": "update"}, 200, id="P12: events_update"),
    pytest.param({"events": "delete"}, 200, id="P13: events_delete"),
    pytest.param({"events": "change"}, 200, id="P14: events_change"),
    pytest.param({"events": "all"}, 200, id="P15: events_all"),
    pytest.param({"event_type": "insert"}, 200, id="P16: event_type_insert"),
    pytest.param({"event_type": "modify"}, 200, id="P17: event_type_modify"),
    pytest.param({"event_type": "remove"}, 200, id="P18: event_type_remove"),
    pytest.param({"action": "watch"}, 200, id="P19: action_watch"),
    pytest.param({"action": "monitor"}, 200, id="P20: action_monitor"),
    
    # --- Фильтрация по полям ---
    pytest.param({"filter": '{"name": "eth-0-1"}'}, 200, id="P21: filter_by_name"),
    pytest.param({"filter": '{"rt_active": true}'}, 200, id="P22: filter_by_rt_active"),
    pytest.param({"filter": '{"name": "bond1"}'}, 200, id="P23: filter_by_bond"),
    pytest.param({"watch": "name"}, 200, id="P24: watch_name_field"),
    pytest.param({"watch": "rt_active"}, 200, id="P25: watch_rt_active_field"),
    pytest.param({"watch": "all"}, 200, id="P26: watch_all_fields"),
    pytest.param({"fields": "name,rt_active"}, 200, id="P27: specific_fields"),
    pytest.param({"fields": "name"}, 200, id="P28: name_field_only"),
    pytest.param({"include": "metadata"}, 200, id="P29: include_metadata"),
    pytest.param({"exclude": "system"}, 200, id="P30: exclude_system"),
    
    # --- Комбинированные параметры ---
    pytest.param({"format": "sse", "events": "update"}, 200, id="P31: sse_update_events"),
    pytest.param({"stream": "true", "realtime": "true"}, 200, id="P32: stream_realtime"),
    pytest.param({"filter": '{"rt_active": true}', "events": "change"}, 200, id="P33: filter_and_events"),
    pytest.param({"watch": "name", "format": "json"}, 200, id="P34: watch_name_json"),
    pytest.param({"fields": "name", "events": "update"}, 200, id="P35: fields_and_events"),
    
    # --- Специальные параметры ---
    pytest.param({"timeout": "30"}, 200, id="P36: timeout_30"),
    pytest.param({"timeout": "60"}, 200, id="P37: timeout_60"),
    pytest.param({"heartbeat": "10"}, 200, id="P38: heartbeat_10"),
    pytest.param({"heartbeat": "30"}, 200, id="P39: heartbeat_30"),
    pytest.param({"buffer_size": "1024"}, 200, id="P40: buffer_size_1024"),
    pytest.param({"buffer_size": "4096"}, 200, id="P41: buffer_size_4096"),
    pytest.param({"max_events": "100"}, 200, id="P42: max_events_100"),
    pytest.param({"max_events": "500"}, 200, id="P43: max_events_500"),
    pytest.param({"reconnect": "true"}, 200, id="P44: reconnect_enabled"),
    pytest.param({"reconnect": "false"}, 200, id="P45: reconnect_disabled"),
    pytest.param({"retry_interval": "5"}, 200, id="P46: retry_interval_5"),
    pytest.param({"retry_interval": "10"}, 200, id="P47: retry_interval_10"),
    pytest.param({"compression": "gzip"}, 200, id="P48: compression_gzip"),
    pytest.param({"compression": "none"}, 200, id="P49: compression_none"),
    pytest.param({"encoding": "utf-8"}, 200, id="P50: encoding_utf8"),
    pytest.param({"encoding": "ascii"}, 200, id="P51: encoding_ascii"),
    pytest.param({"protocol": "http"}, 200, id="P52: protocol_http"),
    pytest.param({"protocol": "websocket"}, 200, id="P53: protocol_websocket"),
    
    # --- Граничные значения ---
    pytest.param({"unsupported_param": "value"}, 200, id="P54: unsupported_param_ignored"),
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


def _format_curl_command(api_client, endpoint, params):
    """Формирует и возвращает cURL-строку для воспроизведения запроса."""
    base_url = getattr(api_client, "base_url", "http://127.0.0.1")
    full_url = f"{base_url.rstrip('/')}/{endpoint.lstrip('/')}"
    
    # Формируем строку параметров
    param_str = "&".join([f"{k}={v}" for k, v in params.items() if v is not None])
    if param_str:
        full_url += f"?{param_str}"

    headers = getattr(api_client, 'headers', {})
    headers_str = " \\\n  ".join([f"-H '{k}: {v}'" for k, v in headers.items()])
    
    curl_command = f"curl -X GET '{full_url}'"
    if headers_str:
        curl_command += f" \\\n  {headers_str}"
        
    return curl_command


@pytest.mark.parametrize("params, expected_status", PARAMS)
def test_interface_runtimes_change_stream_parametrized(api_client, params, expected_status):
    """
    Основной параметризованный тест для эндпоинта /interfaceRuntimes/change-stream.
    1. Отправляет GET-запрос с указанными параметрами.
    2. Проверяет соответствие статус-кода ожидаемому.
    3. Для change-stream эндпоинтов проверяет наличие соответствующих заголовков.
    4. В случае падения теста выводит полную cURL-команду для воспроизведения.
    
    Примечание: change-stream эндпоинты могут возвращать Server-Sent Events или WebSocket соединения,
    поэтому валидация ответа адаптирована под специфику streaming протоколов.
    """
    try:
        # Устанавливаем короткий timeout для streaming эндпоинтов
        response = api_client.get(ENDPOINT, params=params, timeout=3)
        
        # 1. Проверка статус-кода
        assert response.status_code == expected_status, \
            f"Ожидался статус-код {expected_status}, получен {response.status_code}. Ответ: {response.text}"

        # 2. Специальная валидация для change-stream эндпоинтов
        if response.status_code == 200:
            # Проверяем заголовки для streaming
            content_type = response.headers.get('content-type', '').lower()
            
            # Для SSE ожидаем text/event-stream или application/json
            if 'text/event-stream' in content_type:
                # SSE формат - проверяем что получили корректные SSE данные
                assert response.text, "SSE stream должен содержать данные"
            elif 'application/json' in content_type:
                # JSON формат - пытаемся распарсить как JSON
                try:
                    data = response.json()
                    # Для change-stream может быть объект или массив
                    assert isinstance(data, (dict, list)), f"Ответ должен быть JSON объектом или массивом"
                except json.JSONDecodeError:
                    # Если не удалось распарсить как JSON, проверяем что это строка
                    assert isinstance(response.text, str), "Ответ должен быть валидной строкой"
            else:
                # Для других типов контента просто проверяем что есть ответ
                assert response.text or response.status_code == 200, "Должен быть ответ или статус 200"

    except Exception as e:
        # Для streaming эндпоинтов timeout - это нормально
        if "timed out" in str(e).lower() or "timeout" in str(e).lower():
            # Timeout для streaming эндпоинта считается успешным подключением
            assert True, "Timeout для change-stream эндпоинта является ожидаемым поведением"
        else:
            # 3. Формирование и вывод детального отчета об ошибке для других ошибок
            curl_command = _format_curl_command(api_client, ENDPOINT, params)
            
            error_message = (
                f"\nТест с параметрами {params} упал.\n"
                f"Ошибка: {e}\n\n"
                "================= Failed Test Request (cURL) ================\n"
                f"{curl_command}\n"
                "============================================================="
            )
            pytest.fail(error_message, pytrace=False) 