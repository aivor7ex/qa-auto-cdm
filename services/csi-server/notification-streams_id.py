"""
Тесты для эндпоинта /notification-streams/{id} сервиса csi-server.

Проверяется:
- Статус-код 200 OK
- Соответствие структуры ответа схеме (объект notification stream)
- Устойчивость к 35+ различным query-параметрам
- Вывод cURL-команды при ошибке в параметризованных тестах
- Динамическое получение ID из списка notification streams
"""
import pytest
import json
from collections.abc import Mapping, Sequence

ENDPOINT = "/notification-streams/{id}"

NOTIFICATION_STREAM_SCHEMA = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
        "name": {"type": "string"},
        "priority": {"type": "string"},
        "userIds": {"type": "array", "items": {"type": "string"}}
    },
    "required": ["id", "name", "priority", "userIds"],
}

# Осмысленная параметризация для тестирования эндпоинта /notification-streams/{id}
PARAMS = [
    # --- Базовые позитивные сценарии ---
    pytest.param({}, 200, id="P01: no_params"),
    pytest.param({"include": "users"}, 200, id="P02: include_users"),
    pytest.param({"include": "details"}, 200, id="P03: include_details"),
    pytest.param({"include": "stats"}, 200, id="P04: include_stats"),
    pytest.param({"include": "users,details"}, 200, id="P05: include_multiple"),
    pytest.param({"include": "users,details,stats"}, 200, id="P06: include_all"),
    
    # --- Фильтрация по полям ---
    pytest.param({"fields": "id,name"}, 200, id="P07: fields_id_name"),
    pytest.param({"fields": "id,priority"}, 200, id="P08: fields_id_priority"),
    pytest.param({"fields": "name,userIds"}, 200, id="P09: fields_name_userIds"),
    pytest.param({"fields": "id,name,priority"}, 200, id="P10: fields_id_name_priority"),
    pytest.param({"fields": "id,name,priority,userIds"}, 200, id="P11: fields_all"),
    
    # --- Параметры расширения ---
    pytest.param({"expand": "users"}, 200, id="P12: expand_users"),
    pytest.param({"expand": "details"}, 200, id="P13: expand_details"),
    pytest.param({"expand": "stats"}, 200, id="P14: expand_stats"),
    pytest.param({"expand": "users,details"}, 200, id="P15: expand_multiple"),
    pytest.param({"expand": "users,details,stats"}, 200, id="P16: expand_all"),
    
    # --- Параметры версионирования ---
    pytest.param({"version": "1"}, 200, id="P17: version_1"),
    pytest.param({"version": "2"}, 200, id="P18: version_2"),
    pytest.param({"version": "latest"}, 200, id="P19: version_latest"),
    pytest.param({"api_version": "v1"}, 200, id="P20: api_version_v1"),
    pytest.param({"api_version": "v2"}, 200, id="P21: api_version_v2"),
    
    # --- Параметры локализации ---
    pytest.param({"lang": "en"}, 200, id="P22: lang_en"),
    pytest.param({"lang": "ru"}, 200, id="P23: lang_ru"),
    pytest.param({"locale": "en_US"}, 200, id="P24: locale_en_US"),
    pytest.param({"locale": "ru_RU"}, 200, id="P25: locale_ru_RU"),
    pytest.param({"timezone": "UTC"}, 200, id="P26: timezone_UTC"),
    pytest.param({"timezone": "Europe/Moscow"}, 200, id="P27: timezone_Moscow"),
    
    # --- Параметры форматирования ---
    pytest.param({"format": "json"}, 200, id="P28: format_json"),
    pytest.param({"pretty": "true"}, 200, id="P29: pretty_true"),
    pytest.param({"pretty": "false"}, 200, id="P30: pretty_false"),
    pytest.param({"indent": "2"}, 200, id="P31: indent_2"),
    pytest.param({"indent": "4"}, 200, id="P32: indent_4"),
    
    # --- Параметры кэширования ---
    pytest.param({"cache": "true"}, 200, id="P33: cache_true"),
    pytest.param({"cache": "false"}, 200, id="P34: cache_false"),
    pytest.param({"cache_control": "no-cache"}, 200, id="P35: cache_control_no_cache"),
    pytest.param({"cache_control": "max-age=3600"}, 200, id="P36: cache_control_max_age"),
    
    # --- Параметры безопасности ---
    pytest.param({"secure": "true"}, 200, id="P37: secure_true"),
    pytest.param({"secure": "false"}, 200, id="P38: secure_false"),
    pytest.param({"validate": "true"}, 200, id="P39: validate_true"),
    pytest.param({"validate": "false"}, 200, id="P40: validate_false"),
    
    # --- Параметры отладки ---
    pytest.param({"debug": "true"}, 200, id="P41: debug_true"),
    pytest.param({"debug": "false"}, 200, id="P42: debug_false"),
    pytest.param({"trace": "true"}, 200, id="P43: trace_true"),
    pytest.param({"trace": "false"}, 200, id="P44: trace_false"),
    
    # --- Параметры метаданных ---
    pytest.param({"meta": "true"}, 200, id="P45: meta_true"),
    pytest.param({"meta": "false"}, 200, id="P46: meta_false"),
    pytest.param({"info": "true"}, 200, id="P47: info_true"),
    pytest.param({"info": "false"}, 200, id="P48: info_false"),
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


def _get_notification_stream_id(api_client, auth_token):
    """
    Получает ID первого notification stream из списка.
    Если список пуст или недоступен, возвращает None.
    """
    try:
        headers = {
            'x-access-token': auth_token,
            'token': auth_token
        }
        
        response = api_client.get("/notification-streams", headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list) and len(data) > 0:
                return data[0].get('id')
        
        return None
    except Exception:
        return None


@pytest.mark.parametrize("params, expected_status", PARAMS)
def test_notification_streams_id_parametrized(api_client, auth_token, params, expected_status):
    """
    Основной параметризованный тест для эндпоинта /notification-streams/{id}.
    1. Получает ID notification stream из списка.
    2. Отправляет GET-запрос с указанными параметрами.
    3. Проверяет соответствие статус-кода ожидаемому.
    4. Для успешных ответов (200) валидирует схему JSON.
    5. В случае падения теста выводит полную cURL-команду для воспроизведения.
    """
    # Получаем ID notification stream
    stream_id = _get_notification_stream_id(api_client, auth_token)
    
    if stream_id is None:
        pytest.skip("Не удалось получить ID notification stream из списка")
    
    try:
        # Формируем endpoint с ID
        endpoint = ENDPOINT.format(id=stream_id)
        
        # Добавляем заголовки авторизации
        headers = {
            'x-access-token': auth_token,
            'token': auth_token
        }
        
        response = api_client.get(endpoint, params=params, headers=headers)
        
        # 1. Проверка статус-кода
        assert response.status_code == expected_status, \
            f"Ожидался статус-код {expected_status}, получен {response.status_code}. Ответ: {response.text}"

        # 2. Валидация схемы ответа
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, dict), f"Тело ответа не является объектом JSON, получено: {type(data).__name__}"
            # Проверяем структуру notification stream
            _check_types_recursive(data, NOTIFICATION_STREAM_SCHEMA)

    except (AssertionError, json.JSONDecodeError) as e:
        # 3. Формирование и вывод детального отчета об ошибке
        endpoint = ENDPOINT.format(id=stream_id)
        curl_command = _format_curl_command(api_client, endpoint, params, auth_token)
        
        error_message = (
            f"\nТест с параметрами {params} упал.\n"
            f"ID notification stream: {stream_id}\n"
            f"Ошибка: {e}\n\n"
            "================= Failed Test Request (cURL) ================\n"
            f"{curl_command}\n"
            "============================================================="
        )
        pytest.fail(error_message, pytrace=False)
