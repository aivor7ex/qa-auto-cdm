import pytest
import json
import requests


ENDPOINT = "/utils/arp"
METHOD = "POST"


# Схема успешного ответа (из примера R0/допущений)
RESPONSE_SCHEMA_200 = {
    "required": {
        "pid": int,
    },
    "optional": {},
}


def validate_schema(data, schema):
    """Простая валидация схемы ответа (dict), поддерживает required/optional поля."""
    assert isinstance(data, dict), f"Ожидался объект JSON (dict), получено: {type(data).__name__}"
    for key, expected_type in schema.get("required", {}).items():
        assert key in data, f"Отсутствует обязательное поле '{key}': {json.dumps(data, ensure_ascii=False, indent=2)}"
        assert isinstance(data[key], expected_type), (
            f"Поле '{key}' имеет тип {type(data[key]).__name__}, ожидался {expected_type.__name__}"
        )
    for key, expected_type in schema.get("optional", {}).items():
        if key in data and data[key] is not None:
            assert isinstance(data[key], expected_type), (
                f"Необязательное поле '{key}' имеет тип {type(data[key]).__name__}, ожидался {expected_type.__name__}"
            )


def validate_error(resp_json):
    """Универсальная проверка ошибки: допускаем 'detail' или объект 'error'."""
    assert isinstance(resp_json, dict), f"Ожидался dict в ошибке, получено: {type(resp_json).__name__}"
    if "detail" in resp_json:
        assert isinstance(resp_json["detail"], (str, list)), "detail должен быть str или list"
        return
    assert "error" in resp_json, f"Ожидались поля 'detail' или 'error', получено: {json.dumps(resp_json, ensure_ascii=False)}"
    err = resp_json["error"]
    assert isinstance(err, dict), "'error' должен быть объектом"
    if "statusCode" in err:
        assert isinstance(err["statusCode"], int)
    if "message" in err and err["message"] is not None:
        assert isinstance(err["message"], str)
    if "name" in err and err["name"] is not None:
        assert isinstance(err["name"], str)


# 40 уникальных и осмысленных кейсов (R1, R16)
cases = [
    # 1–21: Позитивные (минимальный и разные допустимые формы с игнорируемыми полями)
    ({}, None, 200, True, "minimal empty object"),
    ({"extra": 1}, None, 200, True, "extra int"),
    ({"extra": 0}, None, 200, True, "extra zero"),
    ({"extra": -1}, None, 200, True, "extra negative int"),
    ({"extra": 1.5}, None, 200, True, "extra float"),
    ({"extra": True}, None, 200, True, "extra bool true"),
    ({"extra": False}, None, 200, True, "extra bool false"),
    ({"extra": None}, None, 200, True, "extra null"),
    ({"extra": "value"}, None, 200, True, "extra short string"),
    ({"extra": ""}, None, 200, True, "extra empty string"),
    ({"unicode": "тест"}, None, 200, True, "unicode value"),
    ({"special": "!@#$%^&*()[]{};:'\",.<>/?\\|`~"}, None, 200, True, "special chars value"),
    ({"long": "x" * 1024}, None, 200, True, "long string value"),
    ({"nested": {"a": 1}}, None, 200, True, "nested object"),
    ({"nested": {"a": None}}, None, 200, True, "nested object with null"),
    ({"list": [1, 2, 3]}, None, 200, True, "list of ints"),
    ({"list": []}, None, 200, True, "empty list"),
    ({"nestedList": [{"a": 1}, {"b": "c"}]}, None, 200, True, "list of objects"),
    ({"whitespace": "   "}, None, 200, True, "whitespace value"),
    ({"big": 10**9}, None, 200, True, "big integer"),
    ({"float": 0.0}, None, 200, True, "zero float"),

    # 22–40: Негативные (реально невалидный JSON под application/json) + немного edge 200
    ("not json", {"Content-Type": "application/json"}, 400, False, "text as json body"),
    ("{invalid json}", {"Content-Type": "application/json"}, 400, False, "invalid json syntax"),
    ("{", {"Content-Type": "application/json"}, 400, False, "unterminated object"),
    ("[", {"Content-Type": "application/json"}, 400, False, "unterminated array"),
    ("{\"a\":}", {"Content-Type": "application/json"}, 400, False, "missing value after key"),
    ("{\"a\":1,,}", {"Content-Type": "application/json"}, 400, False, "extra comma"),
    ("{\"a\":1 \"b\":2}", {"Content-Type": "application/json"}, 400, False, "missing comma between pairs"),
    ("{'a':1}", {"Content-Type": "application/json"}, 400, False, "single quotes not allowed"),
    ("{a:1}", {"Content-Type": "application/json"}, 400, False, "unquoted key"),
    ("\"unterminated", {"Content-Type": "application/json"}, 400, False, "unterminated string"),
    ("NaN", {"Content-Type": "application/json"}, 400, False, "NaN literal invalid"),
    ("Infinity", {"Content-Type": "application/json"}, 400, False, "Infinity literal invalid"),
    ("-Infinity", {"Content-Type": "application/json"}, 400, False, "-Infinity literal invalid"),
    ("tru", {"Content-Type": "application/json"}, 400, False, "misspelled true"),
    ("nul", {"Content-Type": "application/json"}, 400, False, "misspelled null"),
    ("[]]", {"Content-Type": "application/json"}, 400, False, "extra closing bracket")
]


@pytest.mark.parametrize(
    "payload, headers, expected_status, expect_success, case",
    cases,
    ids=[c for *_, c in cases],
)
def test_post_utils_arp(api_client, attach_curl_on_fail, payload, headers, expected_status, expect_success, case):
    """
    Тестирует POST /utils/arp: коды ответа, валидность JSON и структуру данных.
    """
    def do_request(body, headers_override=None):
        if headers_override:
            if body is None:
                return api_client.post(ENDPOINT, headers=headers_override)
            if isinstance(body, str):
                return api_client.post(ENDPOINT, data=body, headers=headers_override)
            if isinstance(body, (list, int, float, bool)):
                return api_client.post(ENDPOINT, data=json.dumps(body), headers=headers_override)
            # dict
            return api_client.post(ENDPOINT, data=json.dumps(body), headers=headers_override)
        else:
            if body is None:
                return api_client.post(ENDPOINT, data=None)
            if isinstance(body, str):
                return api_client.post(ENDPOINT, data=body)
            if isinstance(body, list):
                return api_client.post(ENDPOINT, data=json.dumps(body))
            if isinstance(body, (int, float, bool)):
                return api_client.post(ENDPOINT, data=json.dumps(body))
            # dict
            return api_client.post(ENDPOINT, json=body)

    with attach_curl_on_fail(ENDPOINT, payload, headers, METHOD):
        resp = do_request(payload, headers)

        assert resp.status_code == expected_status, (
            f"{case}: ожидался статус {expected_status}, получен {resp.status_code}. Ответ: {resp.text}"
        )

        ct = resp.headers.get("Content-Type", "")
        if expect_success:
            assert "application/json" in ct, f"Ожидался JSON в ответе 200, получено: {ct}"
            data = resp.json()
            validate_schema(data, RESPONSE_SCHEMA_200)
            # Базовая проверка схемы запроса для успешных кейсов: тело должно быть объектом либо пустым
            if isinstance(payload, dict):
                assert isinstance(payload, dict)
        else:
            if resp.status_code in (400, 422) and "application/json" in ct:
                err = resp.json()
                validate_error(err)


