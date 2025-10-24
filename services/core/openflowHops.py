import pytest
import json
from collections.abc import Mapping, Sequence
import time

ENDPOINT = "/openflowHops"

OPENFLOW_HOP_SCHEMA = {
    "type": "object",
    "properties": {
        "ipv4_addr": {"type": "string"},
        "mac_addr": {"type": "string"},
        "id": {"type": "string"}
    },
    "required": ["ipv4_addr", "mac_addr", "id"]
}

# Автофикстура для задержки между каждым тестом
@pytest.fixture(autouse=True)
def pause_between_tests():
    yield
    time.sleep(1)

# Осмысленная параметризация для тестирования эндпоинта /openflowHops
PARAMS = [
    # --- Базовые позитивные сценарии ---
    pytest.param({}, 200, id="P01: no_params"),
    pytest.param({"filter": '{"ipv4_addr": "192.168.1.1"}'}, 200, id="P02: filter_by_ipv4"),
    pytest.param({"filter": '{"ipv4_addr": "10.0.0.1"}'}, 200, id="P03: filter_by_ipv4_10"),
    pytest.param({"filter": '{"ipv4_addr": "172.16.0.1"}'}, 200, id="P04: filter_by_ipv4_172"),
    pytest.param({"filter": '{"ipv4_addr": "183.45.46.14"}'}, 200, id="P05: filter_by_ipv4_183"),
    pytest.param({"filter": '{"mac_addr": "00:11:22:33:44:55"}'}, 200, id="P06: filter_by_mac"),
    pytest.param({"filter": '{"mac_addr": "a7:07:c9:f9:1a:6a"}'}, 200, id="P07: filter_by_mac_a7"),
    pytest.param({"filter": '{"id": "687feba8aa5c6d0009377df4"}'}, 200, id="P08: filter_by_id"),
    pytest.param({"filter": '{"id": "507f1f77bcf86cd799439011"}'}, 200, id="P09: filter_by_id_507"),
    pytest.param({"filter": '{"id": "507f191e810c19729de860ea"}'}, 200, id="P10: filter_by_id_mongo"),
    
    # --- Фильтрация по IP диапазонам ---
    pytest.param({"filter": '{"ipv4_addr": {"$regex": "192.168"}}'}, 200, id="P11: filter_ip_private"),
    pytest.param({"filter": '{"ipv4_addr": {"$regex": "10."}}'}, 200, id="P12: filter_ip_10_network"),
    pytest.param({"filter": '{"ipv4_addr": {"$regex": "172.16"}}'}, 200, id="P13: filter_ip_172_network"),
    pytest.param({"filter": '{"ipv4_addr": {"$regex": "127.0.0.1"}}'}, 200, id="P14: filter_ip_localhost"),
    pytest.param({"filter": '{"ipv4_addr": {"$regex": "^192"}}'}, 200, id="P15: filter_ip_starts_192"),
    pytest.param({"filter": '{"ipv4_addr": {"$regex": ".1$"}}'}, 200, id="P16: filter_ip_ends_1"),
    pytest.param({"filter": '{"ipv4_addr": {"$ne": "0.0.0.0"}}'}, 200, id="P17: filter_ip_not_any"),
    pytest.param({"filter": '{"ipv4_addr": {"$ne": "255.255.255.255"}}'}, 200, id="P18: filter_ip_not_broadcast"),
    
    # --- Фильтрация по MAC адресам ---
    pytest.param({"filter": '{"mac_addr": {"$regex": "00:"}}'}, 200, id="P19: filter_mac_starts_00"),
    pytest.param({"filter": '{"mac_addr": {"$regex": "a7:"}}'}, 200, id="P20: filter_mac_starts_a7"),
    pytest.param({"filter": '{"mac_addr": {"$regex": ":55$"}}'}, 200, id="P21: filter_mac_ends_55"),
    pytest.param({"filter": '{"mac_addr": {"$regex": ":6a$"}}'}, 200, id="P22: filter_mac_ends_6a"),
    pytest.param({"filter": '{"mac_addr": {"$regex": "ff:ff"}}'}, 200, id="P23: filter_mac_broadcast"),
    pytest.param({"filter": '{"mac_addr": {"$ne": "00:00:00:00:00:00"}}'}, 200, id="P24: filter_mac_not_null"),
    pytest.param({"filter": '{"mac_addr": {"$ne": "ff:ff:ff:ff:ff:ff"}}'}, 200, id="P25: filter_mac_not_broadcast"),
    
    # --- Фильтрация по ObjectId ---
    pytest.param({"filter": '{"id": {"$regex": "^507f"}}'}, 200, id="P26: filter_id_starts_507f"),
    pytest.param({"filter": '{"id": {"$regex": "^687f"}}'}, 200, id="P27: filter_id_starts_687f"),
    pytest.param({"filter": '{"id": {"$regex": "df4$"}}'}, 200, id="P28: filter_id_ends_df4"),
    pytest.param({"filter": '{"id": {"$regex": "011$"}}'}, 200, id="P29: filter_id_ends_011"),
    pytest.param({"filter": '{"id": {"$ne": "000000000000000000000000"}}'}, 200, id="P30: filter_id_not_null"),
    
    # --- Комбинированные фильтры ---
    pytest.param({"filter": '{"ipv4_addr": {"$regex": "192.168"}, "mac_addr": {"$regex": "00:"}}'}, 200, id="P31: ip_and_mac"),
    pytest.param({"filter": '{"ipv4_addr": "192.168.1.1", "mac_addr": "00:11:22:33:44:55"}'}, 200, id="P32: specific_ip_mac"),
    pytest.param({"filter": '{"id": "687feba8aa5c6d0009377df4", "ipv4_addr": "183.45.46.14"}'}, 200, id="P33: id_and_ip"),
    
    # --- Специальные MongoDB операторы ---
    pytest.param({"filter": '{"ipv4_addr": {"$in": ["192.168.1.1", "10.0.0.1", "172.16.0.1"]}}'}, 200, id="P34: ip_in_list"),
    pytest.param({"filter": '{"mac_addr": {"$in": ["00:11:22:33:44:55", "a7:07:c9:f9:1a:6a"]}}'}, 200, id="P35: mac_in_list"),
    pytest.param({"filter": '{"ipv4_addr": {"$nin": ["127.0.0.1", "0.0.0.0"]}}'}, 200, id="P36: ip_not_in_list"),
    pytest.param({"filter": '{"$or": [{"ipv4_addr": "192.168.1.1"}, {"ipv4_addr": "10.0.0.1"}]}'}, 200, id="P37: or_condition"),
    pytest.param({"filter": '{"$and": [{"ipv4_addr": {"$regex": "192.168"}}, {"mac_addr": {"$regex": "00:"}}]}'}, 200, id="P38: and_condition"),
    
    # --- Поиск и фильтрация ---
    pytest.param({"search": "192.168"}, 200, id="P39: search_ip"),
    pytest.param({"search": "183.45"}, 200, id="P40: search_ip_183"),
    pytest.param({"search": "a7:07"}, 200, id="P41: search_mac"),
    pytest.param({"search": "687f"}, 200, id="P42: search_id"),
    pytest.param({"q": "hop"}, 200, id="P43: query_hop"),
    pytest.param({"q": "openflow"}, 200, id="P44: query_openflow"),
    pytest.param({"ipv4_addr": "192.168.1.1"}, 200, id="P45: filter_by_ipv4_param"),
    pytest.param({"mac_addr": "00:11:22:33:44:55"}, 200, id="P46: filter_by_mac_param"),
    pytest.param({"id": "687feba8aa5c6d0009377df4"}, 200, id="P47: filter_by_id_param"),
    
    # --- Сортировка ---
    pytest.param({"sort": "ipv4_addr"}, 200, id="P48: sort_by_ip_asc"),
    pytest.param({"sort": "-ipv4_addr"}, 200, id="P49: sort_by_ip_desc"),
    pytest.param({"sort": "mac_addr"}, 200, id="P50: sort_by_mac"),
    pytest.param({"sort": "-mac_addr"}, 200, id="P51: sort_by_mac_desc"),
    pytest.param({"sort": "id"}, 200, id="P52: sort_by_id"),
    pytest.param({"sort": "-id"}, 200, id="P53: sort_by_id_desc"),
    
    # --- Постраничная навигация ---
    pytest.param({"limit": "10"}, 200, id="P54: pagination_limit_10"),
    pytest.param({"limit": "1"}, 200, id="P55: pagination_limit_1"),
    pytest.param({"offset": "1"}, 200, id="P56: pagination_offset_1"),
    pytest.param({"limit": "2", "offset": "1"}, 200, id="P57: pagination_limit_offset"),
    
    # --- Дополнительные параметры ---
    pytest.param({"include_metadata": "true"}, 200, id="P58: include_metadata"),
    pytest.param({"format": "json"}, 200, id="P59: format_json"),
    pytest.param({"verbose": "true"}, 200, id="P60: verbose_true"),
    
    # --- Негативные сценарии с некорректными фильтрами ---
    pytest.param({"filter": "invalid_json"}, 400, id="N01: invalid_json_rejected"),
    pytest.param({"filter": '{"invalid": }'}, 400, id="N02: malformed_json_rejected"),
    pytest.param({"filter": "null"}, 200, id="N03: null_filter_ignored"),
    pytest.param({"filter": '{"ipv4_addr": {"$invalidOp": "value"}}'}, 200, id="N04: invalid_mongo_op_ignored"),
    pytest.param({"filter": '{"nonexistent_field": "value"}'}, 200, id="N05: nonexistent_field_ignored"),
    
    # --- Граничные значения ---
    pytest.param({"limit": "0"}, 200, id="P61: zero_limit"),
    pytest.param({"limit": "-1"}, 200, id="P62: negative_limit_ignored"),
    pytest.param({"offset": "-5"}, 200, id="P63: negative_offset_ignored"),
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
def test_openflow_hops_parametrized(api_client, params, expected_status):
    """
    Основной параметризованный тест для эндпоинта /openflowHops.
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
            # Проверяем структуру каждого hop в ответе (если есть)
            for hop_data in data:
                _check_types_recursive(hop_data, OPENFLOW_HOP_SCHEMA)
                # Дополнительная проверка IP адреса
                assert "." in hop_data["ipv4_addr"], f"IPv4 адрес должен содержать точки: {hop_data['ipv4_addr']}"
                # Дополнительная проверка MAC адреса  
                assert ":" in hop_data["mac_addr"], f"MAC адрес должен содержать двоеточия: {hop_data['mac_addr']}"
                # Дополнительная проверка что ID не пустой
                assert hop_data["id"], f"ID не должен быть пустым: {hop_data['id']}"
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
