import pytest
import json
from collections.abc import Mapping, Sequence
import time

ENDPOINT = "/openflowGateways"

OPENFLOW_GATEWAY_SCHEMA = {
    "type": "object", 
    "properties": {
        "id": {"type": "string"},
        "name": {"type": "string"},
        "ip_address": {"type": "string"},
        "port": {"type": "integer"},
        "status": {"type": "string"},
        "active": {"type": "boolean"}
    }
}

# Автофикстура для задержки между каждым тестом
@pytest.fixture(autouse=True)
def pause_between_tests():
    yield
    time.sleep(1)

# Осмысленная параметризация для тестирования эндпоинта /openflowGateways
PARAMS = [
    # --- Базовые позитивные сценарии ---
    pytest.param({}, 200, id="P01: no_params"),
    pytest.param({"filter": '{"status": "active"}'}, 200, id="P02: filter_by_status_active"),
    pytest.param({"filter": '{"status": "inactive"}'}, 200, id="P03: filter_by_status_inactive"),
    pytest.param({"filter": '{"active": true}'}, 200, id="P04: filter_by_active_true"),
    pytest.param({"filter": '{"active": false}'}, 200, id="P05: filter_by_active_false"),
    pytest.param({"filter": '{"name": "gateway1"}'}, 200, id="P06: filter_by_name"),
    pytest.param({"filter": '{"ip_address": "192.168.1.1"}'}, 200, id="P07: filter_by_ip"),
    pytest.param({"filter": '{"port": 6633}'}, 200, id="P08: filter_by_port"),
    pytest.param({"filter": '{"port": 6653}'}, 200, id="P09: filter_by_port_6653"),
    pytest.param({"filter": '{"port": {"$gte": 6000}}'}, 200, id="P10: filter_port_gte"),
    
    # --- Фильтрация по диапазонам ---
    pytest.param({"filter": '{"port": {"$lte": 7000}}'}, 200, id="P11: filter_port_lte"),
    pytest.param({"filter": '{"port": {"$gt": 1024}}'}, 200, id="P12: filter_port_gt"),
    pytest.param({"filter": '{"port": {"$lt": 65535}}'}, 200, id="P13: filter_port_lt"),
    pytest.param({"filter": '{"port": {"$ne": 22}}'}, 200, id="P14: filter_port_not_ssh"),
    pytest.param({"filter": '{"status": {"$ne": "unknown"}}'}, 200, id="P15: filter_status_not_unknown"),
    
    # --- Фильтрация по IP адресам ---
    pytest.param({"filter": '{"ip_address": {"$regex": "192.168"}}'}, 200, id="P16: filter_ip_private"),
    pytest.param({"filter": '{"ip_address": {"$regex": "10."}}'}, 200, id="P17: filter_ip_10_network"),
    pytest.param({"filter": '{"ip_address": {"$regex": "172.16"}}'}, 200, id="P18: filter_ip_172_network"),
    pytest.param({"filter": '{"ip_address": {"$regex": "127.0.0.1"}}'}, 200, id="P19: filter_ip_localhost"),
    pytest.param({"filter": '{"ip_address": {"$ne": "0.0.0.0"}}'}, 200, id="P20: filter_ip_not_any"),
    
    # --- Комбинированные фильтры ---
    pytest.param({"filter": '{"active": true, "status": "active"}'}, 200, id="P21: active_and_status"),
    pytest.param({"filter": '{"port": 6633, "active": true}'}, 200, id="P22: port_and_active"),
    pytest.param({"filter": '{"ip_address": {"$regex": "192.168"}, "active": true}'}, 200, id="P23: ip_and_active"),
    pytest.param({"filter": '{"status": "active", "port": {"$gte": 6000}}'}, 200, id="P24: status_and_port_range"),
    
    # --- Специальные MongoDB операторы ---
    pytest.param({"filter": '{"status": {"$in": ["active", "inactive", "pending"]}}'}, 200, id="P25: status_in_list"),
    pytest.param({"filter": '{"port": {"$in": [6633, 6653, 6640]}}'}, 200, id="P26: port_in_list"),
    pytest.param({"filter": '{"status": {"$nin": ["error", "failed"]}}'}, 200, id="P27: status_not_in_list"),
    pytest.param({"filter": '{"$or": [{"active": true}, {"status": "pending"}]}'}, 200, id="P28: or_condition"),
    pytest.param({"filter": '{"$and": [{"active": true}, {"port": {"$gt": 1024}}]}'}, 200, id="P29: and_condition"),
    
    # --- Поиск и фильтрация ---
    pytest.param({"search": "gateway"}, 200, id="P30: search_gateway"),
    pytest.param({"search": "openflow"}, 200, id="P31: search_openflow"),
    pytest.param({"search": "192.168"}, 200, id="P32: search_ip"),
    pytest.param({"search": "6633"}, 200, id="P33: search_port"),
    pytest.param({"q": "controller"}, 200, id="P34: query_controller"),
    pytest.param({"q": "switch"}, 200, id="P35: query_switch"),
    pytest.param({"name": "gateway1"}, 200, id="P36: filter_by_name_param"),
    pytest.param({"status": "active"}, 200, id="P37: filter_by_status_param"),
    pytest.param({"active": "true"}, 200, id="P38: filter_by_active_param"),
    
    # --- Сортировка ---
    pytest.param({"sort": "name"}, 200, id="P39: sort_by_name_asc"),
    pytest.param({"sort": "-name"}, 200, id="P40: sort_by_name_desc"),
    pytest.param({"sort": "ip_address"}, 200, id="P41: sort_by_ip"),
    pytest.param({"sort": "port"}, 200, id="P42: sort_by_port"),
    pytest.param({"sort": "status"}, 200, id="P43: sort_by_status"),
    pytest.param({"sort": "-active"}, 200, id="P44: sort_by_active_desc"),
    
    # --- Постраничная навигация ---
    pytest.param({"limit": "10"}, 200, id="P45: pagination_limit_10"),
    pytest.param({"limit": "1"}, 200, id="P46: pagination_limit_1"),
    pytest.param({"offset": "5"}, 200, id="P47: pagination_offset_5"),
    pytest.param({"limit": "5", "offset": "2"}, 200, id="P48: pagination_limit_offset"),
    
    # --- Дополнительные параметры ---
    pytest.param({"include_metadata": "true"}, 200, id="P49: include_metadata"),
    pytest.param({"include_metadata": "false"}, 200, id="P50: exclude_metadata"),
    pytest.param({"format": "json"}, 200, id="P51: format_json"),
    pytest.param({"format": "text"}, 200, id="P52: format_text"),
    pytest.param({"verbose": "true"}, 200, id="P53: verbose_true"),
    pytest.param({"verbose": "false"}, 200, id="P54: verbose_false"),
    
    # --- Негативные сценарии с некорректными фильтрами ---
    pytest.param({"filter": "invalid_json"}, 400, id="N01: invalid_json_rejected"),
    pytest.param({"filter": '{"invalid": }'}, 400, id="N02: malformed_json_rejected"),
    pytest.param({"filter": "null"}, 200, id="N03: null_filter_ignored"),
    pytest.param({"filter": '{"port": {"$invalidOp": "value"}}'}, 200, id="N04: invalid_mongo_op_ignored"),
    pytest.param({"filter": '{"nonexistent_field": "value"}'}, 200, id="N05: nonexistent_field_ignored"),
    
    # --- Граничные значения ---
    pytest.param({"limit": "0"}, 200, id="P55: zero_limit"),
    pytest.param({"limit": "-1"}, 200, id="P56: negative_limit_ignored"),
    pytest.param({"offset": "-5"}, 200, id="P57: negative_offset_ignored"),
    pytest.param({"unsupported_param": "value"}, 200, id="P58: unsupported_param_ignored"),
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
def test_openflow_gateways_parametrized(api_client, params, expected_status):
    """
    Основной параметризованный тест для эндпоинта /openflowGateways.
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
            # Проверяем структуру каждого gateway в ответе (если есть)
            for gateway_data in data:
                _check_types_recursive(gateway_data, OPENFLOW_GATEWAY_SCHEMA)
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
