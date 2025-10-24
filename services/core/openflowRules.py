import pytest
import json
from collections.abc import Mapping, Sequence
import time

ENDPOINT = "/openflowRules"

OPENFLOW_RULE_SCHEMA = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
        "switch_id": {"type": "string"},
        "table_id": {"type": "integer"},
        "priority": {"type": "integer"},
        "match": {"type": "object"},
        "actions": {"type": "array"},
        "cookie": {"type": "string"},
        "idle_timeout": {"type": "integer"},
        "hard_timeout": {"type": "integer"},
        "flags": {"type": "array"},
        "stats": {"type": "object"}
    }
}

# Автофикстура для задержки между каждым тестом
@pytest.fixture(autouse=True)
def pause_between_tests():
    yield
    time.sleep(1)

# Осмысленная параметризация для тестирования эндпоинта /openflowRules
PARAMS = [
    # --- Базовые позитивные сценарии ---
    pytest.param({}, 200, id="P01: no_params"),
    pytest.param({"filter": '{"switch_id": "of:0000000000000001"}'}, 200, id="P02: filter_by_switch_id"),
    pytest.param({"filter": '{"switch_id": "of:0000000000000002"}'}, 200, id="P03: filter_by_switch_id_2"),
    pytest.param({"filter": '{"table_id": 0}'}, 200, id="P04: filter_by_table_0"),
    pytest.param({"filter": '{"table_id": 1}'}, 200, id="P05: filter_by_table_1"),
    pytest.param({"filter": '{"table_id": 10}'}, 200, id="P06: filter_by_table_10"),
    pytest.param({"filter": '{"priority": 100}'}, 200, id="P07: filter_by_priority_100"),
    pytest.param({"filter": '{"priority": 1000}'}, 200, id="P08: filter_by_priority_1000"),
    pytest.param({"filter": '{"priority": 65535}'}, 200, id="P09: filter_by_priority_max"),
    pytest.param({"filter": '{"cookie": "0x0"}'}, 200, id="P10: filter_by_cookie"),
    
    # --- Фильтрация по приоритету ---
    pytest.param({"filter": '{"priority": {"$gte": 100}}'}, 200, id="P11: filter_priority_gte_100"),
    pytest.param({"filter": '{"priority": {"$lte": 1000}}'}, 200, id="P12: filter_priority_lte_1000"),
    pytest.param({"filter": '{"priority": {"$gt": 0}}'}, 200, id="P13: filter_priority_gt_0"),
    pytest.param({"filter": '{"priority": {"$lt": 65535}}'}, 200, id="P14: filter_priority_lt_max"),
    pytest.param({"filter": '{"priority": {"$ne": 0}}'}, 200, id="P15: filter_priority_not_0"),
    
    # --- Фильтрация по таблицам ---
    pytest.param({"filter": '{"table_id": {"$gte": 0}}'}, 200, id="P16: filter_table_gte_0"),
    pytest.param({"filter": '{"table_id": {"$lte": 255}}'}, 200, id="P17: filter_table_lte_255"),
    pytest.param({"filter": '{"table_id": {"$in": [0, 1, 2, 3]}}'}, 200, id="P18: filter_table_in_list"),
    pytest.param({"filter": '{"table_id": {"$nin": [255]}}'}, 200, id="P19: filter_table_not_255"),
    
    # --- Фильтрация по таймаутам ---
    pytest.param({"filter": '{"idle_timeout": 0}'}, 200, id="P20: filter_idle_timeout_0"),
    pytest.param({"filter": '{"idle_timeout": {"$gt": 0}}'}, 200, id="P21: filter_idle_timeout_gt_0"),
    pytest.param({"filter": '{"hard_timeout": 0}'}, 200, id="P22: filter_hard_timeout_0"),
    pytest.param({"filter": '{"hard_timeout": {"$gt": 0}}'}, 200, id="P23: filter_hard_timeout_gt_0"),
    pytest.param({"filter": '{"idle_timeout": {"$lte": 300}}'}, 200, id="P24: filter_idle_timeout_lte_300"),
    
    # --- Фильтрация по Switch ID ---
    pytest.param({"filter": '{"switch_id": {"$regex": "of:"}}'}, 200, id="P25: filter_switch_starts_of"),
    pytest.param({"filter": '{"switch_id": {"$regex": "0000000000000001$"}}'}, 200, id="P26: filter_switch_ends_001"),
    pytest.param({"filter": '{"switch_id": {"$ne": ""}}'}, 200, id="P27: filter_switch_not_empty"),
    
    # --- Комбинированные фильтры ---
    pytest.param({"filter": '{"switch_id": "of:0000000000000001", "table_id": 0}'}, 200, id="P28: switch_and_table"),
    pytest.param({"filter": '{"table_id": 0, "priority": {"$gte": 100}}'}, 200, id="P29: table_and_priority"),
    pytest.param({"filter": '{"switch_id": {"$regex": "of:"}, "priority": {"$gt": 0}}'}, 200, id="P30: switch_regex_priority"),
    pytest.param({"filter": '{"idle_timeout": 0, "hard_timeout": 0}'}, 200, id="P31: permanent_rules"),
    
    # --- Специальные MongoDB операторы ---
    pytest.param({"filter": '{"priority": {"$in": [100, 1000, 65535]}}'}, 200, id="P32: priority_in_list"),
    pytest.param({"filter": '{"switch_id": {"$in": ["of:0000000000000001", "of:0000000000000002"]}}'}, 200, id="P33: switch_in_list"),
    pytest.param({"filter": '{"table_id": {"$nin": [254, 255]}}'}, 200, id="P34: table_not_in_list"),
    pytest.param({"filter": '{"$or": [{"priority": {"$gte": 1000}}, {"table_id": 0}]}'}, 200, id="P35: or_condition"),
    pytest.param({"filter": '{"$and": [{"priority": {"$gt": 0}}, {"table_id": {"$lt": 255}}]}'}, 200, id="P36: and_condition"),
    
    # --- Поиск и фильтрация ---
    pytest.param({"search": "of:0000000000000001"}, 200, id="P37: search_switch"),
    pytest.param({"search": "priority"}, 200, id="P38: search_priority"),
    pytest.param({"search": "100"}, 200, id="P39: search_number"),
    pytest.param({"search": "table"}, 200, id="P40: search_table"),
    pytest.param({"q": "flow"}, 200, id="P41: query_flow"),
    pytest.param({"q": "rule"}, 200, id="P42: query_rule"),
    pytest.param({"switch_id": "of:0000000000000001"}, 200, id="P43: filter_by_switch_param"),
    pytest.param({"table_id": "0"}, 200, id="P44: filter_by_table_param"),
    pytest.param({"priority": "100"}, 200, id="P45: filter_by_priority_param"),
    
    # --- Сортировка ---
    pytest.param({"sort": "priority"}, 200, id="P46: sort_by_priority_asc"),
    pytest.param({"sort": "-priority"}, 200, id="P47: sort_by_priority_desc"),
    pytest.param({"sort": "switch_id"}, 200, id="P48: sort_by_switch"),
    pytest.param({"sort": "table_id"}, 200, id="P49: sort_by_table"),
    pytest.param({"sort": "-table_id"}, 200, id="P50: sort_by_table_desc"),
    pytest.param({"sort": "cookie"}, 200, id="P51: sort_by_cookie"),
    pytest.param({"sort": "idle_timeout"}, 200, id="P52: sort_by_idle_timeout"),
    pytest.param({"sort": "hard_timeout"}, 200, id="P53: sort_by_hard_timeout"),
    
    # --- Постраничная навигация ---
    pytest.param({"limit": "10"}, 200, id="P54: pagination_limit_10"),
    pytest.param({"limit": "1"}, 200, id="P55: pagination_limit_1"),
    pytest.param({"offset": "5"}, 200, id="P56: pagination_offset_5"),
    pytest.param({"limit": "5", "offset": "2"}, 200, id="P57: pagination_limit_offset"),
    
    # --- Дополнительные параметры ---
    pytest.param({"include_metadata": "true"}, 200, id="P58: include_metadata"),
    pytest.param({"include_stats": "true"}, 200, id="P59: include_stats"),
    pytest.param({"include_actions": "true"}, 200, id="P60: include_actions"),
    pytest.param({"format": "json"}, 200, id="P61: format_json"),
    pytest.param({"format": "text"}, 200, id="P62: format_text"),
    pytest.param({"verbose": "true"}, 200, id="P63: verbose_true"),
    pytest.param({"detailed": "true"}, 200, id="P64: detailed_true"),
    
    # --- Специальные OpenFlow параметры ---
    pytest.param({"active": "true"}, 200, id="P65: active_rules_only"),
    pytest.param({"permanent": "true"}, 200, id="P66: permanent_rules_only"),
    pytest.param({"with_stats": "true"}, 200, id="P67: rules_with_stats"),
    pytest.param({"expired": "false"}, 200, id="P68: non_expired_rules"),
    
    # --- Негативные сценарии с некорректными фильтрами ---
    pytest.param({"filter": "invalid_json"}, 400, id="N01: invalid_json_rejected"),
    pytest.param({"filter": '{"invalid": }'}, 400, id="N02: malformed_json_rejected"),
    pytest.param({"filter": "null"}, 200, id="N03: null_filter_ignored"),
    pytest.param({"filter": '{"priority": {"$invalidOp": "value"}}'}, 200, id="N04: invalid_mongo_op_ignored"),
    pytest.param({"filter": '{"nonexistent_field": "value"}'}, 200, id="N05: nonexistent_field_ignored"),
    
    # --- Граничные значения ---
    pytest.param({"limit": "0"}, 200, id="P69: zero_limit"),
    pytest.param({"limit": "-1"}, 200, id="P70: negative_limit_ignored"),
    pytest.param({"offset": "-5"}, 200, id="P71: negative_offset_ignored"),
    pytest.param({"unsupported_param": "value"}, 200, id="P72: unsupported_param_ignored"),
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
def test_openflow_rules_parametrized(api_client, params, expected_status):
    """
    Основной параметризованный тест для эндпоинта /openflowRules.
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
            # Проверяем структуру каждого правила в ответе (если есть)
            for rule_data in data:
                _check_types_recursive(rule_data, OPENFLOW_RULE_SCHEMA)
                # Дополнительные проверки для OpenFlow правил
                if "priority" in rule_data:
                    assert 0 <= rule_data["priority"] <= 65535, f"Приоритет должен быть в диапазоне 0-65535: {rule_data['priority']}"
                if "table_id" in rule_data:
                    assert 0 <= rule_data["table_id"] <= 255, f"Table ID должен быть в диапазоне 0-255: {rule_data['table_id']}"
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