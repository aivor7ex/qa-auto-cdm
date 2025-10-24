import pytest
import json
from collections.abc import Mapping, Sequence

ENDPOINT = "/routingPolicies/count"

COUNT_SCHEMA = {
    "type": "object",
    "properties": {
        "count": {"type": "integer"},
    },
    "required": ["count"],
}

# Осмысленная параметризация для тестирования эндпоинта /routingPolicies/count
PARAMS = [
    # --- Базовые позитивные сценарии ---
    pytest.param({}, 200, id="P01: no_params"),
    pytest.param({"limit": "10"}, 200, id="P02: with_limit_param"),
    pytest.param({"offset": "5"}, 200, id="P03: with_offset_param"),
    pytest.param({"filter": '{"active": true}'}, 200, id="P04: filter_by_active_true"),
    pytest.param({"filter": '{"active": false}'}, 200, id="P05: filter_by_active_false"),
    pytest.param({"filter": '{"priority": 1000}'}, 200, id="P06: filter_by_priority"),
    pytest.param({"filter": '{"table": 100}'}, 200, id="P07: filter_by_table"),
    pytest.param({"filter": '{"name": "test"}'}, 200, id="P08: filter_by_name"),
    
    # --- Поиск и текстовые фильтры ---
    pytest.param({"search": "policy"}, 200, id="P09: search_text"),
    pytest.param({"q": "routing"}, 200, id="P10: query_text"),
    pytest.param({"name": "test_policy"}, 200, id="P11: filter_by_name_param"),
    
    # --- Комбинации фильтров ---
    pytest.param({"filter": '{"active": true, "priority": 1000}'}, 200, id="P12: multiple_filters"),
    pytest.param({"active": "true", "priority": "1000"}, 200, id="P13: param_filters"),
    
    # --- Сортировка и пагинация ---
    pytest.param({"sort": "name"}, 200, id="P14: sort_by_name"),
    pytest.param({"sort": "priority"}, 200, id="P15: sort_by_priority"),
    pytest.param({"sort": "-created"}, 200, id="P16: sort_desc"),
    pytest.param({"page": "1"}, 200, id="P17: first_page"),
    pytest.param({"pageSize": "50"}, 200, id="P18: page_size"),
    
    # --- Негативные сценарии ---
    pytest.param({"filter": "invalid_json"}, 200, id="N01: invalid_json_filter_ignored"),
    pytest.param({"filter": '{"invalid": }'}, 200, id="N02: malformed_json_ignored"),
    pytest.param({"filter": "null"}, 200, id="P19: null_filter_ignored"),
    pytest.param({"limit": "-1"}, 200, id="P20: negative_limit_ignored"),
    pytest.param({"offset": "-5"}, 200, id="P21: negative_offset_ignored"),
    
    # --- Граничные значения ---
    pytest.param({"limit": "0"}, 200, id="P22: zero_limit"),
    pytest.param({"limit": "1000"}, 200, id="P23: high_limit"),
    pytest.param({"offset": "1000"}, 200, id="P24: high_offset"),
    pytest.param({"unsupported_param": "value"}, 200, id="P25: unsupported_param_ignored"),
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
def test_routing_policies_count_parametrized(api_client, params, expected_status):
    """
    Основной параметризованный тест для эндпоинта /routingPolicies/count.
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
            assert isinstance(data, dict), f"Тело ответа не является объектом JSON, получено: {type(data).__name__}"
            _check_types_recursive(data, COUNT_SCHEMA)

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