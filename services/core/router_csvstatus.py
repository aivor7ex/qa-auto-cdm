"""Tests for the /router/csvstatus endpoint."""
import pytest
import json
from collections.abc import Mapping, Sequence

ENDPOINT = "/router/csvstatus"

CSV_STATUS_SCHEMA = {
    "type": "object",
    "properties": {
        "status": {"type": "string"},
        "csv": {"type": "string"},
        "data": {"type": "array"},
        "headers": {"type": "array"},
        "rows": {"type": "integer"}
    },
    "required": [],
}

# Осмысленная параметризация для тестирования эндпоинта /router/csvstatus/{id}
PARAMS = [
    # --- Базовые негативные сценарии с несуществующими ID ---
    pytest.param({"id": "routes"}, 404, id="N01: routes_status_not_found"),
    pytest.param({"id": "interfaces"}, 404, id="N02: interfaces_status_not_found"),
    pytest.param({"id": "neighbors"}, 404, id="N03: neighbors_status_not_found"),
    pytest.param({"id": "statistics"}, 404, id="N04: statistics_status_not_found"),
    pytest.param({"id": "config"}, 404, id="N05: config_status_not_found"),
    pytest.param({"id": "ospf"}, 404, id="N06: ospf_status_not_found"),
    pytest.param({"id": "bgp"}, 404, id="N07: bgp_status_not_found"),
    pytest.param({"id": "rip"}, 404, id="N08: rip_status_not_found"),
    pytest.param({"id": "static"}, 404, id="N09: static_status_not_found"),
    pytest.param({"id": "kernel"}, 404, id="N10: kernel_status_not_found"),
    
    # --- Дополнительные параметры с несуществующими ID ---
    pytest.param({"id": "routes", "format": "csv"}, 404, id="N11: routes_with_format"),
    pytest.param({"id": "routes", "delimiter": ","}, 404, id="N12: routes_with_delimiter"),
    pytest.param({"id": "routes", "headers": "true"}, 404, id="N13: routes_with_headers"),
    pytest.param({"id": "routes", "encoding": "utf-8"}, 404, id="N14: routes_with_encoding"),
    pytest.param({"id": "interfaces", "compact": "true"}, 404, id="N15: interfaces_compact"),
    pytest.param({"id": "interfaces", "verbose": "true"}, 404, id="N16: interfaces_verbose"),
    pytest.param({"id": "statistics", "period": "1h"}, 404, id="N17: statistics_period"),
    pytest.param({"id": "statistics", "aggregation": "sum"}, 404, id="N18: statistics_aggregation"),
    
    # --- Комбинации параметров с несуществующими ID ---
    pytest.param({"id": "routes", "format": "csv", "headers": "true"}, 404, id="N19: routes_csv_headers"),
    pytest.param({"id": "interfaces", "format": "csv", "delimiter": ";"}, 404, id="N20: interfaces_csv_semicolon"),
    pytest.param({"id": "neighbors", "verbose": "true", "format": "csv"}, 404, id="N21: neighbors_verbose_csv"),
    pytest.param({"id": "statistics", "period": "1d", "aggregation": "avg"}, 404, id="N22: statistics_daily_avg"),
    
    # --- Специальные фильтры с несуществующими ID ---
    pytest.param({"id": "routes", "protocol": "ospf"}, 404, id="N23: routes_ospf"),
    pytest.param({"id": "routes", "protocol": "bgp"}, 404, id="N24: routes_bgp"),
    pytest.param({"id": "routes", "protocol": "static"}, 404, id="N25: routes_static"),
    pytest.param({"id": "interfaces", "type": "ethernet"}, 404, id="N26: interfaces_ethernet"),
    pytest.param({"id": "interfaces", "type": "bond"}, 404, id="N27: interfaces_bond"),
    pytest.param({"id": "interfaces", "active": "true"}, 404, id="N28: interfaces_active"),
    pytest.param({"id": "neighbors", "state": "full"}, 404, id="N29: neighbors_full_state"),
    pytest.param({"id": "neighbors", "state": "down"}, 404, id="N30: neighbors_down_state"),
    pytest.param({"id": "statistics", "interface": "eth0"}, 404, id="N31: statistics_eth0"),
    pytest.param({"id": "config", "section": "routing"}, 404, id="N32: config_routing_section"),
    
    # --- Дополнительные системные параметры с несуществующими ID ---
    pytest.param({"id": "routes", "limit": "100"}, 404, id="N33: routes_with_limit"),
    pytest.param({"id": "routes", "offset": "10"}, 404, id="N34: routes_with_offset"),
    pytest.param({"id": "routes", "sort": "metric"}, 404, id="N35: routes_sort_metric"),
    pytest.param({"id": "interfaces", "filter": "active"}, 404, id="N36: interfaces_filter_active"),
    
    # --- Дополнительные негативные сценарии ---
    pytest.param({"id": "nonexistent"}, 404, id="N38: nonexistent_id"),
    pytest.param({"id": "invalid-format"}, 404, id="N39: invalid_format_id"),
    pytest.param({"id": ""}, 422, id="N40: empty_id"),
    pytest.param({"id": " "}, 404, id="N41: space_id"),
    pytest.param({"id": "12345"}, 404, id="N42: numeric_id"),
    pytest.param({"id": "special!@#"}, 404, id="N43: special_chars_id"),
    pytest.param({"id": "very-long-invalid-id-name"}, 404, id="N44: long_invalid_id"),
    pytest.param({"id": "null"}, 404, id="N45: null_string_id"),
    pytest.param({"id": "undefined"}, 404, id="N46: undefined_string_id"),
    
    # --- Граничные значения ---
    pytest.param({"id": "routes", "unsupported": "param"}, 404, id="N37: routes_unsupported_param"),
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


def _format_curl_command(api_client, endpoint, status_id, params):
    """Формирует и возвращает cURL-строку для воспроизведения запроса."""
    base_url = getattr(api_client, "base_url", "http://127.0.0.1")
    full_url = f"{base_url.rstrip('/')}/{endpoint.lstrip('/')}/{status_id}"
    
    # Формируем строку параметров (исключая id)
    filtered_params = {k: v for k, v in params.items() if k != "id"}
    if filtered_params:
        param_str = "&".join([f"{k}={v}" for k, v in filtered_params.items() if v is not None])
        full_url += f"?{param_str}"

    headers = getattr(api_client, 'headers', {})
    headers_str = " \\\n  ".join([f"-H '{k}: {v}'" for k, v in headers.items()])
    
    curl_command = f"curl -X GET '{full_url}'"
    if headers_str:
        curl_command += f" \\\n  {headers_str}"
        
    return curl_command


@pytest.mark.parametrize("params, expected_status", PARAMS)
def test_router_csv_status_parametrized(api_client, params, expected_status):
    """
    Основной параметризованный тест для эндпоинта /router/csvstatus/{id}.
    1. Отправляет GET-запрос с указанными параметрами и ID.
    2. Проверяет соответствие статус-кода ожидаемому.
    3. Для успешных ответов (200) валидирует схему JSON.
    4. В случае падения теста выводит полную cURL-команду для воспроизведения.
    """
    status_id = params.pop("id")
    try:
        response = api_client.get(f"{ENDPOINT}/{status_id}", params=params)
        
        # 1. Проверка статус-кода
        assert response.status_code == expected_status, \
            f"Ожидался статус-код {expected_status}, получен {response.status_code}. Ответ: {response.text}"

        # 2. Валидация схемы ответа
        if response.status_code == 200:
            data = response.json()
            # CSV status может возвращать разные форматы данных
            if isinstance(data, dict):
                _check_types_recursive(data, CSV_STATUS_SCHEMA)
            elif isinstance(data, list):
                # Для некоторых CSV статусов может вернуться массив
                pass
            elif isinstance(data, str):
                # Для некоторых CSV статусов может вернуться строка
                pass
        elif response.status_code in [404, 422]:
            # Для 404/422 статус-кодов проверяем что есть error объект
            data = response.json()
            assert "error" in data, f"Ответ с {response.status_code} статусом должен содержать error объект"

    except (AssertionError, json.JSONDecodeError) as e:
        # 3. Формирование и вывод детального отчета об ошибке
        curl_command = _format_curl_command(api_client, ENDPOINT, status_id, params)
        
        error_message = (
            f"\nТест с ID '{status_id}' и параметрами {params} упал.\n"
            f"Ошибка: {e}\n\n"
            "================= Failed Test Request (cURL) ================\n"
            f"{curl_command}\n"
            "============================================================="
        )
        pytest.fail(error_message, pytrace=False) 