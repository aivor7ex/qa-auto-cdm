"""Tests for the /router/ospf/ospfExternalLinks/count endpoint."""
import pytest
import json
from collections.abc import Mapping, Sequence

ENDPOINT = "/router/ospf/ospfExternalLinks/count"

COUNT_SCHEMA = {
    "type": "object",
    "properties": {
        "count": {"type": "integer"}
    },
    "required": ["count"],
}

# Осмысленная параметризация для тестирования эндпоинта /router/ospf/ospfExternalLinks/count
PARAMS = [
    # --- Базовые позитивные сценарии ---
    pytest.param({}, 200, id="P01: no_params"),
    pytest.param({"filter": '{"type": "external"}'}, 200, id="P02: filter_by_type_external"),
    pytest.param({"filter": '{"type": "asbr"}'}, 200, id="P03: filter_by_type_asbr"),
    pytest.param({"filter": '{"metric": 1}'}, 200, id="P04: filter_by_metric_1"),
    pytest.param({"filter": '{"metric": 10}'}, 200, id="P05: filter_by_metric_10"),
    pytest.param({"filter": '{"metric": 100}'}, 200, id="P06: filter_by_metric_100"),
    pytest.param({"filter": '{"linkStateId": "192.168.1.0"}'}, 200, id="P07: filter_by_link_state_id"),
    pytest.param({"filter": '{"advertisingRouter": "10.0.0.1"}'}, 200, id="P08: filter_by_advertising_router"),
    pytest.param({"filter": '{"forwardingAddress": "0.0.0.0"}'}, 200, id="P09: filter_by_forwarding_address"),
    pytest.param({"filter": '{"externalRouteTag": 0}'}, 200, id="P10: filter_by_external_route_tag"),
    
    # --- Комбинированные фильтры ---
    pytest.param({"filter": '{"type": "external", "metric": 10}'}, 200, id="P11: type_and_metric"),
    pytest.param({"filter": '{"metric": {"$gte": 1, "$lte": 100}}'}, 200, id="P12: metric_range"),
    pytest.param({"filter": '{"type": "external", "linkStateId": "192.168.1.0"}'}, 200, id="P13: type_and_link_state_id"),
    pytest.param({"filter": '{"advertisingRouter": "10.0.0.1", "forwardingAddress": "0.0.0.0"}'}, 200, id="P14: router_and_forwarding"),
    
    # --- Поиск и фильтрация ---
    pytest.param({"search": "external"}, 200, id="P15: search_external"),
    pytest.param({"search": "192.168"}, 200, id="P16: search_ip_subnet"),
    pytest.param({"search": "10.0.0"}, 200, id="P17: search_router_ip"),
    pytest.param({"q": "ospf"}, 200, id="P18: query_ospf"),
    pytest.param({"type": "external"}, 200, id="P19: filter_by_type_param"),
    pytest.param({"metric": "10"}, 200, id="P20: filter_by_metric_param"),
    pytest.param({"linkStateId": "192.168.1.0"}, 200, id="P21: filter_by_link_state_id_param"),
    pytest.param({"advertisingRouter": "10.0.0.1"}, 200, id="P22: filter_by_advertising_router_param"),
    
    # --- Дополнительные параметры (игнорируются для count) ---
    pytest.param({"sort": "metric"}, 200, id="P23: sort_ignored"),
    pytest.param({"limit": "10"}, 200, id="P24: limit_ignored"),
    pytest.param({"offset": "5"}, 200, id="P25: offset_ignored"),
    pytest.param({"order": "desc"}, 200, id="P26: order_ignored"),
    pytest.param({"page": "1"}, 200, id="P27: page_ignored"),
    
    # --- Специальные фильтры ---
    pytest.param({"enabled": "true"}, 200, id="P28: filter_by_enabled"),
    pytest.param({"active": "true"}, 200, id="P29: filter_by_active"),
    pytest.param({"age": "300"}, 200, id="P30: filter_by_age"),
    pytest.param({"sequence": "1"}, 200, id="P31: filter_by_sequence"),
    pytest.param({"checksum": "0x1234"}, 200, id="P32: filter_by_checksum"),
    pytest.param({"length": "36"}, 200, id="P33: filter_by_length"),
    pytest.param({"prefix": "192.168.0.0/16"}, 200, id="P34: filter_by_prefix"),
    pytest.param({"mask": "255.255.0.0"}, 200, id="P35: filter_by_mask"),
    pytest.param({"cost": "1"}, 200, id="P36: filter_by_cost"),
    pytest.param({"routeType": "1"}, 200, id="P37: filter_by_route_type_1"),
    pytest.param({"routeType": "2"}, 200, id="P38: filter_by_route_type_2"),
    pytest.param({"area": "0.0.0.0"}, 200, id="P39: filter_by_area"),
    pytest.param({"interface": "eth0"}, 200, id="P40: filter_by_interface"),
    pytest.param({"neighbor": "10.0.0.2"}, 200, id="P41: filter_by_neighbor"),
    pytest.param({"tag": "100"}, 200, id="P42: filter_by_tag"),
    pytest.param({"priority": "1"}, 200, id="P43: filter_by_priority"),
    pytest.param({"state": "full"}, 200, id="P44: filter_by_state"),
    pytest.param({"database": "external"}, 200, id="P45: filter_by_database"),
    pytest.param({"protocol": "ospf"}, 200, id="P46: filter_by_protocol"),
    
    # --- Негативные сценарии ---
    pytest.param({"filter": "invalid_json"}, 400, id="N01: invalid_json_filter_rejected"),
    pytest.param({"filter": '{"invalid": }'}, 400, id="N02: malformed_json_rejected"),
    pytest.param({"filter": "null"}, 200, id="P47: null_filter_ignored"),
    pytest.param({"limit": "-1"}, 200, id="P48: negative_limit_ignored"),
    pytest.param({"offset": "-5"}, 200, id="P49: negative_offset_ignored"),
    
    # --- Граничные значения ---
    pytest.param({"unsupported_param": "value"}, 200, id="P50: unsupported_param_ignored"),
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
def test_router_ospf_external_links_count_parametrized(api_client, params, expected_status):
    """
    Основной параметризованный тест для эндпоинта /router/ospf/ospfExternalLinks/count.
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