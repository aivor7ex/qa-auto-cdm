import pytest
import json
from collections.abc import Mapping, Sequence

ENDPOINT = "/router/linuxRoutes"

LINUX_ROUTE_SCHEMA = {
    "type": "object",
    "properties": {
        "mask": {"type": ["string", "null"]},
        "distance": {"type": ["integer", "null"]},
        "metric": {"type": ["integer", "null"]},
        "local": {"type": "boolean"},
        "kernel": {"type": "boolean"},
        "connected": {"type": "boolean"},
        "static": {"type": "boolean"},
        "rip": {"type": "boolean"},
        "ospf": {"type": "boolean"},
        "isIs": {"type": "boolean"},
        "bgp": {"type": "boolean"}
    },
    "required": [],
}

# Осмысленная параметризация для тестирования эндпоинта /router/linuxRoutes
PARAMS = [
    # --- Базовые позитивные сценарии ---
    pytest.param({}, 200, id="P01: no_params"),
    pytest.param({"filter": '{"local": true}'}, 200, id="P02: filter_by_local_true"),
    pytest.param({"filter": '{"local": false}'}, 200, id="P03: filter_by_local_false"),
    pytest.param({"filter": '{"kernel": true}'}, 200, id="P04: filter_by_kernel_true"),
    pytest.param({"filter": '{"kernel": false}'}, 200, id="P05: filter_by_kernel_false"),
    pytest.param({"filter": '{"connected": true}'}, 200, id="P06: filter_by_connected_true"),
    pytest.param({"filter": '{"connected": false}'}, 200, id="P07: filter_by_connected_false"),
    pytest.param({"filter": '{"static": true}'}, 200, id="P08: filter_by_static_true"),
    pytest.param({"filter": '{"static": false}'}, 200, id="P09: filter_by_static_false"),
    pytest.param({"filter": '{"ospf": true}'}, 200, id="P10: filter_by_ospf_true"),
    
    # --- Протокольные фильтры ---
    pytest.param({"filter": '{"ospf": false}'}, 200, id="P11: filter_by_ospf_false"),
    pytest.param({"filter": '{"rip": true}'}, 200, id="P12: filter_by_rip_true"),
    pytest.param({"filter": '{"rip": false}'}, 200, id="P13: filter_by_rip_false"),
    pytest.param({"filter": '{"bgp": true}'}, 200, id="P14: filter_by_bgp_true"),
    pytest.param({"filter": '{"bgp": false}'}, 200, id="P15: filter_by_bgp_false"),
    pytest.param({"filter": '{"isIs": true}'}, 200, id="P16: filter_by_isis_true"),
    pytest.param({"filter": '{"isIs": false}'}, 200, id="P17: filter_by_isis_false"),
    
    # --- Комбинированные фильтры ---
    pytest.param({"filter": '{"local": true, "kernel": false}'}, 200, id="P18: local_and_not_kernel"),
    pytest.param({"filter": '{"static": true, "connected": false}'}, 200, id="P19: static_and_not_connected"),
    pytest.param({"filter": '{"ospf": true, "bgp": false}'}, 200, id="P20: ospf_and_not_bgp"),
    pytest.param({"filter": '{"kernel": true, "local": true}'}, 200, id="P21: kernel_and_local"),
    
    # --- Поиск и фильтрация ---
    pytest.param({"search": "route"}, 200, id="P22: search_route"),
    pytest.param({"search": "192.168"}, 200, id="P23: search_ip_subnet"),
    pytest.param({"search": "10.0"}, 200, id="P24: search_10_subnet"),
    pytest.param({"q": "linux"}, 200, id="P25: query_text"),
    pytest.param({"local": "true"}, 200, id="P26: filter_by_local_param"),
    pytest.param({"kernel": "true"}, 200, id="P27: filter_by_kernel_param"),
    pytest.param({"static": "true"}, 200, id="P28: filter_by_static_param"),
    pytest.param({"connected": "true"}, 200, id="P29: filter_by_connected_param"),
    pytest.param({"ospf": "true"}, 200, id="P30: filter_by_ospf_param"),
    
    # --- Сортировка ---
    pytest.param({"sort": "mask"}, 200, id="P31: sort_by_mask"),
    pytest.param({"sort": "-mask"}, 200, id="P32: sort_by_mask_desc"),
    pytest.param({"sort": "distance"}, 200, id="P33: sort_by_distance"),
    pytest.param({"sort": "-distance"}, 200, id="P34: sort_by_distance_desc"),
    pytest.param({"sort": "metric"}, 200, id="P35: sort_by_metric"),
    pytest.param({"sort": "-metric"}, 200, id="P36: sort_by_metric_desc"),
    
    # --- Постраничная навигация ---
    pytest.param({"limit": "10"}, 200, id="P37: pagination_limit_10"),
    pytest.param({"limit": "1"}, 200, id="P38: pagination_limit_1"),
    pytest.param({"offset": "5"}, 200, id="P39: pagination_offset_5"),
    pytest.param({"limit": "5", "offset": "2"}, 200, id="P40: pagination_limit_offset"),
    
    # --- Комбинации параметров ---
    pytest.param({"sort": "mask", "limit": "3"}, 200, id="P41: sort_and_limit"),
    pytest.param({"filter": '{"local": true}', "sort": "distance"}, 200, id="P42: filter_and_sort"),
    pytest.param({"search": "192.168", "limit": "5"}, 200, id="P43: search_and_limit"),
    
    # --- Специальные фильтры ---
    pytest.param({"protocol": "ospf"}, 200, id="P44: filter_by_protocol_ospf"),
    pytest.param({"protocol": "bgp"}, 200, id="P45: filter_by_protocol_bgp"),
    pytest.param({"protocol": "static"}, 200, id="P46: filter_by_protocol_static"),
    pytest.param({"type": "unicast"}, 200, id="P47: filter_by_type_unicast"),
    pytest.param({"type": "multicast"}, 200, id="P48: filter_by_type_multicast"),
    pytest.param({"scope": "global"}, 200, id="P49: filter_by_scope_global"),
    pytest.param({"scope": "host"}, 200, id="P50: filter_by_scope_host"),
    
    # --- Негативные сценарии ---
    pytest.param({"filter": "invalid_json"}, 400, id="N01: invalid_json_filter_rejected"),
    pytest.param({"filter": '{"invalid": }'}, 400, id="N02: malformed_json_rejected"),
    pytest.param({"filter": "null"}, 200, id="P51: null_filter_ignored"),
    pytest.param({"limit": "-1"}, 200, id="P52: negative_limit_ignored"),
    pytest.param({"offset": "-5"}, 200, id="P53: negative_offset_ignored"),
    
    # --- Граничные значения ---
    pytest.param({"limit": "0"}, 200, id="P54: zero_limit"),
    pytest.param({"unsupported_param": "value"}, 200, id="P55: unsupported_param_ignored"),
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
    elif isinstance(schema_type, list):
        # Для полей с типом ["string", "null"] и подобными
        if obj is None and "null" in schema_type:
            return
        for type_option in schema_type:
            if type_option == "string" and isinstance(obj, str):
                return
            elif type_option == "integer" and isinstance(obj, int):
                return
            elif type_option == "boolean" and isinstance(obj, bool):
                return
        assert False, f"Поле не соответствует ни одному из типов {schema_type}, получено: {type(obj).__name__}"


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
def test_router_linux_routes_parametrized(api_client, params, expected_status):
    """
    Основной параметризованный тест для эндпоинта /router/linuxRoutes.
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
            # Проверяем структуру каждого маршрута в ответе
            for route_data in data:
                _check_types_recursive(route_data, LINUX_ROUTE_SCHEMA)
        elif response.status_code in [400, 422]:
            # Для 400/422 статус-кодов проверяем что есть error объект
            data = response.json()
            assert "error" in data, f"Ответ с {response.status_code} статусом должен содержать error объект"

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