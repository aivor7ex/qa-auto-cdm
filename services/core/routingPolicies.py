import pytest
import json
from collections.abc import Mapping, Sequence

ENDPOINT = "/routingPolicies"

ROUTING_POLICY_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "toNetwork": {"type": "string"},
        "fromNetwork": {"type": "string"},
        "table": {"type": "integer"},
        "priority": {"type": "integer"},
        "interfaceId": {"type": "string"},
        "active": {"type": "boolean"},
        "id": {"type": "string"},
    },
    "required": ["name", "toNetwork", "fromNetwork", "table", "priority", "interfaceId", "active", "id"],
}

# Осмысленная параметризация для тестирования эндпоинта /routingPolicies
PARAMS = [
    # --- Базовые позитивные сценарии ---
    pytest.param({}, 200, id="P01: no_params"),
    pytest.param({"filter": '{"active": true}'}, 200, id="P02: filter_by_active_true"),
    pytest.param({"filter": '{"active": false}'}, 200, id="P03: filter_by_active_false"),
    pytest.param({"filter": '{"priority": 1000}'}, 200, id="P04: filter_by_priority"),
    pytest.param({"filter": '{"table": 100}'}, 200, id="P05: filter_by_table"),
    pytest.param({"filter": '{"name": "My Test Policy"}'}, 200, id="P06: filter_by_name"),
    pytest.param({"filter": '{"interfaceId": "eth-0-12"}'}, 200, id="P07: filter_by_interface"),
    
    # --- Сортировка ---
    pytest.param({"sort": "name"}, 200, id="P08: sort_by_name_asc"),
    pytest.param({"sort": "-name"}, 200, id="P09: sort_by_name_desc"),
    pytest.param({"sort": "priority"}, 200, id="P10: sort_by_priority_asc"),
    pytest.param({"sort": "-priority"}, 200, id="P11: sort_by_priority_desc"),
    pytest.param({"sort": "table"}, 200, id="P12: sort_by_table"),
    pytest.param({"sort": "interfaceId"}, 200, id="P13: sort_by_interface"),
    
    # --- Постраничная навигация ---
    pytest.param({"limit": "5"}, 200, id="P14: pagination_limit_5"),
    pytest.param({"limit": "1"}, 200, id="P15: pagination_limit_1"),
    pytest.param({"offset": "10"}, 200, id="P16: pagination_offset_10"),
    pytest.param({"limit": "5", "offset": "2"}, 200, id="P17: pagination_limit_offset"),
    
    # --- Поиск и фильтрация ---
    pytest.param({"search": "policy"}, 200, id="P18: search_text"),
    pytest.param({"q": "test"}, 200, id="P19: query_text"),
    pytest.param({"name": "My Test Policy"}, 200, id="P20: filter_by_name_param"),
    
    # --- Комбинации фильтров ---
    pytest.param({"filter": '{"active": true, "priority": 1000}'}, 200, id="P21: multiple_filters"),
    pytest.param({"active": "true", "table": "100"}, 200, id="P22: param_filters"),
    pytest.param({"sort": "name", "limit": "3"}, 200, id="P23: sort_and_limit"),
    
    # --- Негативные сценарии ---
    pytest.param({"filter": "invalid_json"}, 400, id="N01: invalid_json_filter_error"),
    pytest.param({"filter": '{"invalid": }'}, 400, id="N02: malformed_json_error"),
    pytest.param({"filter": "null"}, 200, id="P24: null_filter_ignored"),
    pytest.param({"limit": "-1"}, 200, id="P25: negative_limit_ignored"),
    pytest.param({"offset": "-5"}, 200, id="P26: negative_offset_ignored"),
    
    # --- Граничные значения ---
    pytest.param({"limit": "0"}, 200, id="P27: zero_limit"),
    pytest.param({"limit": "1000"}, 200, id="P28: high_limit"),
    pytest.param({"offset": "1000"}, 200, id="P29: high_offset"),
    pytest.param({"unsupported_param": "value"}, 200, id="P30: unsupported_param_ignored"),
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
def test_routing_policies_parametrized(api_client, params, expected_status):
    """
    Основной параметризованный тест для эндпоинта /routingPolicies.
    1. Отправляет GET-запрос с указанными параметрами.
    2. Проверяет соответствие статус-кода ожидаемому.
    3. Для успешных ответов (200) валидирует схему JSON.
    4. В случае падения теста выводит полную cURL-команду для воспроизведения.
    """
    try:
        response = api_client.get(ENDPOINT, params=params)
        
        # 1. Проверка статус-кода
        assert response.status_code == expected_status, \
            f"Ожидался статус-код {expected_status}, получен {response.status_code}. Ответ: {response.text}"

        # 2. Валидация схемы ответа
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list), f"Тело ответа не является массивом JSON, получено: {type(data).__name__}"
            # Проверяем структуру каждой policy в ответе
            for policy_data in data:
                _check_types_recursive(policy_data, ROUTING_POLICY_SCHEMA)
        elif response.status_code == 400:
            # Для 400 статус-кода проверяем что есть error объект
            data = response.json()
            assert "error" in data, f"Ответ с 400 статусом должен содержать error объект"

    except (AssertionError, json.JSONDecodeError) as e:
        # 3. Формирование и вывод детального отчета об ошибке
        curl_command = _format_curl_command(api_client, ENDPOINT, params)
        
        error_message = (
            f"\nТест с параметрами {params} упал.\n"
            f"Ошибка: {e}\n\n"
            "================= Failed Test Request (cURL) ================\n"
            f"{curl_command}\n"
            "============================================================="
        )
        pytest.fail(error_message, pytrace=False) 