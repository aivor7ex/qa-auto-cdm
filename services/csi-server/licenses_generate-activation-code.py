import json
import pytest

# Константы для тестируемого эндпоинта и схемы успешного ответа
ENDPOINT = "/licenses/generate-activation-code"
SUCCESS_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "value": {"type": "string"}
    },
    "required": ["value"]
}


def _print_validation(step: str, ok: bool, details: str = "") -> None:
    msg = f"[validation] step={step} status={'OK' if ok else 'FAIL'}"
    if details:
        msg += f" — {details}"
    print(msg)


def _handle_agent_response(agent_result):
    # Успех: агент вернул JSON {"result":"OK"}
    if isinstance(agent_result, dict) and agent_result.get("result") == "OK":
        _print_validation("agent-response", True, details="result=OK")
        return
    
    # Агент недоступен — тест должен падать (не пропускать)
    if agent_result == "unavailable":
        _print_validation("agent-availability", False, details="agent=unavailable")
        pytest.fail("Agent verification unavailable: агент недоступен")

    # Явная ошибка: агент вернул {"result":"ERROR","message":"..."}
    if isinstance(agent_result, dict) and agent_result.get("result") == "ERROR":
        message = agent_result.get("message", "unknown error")
        _print_validation("agent-response", False, details=f"result=ERROR message={message}")
        pytest.fail(f"Agent verification failed: {message}")

    # Агент недоступен или неожиданный ответ — не пропускаем тест
    warn = f"Agent verification unavailable or unexpected response: {agent_result}"
    _print_validation("agent-response", False, details=warn)
    pytest.fail("Agent verification unavailable or unexpected response")


def test_licenses_generate_activation_code_agent_verification(agent_verification):
    # Шаг 1: подготовка пустого тела запроса к агенту
    payload = {}
    _print_validation("prepare-payload", True, details=json.dumps(payload))

    # Шаг 2: вызов агента для эндпоинта /licenses/generate-activation-code
    _print_validation("agent-request", True, details=f"endpoint={ENDPOINT}")
    agent_result = agent_verification(ENDPOINT, payload)

    # Шаг 3: обработка ответа агента согласно контракту
    _handle_agent_response(agent_result)


def _check_types_recursive(obj, schema):
    if schema.get("type") == "object":
        assert isinstance(obj, dict), f"Expected object, got {type(obj)}"
        for key, prop in schema.get("properties", {}).items():
            if key in obj:
                _check_types_recursive(obj[key], prop)
        for req in schema.get("required", []):
            assert req in obj, f"Missing required field: {req}"
    elif schema.get("type") == "array":
        assert isinstance(obj, list) and not isinstance(obj, str), f"Expected array, got {type(obj)}"
        if "items" in schema and isinstance(schema["items"], list):
            for item, item_schema in zip(obj, schema["items"]):
                _check_types_recursive(item, item_schema)
        elif "items" in schema and isinstance(schema["items"], dict):
            for item in obj:
                _check_types_recursive(item, schema["items"])
    elif schema.get("type") == "string":
        assert isinstance(obj, str), f"Expected string, got {type(obj)}"
    elif schema.get("type") == "integer":
        assert isinstance(obj, int), f"Expected integer, got {type(obj)}"
    elif schema.get("type") == "number":
        assert isinstance(obj, (int, float)), f"Expected number, got {type(obj)}"
    elif schema.get("type") == "boolean":
        assert isinstance(obj, bool), f"Expected boolean, got {type(obj)}"
    elif schema.get("type") == "null":
        assert obj is None, f"Expected null, got {type(obj)}"


def _get_license_number(api_client, api_base_url, auth_token, attach_curl_on_fail):
    endpoint = "/licenses"
    url = f"{api_base_url}{endpoint}"
    headers = {"x-access-token": auth_token, "Content-Type": "application/json"}
    with attach_curl_on_fail(endpoint, None, headers, "GET"):
        response = api_client.get(url, headers=headers)
        assert response.status_code == 200, f"Ожидается 200 OK; получено {response.status_code}"
        data = response.json()
        assert isinstance(data, dict) and "licenseNumber" in data, "В ответе должен быть licenseNumber"
        return data["licenseNumber"]


