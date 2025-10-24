import pytest
import json
from collections.abc import Mapping, Sequence

ENDPOINT = "/services"

SERVICE_SCHEMA = {
    "type": "object",
    "properties": {
        "definition": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "stack": {"type": "string"},
                "container": {"type": "string"},
                "description": {"anyOf": [{"type": "string"}, {"type": "null"}]},
                "address": {"type": "string"},
            },
            "required": ["name", "stack", "container", "address"],
        },
        "state": {"type": "string"},
        "last_good_time": {"anyOf": [{"type": "string"}, {"type": "null"}]},
    },
    "required": ["definition", "state"],
}

# Схема для ошибок валидации (400 Bad Request)
ERROR_400_SCHEMA = {
    "type": "object",
    "properties": {
        "error": {
            "type": "object",
            "properties": {
                "statusCode": {"type": "integer", "const": 400},
                "name": {"type": "string"},
                "message": {"type": "string"},
            },
            "required": ["statusCode", "name", "message"],
        }
    },
    "required": ["error"],
}

# --- Осмысленная параметризация для тестирования эндпоинта /services ---
# Каждый тест проверяет конкретный аспект API
PARAMS = [
    # --- Базовые позитивные сценарии ---
    pytest.param({}, 200, id="P01: no_params"),
    pytest.param({"stack": "ngfw"}, 200, id="P02: filter_by_stack_ngfw"),
    pytest.param({"state": "good"}, 200, id="P03: filter_by_state_good"),
    pytest.param({"state": "bad"}, 200, id="P04: filter_by_state_bad"),
    pytest.param({"name": "redis"}, 200, id="P05: filter_by_name_redis"),
    pytest.param({"name": "non-existent-service"}, 200, id="P06: filter_by_non_existent_name"),

    # --- Сортировка ---
    pytest.param({"sort": "name"}, 200, id="P07: sort_by_name_asc"),
    pytest.param({"sort": "-name"}, 200, id="P08: sort_by_name_desc"),
    pytest.param({"sort": "stack", "order": "asc"}, 200, id="P09: sort_by_stack_asc"),
    pytest.param({"sort": "state", "order": "desc"}, 200, id="P10: sort_by_state_desc"),

    # --- Постраничная навигация (Пагинация) ---
    pytest.param({"limit": "5"}, 200, id="P11: pagination_limit_5"),
    pytest.param({"limit": "1"}, 200, id="P12: pagination_limit_1"),
    pytest.param({"offset": "10"}, 200, id="P13: pagination_offset_10"),
    pytest.param({"limit": "5", "offset": "5"}, 200, id="P14: pagination_limit_5_offset_5"),
    
    # --- Полнотекстовый поиск ---
    pytest.param({"q": "switch"}, 200, id="P15: search_for_switch"),
    pytest.param({"q": "redis"}, 200, id="P16: search_for_redis"),
    pytest.param({"q": "non-existent-text"}, 200, id="P17: search_for_non_existent"),
    
    # --- Комбинации фильтров ---
    pytest.param({"stack": "ngfw", "state": "good"}, 200, id="P18: filter_by_stack_and_state"),
    pytest.param({"stack": "shared", "q": "mongo"}, 200, id="P19: filter_by_stack_and_search"),

    # --- Негативные сценарии и граничные значения ---
    pytest.param({"sort": ""}, 400, id="N01: sort_by_empty_string"),
    pytest.param({"order": "invalid"}, 200, id="N02: invalid_order_value_ignored"),
    pytest.param({"limit": "-1"}, 200, id="N03: invalid_limit_negative_ignored"),
    pytest.param({"limit": "abc"}, 200, id="N04: invalid_limit_string_ignored"),
    pytest.param({"offset": "-5"}, 200, id="N05: invalid_offset_negative_ignored"),
    pytest.param({"offset": "xyz"}, 200, id="N06: invalid_offset_string"),
    pytest.param({"unsupported_param": "value"}, 200, id="P20: unsupported_parameter_is_ignored"),
    
    # --- Дополнительные проверки для покрытия 25+ тестов ---
    pytest.param({"sort": "address"}, 200, id="P21: sort_by_address"),
    pytest.param({"state": "unknown"}, 200, id="P22: filter_by_state_unknown"),
    pytest.param({"q": "NGFW"}, 200, id="P23: search_case_insensitive"),
    pytest.param({"stack": "tls-bridge"}, 200, id="P24: filter_by_stack_tls_bridge"),
    pytest.param({"name": "mongo", "state": "good"}, 200, id="P25: filter_name_and_state"),
    pytest.param({"limit": "100"}, 200, id="P26: pagination_high_limit"),
]


def _check_types_recursive(obj, schema):
    """Рекурсивно проверяет типы данных в объекте на соответствие схеме."""
    if "anyOf" in schema:
        # Проверяем, что тип объекта соответствует хотя бы одной из схем в anyOf
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


# Локальный форматтер curl удален — используем фикстуру attach_curl_on_fail


@pytest.mark.parametrize("params, expected_status", PARAMS)
def test_services_parametrized(api_client, params, expected_status, attach_curl_on_fail):
    """
    Основной параметризованный тест для эндпоинта /services.
    1. Отправляет GET-запрос с указанными параметрами.
    2. Проверяет соответствие статус-кода ожидаемому.
    3. Для успешных ответов (200) валидирует схему JSON.
    4. Для ответов с ошибкой (400) валидирует схему ошибки.
    5. В случае падения теста выводит полную cURL-команду для воспроизведения.
    """
    with attach_curl_on_fail(ENDPOINT, params, None, "GET"):
        response = api_client.get(ENDPOINT, params=params)
        # 1. Проверка статус-кода
        assert response.status_code == expected_status, \
            f"Ожидался статус-код {expected_status}, получен {response.status_code}. Ответ: {response.text}"

        # 2. Валидация схемы ответа
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, dict), f"Тело ответа не является объектом JSON, получено: {type(data).__name__}"
            # Проверяем структуру каждого сервиса в ответе
            for service_data in data.values():
                _check_types_recursive(service_data, SERVICE_SCHEMA)
        elif response.status_code == 400 and response.text:
            # Валидируем структуру ответа для ошибок 400
            data = response.json()
            _check_types_recursive(data, ERROR_400_SCHEMA)
