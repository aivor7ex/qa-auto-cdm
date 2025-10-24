import pytest
from jsonschema import validate, ValidationError
import re

# Константа с эндпоинтом
ENDPOINT = "/vlans/bridge"

# --- Схема ответа ---
BRIDGE_ITEM_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "id": {"type": "string"},
        "stp": {"type": "string"},
        "vlanId": {"type": "integer"},
        "mtu": {"type": "integer"},
        "MAC": {"type": "string"},
        "l2mode": {"type": "boolean"}
    },
    "required": ["vlanId"]
}

ROOT_SCHEMA = {
    "type": "array",
    "items": BRIDGE_ITEM_SCHEMA
}

# --- Проверка MAC-адреса ---
def is_valid_mac(mac):
    return bool(re.match(r"^[0-9a-fA-F]{2}(:[0-9a-fA-F]{2}){5}$", mac))

# --- Параметризация ---
PARAMS = [
    ("no_params", {}, 200, "Без параметров"),
    ("random_param", {"random": "value"}, 200, "Случайный параметр"),
    ("limit_valid", {"limit": 1}, 200, "Валидный limit"),
    ("limit_zero", {"limit": 0}, 200, "Limit 0"),
    ("limit_negative", {"limit": -1}, 200, "Limit отрицательный"),
    ("limit_string", {"limit": "abc"}, 200, "Limit строка"),
    ("skip_valid", {"skip": 1}, 200, "Валидный skip"),
    ("skip_zero", {"skip": 0}, 200, "Skip 0"),
    ("skip_negative", {"skip": -5}, 200, "Skip отрицательный"),
    ("skip_string", {"skip": "xyz"}, 200, "Skip строка"),
    ("filter_name", {"filter": '{"name": "native"}'}, 200, "Фильтр по name"),
    ("filter_id", {"filter": '{"id": "vlaneth0"}'}, 200, "Фильтр по id"),
    ("filter_invalid_json", {"filter": "{'name': 'native'}"}, 200, "Невалидный JSON"),
    ("filter_not_json", {"filter": "not_a_json"}, 200, "Фильтр не JSON"),
    ("filter_empty", {"filter": ""}, 200, "Пустой фильтр"),
    ("filter_long", {"filter": '{"name": "%s"}' % ("a"*1024)}, 200, "Длинная строка в фильтре"),
    ("filter_nonexistent", {"filter": '{"non_existent_field": "value"}'}, 200, "Фильтр по несуществующему полю"),
    ("param_empty_value", {"param": ""}, 200, "Параметр с пустым значением"),
    ("param_int", {"param": 123}, 200, "Параметр с числовым значением"),
    ("param_bool", {"param": True}, 200, "Параметр с булевым значением"),
    ("param_list", {"param": [1, 2, 3]}, 200, "Параметр со списком"),
    ("param_dict", {"param": {"a": "b"}}, 200, "Параметр со словарем"),
    ("param_sql_injection", {"param": "1' OR '1'='1"}, 200, "SQL-инъекция"),
    ("param_xss", {"param": "<script>alert(1)</script>"}, 200, "XSS-атака"),
    ("param_long", {"param": "a" * 1024}, 200, "Длинное значение параметра"),
    ("param_null_byte", {"param": "a\0b"}, 200, "Null byte в значении"),
    ("param_special_chars", {"param": "!@#$%^&*()_+-="}, 200, "Спецсимволы в значении"),
    ("param_utf8", {"param": "тест"}, 200, "UTF-8 символы"),
    ("multiple_params", {"p1": "v1", "p2": "v2", "p3": "v3"}, 200, "Несколько параметров"),
    ("param_with_space", {"a b": "c d"}, 200, "Пробелы в имени и значении"),
    ("param_name_special", {"@#$%^": "value"}, 200, "Спецсимволы в имени параметра"),
    ("param_leading_zeros", {"p": "000123"}, 200, "Ведущие нули"),
    ("param_trailing_spaces", {"p": "value   "}, 200, "Пробелы в конце значения"),
]

# --- Валидация структуры ---
def recursive_validate(data, schema):
    validate(instance=data, schema=schema)
    if schema["type"] == "array":
        for item in data:
            recursive_validate(item, schema["items"])
    elif schema["type"] == "object":
        for key, prop in schema.get("properties", {}).items():
            if key in data and prop["type"] in ("object", "array"):
                recursive_validate(data[key], prop)

def _format_curl_command(response):
    try:
        req = response.request
        method = req.method
        url = req.url
        headers = [f"-H '{k}: {v}'" for k, v in req.headers.items()]
        body = req.body.decode('utf-8') if req.body else None
        curl = f"curl -X {method} '{url}'"
        if headers:
            curl += ' \\n  ' + ' \\n  '.join(headers)
        if body:
            curl += f" \\n  -d '{body}'"
    except Exception:
        curl = "curl -X '<unknown-url>'"
    return curl

# --- Базовый тест ---
def test_vlans_bridge_base(api_client):
    """
    Проверяет базовое поведение эндпоинта: статус 200, структура по схеме, валидность MAC.
    """
    response = api_client.get(ENDPOINT)
    try:
        assert response.status_code == 200, f"Ожидался статус-код 200, получен {response.status_code}"
        data = response.json()
        recursive_validate(data, ROOT_SCHEMA)
        # Проверка валидности MAC для каждого объекта, если поле присутствует
        for item in data:
            if "MAC" in item:
                assert is_valid_mac(item["MAC"]), f"MAC-адрес невалиден: {item['MAC']}"
    except (AssertionError, ValidationError, Exception) as e:
        curl_command = _format_curl_command(response)
        error_message = (
            f"\nБазовый тест /vlans/bridge упал.\n"
            f"Ошибка: {e}\n\n"
            "================= Failed Test Request (cURL) ================\n"
            f"{curl_command}\n"
            "============================================================="
        )
        pytest.fail(error_message, pytrace=False)

# --- Параметризованный тест ---
@pytest.mark.parametrize("case, params, expected_status, desc", PARAMS)
def test_vlans_bridge_parametrized(api_client, case, params, expected_status, desc):
    """
    Проверяет устойчивость /vlans/bridge к различным query-параметрам.
    Ожидается, что все параметры будут проигнорированы.
    """
    response = api_client.get(ENDPOINT, params=params)
    try:
        assert response.status_code == expected_status, f"Ожидался статус-код {expected_status}, получен {response.status_code}"
        if response.status_code == 200:
            data = response.json()
            recursive_validate(data, ROOT_SCHEMA)
            for item in data:
                if "MAC" in item:
                    assert is_valid_mac(item["MAC"]), f"MAC-адрес невалиден: {item['MAC']}"
    except (AssertionError, ValidationError, Exception) as e:
        curl_command = _format_curl_command(response)
        error_message = (
            f"\nПараметризованный тест '{desc}' упал.\n"
            f"Ошибка: {e}\n\n"
            "================= Failed Test Request (cURL) ================\n"
            f"{curl_command}\n"
            "============================================================="
        )
        pytest.fail(error_message, pytrace=False) 