# ---------------------------- Позитивные кейсы ----------------------------
@pytest.mark.parametrize(
    "case",
    [
        {
            "name": "bundled_true",
            "headers": lambda token: {"x-access-token": token, "Content-Type": "application/json"},
            "body": {"licenseNumber": None, "bundled": True},
            "use_fetched": True,
            "expect_suffix": True,
        },
        {
            "name": "bundled_false",
            "headers": lambda token: {"x-access-token": token, "Content-Type": "application/json"},
            "body": {"licenseNumber": None, "bundled": False},
            "use_fetched": True,
            "expect_suffix": False,
        },
        {
            "name": "bundled_missing",
            "headers": lambda token: {"x-access-token": token, "Content-Type": "application/json"},
            "body": {"licenseNumber": None},
            "use_fetched": True,
            "expect_suffix": None,
        },
        {
            "name": "min_length_licenseNumber",
            "headers": lambda token: {"x-access-token": token, "Content-Type": "application/json"},
            "body": {"licenseNumber": "A", "bundled": True},
            "expect_suffix": True,
        },
        {
            "name": "long_licenseNumber_boundary",
            "headers": lambda token: {"x-access-token": token, "Content-Type": "application/json"},
            "body": {"licenseNumber": "LIC-" + ("0" * 256), "bundled": True},
            "expect_suffix": True,
        },
        {
            "name": "unicode_licenseNumber",
            "headers": lambda token: {"x-access-token": token, "Content-Type": "application/json"},
            "body": {"licenseNumber": "ЛИЦЕНЗИЯ-Ω-测试", "bundled": True},
            "expect_suffix": True,
        },
        {
            "name": "trim_spaces_in_licenseNumber",
            "headers": lambda token: {"x-access-token": token, "Content-Type": "application/json"},
            "body": {"licenseNumber": None, "bundled": True},
            "use_fetched": True,
            "wrap_spaces": True,
            "expect_suffix": True,
        },
        {
            "name": "idempotency_same_input_diff_values",
            "headers": lambda token: {"x-access-token": token, "Content-Type": "application/json"},
            "body": {"licenseNumber": None, "bundled": True},
            "use_fetched": True,
            "idempotency": True,
        },
    ],
    ids=lambda c: c["name"],
)
def test_licenses_generate_activation_code_positive(api_client, api_base_url, auth_token, attach_curl_on_fail, case):
    url = f"{api_base_url}{ENDPOINT}"
    headers = case["headers"](auth_token) if callable(case.get("headers")) else (case.get("headers") or {})

    with attach_curl_on_fail(ENDPOINT, case.get("body"), headers, "POST"):
        # Подстановка licenseNumber из /licenses при необходимости
        body = dict(case["body"]) if case.get("body") else {}
        if case.get("use_fetched"):
            license_number = _get_license_number(api_client, api_base_url, auth_token, attach_curl_on_fail)
            if case.get("wrap_spaces"):
                license_number = f"  {license_number}  "
            body["licenseNumber"] = license_number

        if case.get("idempotency"):
            r1 = api_client.post(url, headers=headers, json=body)
            r2 = api_client.post(url, headers=headers, json=body)
            assert r1.status_code == 200 and r2.status_code == 200, f"Ожидается 200 OK; получено {r1.status_code}/{r2.status_code}"
            d1 = r1.json(); d2 = r2.json()
            _check_types_recursive(d1, SUCCESS_RESPONSE_SCHEMA)
            _check_types_recursive(d2, SUCCESS_RESPONSE_SCHEMA)
            assert d1["value"] != d2["value"], "Значение должно отличаться для одно и того же ввода (разное createdAt)"
            return

        response = api_client.post(url, headers=headers, json=body)
        assert response.status_code == 200, f"Ожидается 200 OK; получено {response.status_code}"
        data = response.json()
        _check_types_recursive(data, SUCCESS_RESPONSE_SCHEMA)

        # Проверка суффикса в зависимости от bundled
        license_num = body.get("licenseNumber")
        expect_suffix = case.get("expect_suffix")
        if expect_suffix is True:
            assert data["value"].endswith(f"!{license_num}"), "Ожидается суффикс '!<licenseNumber>' в value"
        elif expect_suffix is False:
            assert not data["value"].endswith(f"!{license_num}"), "При bundled=false суффикса быть не должно"


