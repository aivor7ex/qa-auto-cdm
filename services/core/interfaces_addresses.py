"""Tests for the /interfaces/addresses endpoint."""
import pytest
import json
from collections.abc import Mapping, Sequence

ENDPOINT = "/interfaces/addresses"

INTERFACE_ADDRESSES_SCHEMA = {
    "type": "object",
    "properties": {
        "ip": {
            "type": "array",
            "items": {
    "type": "object",
    "properties": {
        "fullAddr": {"type": "string"},
        "addr": {"type": "string"},
        "netmask": {"type": "string"},
                    "proto": {"type": "string"}
                }
            }
        }
    },
    "required": [],
}

# Осмысленная параметризация для тестирования эндпоинта /interfaces/addresses
PARAMS = [
    # --- Базовые позитивные сценарии ---
    pytest.param({}, 200, id="P01: no_params"),
    pytest.param({"format": "json"}, 200, id="P02: format_json"),
    pytest.param({"format": "text"}, 200, id="P03: format_text"),
    pytest.param({"format": "xml"}, 200, id="P04: format_xml"),
    pytest.param({"format": "yaml"}, 200, id="P05: format_yaml"),
    pytest.param({"verbose": "true"}, 200, id="P06: verbose_true"),
    pytest.param({"verbose": "false"}, 200, id="P07: verbose_false"),
    pytest.param({"detailed": "true"}, 200, id="P08: detailed_true"),
    pytest.param({"detailed": "false"}, 200, id="P09: detailed_false"),
    pytest.param({"include_metadata": "true"}, 200, id="P10: include_metadata"),
    
    # --- Фильтрация по типам адресов ---
    pytest.param({"protocol": "ip4"}, 200, id="P11: protocol_ipv4"),
    pytest.param({"protocol": "ip6"}, 200, id="P12: protocol_ipv6"),
    pytest.param({"protocol": "all"}, 200, id="P13: protocol_all"),
    pytest.param({"type": "static"}, 200, id="P14: type_static"),
    pytest.param({"type": "dynamic"}, 200, id="P15: type_dynamic"),
    pytest.param({"type": "dhcp"}, 200, id="P16: type_dhcp"),
    pytest.param({"scope": "global"}, 200, id="P17: scope_global"),
    pytest.param({"scope": "local"}, 200, id="P18: scope_local"),
    pytest.param({"scope": "link"}, 200, id="P19: scope_link"),
    pytest.param({"scope": "host"}, 200, id="P20: scope_host"),
    
    # --- Фильтрация по сетям ---
    pytest.param({"network": "192.168.1.0/24"}, 200, id="P21: network_192_168"),
    pytest.param({"network": "10.0.0.0/8"}, 200, id="P22: network_10"),
    pytest.param({"network": "172.16.0.0/12"}, 200, id="P23: network_172_16"),
    pytest.param({"subnet": "255.255.255.0"}, 200, id="P24: subnet_24"),
    pytest.param({"subnet": "255.255.0.0"}, 200, id="P25: subnet_16"),
    pytest.param({"netmask": "24"}, 200, id="P26: netmask_24"),
    pytest.param({"netmask": "16"}, 200, id="P27: netmask_16"),
    pytest.param({"netmask": "8"}, 200, id="P28: netmask_8"),
    pytest.param({"cidr": "24"}, 200, id="P29: cidr_24"),
    pytest.param({"cidr": "16"}, 200, id="P30: cidr_16"),
    
    # --- Фильтрация по интерфейсам ---
    pytest.param({"interface": "eth-0-1"}, 200, id="P31: interface_eth_0_1"),
    pytest.param({"interface": "bond1"}, 200, id="P32: interface_bond1"),
    pytest.param({"interface": "lo"}, 200, id="P33: interface_loopback"),
    pytest.param({"interface": "all"}, 200, id="P34: interface_all"),
    pytest.param({"if": "eth-0-1"}, 200, id="P35: if_eth_0_1"),
    pytest.param({"dev": "bond1"}, 200, id="P36: dev_bond1"),
    pytest.param({"device": "eth-0-2"}, 200, id="P37: device_eth_0_2"),
    
    # --- Комбинированные параметры ---
    pytest.param({"protocol": "ip4", "interface": "eth-0-1"}, 200, id="P38: ipv4_on_eth"),
    pytest.param({"type": "static", "scope": "global"}, 200, id="P39: static_global"),
    pytest.param({"network": "192.168.1.0/24", "interface": "eth-0-1"}, 200, id="P40: network_on_interface"),
    pytest.param({"format": "json", "verbose": "true"}, 200, id="P41: json_verbose"),
    pytest.param({"protocol": "ip6", "detailed": "true"}, 200, id="P42: ipv6_detailed"),
    
    # --- Поиск и фильтрация ---
    pytest.param({"search": "192.168"}, 200, id="P43: search_192_168"),
    pytest.param({"search": "10.0"}, 200, id="P44: search_10_0"),
    pytest.param({"search": "eth"}, 200, id="P45: search_eth"),
    pytest.param({"q": "address"}, 200, id="P46: query_address"),
    pytest.param({"filter": "active"}, 200, id="P47: filter_active"),
    pytest.param({"filter": "primary"}, 200, id="P48: filter_primary"),
    
    # --- Специальные параметры ---
    pytest.param({"include_loopback": "true"}, 200, id="P49: include_loopback"),
    pytest.param({"include_loopback": "false"}, 200, id="P50: exclude_loopback"),
    pytest.param({"include_virtual": "true"}, 200, id="P51: include_virtual"),
    pytest.param({"include_virtual": "false"}, 200, id="P52: exclude_virtual"),
    pytest.param({"resolve_names": "true"}, 200, id="P53: resolve_names"),
    pytest.param({"resolve_names": "false"}, 200, id="P54: no_resolve_names"),
    pytest.param({"show_prefixes": "true"}, 200, id="P55: show_prefixes"),
    pytest.param({"show_prefixes": "false"}, 200, id="P56: hide_prefixes"),
    pytest.param({"include_stats": "true"}, 200, id="P57: include_stats_format"),
    pytest.param({"include_stats": "false"}, 200, id="P58: exclude_stats_format"),
    
    # --- Дополнительные системные параметры ---
    pytest.param({"sort": "addr"}, 200, id="P59: sort_by_address"),
    pytest.param({"sort": "interface"}, 200, id="P60: sort_by_interface"),
    pytest.param({"limit": "10"}, 200, id="P61: limit_10"),
    pytest.param({"offset": "5"}, 200, id="P62: offset_5"),
    pytest.param({"page": "1"}, 200, id="P63: page_1"),
    
    # --- Граничные значения ---
    pytest.param({"unsupported_param": "value"}, 200, id="P64: unsupported_param_ignored"),
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
def test_interfaces_addresses_parametrized(api_client, params, expected_status):
    """
    Основной параметризованный тест для эндпоинта /interfaces/addresses.
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
            _check_types_recursive(data, INTERFACE_ADDRESSES_SCHEMA)
            
            # Дополнительная проверка структуры массива ip
            if "ip" in data:
                assert isinstance(data["ip"], list), "Поле 'ip' должно быть массивом"
                for ip_item in data["ip"]:
                    assert isinstance(ip_item, dict), "Каждый элемент массива 'ip' должен быть объектом"

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