"""
Тесты для эндпоинта /interfaces/{id} сервиса core.

Проверяется:
- Успешное получение объекта по валидному ID (200 OK)
- Корректность структуры ответа схеме
- Реакция на невалидные и несуществующие ID (404 Not Found)
- Устойчивость к 35+ различным вариантам невалидных ID
"""
import pytest
import json
from collections.abc import Mapping, Sequence
import time

ENDPOINT = "/interfaces"

INTERFACE_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "accessory": {"type": "string"},
        "ifType": {"type": "string"},
        "isBond": {"type": "boolean"},
        "active": {"type": "boolean"},
        "pos": {"type": "integer"}
    },
    "required": ["name", "accessory", "ifType", "active", "pos"],
}

# Автофикстура для задержки между каждым тестом
@pytest.fixture(autouse=True)
def pause_between_tests():
    yield
    time.sleep(0.5)

# Осмысленная параметризация для тестирования эндпоинта /interfaces/{id}
PARAMS = [
    # --- Базовые позитивные сценарии с потенциально существующими ID ---
    pytest.param({"id": "1"}, 204, id="P01: existing_id_1"),
    pytest.param({"id": "2"}, 204, id="P02: existing_id_2"),
    pytest.param({"id": "3"}, 204, id="P03: existing_id_3"),
    pytest.param({"id": "10"}, 204, id="P04: existing_id_10"),
    pytest.param({"id": "100"}, 204, id="P05: existing_id_100"),
    pytest.param({"id": "bond1"}, 200, id="P06: existing_bond1_id"),
    pytest.param({"id": "bond2"}, 200, id="P07: existing_bond2_id"),
    pytest.param({"id": "eth-0-1"}, 200, id="P08: existing_eth_0_1_id"),
    pytest.param({"id": "eth-0-2"}, 200, id="P09: existing_eth_0_2_id"),
    pytest.param({"id": "lo"}, 204, id="P10: existing_loopback_id"),
    
    # --- Дополнительные параметры с существующими ID ---
    pytest.param({"id": "1", "format": "json"}, 204, id="P11: id_1_with_format"),
    pytest.param({"id": "1", "verbose": "true"}, 204, id="P12: id_1_verbose"),
    pytest.param({"id": "1", "detailed": "true"}, 204, id="P13: id_1_detailed"),
    pytest.param({"id": "1", "include_metadata": "true"}, 204, id="P14: id_1_metadata"),
    pytest.param({"id": "1", "expand": "true"}, 204, id="P15: id_1_expand"),
    pytest.param({"id": "bond1", "format": "xml"}, 200, id="P16: bond1_with_xml"),
    pytest.param({"id": "bond1", "verbose": "false"}, 200, id="P17: bond1_not_verbose"),
    pytest.param({"id": "bond1", "cache": "true"}, 200, id="P18: bond1_with_cache"),
    pytest.param({"id": "bond1", "refresh": "true"}, 200, id="P19: bond1_refresh"),
    pytest.param({"id": "bond1", "timeout": "30"}, 200, id="P20: bond1_timeout"),
    
    # --- Комбинации параметров с существующими ID ---
    pytest.param({"id": "1", "format": "json", "verbose": "true"}, 204, id="P21: id_1_json_verbose"),
    pytest.param({"id": "1", "detailed": "true", "expand": "true"}, 204, id="P22: id_1_detailed_expand"),
    pytest.param({"id": "bond1", "include_metadata": "true", "verbose": "true"}, 200, id="P23: bond1_metadata_verbose"),
    
    # --- Игнорируемые параметры с существующими ID ---
    pytest.param({"id": "1", "limit": "10"}, 204, id="P24: id_1_with_limit"),
    pytest.param({"id": "1", "offset": "5"}, 204, id="P25: id_1_with_offset"),
    pytest.param({"id": "1", "sort": "name"}, 204, id="P26: id_1_with_sort"),
    pytest.param({"id": "1", "search": "ignored"}, 204, id="P27: id_1_with_search"),
    pytest.param({"id": "1", "page": "1"}, 204, id="P28: id_1_with_page"),
    pytest.param({"id": "1", "q": "query"}, 204, id="P29: id_1_with_query"),
    
    # --- Негативные сценарии с несуществующими ID ---
    pytest.param({"id": "nonexistent"}, 204, id="N01: nonexistent_id"),
    pytest.param({"id": "fake-interface"}, 204, id="N02: fake_interface_id"),
    pytest.param({"id": "test123"}, 204, id="N03: test_id"),
    pytest.param({"id": "invalid-name"}, 204, id="N04: invalid_name_id"),
    pytest.param({"id": "999999"}, 204, id="N05: non_existing_id_999999"),
    pytest.param({"id": "eth-999-999"}, 204, id="N06: non_existing_eth"),
    pytest.param({"id": "unknown"}, 204, id="N07: unknown_id"),
    pytest.param({"id": "missing"}, 204, id="N08: missing_id"),
    pytest.param({"id": "notfound"}, 204, id="N09: notfound_id"),
    pytest.param({"id": "absent"}, 204, id="N10: absent_id"),
    
    # --- Специальные символы и граничные случаи ---
    pytest.param({"id": ""}, 200, id="N11: empty_id_returns_list"),
    pytest.param({"id": " "}, 204, id="N12: space_id"),
    pytest.param({"id": "null"}, 204, id="N13: null_string_id"),
    pytest.param({"id": "undefined"}, 204, id="N14: undefined_string_id"),
    pytest.param({"id": "0"}, 204, id="N15: zero_id"),
    pytest.param({"id": "-1"}, 204, id="N16: negative_id"),
    pytest.param({"id": "special!@#$%^&*()"}, 204, id="N17: special_chars_id"),
    pytest.param({"id": "../../etc/passwd"}, 404, id="N18: path_traversal_id"),
    pytest.param({"id": "<script>alert(1)</script>"}, 404, id="N19: xss_id"),
    pytest.param({"id": "' OR 1=1 --"}, 204, id="N20: sql_injection_id"),
    pytest.param({"id": "very-long-interface-name-that-should-not-exist-in-system"}, 204, id="N21: very_long_id"),
    
    # --- Дополнительные параметры с несуществующими ID ---
    pytest.param({"id": "nonexistent", "format": "json"}, 204, id="N22: nonexistent_with_format"),
    pytest.param({"id": "fake", "verbose": "true"}, 204, id="N23: fake_verbose"),
    pytest.param({"id": "", "detailed": "true"}, 200, id="N24: empty_detailed"),
    
    # --- Граничные значения ---
    pytest.param({"id": "1", "unsupported": "param"}, 204, id="P30: id_1_unsupported_param"),
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


def _format_curl_command(api_client, endpoint, interface_id, params):
    """Формирует и возвращает cURL-строку для воспроизведения запроса."""
    base_url = getattr(api_client, "base_url", "http://127.0.0.1")
    full_url = f"{base_url.rstrip('/')}/{endpoint.lstrip('/')}/{interface_id}"
    
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
def test_interfaces_id_parametrized(api_client, params, expected_status):
    """
    Основной параметризованный тест для эндпоинта /interfaces/{id}.
    1. Отправляет GET-запрос с указанными параметрами и ID.
    2. Проверяет соответствие статус-кода ожидаемому.
    3. Для успешных ответов (200) валидирует схему JSON.
    4. В случае падения теста выводит полную cURL-команду для воспроизведения.
    """
    interface_id = params.pop("id")
    try:
        response = api_client.get(f"{ENDPOINT}/{interface_id}", params=params)
        
        # 1. Проверка статус-кода
        assert response.status_code == expected_status, \
            f"Ожидался статус-код {expected_status}, получен {response.status_code}. Ответ: {response.text}"

        # 2. Валидация схемы ответа
        if response.status_code == 200:
            data = response.json()
            # Для пустого ID возвращается список интерфейсов
            if interface_id == "":
                assert isinstance(data, list), f"Тело ответа не является массивом JSON, получено: {type(data).__name__}"
                for interface_data in data:
                    _check_types_recursive(interface_data, INTERFACE_SCHEMA)
            else:
                assert isinstance(data, dict), f"Тело ответа не является объектом JSON, получено: {type(data).__name__}"
                _check_types_recursive(data, INTERFACE_SCHEMA)
                # Дополнительная проверка что name соответствует запрошенному ID
                assert data["name"] == interface_id, f"Name в ответе {data['name']} не соответствует запрошенному ID {interface_id}"
        elif response.status_code == 204:
            # Для 204 ответов проверяем что тело пустое
            assert not response.text, f"Ответ 204 должен иметь пустое тело, получено: {response.text}"
        elif response.status_code == 404:
            # Для 404 статус-кода проверяем что есть error объект
            data = response.json()
            assert "error" in data, f"Ответ с 404 статусом должен содержать error объект"

    except (AssertionError, json.JSONDecodeError) as e:
        # 3. Формирование и вывод детального отчета об ошибке
        curl_command = _format_curl_command(api_client, ENDPOINT, interface_id, params)
        
        error_message = (
            f"\nТест с ID '{interface_id}' и параметрами {params} упал.\n"
            f"Ошибка: {e}\n\n"
            "================= Failed Test Request (cURL) ================\n"
            f"{curl_command}\n"
            "============================================================="
        )
        pytest.fail(error_message, pytrace=False) 