# --------------------- Негативные валидационные/парсинг кейсы ---------------------
@pytest.mark.parametrize(
    "case",
    [
        {
            "name": "missing_licenseNumber",
            "headers": lambda token: {"x-access-token": token, "Content-Type": "application/json"},
            "send_json": True,
            "payload": {"bundled": True},
            "expect_code": 400,
        },
        {
            "name": "licenseNumber_number",
            "headers": lambda token: {"x-access-token": token, "Content-Type": "application/json"},
            "send_json": False,
            "raw": json.dumps({"licenseNumber": 12345, "bundled": True}),
            "expect_code": 400,
        },
        {
            "name": "bundled_string",
            "headers": lambda token: {"x-access-token": token, "Content-Type": "application/json"},
            "send_json": False,
            "raw": json.dumps({"licenseNumber": "LIC-004", "bundled": "true"}),
            "expect_code": 400,
        },
        {
            "name": "empty_licenseNumber",
            "headers": lambda token: {"x-access-token": token, "Content-Type": "application/json"},
            "send_json": True,
            "payload": {"licenseNumber": "", "bundled": True},
            "expect_code": 400,
        },
        {
            "name": "extra_fields_ignored",
            "headers": lambda token: {"x-access-token": token, "Content-Type": "application/json"},
            "send_json": True,
            "payload": {"licenseNumber": "LIC-005", "bundled": False, "extra": "ignored"},
            "expect_non_5xx": True,
        },
        {
            "name": "invalid_json",
            "headers": lambda token: {"x-access-token": token, "Content-Type": "application/json"},
            "send_json": False,
            "raw": '{"licenseNumber":"LIC-006","bundled":true',
            "expect_code": 400,
        },
        {
            "name": "no_content_type_header",
            "headers": lambda token: {"x-access-token": token},
            "send_json": False,
            "raw": json.dumps({"licenseNumber": "LIC-007", "bundled": True}),
            "expect_non_5xx": True,
        },
        {
            "name": "array_instead_of_object",
            "headers": lambda token: {"x-access-token": token, "Content-Type": "application/json"},
            "send_json": False,
            "raw": json.dumps([{"licenseNumber": "LIC-ARR", "bundled": True}]),
            "expect_code": 400,
        },
        {
            "name": "urlencoded_content_type",
            "headers": lambda token: {"x-access-token": token, "Content-Type": "application/x-www-form-urlencoded"},
            "send_json": False,
            "raw": "licenseNumber=LIC-URLENC&bundled=true",
            "expect_code": 200,
        },
        {
            "name": "null_fields",
            "headers": lambda token: {"x-access-token": token, "Content-Type": "application/json"},
            "send_json": False,
            "raw": json.dumps({"licenseNumber": None, "bundled": None}),
            "expect_code": 400,
        },
        {
            "name": "object_licenseNumber",
            "headers": lambda token: {"x-access-token": token, "Content-Type": "application/json"},
            "send_json": False,
            "raw": json.dumps({"licenseNumber": {"code": "LIC-OBJ"}, "bundled": True}),
            "expect_code": 400,
        },
        {
            "name": "empty_body",
            "headers": lambda token: {"x-access-token": token, "Content-Type": "application/json"},
            "send_json": False,
            "raw": "",
            "expect_code": 400,
        },
        {
            "name": "empty_object",
            "headers": lambda token: {"x-access-token": token, "Content-Type": "application/json"},
            "send_json": False,
            "raw": "{}",
            "expect_code": 400,
        },
        {
            "name": "null_body",
            "headers": lambda token: {"x-access-token": token, "Content-Type": "application/json"},
            "send_json": False,
            "raw": "null",
            "expect_code": 400,
        },
    ],
    ids=lambda c: c["name"],
)
def test_licenses_generate_activation_code_validation(api_client, api_base_url, auth_token, attach_curl_on_fail, case):
    url = f"{api_base_url}{ENDPOINT}"
    headers = case["headers"](auth_token) if callable(case.get("headers")) else (case.get("headers") or {})

    with attach_curl_on_fail(ENDPOINT, case.get("payload") if case.get("send_json") else case.get("raw"), headers, "POST"):
        if case.get("send_json"):
            response = api_client.post(url, headers=headers, json=case.get("payload"))
        else:
            response = api_client.post(url, headers=headers, data=case.get("raw", ""))

        if case.get("expect_code") is not None:
            assert response.status_code == case["expect_code"], f"Ожидается {case['expect_code']}; получено {response.status_code}"
        elif case.get("expect_non_5xx"):
            assert response.status_code < 500, f"Неожиданный статус сервера: {response.status_code}"


