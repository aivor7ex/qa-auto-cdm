import pytest
import json
from collections.abc import Mapping, Sequence

ENDPOINT = "/vrrps"

VRRP_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "group": {"type": "integer"},
        "virtualAddress": {
            "type": "object",
            "properties": {
                "ipv4": {"type": "string"}
            },
            "required": ["ipv4"]
        },
        "interface": {"type": "string"},
        "priority": {"type": "integer"},
        "authType": {"type": "string"},
        "password": {"type": "string"},
        "preempt": {"type": "boolean"},
        "sourceIp": {"type": "array", "items": {"type": "string"}},
        "vlan": {"type": "integer"},
        "id": {"type": "string"},
    },
    "required": ["name", "group", "virtualAddress", "interface", "priority", "authType", "password", "preempt", "sourceIp", "vlan", "id"],
}

# Осмысленная параметризация для тестирования эндпоинта /vrrps
PARAMS = [
    # --- Базовые позитивные сценарии ---
    pytest.param({}, 200, id="P01: no_params"),
    pytest.param({"filter": '{"group": 51}'}, 200, id="P02: filter_by_group"),
    pytest.param({"filter": '{"priority": 100}'}, 200, id="P03: filter_by_priority"),
    pytest.param({"filter": '{"authType": "plain-text"}'}, 200, id="P04: filter_by_auth_type"),
    pytest.param({"filter": '{"preempt": true}'}, 200, id="P05: filter_by_preempt_true"),
    pytest.param({"filter": '{"preempt": false}'}, 200, id="P06: filter_by_preempt_false"),
    pytest.param({"filter": '{"vlan": 1}'}, 200, id="P07: filter_by_vlan"),
    pytest.param({"filter": '{"interface": "1"}'}, 200, id="P08: filter_by_interface"),
    pytest.param({"filter": '{"name": "vrrp_group1"}'}, 200, id="P09: filter_by_name"),
    
    # --- Сортировка ---
    pytest.param({"sort": "name"}, 200, id="P10: sort_by_name_asc"),
    pytest.param({"sort": "-name"}, 200, id="P11: sort_by_name_desc"),
    pytest.param({"sort": "group"}, 200, id="P12: sort_by_group_asc"),
    pytest.param({"sort": "-group"}, 200, id="P13: sort_by_group_desc"),
    pytest.param({"sort": "priority"}, 200, id="P14: sort_by_priority"),
    pytest.param({"sort": "vlan"}, 200, id="P15: sort_by_vlan"),
    
    # --- Постраничная навигация ---
    pytest.param({"limit": "5"}, 200, id="P16: pagination_limit_5"),
    pytest.param({"limit": "1"}, 200, id="P17: pagination_limit_1"),
    pytest.param({"offset": "10"}, 200, id="P18: pagination_offset_10"),
    pytest.param({"limit": "3", "offset": "1"}, 200, id="P19: pagination_limit_offset"),
    
    # --- Поиск и фильтрация ---
    pytest.param({"search": "vrrp"}, 200, id="P20: search_text"),
    pytest.param({"q": "group"}, 200, id="P21: query_text"),
    pytest.param({"name": "vrrp_group1"}, 200, id="P22: filter_by_name_param"),
    pytest.param({"group": "51"}, 200, id="P23: filter_by_group_param"),
    
    # --- Комбинации фильтров ---
    pytest.param({"filter": '{"preempt": true, "vlan": 1}'}, 200, id="P24: multiple_filters"),
    pytest.param({"group": "51", "priority": "100"}, 200, id="P25: param_filters"),
    pytest.param({"sort": "name", "limit": "2"}, 200, id="P26: sort_and_limit"),
    
    # --- Негативные сценарии ---
    pytest.param({"filter": "invalid_json"}, 400, id="N01: invalid_json_filter_error"),
    pytest.param({"filter": '{"invalid": }'}, 400, id="N02: malformed_json_error"),
    pytest.param({"filter": "null"}, 200, id="P27: null_filter_ignored"),
    pytest.param({"limit": "-1"}, 200, id="P28: negative_limit_ignored"),
    pytest.param({"offset": "-5"}, 200, id="P29: negative_offset_ignored"),
    
    # --- Граничные значения ---
    pytest.param({"limit": "0"}, 200, id="P30: zero_limit"),
    pytest.param({"limit": "1000"}, 200, id="P31: high_limit"),
    pytest.param({"offset": "1000"}, 200, id="P32: high_offset"),
    pytest.param({"unsupported_param": "value"}, 200, id="P33: unsupported_param_ignored"),
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
        response = api_client.get(ENDPOINT, params=params)
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
def test_vrrps_parametrized(api_client, params, expected_status):
    """
    Основной параметризованный тест для эндпоинта /vrrps.
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
            # Проверяем структуру каждого VRRP в ответе
            for vrrp_data in data:
                _check_types_recursive(vrrp_data, VRRP_SCHEMA)
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