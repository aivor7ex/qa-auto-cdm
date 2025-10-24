import pytest
from jsonschema import validate, ValidationError

# --- Константы ---
ENDPOINT = "/router/ospf/ospfLinks/count"

# --- Схема ответа ---
COUNT_SCHEMA = {
    "type": "object",
    "properties": {
        "count": {"type": "integer"}
    },
    "required": ["count"],
    "additionalProperties": False
}

# --- Вспомогательная функция ---
def _print_curl(response):
    try:
        full_url = response.request.url
        curl_command = f"curl -X GET '{full_url}'"
    except Exception:
        curl_command = "curl -X '<unknown-url>'"
    print(f"\n\ncURL-запрос для воспроизведения: {curl_command}\n")

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
    ("offset_valid", {"offset": 1}, 200, "Валидный offset"),
    ("offset_zero", {"offset": 0}, 200, "Offset 0"),
    ("offset_negative", {"offset": -1}, 200, "Offset отрицательный"),
    ("offset_string", {"offset": "abc"}, 200, "Offset строка"),
    ("filter_empty", {"filter": ""}, 200, "Пустой фильтр"),
    ("filter_long", {"filter": "a"*1024}, 400, "Длинная строка в фильтре"),
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
    ("empty_key", {"": "value"}, 200, "Пустой ключ"),
    ("empty_dict", {}, 200, "Пустой словарь"),
    ("none_value", {"param": None}, 200, "None значение"),
    ("duplicate_param", [ ("param", "a"), ("param", "b") ], 200, "Дублирующийся параметр"),
]

# --- Тест ---
@pytest.mark.parametrize("case, params, expected_status, desc", PARAMS)
def test_router_ospf_ospfLinks_count_parametrized(api_client, case, params, expected_status, desc):
    """
    Проверяет устойчивость /router/ospf/ospfLinks/count к различным query-параметрам.
    Ожидается, что все параметры будут проигнорированы.
    """
    if case == "duplicate_param":
        response = api_client.get(ENDPOINT, params=params)
    else:
        response = api_client.get(ENDPOINT, params=params)
    try:
        assert response.status_code == expected_status, f"Ожидался статус-код {expected_status}, получен {response.status_code}"
        if response.status_code == 200:
            data = response.json()
            validate(instance=data, schema=COUNT_SCHEMA)
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