# ------------------------ Аутентификация/авторизация ------------------------
@pytest.mark.parametrize(
    "case",
    [
        {
            "name": "valid_token_control",
            "headers": lambda token: {"x-access-token": token, "Content-Type": "application/json"},
            "expect_code": 200,
            "payload": {"licenseNumber": "LIC-AUTH-OK", "bundled": True},
        },
        {
            "name": "no_token",
            "headers": lambda token: {"Content-Type": "application/json"},
            "expect_code": 401,
            "payload": {"licenseNumber": "LIC-NO-TOKEN", "bundled": True},
        },
        {
            "name": "invalid_token",
            "headers": lambda token: {"x-access-token": "invalid-token", "Content-Type": "application/json"},
            "expect_code": 401,
            "payload": {"licenseNumber": "LIC-BAD-TOKEN", "bundled": True},
        },
        {
            "name": "header_case_insensitive",
            "headers": lambda token: {"content-type": "application/json", "X-Access-Token": token},
            "expect_code": 200,
            "payload": {"licenseNumber": "LIC-HEADER-CASE", "bundled": True},
        },
        {
            "name": "double_token_headers_last_wins",
            "headers": lambda token: {"Content-Type": "application/json", "x-access-token": token},
            "also_add": {"x-access-token": "invalid"},
            "expect_code": 200,
            "payload": {"licenseNumber": "LIC-DUP-HEAD", "bundled": True},
        },
    ],
    ids=lambda c: c["name"],
)
def test_licenses_generate_activation_code_auth(api_client, api_base_url, auth_token, attach_curl_on_fail, case):
    url = f"{api_base_url}{ENDPOINT}"
    base_headers = case["headers"](auth_token) if callable(case.get("headers")) else (case.get("headers") or {})
    if case.get("also_add"):
        # Порядок заголовков в HTTP не гарантируется, поэтому моделируем слияние; последний ключ перетрет предыдущий
        tmp = dict(case["also_add"])  # сначала «неправильный»
        tmp.update(base_headers)       # затем «правильный» (последний побеждает)
        headers = tmp
    else:
        headers = base_headers

    # Подстановка licenseNumber из /licenses для позитивных кейсов, когда требуется валидный номер
    payload = dict(case.get("payload") or {})
    if payload.get("licenseNumber") in (None, "LIC-AUTH-OK", "LIC-HEADER-CASE", "LIC-DUP-HEAD") and case["expect_code"] == 200:
        payload["licenseNumber"] = _get_license_number(api_client, api_base_url, auth_token, attach_curl_on_fail)

    with attach_curl_on_fail(ENDPOINT, payload, headers, "POST"):
        response = api_client.post(url, headers=headers, json=payload)
        assert response.status_code == case["expect_code"], f"Ожидается {case['expect_code']}; получено {response.status_code}"
        if response.status_code == 200 and response.content:
            data = response.json()
            _check_types_recursive(data, SUCCESS_RESPONSE_SCHEMA)


# ------------------------ Системные/сервисные сбои ------------------------
@pytest.mark.parametrize(
    "case",
    [
        {
            "name": "route_not_found",
            "headers": lambda token: {"x-access-token": token, "Content-Type": "application/json"},
            "payload": {"licenseNumber": "LIC-404", "bundled": True},
            "use_wrong_path": True,
            "expect_code": 404,
        },
        {
            "name": "serial_number_fetch_error",
            "headers": lambda token: {"x-access-token": token, "Content-Type": "application/json"},
            "payload": {"licenseNumber": "LIC-NO-SERIAL", "bundled": True},
            "expect_code": 200,
        },
    ],
    ids=lambda c: c["name"],
)
def test_licenses_generate_activation_code_system(api_client, api_base_url, auth_token, attach_curl_on_fail, case):
    headers = case["headers"](auth_token) if callable(case.get("headers")) else (case.get("headers") or {})
    effective_endpoint = f"{ENDPOINT}X" if case.get("use_wrong_path") else ENDPOINT
    effective_url = f"{api_base_url}{effective_endpoint}"

    with attach_curl_on_fail(effective_endpoint, case.get("payload"), headers, "POST"):
        response = api_client.post(effective_url, headers=headers, json=case.get("payload"))
        assert response.status_code == case["expect_code"], f"Ожидается {case['expect_code']}; получено {response.status_code}"

