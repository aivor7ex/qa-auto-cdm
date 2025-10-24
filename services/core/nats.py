import pytest
import json
from collections.abc import Mapping, Sequence

ENDPOINT = "/nats"

NAT_SCHEMA = {
    "type": "object",
    "properties": {
        "natType": {"type": "string"},
        "sourceNet": {"type": "string"},
        "outInterface": {"type": "string"},
        "proto": {"type": "string"},
        "id": {"type": "string"},
        "objHash": {"type": "string"}
    },
    "required": ["id"],
}

# Осмысленная параметризация для тестирования эндпоинта /nats
PARAMS = [
    # --- Базовые позитивные сценарии ---
    pytest.param({}, 200, id="P01: no_params"),
    pytest.param({"filter": '{"natType": "MASQUERADE"}'}, 200, id="P02: filter_by_masquerade"),
    pytest.param({"filter": '{"natType": "SNAT"}'}, 200, id="P03: filter_by_snat"),
    pytest.param({"filter": '{"natType": "DNAT"}'}, 200, id="P04: filter_by_dnat"),
    pytest.param({"filter": '{"proto": "all"}'}, 200, id="P05: filter_by_proto_all"),
    pytest.param({"filter": '{"proto": "tcp"}'}, 200, id="P06: filter_by_proto_tcp"),
    pytest.param({"filter": '{"proto": "udp"}'}, 200, id="P07: filter_by_proto_udp"),
    pytest.param({"filter": '{"proto": "icmp"}'}, 200, id="P08: filter_by_proto_icmp"),
    pytest.param({"filter": '{"sourceNet": "192.168.1.0/24"}'}, 200, id="P09: filter_by_source_net"),
    pytest.param({"filter": '{"outInterface": "eth-0-1:1"}'}, 200, id="P10: filter_by_out_interface"),
    
    # --- Фильтрация по сетям ---
    pytest.param({"filter": '{"sourceNet": "10.0.0.0/8"}'}, 200, id="P11: filter_by_10_network"),
    pytest.param({"filter": '{"sourceNet": "172.16.0.0/12"}'}, 200, id="P12: filter_by_172_network"),
    pytest.param({"filter": '{"sourceNet": "0.0.0.0/0"}'}, 200, id="P13: filter_by_any_network"),
    pytest.param({"filter": '{"sourceNet": {"$regex": "192.168"}}'}, 200, id="P14: filter_source_regex"),
    
    # --- Фильтрация по интерфейсам ---
    pytest.param({"filter": '{"outInterface": "eth-0-1"}'}, 200, id="P15: filter_by_eth_interface"),
    pytest.param({"filter": '{"outInterface": "bond1"}'}, 200, id="P16: filter_by_bond_interface"),
    pytest.param({"filter": '{"outInterface": {"$regex": "eth"}}'}, 200, id="P17: filter_interface_regex"),
    pytest.param({"filter": '{"outInterface": {"$regex": "bond"}}'}, 200, id="P18: filter_bond_regex"),
    
    # --- Комбинированные фильтры ---
    pytest.param({"filter": '{"natType": "MASQUERADE", "proto": "all"}'}, 200, id="P19: masquerade_all_proto"),
    pytest.param({"filter": '{"natType": "SNAT", "proto": "tcp"}'}, 200, id="P20: snat_tcp"),
    pytest.param({"filter": '{"sourceNet": "192.168.1.0/24", "proto": "tcp"}'}, 200, id="P21: source_net_tcp"),
    pytest.param({"filter": '{"outInterface": "eth-0-1:1", "natType": "MASQUERADE"}'}, 200, id="P22: interface_masquerade"),
    pytest.param({"filter": '{"proto": "all", "sourceNet": "0.0.0.0/0"}'}, 200, id="P23: all_proto_any_source"),
    
    # --- Поиск и фильтрация ---
    pytest.param({"search": "MASQUERADE"}, 200, id="P24: search_masquerade"),
    pytest.param({"search": "192.168"}, 200, id="P25: search_ip_subnet"),
    pytest.param({"search": "eth-0-1"}, 200, id="P26: search_interface"),
    pytest.param({"search": "tcp"}, 200, id="P27: search_protocol"),
    pytest.param({"search": "all"}, 200, id="P28: search_all"),
    pytest.param({"q": "nat"}, 200, id="P29: query_nat"),
    pytest.param({"q": "rule"}, 200, id="P30: query_rule"),
    pytest.param({"natType": "MASQUERADE"}, 200, id="P31: filter_by_nat_type_param"),
    pytest.param({"proto": "all"}, 200, id="P32: filter_by_proto_param"),
    pytest.param({"sourceNet": "192.168.1.0/24"}, 200, id="P33: filter_by_source_net_param"),
    pytest.param({"outInterface": "eth-0-1:1"}, 200, id="P34: filter_by_out_interface_param"),
    
    # --- Сортировка ---
    pytest.param({"sort": "natType"}, 200, id="P35: sort_by_nat_type"),
    pytest.param({"sort": "-natType"}, 200, id="P36: sort_by_nat_type_desc"),
    pytest.param({"sort": "sourceNet"}, 200, id="P37: sort_by_source_net"),
    pytest.param({"sort": "-sourceNet"}, 200, id="P38: sort_by_source_net_desc"),
    pytest.param({"sort": "outInterface"}, 200, id="P39: sort_by_out_interface"),
    pytest.param({"sort": "-outInterface"}, 200, id="P40: sort_by_out_interface_desc"),
    pytest.param({"sort": "proto"}, 200, id="P41: sort_by_protocol"),
    pytest.param({"sort": "-proto"}, 200, id="P42: sort_by_protocol_desc"),
    pytest.param({"sort": "id"}, 200, id="P43: sort_by_id"),
    pytest.param({"sort": "-id"}, 200, id="P44: sort_by_id_desc"),
    
    # --- Постраничная навигация ---
    pytest.param({"limit": "10"}, 200, id="P45: pagination_limit_10"),
    pytest.param({"limit": "1"}, 200, id="P46: pagination_limit_1"),
    pytest.param({"offset": "5"}, 200, id="P47: pagination_offset_5"),
    pytest.param({"limit": "3", "offset": "1"}, 200, id="P48: pagination_limit_offset"),
    
    # --- Комбинации параметров ---
    pytest.param({"sort": "natType", "limit": "5"}, 200, id="P49: sort_and_limit"),
    pytest.param({"filter": '{"natType": "MASQUERADE"}', "sort": "sourceNet"}, 200, id="P50: filter_and_sort"),
    pytest.param({"search": "192.168", "limit": "3"}, 200, id="P51: search_and_limit"),
    pytest.param({"natType": "MASQUERADE", "sort": "outInterface"}, 200, id="P52: nat_type_and_sort"),
    
    # --- Специальные параметры ---
    pytest.param({"include_stats": "true"}, 200, id="P53: include_stats"),
    pytest.param({"include_stats": "false"}, 200, id="P54: exclude_stats"),
    pytest.param({"include_config": "true"}, 200, id="P55: include_config"),
    pytest.param({"include_config": "false"}, 200, id="P56: exclude_config"),
    pytest.param({"detailed": "true"}, 200, id="P57: detailed_info"),
    pytest.param({"detailed": "false"}, 200, id="P58: basic_info"),
    pytest.param({"format": "json"}, 200, id="P59: format_json"),
    pytest.param({"format": "xml"}, 200, id="P60: format_xml"),
    pytest.param({"verbose": "true"}, 200, id="P61: verbose_output"),
    pytest.param({"verbose": "false"}, 200, id="P62: brief_output"),
    pytest.param({"expand": "true"}, 200, id="P63: expand_rules"),
    pytest.param({"expand": "false"}, 200, id="P64: compact_rules"),
    pytest.param({"active": "true"}, 200, id="P65: active_rules_only"),
    pytest.param({"active": "false"}, 200, id="P66: include_inactive"),
    
    # --- Граничные значения ---
    pytest.param({"limit": "0"}, 200, id="P67: zero_limit"),
    pytest.param({"limit": "-1"}, 200, id="P68: negative_limit_ignored"),
    pytest.param({"offset": "-3"}, 200, id="P69: negative_offset_ignored"),
    pytest.param({"unsupported_param": "value"}, 200, id="P70: unsupported_param_ignored"),
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
def test_nats_parametrized(api_client, params, expected_status):
    """
    Основной параметризованный тест для эндпоинта /nats.
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
            # Проверяем структуру каждого NAT правила в ответе
            for nat_data in data:
                _check_types_recursive(nat_data, NAT_SCHEMA)

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