"""
Тесты для эндпоинта /interfaces/all сервиса core.

Проверяется:
- Статус-код 200 OK
- Соответствие структуры ответа схеме (массив объектов)
- Корректность типов данных во всех полях, включая вложенные
- Устойчивость к 35+ различным query-параметрам
"""
import pytest
import json
from collections.abc import Mapping, Sequence

ENDPOINT = "/interfaces/all"

INTERFACE_ALL_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "accessory": {"type": "string"},
        "ifType": {"type": "string"},
        "MAC": {"type": "string"},
        "active": {"type": "boolean"},
        "pos": {"type": "integer"},
        "speed": {"type": "string"},
        "enabled": {"type": "boolean"},
        "linked": {"type": "boolean"}
    },
    "required": ["name"],
}

# Осмысленная параметризация для тестирования эндпоинта /interfaces/all
PARAMS = [
    # --- Базовые позитивные сценарии ---
    pytest.param({}, 200, id="P01: no_params"),
    pytest.param({"filter": '{"active": true}'}, 200, id="P02: filter_by_active_true"),
    pytest.param({"filter": '{"active": false}'}, 200, id="P03: filter_by_active_false"),
    pytest.param({"filter": '{"enabled": true}'}, 200, id="P04: filter_by_enabled_true"),
    pytest.param({"filter": '{"enabled": false}'}, 200, id="P05: filter_by_enabled_false"),
    pytest.param({"filter": '{"linked": true}'}, 200, id="P06: filter_by_linked_true"),
    pytest.param({"filter": '{"linked": false}'}, 200, id="P07: filter_by_linked_false"),
    pytest.param({"filter": '{"ifType": "access"}'}, 200, id="P08: filter_by_access_type"),
    pytest.param({"filter": '{"ifType": "trunk"}'}, 200, id="P09: filter_by_trunk_type"),
    pytest.param({"filter": '{"accessory": "centec"}'}, 200, id="P10: filter_by_centec"),
    
    # --- Фильтрация по названиям ---
    pytest.param({"filter": '{"name": "eth-0-1"}'}, 200, id="P11: filter_by_eth_0_1"),
    pytest.param({"filter": '{"name": "bond1"}'}, 200, id="P12: filter_by_bond1"),
    pytest.param({"filter": '{"name": {"$regex": "eth"}}'}, 200, id="P13: filter_name_regex_eth"),
    pytest.param({"filter": '{"name": {"$regex": "bond"}}'}, 200, id="P14: filter_name_regex_bond"),
    
    # --- Фильтрация по скорости ---
    pytest.param({"filter": '{"speed": "a-1000"}'}, 200, id="P15: filter_by_speed_1000"),
    pytest.param({"filter": '{"speed": "a-100"}'}, 200, id="P16: filter_by_speed_100"),
    pytest.param({"filter": '{"speed": "a-10"}'}, 200, id="P17: filter_by_speed_10"),
    pytest.param({"filter": '{"speed": {"$regex": "1000"}}'}, 200, id="P18: filter_speed_regex_1000"),
    
    # --- Комбинированные фильтры ---
    pytest.param({"filter": '{"active": true, "enabled": true}'}, 200, id="P19: active_and_enabled"),
    pytest.param({"filter": '{"ifType": "access", "active": true}'}, 200, id="P20: access_and_active"),
    pytest.param({"filter": '{"accessory": "centec", "enabled": true}'}, 200, id="P21: centec_and_enabled"),
    pytest.param({"filter": '{"linked": true, "enabled": true}'}, 200, id="P22: linked_and_enabled"),
    pytest.param({"filter": '{"speed": "a-1000", "active": true}'}, 200, id="P23: speed_and_active"),
    
    # --- Поиск и фильтрация ---
    pytest.param({"search": "eth"}, 200, id="P24: search_eth"),
    pytest.param({"search": "bond"}, 200, id="P25: search_bond"),
    pytest.param({"search": "centec"}, 200, id="P26: search_centec"),
    pytest.param({"search": "1000"}, 200, id="P27: search_1000"),
    pytest.param({"q": "interface"}, 200, id="P28: query_interface"),
    pytest.param({"name": "eth-0-1"}, 200, id="P29: filter_by_name_param"),
    pytest.param({"active": "true"}, 200, id="P30: filter_by_active_param"),
    pytest.param({"enabled": "true"}, 200, id="P31: filter_by_enabled_param"),
    pytest.param({"linked": "true"}, 200, id="P32: filter_by_linked_param"),
    pytest.param({"ifType": "access"}, 200, id="P33: filter_by_type_param"),
    pytest.param({"accessory": "centec"}, 200, id="P34: filter_by_accessory_param"),
    
    # --- Сортировка ---
    pytest.param({"sort": "name"}, 200, id="P35: sort_by_name_asc"),
    pytest.param({"sort": "-name"}, 200, id="P36: sort_by_name_desc"),
    pytest.param({"sort": "pos"}, 200, id="P37: sort_by_position"),
    pytest.param({"sort": "-pos"}, 200, id="P38: sort_by_position_desc"),
    pytest.param({"sort": "speed"}, 200, id="P39: sort_by_speed"),
    pytest.param({"sort": "-speed"}, 200, id="P40: sort_by_speed_desc"),
    pytest.param({"sort": "ifType"}, 200, id="P41: sort_by_type"),
    pytest.param({"sort": "accessory"}, 200, id="P42: sort_by_accessory"),
    
    # --- Постраничная навигация ---
    pytest.param({"limit": "10"}, 200, id="P43: pagination_limit_10"),
    pytest.param({"limit": "1"}, 200, id="P44: pagination_limit_1"),
    pytest.param({"offset": "5"}, 200, id="P45: pagination_offset_5"),
    pytest.param({"limit": "5", "offset": "2"}, 200, id="P46: pagination_limit_offset"),
    
    # --- Комбинации параметров ---
    pytest.param({"sort": "name", "limit": "3"}, 200, id="P47: sort_and_limit"),
    pytest.param({"filter": '{"active": true}', "sort": "pos"}, 200, id="P48: filter_and_sort"),
    pytest.param({"search": "eth", "limit": "5"}, 200, id="P49: search_and_limit"),
    pytest.param({"active": "true", "sort": "name"}, 200, id="P50: active_and_sort"),
    
    # --- Специальные параметры ---
    pytest.param({"include_inactive": "true"}, 200, id="P51: include_inactive"),
    pytest.param({"include_inactive": "false"}, 200, id="P52: exclude_inactive"),
    pytest.param({"include_virtual": "true"}, 200, id="P53: include_virtual"),
    pytest.param({"include_virtual": "false"}, 200, id="P54: exclude_virtual"),
    pytest.param({"include_bonds": "true"}, 200, id="P55: include_bonds"),
    pytest.param({"include_bonds": "false"}, 200, id="P56: exclude_bonds"),
    pytest.param({"detailed": "true"}, 200, id="P57: detailed_info"),
    pytest.param({"detailed": "false"}, 200, id="P58: basic_info"),
    pytest.param({"format": "json"}, 200, id="P59: format_json"),
    pytest.param({"format": "xml"}, 200, id="P60: format_xml"),
    pytest.param({"verbose": "true"}, 200, id="P61: verbose_output"),
    pytest.param({"verbose": "false"}, 200, id="P62: brief_output"),
    
    # --- Граничные значения ---
    pytest.param({"limit": "0"}, 200, id="P63: zero_limit"),
    pytest.param({"limit": "-1"}, 200, id="P64: negative_limit_ignored"),
    pytest.param({"offset": "-5"}, 200, id="P65: negative_offset_ignored"),
    pytest.param({"unsupported_param": "value"}, 200, id="P66: unsupported_param_ignored"),
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
def test_interfaces_all_parametrized(api_client, params, expected_status):
    """
    Основной параметризованный тест для эндпоинта /interfaces/all.
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
            # Проверяем структуру каждого интерфейса в ответе
            for interface_data in data:
                _check_types_recursive(interface_data, INTERFACE_ALL_SCHEMA)

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