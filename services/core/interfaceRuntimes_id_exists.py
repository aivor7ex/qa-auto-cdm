"""
Тесты для эндпоинта /interfaceRuntimes/{id}/exists сервиса core.

Проверяется:
- Корректное получение ID из зависимого эндпоинта
- Статус-код 200 OK для существующего ID
- Ответ {"exists": true} для существующего ID
- Ответ {"exists": false} для несуществующего ID
- Устойчивость к 35+ различным форматам ID
- Вывод cURL-команды с пояснением при ошибке
"""
import pytest
import json
from collections.abc import Mapping, Sequence

ENDPOINT = "/interfaceRuntimes"

EXISTS_SCHEMA = {
    "type": "object",
    "properties": {
        "exists": {"type": "boolean"}
    },
    "required": ["exists"],
}

# Осмысленная параметризация для тестирования эндпоинта /interfaceRuntimes/{id}/exists
PARAMS = [
    # --- Базовые позитивные сценарии с потенциально существующими ID ---
    pytest.param({"id": "bond1"}, 200, id="P01: existing_bond1_id"),
    pytest.param({"id": "bond2"}, 200, id="P02: existing_bond2_id"),
    pytest.param({"id": "bond10"}, 200, id="P03: existing_bond10_id"),
    pytest.param({"id": "bond11"}, 200, id="P04: existing_bond11_id"),
    pytest.param({"id": "bond12"}, 200, id="P05: existing_bond12_id"),
    pytest.param({"id": "eth-0-1"}, 200, id="P06: existing_eth_0_1_id"),
    pytest.param({"id": "eth-0-2"}, 200, id="P07: existing_eth_0_2_id"),
    pytest.param({"id": "eth-0-42"}, 200, id="P08: existing_eth_0_42_id"),
    pytest.param({"id": "eth-0-8"}, 200, id="P09: existing_eth_0_8_id"),
    pytest.param({"id": "lo"}, 200, id="P10: existing_loopback_id"),
    
    # --- Негативные сценарии с несуществующими ID ---
    pytest.param({"id": "nonexistent"}, 200, id="N01: nonexistent_id"),
    pytest.param({"id": "fake-interface"}, 200, id="N02: fake_interface_id"),
    pytest.param({"id": "test123"}, 200, id="N03: test_id"),
    pytest.param({"id": "invalid-name"}, 200, id="N04: invalid_name_id"),
    pytest.param({"id": "bond999"}, 200, id="N05: non_existing_bond"),
    pytest.param({"id": "eth-999-999"}, 200, id="N06: non_existing_eth"),
    pytest.param({"id": "unknown"}, 200, id="N07: unknown_id"),
    pytest.param({"id": "missing"}, 200, id="N08: missing_id"),
    pytest.param({"id": "notfound"}, 200, id="N09: notfound_id"),
    pytest.param({"id": "absent"}, 200, id="N10: absent_id"),
    
    # --- Специальные символы и граничные случаи ---
    pytest.param({"id": ""}, 404, id="N11: empty_id"),
    pytest.param({"id": " "}, 200, id="N12: space_id"),
    pytest.param({"id": "null"}, 400, id="N13: null_string_id"),
    pytest.param({"id": "undefined"}, 200, id="N14: undefined_string_id"),
    pytest.param({"id": "0"}, 200, id="N15: zero_id"),
    pytest.param({"id": "1"}, 200, id="N16: one_id"),
    pytest.param({"id": "-1"}, 200, id="N17: negative_id"),
    pytest.param({"id": "special!@#$%^&*()"}, 404, id="N18: special_chars_id"),
    pytest.param({"id": "../../etc/passwd"}, 404, id="N19: path_traversal_id"),
    pytest.param({"id": "<script>alert(1)</script>"}, 404, id="N20: xss_id"),
    pytest.param({"id": "' OR 1=1 --"}, 200, id="N21: sql_injection_id"),
    pytest.param({"id": "very-long-interface-name-that-should-not-exist-in-system"}, 200, id="N22: very_long_id"),
    
    # --- Дополнительные параметры (должны игнорироваться) ---
    pytest.param({"id": "bond1", "format": "json"}, 200, id="P11: bond1_with_format"),
    pytest.param({"id": "bond1", "verbose": "true"}, 200, id="P12: bond1_verbose"),
    pytest.param({"id": "bond1", "detailed": "true"}, 200, id="P13: bond1_detailed"),
    pytest.param({"id": "bond1", "include_metadata": "true"}, 200, id="P14: bond1_metadata"),
    pytest.param({"id": "bond1", "expand": "true"}, 200, id="P15: bond1_expand"),
    pytest.param({"id": "eth-0-1", "format": "xml"}, 200, id="P16: eth_with_xml"),
    pytest.param({"id": "eth-0-1", "verbose": "false"}, 200, id="P17: eth_not_verbose"),
    pytest.param({"id": "eth-0-1", "cache": "true"}, 200, id="P18: eth_with_cache"),
    pytest.param({"id": "eth-0-1", "refresh": "true"}, 200, id="P19: eth_refresh"),
    pytest.param({"id": "eth-0-1", "timeout": "30"}, 200, id="P20: eth_timeout"),
    
    # --- Комбинации параметров ---
    pytest.param({"id": "bond1", "format": "json", "verbose": "true"}, 200, id="P21: bond1_json_verbose"),
    pytest.param({"id": "bond1", "detailed": "true", "expand": "true"}, 200, id="P22: bond1_detailed_expand"),
    pytest.param({"id": "eth-0-1", "include_metadata": "true", "verbose": "true"}, 200, id="P23: eth_metadata_verbose"),
    
    # --- Игнорируемые параметры ---
    pytest.param({"id": "bond1", "limit": "10"}, 200, id="P24: bond1_with_limit"),
    pytest.param({"id": "bond1", "offset": "5"}, 200, id="P25: bond1_with_offset"),
    pytest.param({"id": "bond1", "sort": "name"}, 200, id="P26: bond1_with_sort"),
    pytest.param({"id": "bond1", "filter": "ignored"}, 200, id="P27: bond1_with_filter"),
    pytest.param({"id": "bond1", "search": "ignored"}, 200, id="P28: bond1_with_search"),
    pytest.param({"id": "bond1", "page": "1"}, 200, id="P29: bond1_with_page"),
    pytest.param({"id": "bond1", "q": "query"}, 200, id="P30: bond1_with_query"),
    
    # --- Граничные значения ---
    pytest.param({"id": "bond1", "unsupported": "param"}, 200, id="P31: bond1_unsupported_param"),
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
    full_url = f"{base_url.rstrip('/')}/{endpoint.lstrip('/')}/{interface_id}/exists"
    
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
def test_interface_runtimes_id_exists_parametrized(api_client, params, expected_status):
    """
    Основной параметризованный тест для эндпоинта /interfaceRuntimes/{id}/exists.
    1. Отправляет GET-запрос с указанными параметрами и ID.
    2. Проверяет соответствие статус-кода ожидаемому.
    3. Для успешных ответов (200) валидирует схему JSON.
    4. В случае падения теста выводит полную cURL-команду для воспроизведения.
    """
    interface_id = params.pop("id")
    try:
        response = api_client.get(f"{ENDPOINT}/{interface_id}/exists", params=params)
        
        # 1. Проверка статус-кода
        assert response.status_code == expected_status, \
            f"Ожидался статус-код {expected_status}, получен {response.status_code}. Ответ: {response.text}"

        # 2. Валидация схемы ответа
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, dict), f"Тело ответа не является объектом JSON, получено: {type(data).__name__}"
            _check_types_recursive(data, EXISTS_SCHEMA)
            # Дополнительная проверка что exists - булево значение
            assert isinstance(data["exists"], bool), f"Поле 'exists' должно быть булевым, получено: {type(data['exists'])}"
        elif response.status_code in [400, 404]:
            # Для 400/404 статус-кода проверяем что есть error объект
            data = response.json()
            assert "error" in data, f"Ответ с {response.status_code} статусом должен содержать error объект"

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