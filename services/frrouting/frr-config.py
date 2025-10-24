import pytest
from collections.abc import Mapping, Sequence
from qa_constants import SERVICES

ENDPOINT = "/frr-config"
SERVICE = "frrouting"

PARAMS = [
    ("of_running", {"of": "running"}, 200, "Конфиг 'running'"),
    ("of_current", {"of": "current"}, 404, "Конфиг 'current' (ожидаем 404)"),
    ("of_backup", {"of": "backup"}, 404, "Конфиг 'backup' (ожидаем 404)"),
    ("of_running_with_junk", {"of": "running", "junk": "123"}, 200, "Лишний параметр игнорируется"),
    ("of_with_uppercase", {"of": "RUNNING"}, 400, "Заглавные буквы в 'of' (невалидно)"),
    ("no_params", {}, 400, "Без параметров"),
    ("of_empty", {"of": ""}, 400, "Пустой параметр 'of'"),
    ("of_invalid", {"of": "invalid_value"}, 400, "Невалидное значение 'of'"),
    ("of_sql_injection", {"of": "' OR 1=1 --"}, 400, "SQL-инъекция в 'of'"),
    ("of_list", {"of": ["running"]}, 200, "Список в 'of' (requests возьмет первый элемент)"),
    ("of_dict", {"of": {"key": "running"}}, 400, "Словарь в 'of'"),
    ("param_instead_of", {"param": "running"}, 400, "Неверное имя параметра"),
    ("filter_long", {"filter": "a"*1024}, 400, "Длинная строка в другом параметре"),
    ("limit_valid", {"limit": 1}, 400, "Только limit"),
    ("skip_valid", {"skip": 1}, 400, "Только skip"),
    ("offset_valid", {"offset": 1}, 400, "Только offset"),
    ("filter_nonexistent", {"filter": '{"a": "b"}'}, 400, "Только filter"),
    ("param_int", {"param": 123}, 400, "Только числовой параметр"),
    ("param_bool", {"param": True}, 400, "Только булев параметр"),
    ("param_xss", {"param": "<script>alert(1)</script>"}, 400, "Только XSS"),
    ("param_long", {"param": "a" * 1024}, 400, "Только длинный параметр"),
    ("param_null_byte", {"param": "a\0b"}, 400, "Только null byte"),
    ("param_special_chars", {"param": "!@#$"}, 400, "Только спецсимволы"),
    ("param_utf8", {"param": "тест"}, 400, "Только UTF-8"),
    ("multiple_params", {"p1": "v1", "p2": "v2"}, 400, "Только несколько параметров"),
    ("param_with_space", {"a b": "c d"}, 400, "Только параметр с пробелами"),
    ("param_name_special", {"@#$%^": "value"}, 400, "Только спецсимволы в имени"),
    ("param_leading_zeros", {"p": "000123"}, 400, "Только параметр с нулями"),
    ("param_trailing_spaces", {"p": "value   "}, 400, "Только параметр с пробелами в конце"),
    ("empty_key", {"": "value"}, 400, "Только пустой ключ"),
    ("empty_dict", {}, 400, "Пустой словарь (дубль)"),
    ("none_value", {"param": None}, 400, "Только None значение"),
    ("duplicate_param", [ ("p", "a"), ("p", "b") ], 400, "Только дубли"),
    ("of_null", {"of": None}, 400, "of' is None"),
]

# Схема ответа для успешного кейса (200)
SCHEMA = {
    "type": "string"
}

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
def test_frr_config_robustness(api_client, case, params, expected_status, desc, attach_curl_on_fail, api_base_url):
    with attach_curl_on_fail(ENDPOINT, method="GET"):
        response = api_client.get(ENDPOINT, params=params)
        assert response.status_code == expected_status
        if response.status_code == 200:
            assert response.text.strip(), "Тело ответа не должно быть пустым для успешного запроса"
            _check_types_recursive(response.text, SCHEMA)
        elif response.status_code == 400:
            pass
        elif response.status_code == 404:
            pass 