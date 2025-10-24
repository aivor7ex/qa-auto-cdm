import pytest
from collections.abc import Mapping, Sequence
from qa_constants import SERVICES

ENDPOINT = "/frr-config-mode"
SERVICE = "frrouting"

SCHEMA = {
    "type": "object",
    "properties": {
        "mode": {"type": "string"}
    },
    "required": ["mode"],
    "additionalProperties": False
}

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
    ("offset_valid", {"offset": 1}, 200, "Валидный offset"),
    ("offset_zero", {"offset": 0}, 200, "Offset 0"),
    ("offset_negative", {"offset": -1}, 200, "Offset отрицательный"),
    ("offset_string", {"offset": "abc"}, 200, "Offset строка"),
    ("filter_empty", {"filter": ""}, 200, "Пустой фильтр"),
    ("filter_long", {"filter": "a"*1024}, 200, "Длинная строка в фильтре"),
    ("filter_json", {"filter": '{"a": "b"}'}, 200, "JSON в фильтре"),
    ("param_empty_value", {"param": ""}, 200, "Параметр с пустым значением"),
    ("param_int", {"param": 123}, 200, "Параметр с числовым значением"),
    ("param_bool", {"param": True}, 200, "Параметр с булевым значением"),
    ("param_list", {"param": [1, 2, 3]}, 200, "Параметр со списком"),
    ("param_dict", {"param": {"a": "b"}}, 200, "Параметр со словарем"),
    ("param_sql_injection", {"param": "1' OR '1'='1"}, 200, "SQL-инъекция"),
    ("param_xss", {"param": "<script>alert(1)</script>"}, 200, "XSS-атака"),
    ("param_long", {"param": "a" * 1024}, 200, "Длинное значение параметра"),
    ("param_null_byte", {"param": "a\0b"}, 200, "Null byte в значении"),
    ("param_special_chars", {"param": "!@#$"}, 200, "Спецсимволы в значении"),
    ("param_utf8", {"param": "тест"}, 200, "UTF-8 символы"),
    ("multiple_params", {"p1": "v1", "p2": "v2"}, 200, "Несколько параметров"),
    ("param_with_space", {"a b": "c d"}, 200, "Пробелы в имени и значении"),
    ("param_name_special", {"@#$%^": "value"}, 200, "Спецсимволы в имени"),
    ("param_leading_zeros", {"p": "000123"}, 200, "Ведущие нули"),
    ("param_trailing_spaces", {"p": "value   "}, 200, "Пробелы в конце"),
    ("empty_key", {"": "value"}, 200, "Пустой ключ"),
    ("none_value", {"param": None}, 200, "None значение"),
    ("duplicate_param", [ ("p", "a"), ("p", "b") ], 200, "Дублирующиеся параметры"),
]

def _check_types_recursive(obj, schema):
    if "anyOf" in schema:
        assert any(_try_type(obj, s) for s in schema["anyOf"]), f"Тип {type(obj)} не соответствует anyOf"
        return
    if schema.get("type") == "object":
        assert isinstance(obj, Mapping), f"Ожидался объект, получено: {type(obj)}"
        for key, prop in schema.get("properties", {}).items():
            if key in obj:
                _check_types_recursive(obj[key], prop)
        for req in schema.get("required", []):
            assert req in obj, f"Обязательное поле '{req}' отсутствует"
    elif schema.get("type") == "array":
        assert isinstance(obj, Sequence) and not isinstance(obj, str), f"Ожидался список, получено: {type(obj)}"
        for item in obj:
            _check_types_recursive(item, schema["items"])
    else:
        if schema.get("type") == "string":
            assert isinstance(obj, str)
        elif schema.get("type") == "integer":
            assert isinstance(obj, int)
        elif schema.get("type") == "boolean":
            assert isinstance(obj, bool)
        elif schema.get("type") == "null":
            assert obj is None

def _try_type(obj, schema):
    try:
        _check_types_recursive(obj, schema)
        return True
    except AssertionError:
        return False

@pytest.mark.parametrize("case, params, expected_status, desc", PARAMS)
def test_frr_config_mode_robustness(api_client, case, params, expected_status, desc, api_base_url, attach_curl_on_fail):
    with attach_curl_on_fail(ENDPOINT, params, None, "GET"):
        response = api_client.get(ENDPOINT, params=params)
        # Искусственно вызовем ошибку для проверки вывода cURL (убрать после проверки):
        # if case == "no_params":
        #     assert False, "Проверка вывода cURL"
        assert response.status_code == expected_status
        data = response.json()
        _check_types_recursive(data, SCHEMA) 