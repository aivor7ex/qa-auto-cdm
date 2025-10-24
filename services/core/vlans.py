import pytest
import json
from collections.abc import Mapping, Sequence

ENDPOINT = "/vlans"

VLAN_SCHEMA = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "vlanId": {"type": "integer"},
            "interface": {"type": "string"},
        "id": {"type": "string"},
        "ip": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "fullAddr": {"type": "string"},
                    "addr": {"type": "string"},
                    "netmask": {"type": "string"},
                    "proto": {"type": "string"}
                },
                "required": ["fullAddr", "addr", "netmask", "proto"]
            }
        },
        "ipv6": {"type": "array"},
        "mtu": {"type": "integer"},
        "MAC": {"type": "string"},
        "l2mode": {"type": "integer"},
        "stp": {"type": "boolean"}
    },
    "required": ["vlanId", "interface", "id"],
}

# Осмысленная параметризация для тестирования эндпоинта /vlans
PARAMS = [
    # --- Базовые позитивные сценарии ---
    pytest.param({}, 200, id="P01: no_params"),
    pytest.param({"filter": '{"vlanId": 0}'}, 200, id="P02: filter_by_vlan_id_0"),
    pytest.param({"filter": '{"vlanId": 1}'}, 200, id="P03: filter_by_vlan_id_1"),
    pytest.param({"filter": '{"vlanId": 10}'}, 200, id="P04: filter_by_vlan_id_10"),
    pytest.param({"filter": '{"name": "native"}'}, 200, id="P05: filter_by_name_native"),
    pytest.param({"filter": '{"name": "qwe"}'}, 200, id="P06: filter_by_name_qwe"),
    pytest.param({"filter": '{"interface": "eth-0-1"}'}, 200, id="P07: filter_by_interface"),
    pytest.param({"filter": '{"l2mode": 0}'}, 200, id="P08: filter_by_l2mode"),
    pytest.param({"filter": '{"stp": false}'}, 200, id="P09: filter_by_stp_false"),
    
    # --- Сортировка ---
    pytest.param({"sort": "vlanId"}, 200, id="P10: sort_by_vlanId_asc"),
    pytest.param({"sort": "-vlanId"}, 200, id="P11: sort_by_vlanId_desc"),
    pytest.param({"sort": "name"}, 200, id="P12: sort_by_name_asc"),
    pytest.param({"sort": "-name"}, 200, id="P13: sort_by_name_desc"),
    pytest.param({"sort": "interface"}, 200, id="P14: sort_by_interface"),
    pytest.param({"sort": "mtu"}, 200, id="P15: sort_by_mtu"),
    
    # --- Постраничная навигация ---
    pytest.param({"limit": "10"}, 200, id="P16: pagination_limit_10"),
    pytest.param({"limit": "1"}, 200, id="P17: pagination_limit_1"),
    pytest.param({"skip": "5"}, 200, id="P18: pagination_skip_5"),
    pytest.param({"limit": "5", "skip": "2"}, 200, id="P19: pagination_limit_skip"),
    
    # --- Поиск и фильтрация ---
    pytest.param({"search": "native"}, 200, id="P20: search_native"),
    pytest.param({"search": "eth"}, 200, id="P21: search_eth_interfaces"),
    pytest.param({"q": "vlan"}, 200, id="P22: query_text"),
    pytest.param({"name": "native"}, 200, id="P23: filter_by_name_param"),
    pytest.param({"vlanId": "0"}, 200, id="P24: filter_by_vlanId_param"),
    
    # --- Комбинации фильтров ---
    pytest.param({"filter": '{"vlanId": 0, "name": "native"}'}, 200, id="P25: multiple_filters"),
    pytest.param({"vlanId": "0", "interface": "eth-0-1"}, 200, id="P26: param_filters"),
    pytest.param({"sort": "vlanId", "limit": "3"}, 200, id="P27: sort_and_limit"),
    
    # --- Негативные сценарии ---
    pytest.param({"filter": "invalid_json"}, 400, id="N01: invalid_json_filter_error"),
    pytest.param({"filter": '{"invalid": }'}, 400, id="N02: malformed_json_error"),
    pytest.param({"filter": "null"}, 200, id="P28: null_filter_ignored"),
    pytest.param({"limit": "-1"}, 200, id="P29: negative_limit_ignored"),
    pytest.param({"skip": "-5"}, 200, id="P30: negative_skip_ignored"),
    
    # --- Граничные значения ---
    pytest.param({"limit": "0"}, 200, id="P31: zero_limit"),
    pytest.param({"limit": "1000"}, 200, id="P32: high_limit"),
    pytest.param({"skip": "1000"}, 200, id="P33: high_skip"),
    pytest.param({"unsupported_param": "value"}, 200, id="P34: unsupported_param_ignored"),
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
def test_vlans_parametrized(api_client, params, expected_status):
    """
    Основной параметризованный тест для эндпоинта /vlans.
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
            # Проверяем структуру каждого VLAN в ответе
            for vlan_data in data:
                _check_types_recursive(vlan_data, VLAN_SCHEMA)
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