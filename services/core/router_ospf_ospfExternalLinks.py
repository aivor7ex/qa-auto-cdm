import pytest
import json
from collections.abc import Mapping, Sequence

ENDPOINT = "/router/ospf/ospfExternalLinks"

OSPF_EXTERNAL_LINK_SCHEMA = {
    "type": "object",
    "properties": {
        "age": {"type": "string"},
        "linkStateId": {"type": "string"},
        "ADVrouter": {"type": "string"},
        "seqNumber": {"type": "string"},
        "checksum": {"type": "string"},
        "netmask": {"type": "string"},
        "forwardingAddress": {"type": "string"}
    },
    "required": [],
}

# Осмысленная параметризация для тестирования эндпоинта /router/ospf/ospfExternalLinks
PARAMS = [
    # --- Базовые позитивные сценарии ---
    pytest.param({}, 200, id="P01: no_params"),
    pytest.param({"filter": '{"age": "1308"}'}, 200, id="P02: filter_by_age"),
    pytest.param({"filter": '{"linkStateId": "10.10.10.0"}'}, 200, id="P03: filter_by_link_state_id"),
    pytest.param({"filter": '{"ADVrouter": "10.10.117.1"}'}, 200, id="P04: filter_by_adv_router"),
    pytest.param({"filter": '{"seqNumber": "80000257"}'}, 200, id="P05: filter_by_seq_number"),
    pytest.param({"filter": '{"checksum": "0x3a5b"}'}, 200, id="P06: filter_by_checksum"),
    pytest.param({"filter": '{"netmask": "/24"}'}, 200, id="P07: filter_by_netmask"),
    pytest.param({"filter": '{"forwardingAddress": "0.0.0.0"}'}, 200, id="P08: filter_by_forwarding_address"),
    
    # --- Фильтрация по диапазонам возрастов ---
    pytest.param({"filter": '{"age": {"$gte": "1000"}}'}, 200, id="P09: filter_age_gte_1000"),
    pytest.param({"filter": '{"age": {"$lte": "2000"}}'}, 200, id="P10: filter_age_lte_2000"),
    pytest.param({"filter": '{"age": {"$in": ["1308", "1400", "1500"]}}'}, 200, id="P11: filter_age_in_list"),
    
    # --- Фильтрация по IP-адресам ---
    pytest.param({"filter": '{"linkStateId": {"$regex": "10.10"}}'}, 200, id="P12: filter_link_state_regex"),
    pytest.param({"filter": '{"ADVrouter": {"$regex": "10.10.117"}}'}, 200, id="P13: filter_adv_router_regex"),
    pytest.param({"filter": '{"forwardingAddress": {"$ne": "0.0.0.0"}}'}, 200, id="P14: filter_non_zero_forwarding"),
    pytest.param({"filter": '{"linkStateId": {"$regex": "^10"}}'}, 200, id="P15: filter_link_state_starts_10"),
    pytest.param({"filter": '{"ADVrouter": {"$regex": "1$"}}'}, 200, id="P16: filter_adv_router_ends_1"),
    
    # --- Фильтрация по netmask ---
    pytest.param({"filter": '{"netmask": "/16"}'}, 200, id="P17: filter_netmask_16"),
    pytest.param({"filter": '{"netmask": "/8"}'}, 200, id="P18: filter_netmask_8"),
    pytest.param({"filter": '{"netmask": {"$regex": "/2"}}'}, 200, id="P19: filter_netmask_regex"),
    
    # --- Комбинированные фильтры ---
    pytest.param({"filter": '{"linkStateId": "10.10.10.0", "netmask": "/24"}'}, 200, id="P20: link_state_and_netmask"),
    pytest.param({"filter": '{"ADVrouter": "10.10.117.1", "age": "1308"}'}, 200, id="P21: adv_router_and_age"),
    pytest.param({"filter": '{"seqNumber": "80000257", "checksum": "0x3a5b"}'}, 200, id="P22: seq_number_and_checksum"),
    pytest.param({"filter": '{"forwardingAddress": "0.0.0.0", "netmask": "/24"}'}, 200, id="P23: forwarding_and_netmask"),
    
    # --- Поиск и фильтрация ---
    pytest.param({"search": "10.10"}, 200, id="P24: search_ip_10_10"),
    pytest.param({"search": "117"}, 200, id="P25: search_117"),
    pytest.param({"search": "1308"}, 200, id="P26: search_age"),
    pytest.param({"search": "80000257"}, 200, id="P27: search_seq_number"),
    pytest.param({"search": "0x3a5b"}, 200, id="P28: search_checksum"),
    pytest.param({"search": "/24"}, 200, id="P29: search_netmask_24"),
    pytest.param({"q": "external"}, 200, id="P30: query_external"),
    pytest.param({"q": "link"}, 200, id="P31: query_link"),
    pytest.param({"age": "1308"}, 200, id="P32: filter_by_age_param"),
    pytest.param({"linkStateId": "10.10.10.0"}, 200, id="P33: filter_by_link_state_param"),
    pytest.param({"ADVrouter": "10.10.117.1"}, 200, id="P34: filter_by_adv_router_param"),
    pytest.param({"seqNumber": "80000257"}, 200, id="P35: filter_by_seq_number_param"),
    
    # --- Сортировка ---
    pytest.param({"sort": "age"}, 200, id="P36: sort_by_age"),
    pytest.param({"sort": "-age"}, 200, id="P37: sort_by_age_desc"),
    pytest.param({"sort": "linkStateId"}, 200, id="P38: sort_by_link_state_id"),
    pytest.param({"sort": "-linkStateId"}, 200, id="P39: sort_by_link_state_id_desc"),
    pytest.param({"sort": "ADVrouter"}, 200, id="P40: sort_by_adv_router"),
    pytest.param({"sort": "-ADVrouter"}, 200, id="P41: sort_by_adv_router_desc"),
    pytest.param({"sort": "seqNumber"}, 200, id="P42: sort_by_seq_number"),
    pytest.param({"sort": "-seqNumber"}, 200, id="P43: sort_by_seq_number_desc"),
    pytest.param({"sort": "checksum"}, 200, id="P44: sort_by_checksum"),
    pytest.param({"sort": "netmask"}, 200, id="P45: sort_by_netmask"),
    
    # --- Постраничная навигация ---
    pytest.param({"limit": "10"}, 200, id="P46: pagination_limit_10"),
    pytest.param({"limit": "1"}, 200, id="P47: pagination_limit_1"),
    pytest.param({"offset": "5"}, 200, id="P48: pagination_offset_5"),
    pytest.param({"limit": "3", "offset": "1"}, 200, id="P49: pagination_limit_offset"),
    
    # --- Комбинации параметров ---
    pytest.param({"sort": "age", "limit": "5"}, 200, id="P50: sort_and_limit"),
    pytest.param({"filter": '{"linkStateId": "10.10.10.0"}', "sort": "age"}, 200, id="P51: filter_and_sort"),
    pytest.param({"search": "10.10", "limit": "3"}, 200, id="P52: search_and_limit"),
    pytest.param({"age": "1308", "sort": "linkStateId"}, 200, id="P53: age_and_sort"),
    
    # --- Специальные параметры ---
    pytest.param({"include_stats": "true"}, 200, id="P54: include_stats"),
    pytest.param({"include_stats": "false"}, 200, id="P55: exclude_stats"),
    pytest.param({"include_config": "true"}, 200, id="P56: include_config"),
    pytest.param({"include_config": "false"}, 200, id="P57: exclude_config"),
    pytest.param({"detailed": "true"}, 200, id="P58: detailed_info"),
    pytest.param({"detailed": "false"}, 200, id="P59: basic_info"),
    pytest.param({"format": "json"}, 200, id="P60: format_json"),
    pytest.param({"format": "xml"}, 200, id="P61: format_xml"),
    pytest.param({"verbose": "true"}, 200, id="P62: verbose_output"),
    pytest.param({"verbose": "false"}, 200, id="P63: brief_output"),
    pytest.param({"expand": "true"}, 200, id="P64: expand_links"),
    pytest.param({"expand": "false"}, 200, id="P65: compact_links"),
    pytest.param({"active": "true"}, 200, id="P66: active_links_only"),
    pytest.param({"active": "false"}, 200, id="P67: include_inactive"),
    pytest.param({"type": "external"}, 200, id="P68: filter_by_type"),
    pytest.param({"area": "0.0.0.0"}, 200, id="P69: filter_by_area"),
    pytest.param({"protocol": "ospf"}, 200, id="P70: filter_by_protocol"),
    
    # --- Граничные значения ---
    pytest.param({"limit": "0"}, 200, id="P71: zero_limit"),
    pytest.param({"limit": "-1"}, 200, id="P72: negative_limit_ignored"),
    pytest.param({"offset": "-3"}, 200, id="P73: negative_offset_ignored"),
    pytest.param({"unsupported_param": "value"}, 200, id="P74: unsupported_param_ignored"),
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
def test_router_ospf_external_links_parametrized(api_client, params, expected_status):
    """
    Основной параметризованный тест для эндпоинта /router/ospf/ospfExternalLinks.
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
            # Проверяем структуру каждой внешней OSPF ссылки в ответе
            for link_data in data:
                _check_types_recursive(link_data, OSPF_EXTERNAL_LINK_SCHEMA)

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