"""
Тесты для эндпоинта /interfaceRuntimes сервиса core.

Проверяется:
- Статус-код 200 OK
- Соответствие структуры ответа схеме (массив объектов)
- Глубокая валидация структуры
- Устойчивость к 35+ различным query-параметрам
- Вывод cURL-команды с пояснением при ошибке
"""
import pytest
import json
from collections.abc import Mapping, Sequence
import time

ENDPOINT = "/interfaceRuntimes"

INTERFACE_RUNTIME_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "rt_active": {"type": "boolean"}
    },
    "required": ["name", "rt_active"],
}

# Автофикстура для задержки между каждым тестом
@pytest.fixture(autouse=True)
def pause_between_tests():
    yield
    time.sleep(1)

# Осмысленная параметризация для тестирования эндпоинта /interfaceRuntimes
PARAMS = [
    # --- Базовые позитивные сценарии ---
    pytest.param({}, 200, id="P01: no_params"),
    pytest.param({"filter": '{"name": "bond1"}'}, 200, id="P02: filter_by_name_bond"),
    pytest.param({"filter": '{"rt_active": true}'}, 200, id="P03: filter_by_rt_active_true"),
    pytest.param({"filter": '{"rt_active": false}'}, 200, id="P04: filter_by_rt_active_false"),
    pytest.param({"filter": '{"name": "eth-0-1"}'}, 200, id="P05: filter_by_name_eth"),
    pytest.param({"filter": '{"name": {"$regex": "bond"}}'}, 200, id="P06: filter_name_regex_bond"),
    pytest.param({"filter": '{"name": {"$regex": "eth"}}'}, 200, id="P07: filter_name_regex_eth"),
    pytest.param({"filter": '{"name": {"$regex": "^bond"}}'}, 200, id="P08: filter_name_starts_bond"),
    pytest.param({"filter": '{"name": {"$regex": "1$"}}'}, 200, id="P09: filter_name_ends_1"),
    pytest.param({"filter": '{"name": {"$ne": "bond1"}}'}, 200, id="P10: filter_name_not_equal"),
    
    # --- Фильтрация по активности ---
    pytest.param({"filter": '{"rt_active": {"$ne": null}}'}, 200, id="P11: filter_rt_active_not_null"),
    pytest.param({"filter": '{"rt_active": {"$exists": true}}'}, 200, id="P12: filter_rt_active_exists"),
    pytest.param({"filter": '{"rt_active": {"$exists": false}}'}, 200, id="P13: filter_rt_active_not_exists"),
    
    # --- Комбинированные фильтры ---
    pytest.param({"filter": '{"name": "bond1", "rt_active": false}'}, 200, id="P14: name_and_rt_active"),
    pytest.param({"filter": '{"name": {"$regex": "bond"}, "rt_active": true}'}, 200, id="P15: bond_regex_active"),
    pytest.param({"filter": '{"name": {"$regex": "eth"}, "rt_active": false}'}, 200, id="P16: eth_regex_inactive"),
    
    # --- Специальные MongoDB операторы ---
    pytest.param({"filter": '{"name": {"$in": ["bond1", "bond2", "eth-0-1"]}}'}, 200, id="P17: filter_name_in_list"),
    pytest.param({"filter": '{"name": {"$nin": ["bond1", "bond2"]}}'}, 200, id="P18: filter_name_not_in_list"),
    pytest.param({"filter": '{"$or": [{"name": "bond1"}, {"name": "eth-0-1"}]}'}, 200, id="P19: filter_or_condition"),
    pytest.param({"filter": '{"$and": [{"rt_active": true}, {"name": {"$regex": "bond"}}]}'}, 200, id="P20: filter_and_condition"),
    
    # --- Поиск и фильтрация ---
    pytest.param({"search": "bond"}, 200, id="P21: search_bond"),
    pytest.param({"search": "eth"}, 200, id="P22: search_eth"),
    pytest.param({"search": "1"}, 200, id="P23: search_number"),
    pytest.param({"search": "active"}, 200, id="P24: search_active"),
    pytest.param({"q": "interface"}, 200, id="P25: query_interface"),
    pytest.param({"q": "runtime"}, 200, id="P26: query_runtime"),
    pytest.param({"name": "bond1"}, 200, id="P27: filter_by_name_param"),
    pytest.param({"rt_active": "false"}, 200, id="P28: filter_by_rt_active_param"),
    pytest.param({"rt_active": "true"}, 200, id="P29: filter_by_rt_active_true_param"),
    
    # --- Сортировка ---
    pytest.param({"sort": "name"}, 200, id="P30: sort_by_name_asc"),
    pytest.param({"sort": "-name"}, 200, id="P31: sort_by_name_desc"),
    pytest.param({"sort": "rt_active"}, 200, id="P32: sort_by_rt_active"),
    pytest.param({"sort": "-rt_active"}, 200, id="P33: sort_by_rt_active_desc"),
    
    # --- Постраничная навигация ---
    pytest.param({"limit": "10"}, 200, id="P34: pagination_limit_10"),
    pytest.param({"limit": "1"}, 200, id="P35: pagination_limit_1"),
    pytest.param({"offset": "5"}, 200, id="P36: pagination_offset_5"),
    pytest.param({"limit": "5", "offset": "2"}, 200, id="P37: pagination_limit_offset"),
    
    # --- Комбинации параметров ---
    pytest.param({"sort": "name", "limit": "3"}, 200, id="P38: sort_and_limit"),
    pytest.param({"filter": '{"rt_active": true}', "sort": "name"}, 200, id="P39: filter_and_sort"),
    pytest.param({"search": "bond", "limit": "5"}, 200, id="P40: search_and_limit"),
    pytest.param({"rt_active": "false", "sort": "name"}, 200, id="P41: rt_active_and_sort"),
    
    # --- Дополнительные параметры ---
    pytest.param({"include_metadata": "true"}, 200, id="P42: include_metadata"),
    pytest.param({"include_metadata": "false"}, 200, id="P43: exclude_metadata"),
    pytest.param({"format": "json"}, 200, id="P44: format_json"),
    pytest.param({"format": "text"}, 200, id="P45: format_text"),
    pytest.param({"format": "xml"}, 200, id="P46: format_xml"),
    pytest.param({"verbose": "true"}, 200, id="P47: verbose_true"),
    pytest.param({"verbose": "false"}, 200, id="P48: verbose_false"),
    pytest.param({"detailed": "true"}, 200, id="P49: detailed_true"),
    pytest.param({"detailed": "false"}, 200, id="P50: detailed_false"),
    pytest.param({"active": "true"}, 200, id="P51: active_only"),
    pytest.param({"active": "false"}, 200, id="P52: include_inactive"),
    
    # --- Негативные сценарии с некорректными фильтрами ---
    pytest.param({"filter": "invalid_json"}, 400, id="N01: invalid_json_rejected"),
    pytest.param({"filter": '{"invalid": }'}, 400, id="N02: malformed_json_rejected"),
    pytest.param({"filter": "null"}, 200, id="N03: null_filter_ignored"),
    pytest.param({"filter": '{"name": {"$invalidOp": "value"}}'}, 200, id="N04: invalid_mongo_op_ignored"),
    pytest.param({"filter": '{"nonexistent_field": "value"}'}, 200, id="N05: nonexistent_field_ignored"),
    
    # --- Граничные значения ---
    pytest.param({"limit": "0"}, 200, id="P53: zero_limit"),
    pytest.param({"limit": "-1"}, 200, id="P54: negative_limit_ignored"),
    pytest.param({"offset": "-5"}, 200, id="P55: negative_offset_ignored"),
    pytest.param({"unsupported_param": "value"}, 200, id="P56: unsupported_param_ignored"),
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
def test_interface_runtimes_parametrized(api_client, params, expected_status):
    """
    Основной параметризованный тест для эндпоинта /interfaceRuntimes.
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
                _check_types_recursive(interface_data, INTERFACE_RUNTIME_SCHEMA)
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