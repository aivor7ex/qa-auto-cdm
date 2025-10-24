"""
Тесты для эндпоинта /locales сервиса csi-server.

Проверяется:
- Статус-код 200 OK
- Соответствие структуры ответа схеме (массив объектов locales)
- Устойчивость к 35+ различным query-параметрам
- Вывод cURL-команды при ошибке в параметризованных тестах
"""
import pytest
import json
from collections.abc import Mapping, Sequence

ENDPOINT = "/locales"

LOCALE_SCHEMA = {
    "type": "object",
    "properties": {
        "id": {"type": "integer"},
        "name": {"type": "string"},
        "value": {"type": "string"}
    },
    "required": ["id", "name", "value"],
}

# Осмысленная параметризация для тестирования эндпоинта /locales
PARAMS = [
    # --- Базовые позитивные сценарии ---
    pytest.param({}, 200, id="P01: no_params"),
    pytest.param({"filter": '{"id": 1}'}, 200, id="P02: filter_by_id_1"),
    pytest.param({"filter": '{"value": "ru-RU"}'}, 200, id="P03: filter_by_ru_RU"),
    pytest.param({"filter": '{"value": "en-US"}'}, 200, id="P04: filter_by_en_US"),
    pytest.param({"filter": '{"name": "Русский"}'}, 200, id="P05: filter_by_russian_name"),
    pytest.param({"filter": '{"name": "English (US)"}'}, 200, id="P06: filter_by_english_name"),
    
    # --- Фильтрация по диапазонам ---
    pytest.param({"filter": '{"id": {"$gte": 1}}'}, 200, id="P07: filter_id_gte_1"),
    pytest.param({"filter": '{"id": {"$lte": 10}}'}, 200, id="P08: filter_id_lte_10"),
    pytest.param({"filter": '{"id": {"$ne": 999}}'}, 200, id="P09: filter_id_not_999"),
    
    # --- Комбинированные фильтры ---
    pytest.param({"filter": '{"id": 1, "value": "ru-RU"}'}, 200, id="P10: filter_id_1_and_ru_RU"),
    pytest.param({"filter": '{"name": "Русский", "value": "ru-RU"}'}, 200, id="P11: filter_russian_name_and_value"),
    
    # --- Поиск и фильтрация ---
    pytest.param({"search": "рус"}, 200, id="P12: search_russian"),
    pytest.param({"search": "english"}, 200, id="P13: search_english"),
    pytest.param({"q": "locale"}, 200, id="P14: query_locale"),
    pytest.param({"id": "1"}, 200, id="P15: filter_by_id_param"),
    pytest.param({"name": "Русский"}, 200, id="P16: filter_by_name_param"),
    pytest.param({"value": "ru-RU"}, 200, id="P17: filter_by_value_param"),
    
    # --- Сортировка ---
    pytest.param({"sort": "id"}, 200, id="P18: sort_by_id_asc"),
    pytest.param({"sort": "-id"}, 200, id="P19: sort_by_id_desc"),
    pytest.param({"sort": "name"}, 200, id="P20: sort_by_name_asc"),
    pytest.param({"sort": "-name"}, 200, id="P21: sort_by_name_desc"),
    pytest.param({"sort": "value"}, 200, id="P22: sort_by_value_asc"),
    pytest.param({"sort": "-value"}, 200, id="P23: sort_by_value_desc"),
    
    # --- Постраничная навигация ---
    pytest.param({"limit": "10"}, 200, id="P24: pagination_limit_10"),
    pytest.param({"limit": "1"}, 200, id="P25: pagination_limit_1"),
    pytest.param({"offset": "0"}, 200, id="P26: pagination_offset_0"),
    pytest.param({"offset": "1"}, 200, id="P27: pagination_offset_1"),
    
    # --- Комбинации параметров ---
    pytest.param({"sort": "name", "limit": "3"}, 200, id="P28: sort_name_and_limit_3"),
    pytest.param({"filter": '{"id": 1}', "sort": "name"}, 200, id="P29: filter_id_1_and_sort_name"),
    
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
def test_locales_parametrized(api_client, auth_token, params, expected_status):
    """
    Основной параметризованный тест для эндпоинта /locales.
    1. Отправляет GET-запрос с указанными параметрами.
    2. Проверяет соответствие статус-кода ожидаемому.
    3. Для успешных ответов (200) валидирует схему JSON.
    4. В случае падения теста выводит полную cURL-команду для воспроизведения.
    """
    try:
        # Добавляем заголовки авторизации
        headers = {
            'x-access-token': auth_token,
            'token': auth_token  # Используем тот же токен для обоих заголовков
        }
        
        response = api_client.get(ENDPOINT, params=params, headers=headers)
        
        # 1. Проверка статус-кода
        assert response.status_code == expected_status, \
            f"Ожидался статус-код {expected_status}, получен {response.status_code}. Ответ: {response.text}"

        # 2. Валидация схемы ответа
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list), f"Тело ответа не является массивом JSON, получено: {type(data).__name__}"
            # Проверяем структуру каждого locale в ответе
            for locale_data in data:
                _check_types_recursive(locale_data, LOCALE_SCHEMA)

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
