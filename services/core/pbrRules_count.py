import pytest
import json
from collections.abc import Mapping, Sequence

ENDPOINT = "/pbrRules/count"

COUNT_SCHEMA = {
    "type": "object",
    "properties": {
        "count": {"type": "integer"}
    },
    "required": ["count"],
}

# Осмысленная параметризация для тестирования эндпоинта /pbrRules/count
PARAMS = [
    # --- Базовые позитивные сценарии ---
    pytest.param({}, 200, id="P01: no_params"),
    pytest.param({"filter": '{"name": "test-rule"}'}, 200, id="P02: filter_by_name"),
    pytest.param({"filter": '{"srcIP": "192.168.1.0/24"}'}, 200, id="P03: filter_by_src_ip"),
    pytest.param({"filter": '{"name": "backup-rule"}'}, 200, id="P04: filter_by_backup_rule"),
    pytest.param({"filter": '{"srcIP": "10.0.0.0/8"}'}, 200, id="P05: filter_by_private_ip_10"),
    pytest.param({"filter": '{"srcIP": "172.16.0.0/12"}'}, 200, id="P06: filter_by_private_ip_172"),
    pytest.param({"filter": '{"name": "emergency-rule"}'}, 200, id="P07: filter_by_emergency_rule"),
    pytest.param({"filter": '{"name": "default-pbr"}'}, 200, id="P08: filter_by_default_rule"),
    pytest.param({"filter": '{"srcIP": "0.0.0.0/0"}'}, 200, id="P09: filter_by_any_ip"),
    pytest.param({"filter": '{"srcIP": "203.0.113.0/24"}'}, 200, id="P10: filter_by_test_net"),
    
    # --- Комбинированные фильтры ---
    pytest.param({"filter": '{"name": "test-rule", "srcIP": "192.168.1.0/24"}'}, 200, id="P11: name_and_ip_filter"),
    pytest.param({"filter": '{"enabled": true, "name": "test-rule"}'}, 200, id="P12: enabled_and_name"),
    pytest.param({"filter": '{"priority": 100, "enabled": true}'}, 200, id="P13: priority_and_enabled"),
    
    # --- Поиск и фильтрация ---
    pytest.param({"search": "rule"}, 200, id="P14: search_rule"),
    pytest.param({"search": "test"}, 200, id="P15: search_test"),
    pytest.param({"search": "192.168"}, 200, id="P16: search_ip_subnet"),
    pytest.param({"q": "pbr"}, 200, id="P17: query_text"),
    pytest.param({"name": "test-rule"}, 200, id="P18: filter_by_name_param"),
    pytest.param({"srcIP": "192.168.1.0/24"}, 200, id="P19: filter_by_src_ip_param"),
    
    # --- Дополнительные параметры (игнорируются для count) ---
    pytest.param({"sort": "name"}, 200, id="P20: sort_ignored"),
    pytest.param({"limit": "10"}, 200, id="P21: limit_ignored"),
    pytest.param({"offset": "5"}, 200, id="P22: offset_ignored"),
    pytest.param({"order": "desc"}, 200, id="P23: order_ignored"),
    pytest.param({"page": "1"}, 200, id="P24: page_ignored"),
    
    # --- Специальные фильтры ---
    pytest.param({"enabled": "true"}, 200, id="P25: filter_by_enabled"),
    pytest.param({"enabled": "false"}, 200, id="P26: filter_by_disabled"),
    pytest.param({"priority": "100"}, 200, id="P27: filter_by_priority"),
    pytest.param({"table": "main"}, 200, id="P28: filter_by_table"),
    pytest.param({"action": "lookup"}, 200, id="P29: filter_by_action"),
    pytest.param({"protocol": "tcp"}, 200, id="P30: filter_by_protocol"),
    pytest.param({"src_port": "80"}, 200, id="P31: filter_by_src_port"),
    pytest.param({"dst_port": "443"}, 200, id="P32: filter_by_dst_port"),
    pytest.param({"interface": "eth0"}, 200, id="P33: filter_by_interface"),
    pytest.param({"gateway": "192.168.1.1"}, 200, id="P34: filter_by_gateway"),
    pytest.param({"tos": "0"}, 200, id="P35: filter_by_tos"),
    pytest.param({"fwmark": "1"}, 200, id="P36: filter_by_fwmark"),
    pytest.param({"metric": "100"}, 200, id="P37: filter_by_metric"),
    pytest.param({"scope": "host"}, 200, id="P38: filter_by_scope"),
    pytest.param({"type": "unicast"}, 200, id="P39: filter_by_type_unicast"),
    pytest.param({"realm": "1"}, 200, id="P40: filter_by_realm"),
    
    # --- Негативные сценарии ---
    pytest.param({"filter": "invalid_json"}, 200, id="N01: invalid_json_filter_ignored"),
    pytest.param({"filter": '{"invalid": }'}, 200, id="N02: malformed_json_ignored"),
    pytest.param({"filter": "null"}, 200, id="P41: null_filter_ignored"),
    pytest.param({"limit": "-1"}, 200, id="P42: negative_limit_ignored"),
    pytest.param({"offset": "-5"}, 200, id="P43: negative_offset_ignored"),
    
    # --- Граничные значения ---
    pytest.param({"unsupported_param": "value"}, 200, id="P44: unsupported_param_ignored"),
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
def test_pbr_rules_count_parametrized(api_client, params, expected_status):
    """
    Основной параметризованный тест для эндпоинта /pbrRules/count.
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