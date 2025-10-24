import pytest
import requests
from jsonschema import validate

ENDPOINT = "/vlans/virtualInterfaces"

VLANS_VIRTUALINTERFACES_SCHEMA = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "id": {"type": "string"}
        },
        "required": ["id"]
    }
}

PARAMS = [
    ("no_params", {}, 200, "Без параметров"),
    ("limit_valid", {"limit": 1}, 200, "Валидный limit (игнорируется)"),
    ("limit_zero", {"limit": 0}, 200, "Limit 0 (игнорируется)"),
    ("limit_negative", {"limit": -1}, 200, "Limit отрицательный (игнорируется)"),
    ("limit_string", {"limit": "abc"}, 200, "Limit - строка (игнорируется)"),
    ("limit_float", {"limit": 1.5}, 200, "Limit - float (игнорируется)"),
    ("skip_valid", {"skip": 1}, 200, "Валидный skip (игнорируется)"),
    ("skip_zero", {"skip": 0}, 200, "Skip 0 (игнорируется)"),
    ("skip_negative", {"skip": -5}, 200, "Skip отрицательный (игнорируется)"),
    ("skip_string", {"skip": "xyz"}, 200, "Skip - строка (игнорируется)"),
    ("skip_float", {"skip": 2.5}, 200, "Skip - float (игнорируется)"),
    ("limit_and_skip", {"limit": 5, "skip": 5}, 200, "Limit и Skip (игнорируются)"),
    ("filter_name", {"filter": '{"name": "native"}'}, 200, "Фильтр по имени (игнорируется)"),
    ("filter_id", {"filter": '{"id": "testid"}'}, 200, "Фильтр по id (игнорируется)"),
    ("filter_invalid_json", {"filter": "{'name': 'native'}"}, 200, "Невалидный JSON (игнорируется)"),
    ("filter_not_json", {"filter": "not_a_json"}, 200, "Фильтр - не JSON (игнорируется)"),
    ("filter_empty", {"filter": ""}, 200, "Пустой фильтр (игнорируется)"),
    ("filter_long", {"filter": '{"name": "%s"}' % ("a"*1024)}, 200, "Длинная строка в фильтре (игнорируется)"),
    ("filter_nonexistent", {"filter": '{"non_existent_field": "value"}'}, 200, "Фильтр по несуществующему полю (игнорируется)"),
    ("random_param", {"random_param": "value"}, 200, "Случайный параметр (игнорируется)"),
    ("param_empty_value", {"param": ""}, 200, "Параметр с пустым значением"),
    ("param_int", {"param": 123}, 200, "Параметр с числовым значением"),
    ("param_bool", {"param": True}, 200, "Параметр с булевым значением"),
    ("param_list", {"param": [1, 2, 3]}, 200, "Параметр со списком в значении"),
    ("param_dict", {"param": {"a": "b"}}, 200, "Параметр со словарем в значении"),
    ("param_sql_injection", {"param": "1' OR '1'='1"}, 200, "Попытка SQL-инъекции в параметре"),
    ("param_xss", {"param": "<script>alert(1)</script>"}, 200, "Попытка XSS-атаки в параметре"),
    ("param_long", {"param": "a" * 1024}, 200, "Длинное значение параметра"),
    ("param_null_byte", {"param": "a\0b"}, 200, "Null byte в значении параметра"),
    ("param_special_chars", {"param": "!@#$%^&*()_+-="}, 200, "Спецсимволы в значении параметра"),
    ("param_utf8", {"param": "тест"}, 200, "UTF-8 символы в значении параметра"),
    ("multiple_params", {"p1": "v1", "p2": "v2", "p3": "v3"}, 200, "Несколько случайных параметров"),
    ("force_fail", {"force_fail": "for_demo"}, 200, "Параметр для проверки вывода cURL (игнорируется)"),
    ("param_with_space", {"a b": "c d"}, 200, "Пробелы в имени и значении параметра"),
    ("param_name_special", {"@#$%^": "value"}, 200, "Спецсимволы в имени параметра"),
    ("param_leading_zeros", {"p": "000123"}, 200, "Ведущие нули в значении параметра"),
    ("param_trailing_spaces", {"p": "value   "}, 200, "Пробелы в конце значения параметра"),
]

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

def test_vlans_virtualInterfaces_success(api_client):
    """
    Проверяет успешный ответ и валидность схемы для /vlans/virtualInterfaces.
    """
    response = api_client.get(ENDPOINT)
    try:
        assert response.status_code == 200, "Ожидался статус-код 200"
        validate(instance=response.json(), schema=VLANS_VIRTUALINTERFACES_SCHEMA)
    except Exception as e:
        curl_command = _format_curl_command(response)
        error_message = (
            f"\nБазовый тест /vlans/virtualInterfaces упал.\n"
            f"Ошибка: {e}\n\n"
            "================= Failed Test Request (cURL) ================\n"
            f"{curl_command}\n"
            "============================================================="
        )
        pytest.fail(error_message, pytrace=False)

@pytest.mark.parametrize("case, params, expected_status, desc", PARAMS)
def test_vlans_virtualInterfaces_parametrized(api_client, case, params, expected_status, desc):
    """
    Проверяет устойчивость /vlans/virtualInterfaces к различным query-параметрам.
    Ожидается, что все параметры будут проигнорированы, кроме невалидного JSON.
    """
    response = api_client.get(ENDPOINT, params=params)
    try:
        assert response.status_code == expected_status, f"Ожидался статус-код {expected_status}"
        if response.status_code == 200:
            validate(instance=response.json(), schema=VLANS_VIRTUALINTERFACES_SCHEMA)
    except Exception as e:
        curl_command = _format_curl_command(response)
        error_message = (
            f"\nПараметризованный тест '{desc}' упал.\n"
            f"Ошибка: {e}\n\n"
            "================= Failed Test Request (cURL) ================\n"
            f"{curl_command}\n"
            "============================================================="
        )
        pytest.fail(error_message, pytrace=False) 