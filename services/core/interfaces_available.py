"""
Тесты для эндпоинта /interfaces/available сервиса core.

Проверяется:
- Статус-код 200 OK
- Соответствие структуры ответа схеме (массив объектов)
- Глубокая валидация вложенных структур
- Устойчивость к 35+ различным query-параметрам
- Вывод cURL-команды с пояснением при ошибке
"""
import pytest
import json
from collections.abc import Mapping, Sequence
import time

ENDPOINT = "/interfaces/available"

INTERFACE_AVAILABLE_SCHEMA = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
        "isBond": {"type": "boolean"},
        "if": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "if": {"type": "string"},
                    "type": {"type": "string"}
                }
            }
        },
        "name": {"type": "string"},
        "ifType": {"type": "string"}
    },
    "required": ["id", "name"],
}

# Автофикстура для задержки между каждым тестом
@pytest.fixture(autouse=True)
def pause_between_tests():
    yield
    time.sleep(1)

# Осмысленная параметризация для тестирования эндпоинта /interfaces/available
PARAMS = [
    # --- Базовые позитивные сценарии ---
    pytest.param({}, 200, id="P01: no_params"),
    pytest.param({"filter": '{"isBond": true}'}, 200, id="P02: filter_by_is_bond_true"),
    pytest.param({"filter": '{"isBond": false}'}, 200, id="P03: filter_by_is_bond_false"),
    pytest.param({"filter": '{"ifType": "access"}'}, 200, id="P04: filter_by_access_type"),
    pytest.param({"filter": '{"ifType": "trunk"}'}, 200, id="P05: filter_by_trunk_type"),
    pytest.param({"filter": '{"name": "eth-0-42"}'}, 200, id="P06: filter_by_specific_name"),
    pytest.param({"filter": '{"name": "eth-0-8"}'}, 200, id="P07: filter_by_another_name"),
    pytest.param({"filter": '{"id": "eth-0-42"}'}, 200, id="P08: filter_by_specific_id"),
    pytest.param({"filter": '{"id": "eth-0-8"}'}, 200, id="P09: filter_by_another_id"),
    pytest.param({"filter": '{"type": "switch"}'}, 200, id="P10: filter_by_switch_type"),
    
    # --- Фильтрация по названиям с regex ---
    pytest.param({"filter": '{"name": {"$regex": "eth"}}'}, 200, id="P11: filter_name_regex_eth"),
    pytest.param({"filter": '{"name": {"$regex": "bond"}}'}, 200, id="P12: filter_name_regex_bond"),
    pytest.param({"filter": '{"id": {"$regex": "eth-0"}}'}, 200, id="P13: filter_id_regex_eth_0"),
    pytest.param({"filter": '{"name": {"$regex": "^eth-0-"}}'}, 200, id="P14: filter_name_starts_with_eth_0"),
    
    # --- Комбинированные фильтры ---
    pytest.param({"filter": '{"isBond": false, "ifType": "access"}'}, 200, id="P15: non_bond_access"),
    pytest.param({"filter": '{"isBond": true, "ifType": "trunk"}'}, 200, id="P16: bond_trunk"),
    pytest.param({"filter": '{"type": "switch", "ifType": "access"}'}, 200, id="P17: switch_access"),
    pytest.param({"filter": '{"isBond": false, "type": "switch"}'}, 200, id="P18: non_bond_switch"),
    
    # --- Поиск и фильтрация ---
    pytest.param({"search": "eth"}, 200, id="P19: search_eth"),
    pytest.param({"search": "42"}, 200, id="P20: search_42"),
    pytest.param({"search": "8"}, 200, id="P21: search_8"),
    pytest.param({"search": "access"}, 200, id="P22: search_access"),
    pytest.param({"search": "switch"}, 200, id="P23: search_switch"),
    pytest.param({"q": "interface"}, 200, id="P24: query_interface"),
    pytest.param({"q": "available"}, 200, id="P25: query_available"),
    pytest.param({"name": "eth-0-42"}, 200, id="P26: filter_by_name_param"),
    pytest.param({"id": "eth-0-8"}, 200, id="P27: filter_by_id_param"),
    pytest.param({"isBond": "false"}, 200, id="P28: filter_by_is_bond_param"),
    pytest.param({"ifType": "access"}, 200, id="P29: filter_by_type_param"),
    
    # --- Сортировка ---
    pytest.param({"sort": "name"}, 200, id="P30: sort_by_name_asc"),
    pytest.param({"sort": "-name"}, 200, id="P31: sort_by_name_desc"),
    pytest.param({"sort": "id"}, 200, id="P32: sort_by_id_asc"),
    pytest.param({"sort": "-id"}, 200, id="P33: sort_by_id_desc"),
    pytest.param({"sort": "ifType"}, 200, id="P34: sort_by_type"),
    pytest.param({"sort": "-ifType"}, 200, id="P35: sort_by_type_desc"),
    
    # --- Постраничная навигация ---
    pytest.param({"limit": "10"}, 200, id="P36: pagination_limit_10"),
    pytest.param({"limit": "1"}, 200, id="P37: pagination_limit_1"),
    pytest.param({"offset": "5"}, 200, id="P38: pagination_offset_5"),
    pytest.param({"limit": "3", "offset": "1"}, 200, id="P39: pagination_limit_offset"),
    
    # --- Комбинации параметров ---
    pytest.param({"sort": "name", "limit": "5"}, 200, id="P40: sort_and_limit"),
    pytest.param({"filter": '{"isBond": false}', "sort": "id"}, 200, id="P41: filter_and_sort"),
    pytest.param({"search": "eth", "limit": "3"}, 200, id="P42: search_and_limit"),
    pytest.param({"isBond": "false", "sort": "name"}, 200, id="P43: is_bond_and_sort"),
    
    # --- Специальные параметры ---
    pytest.param({"include_bonds": "true"}, 200, id="P44: include_bonds"),
    pytest.param({"include_bonds": "false"}, 200, id="P45: exclude_bonds"),
    pytest.param({"include_virtual": "true"}, 200, id="P46: include_virtual"),
    pytest.param({"include_virtual": "false"}, 200, id="P47: exclude_virtual"),
    pytest.param({"only_physical": "true"}, 200, id="P48: only_physical"),
    pytest.param({"only_physical": "false"}, 200, id="P49: include_non_physical"),
    pytest.param({"detailed": "true"}, 200, id="P50: detailed_info"),
    pytest.param({"detailed": "false"}, 200, id="P51: basic_info"),
    pytest.param({"format": "json"}, 200, id="P52: format_json"),
    pytest.param({"format": "xml"}, 200, id="P53: format_xml"),
    pytest.param({"verbose": "true"}, 200, id="P54: verbose_output"),
    pytest.param({"verbose": "false"}, 200, id="P55: brief_output"),
    pytest.param({"show_types": "true"}, 200, id="P56: show_types"),
    pytest.param({"show_types": "false"}, 200, id="P57: hide_types"),
    pytest.param({"status": "available"}, 200, id="P58: status_available"),
    pytest.param({"status": "all"}, 200, id="P59: status_all"),
    pytest.param({"availability": "free"}, 200, id="P60: availability_free"),
    pytest.param({"availability": "unused"}, 200, id="P61: availability_unused"),
    
    # --- Граничные значения ---
    pytest.param({"limit": "0"}, 200, id="P62: zero_limit"),
    pytest.param({"limit": "-1"}, 200, id="P63: negative_limit_ignored"),
    pytest.param({"offset": "-3"}, 200, id="P64: negative_offset_ignored"),
    pytest.param({"unsupported_param": "value"}, 200, id="P65: unsupported_param_ignored"),
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
def test_interfaces_available_parametrized(api_client, params, expected_status):
    """
    Основной параметризованный тест для эндпоинта /interfaces/available.
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
            # Проверяем структуру каждого доступного интерфейса в ответе
            for interface_data in data:
                _check_types_recursive(interface_data, INTERFACE_AVAILABLE_SCHEMA)

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