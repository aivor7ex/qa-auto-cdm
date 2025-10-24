"""
Тесты для эндпоинта /interfaces/count сервиса core.

Проверяется:
- Статус-код 200 OK
- Соответствие структуры ответа схеме
- Корректность типа и значения поля count
- Устойчивость к различным query-параметрам
"""
import pytest
import json
from collections.abc import Mapping, Sequence

ENDPOINT = "/interfaces/count"

COUNT_SCHEMA = {
    "type": "object",
    "properties": {
        "count": {"type": "integer"}
    },
    "required": ["count"],
}

# Осмысленная параметризация для тестирования эндпоинта /interfaces/count
PARAMS = [
    # --- Базовые позитивные сценарии ---
    pytest.param({}, 200, id="P01: no_params"),
    pytest.param({"filter": '{"active": true}'}, 200, id="P02: filter_by_active_true"),
    pytest.param({"filter": '{"active": false}'}, 200, id="P03: filter_by_active_false"),
    pytest.param({"filter": '{"isBond": true}'}, 200, id="P04: filter_by_is_bond_true"),
    pytest.param({"filter": '{"isBond": false}'}, 200, id="P05: filter_by_is_bond_false"),
    pytest.param({"filter": '{"ifType": "access"}'}, 200, id="P06: filter_by_access_type"),
    pytest.param({"filter": '{"ifType": "trunk"}'}, 200, id="P07: filter_by_trunk_type"),
    pytest.param({"filter": '{"accessory": "centec"}'}, 200, id="P08: filter_by_centec"),
    pytest.param({"filter": '{"name": "bond1"}'}, 200, id="P09: filter_by_bond1"),
    pytest.param({"filter": '{"name": "eth-0-1"}'}, 200, id="P10: filter_by_eth_interface"),
    
    # --- Комбинированные фильтры ---
    pytest.param({"filter": '{"active": true, "isBond": true}'}, 200, id="P11: active_and_bond"),
    pytest.param({"filter": '{"ifType": "access", "active": true}'}, 200, id="P12: access_and_active"),
    pytest.param({"filter": '{"accessory": "centec", "active": false}'}, 200, id="P13: centec_and_inactive"),
    pytest.param({"filter": '{"isBond": false, "ifType": "access"}'}, 200, id="P14: non_bond_access"),
    
    # --- Поиск и фильтрация ---
    pytest.param({"search": "bond"}, 200, id="P15: search_bond"),
    pytest.param({"search": "eth"}, 200, id="P16: search_eth"),
    pytest.param({"search": "centec"}, 200, id="P17: search_centec"),
    pytest.param({"q": "interface"}, 200, id="P18: query_interface"),
    pytest.param({"name": "bond1"}, 200, id="P19: filter_by_name_param"),
    pytest.param({"active": "true"}, 200, id="P20: filter_by_active_param"),
    pytest.param({"isBond": "true"}, 200, id="P21: filter_by_is_bond_param"),
    pytest.param({"ifType": "access"}, 200, id="P22: filter_by_type_param"),
    pytest.param({"accessory": "centec"}, 200, id="P23: filter_by_accessory_param"),
    
    # --- Дополнительные параметры (игнорируются для count) ---
    pytest.param({"sort": "name"}, 200, id="P24: sort_ignored"),
    pytest.param({"limit": "10"}, 200, id="P25: limit_ignored"),
    pytest.param({"offset": "5"}, 200, id="P26: offset_ignored"),
    pytest.param({"order": "desc"}, 200, id="P27: order_ignored"),
    pytest.param({"page": "1"}, 200, id="P28: page_ignored"),
    
    # --- Специальные фильтры ---
    pytest.param({"enabled": "true"}, 200, id="P29: filter_by_enabled"),
    pytest.param({"type": "physical"}, 200, id="P30: filter_by_physical"),
    pytest.param({"type": "virtual"}, 200, id="P31: filter_by_virtual"),
    pytest.param({"status": "up"}, 200, id="P32: filter_by_status_up"),
    pytest.param({"status": "down"}, 200, id="P33: filter_by_status_down"),
    pytest.param({"port": "1"}, 200, id="P34: filter_by_port"),
    pytest.param({"vlan": "100"}, 200, id="P35: filter_by_vlan"),
    pytest.param({"speed": "1000"}, 200, id="P36: filter_by_speed"),
    pytest.param({"duplex": "full"}, 200, id="P37: filter_by_duplex"),
    pytest.param({"mtu": "1500"}, 200, id="P38: filter_by_mtu"),
    
    # --- Негативные сценарии ---
    pytest.param({"filter": "invalid_json"}, 200, id="N01: invalid_json_filter_ignored"),
    pytest.param({"filter": '{"invalid": }'}, 200, id="N02: malformed_json_ignored"),
    pytest.param({"filter": "null"}, 200, id="P39: null_filter_ignored"),
    pytest.param({"limit": "-1"}, 200, id="P40: negative_limit_ignored"),
    pytest.param({"offset": "-5"}, 200, id="P41: negative_offset_ignored"),
    
    # --- Граничные значения ---
    pytest.param({"unsupported_param": "value"}, 200, id="P42: unsupported_param_ignored"),
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
def test_interfaces_count_parametrized(api_client, params, expected_status):
    """
    Основной параметризованный тест для эндпоинта /interfaces/count.
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
            # Дополнительная проверка что count является неотрицательным числом
            assert data["count"] >= 0, f"Count должен быть неотрицательным, получено: {data['count']}"

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