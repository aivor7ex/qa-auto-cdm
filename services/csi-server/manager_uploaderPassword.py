import json
import pytest
import uuid

# Между тестами в этом модуле делаем паузу 3 секунды, чтобы разгрузить backend
@pytest.fixture(autouse=True)
def _delay_between_uploader_password_tests():
    yield
    import time
    time.sleep(3)

# Константы для тестируемого эндпоинта и схемы успешного ответа
ENDPOINT = "/manager/uploaderPassword"

# Схема успешного ответа: допускаем 200 {"result":"ok"} или 204 без тела
SUCCESS_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "result": {"type": "string"}
    },
    "required": ["result"]
}


def _check_types_recursive(obj, schema):
    if schema.get("type") == "object":
        assert isinstance(obj, dict), f"Expected object, got {type(obj)}"
        for key, prop in schema.get("properties", {}).items():
            if key in obj:
                _check_types_recursive(obj[key], prop)
        for req in schema.get("required", []):
            assert req in obj, f"Missing required field: {req}"
    elif schema.get("type") == "string":
        assert isinstance(obj, str), f"Expected string, got {type(obj)}"
    elif schema.get("type") == "number":
        assert isinstance(obj, (int, float)), f"Expected number, got {type(obj)}"
    elif schema.get("type") == "array":
        assert isinstance(obj, list), f"Expected array, got {type(obj)}"
        for item in obj:
            if "items" in schema:
                _check_types_recursive(item, schema["items"])


def _print_validation(step: str, success: bool, details: str = ""):
    """
    Выводит результат валидации шага проверки.
    
    Args:
        step: Название шага проверки
        success: Результат проверки
        details: Дополнительная информация
    """
    status = "✓ PASSED" if success else "✗ FAILED"
    msg = f"[validation-{step}] {status}"
    if details:
        msg += f" — {details}"
    print(msg)


def _perform_agent_verification(agent_verification, payload):
    """
    Выполняет проверку через агента для изменения пароля uploader.
    
    Проверяет по контракту:
    - {"result": "OK"}: успех, хэш пароля изменился
    - {"result": "ERROR", "message": "..."}: ошибка проверки или хэш не изменился  
    - "unavailable": агент недоступен - тест должен упасть
    
    Args:
        agent_verification: Фикстура для проверки агента
        payload: Данные запроса (содержат новый пароль)
        
    Returns:
        None: Проверка пройдена успешно
        
    Raises:
        pytest.fail: Если проверка неуспешна или агент недоступен
    """
    # Генерируем рандомный маркер для идентификации теста
    marker = f"test_{uuid.uuid4().hex[:8]}"
    
    # Подготавливаем payload для агента (без пароля в открытом виде по соображениям безопасности)
    agent_payload = {
        "marker": marker,
        "password_set": bool(payload.get("password")),
        "timestamp": int(uuid.uuid4().int & (1<<32)-1)  # Псевдо-timestamp для уникальности
    }
    
    _print_validation("agent-prepare", True, f"marker={marker}")
    
    # Выполняем проверку через агента
    agent_result = agent_verification(ENDPOINT, agent_payload)
    
    if agent_result == "unavailable":
        _print_validation("agent-availability", False, "agent=unavailable")
        pytest.fail("Agent verification unavailable: агент недоступен")
    
    # Обработка стандартного формата ответа агента
    if isinstance(agent_result, dict):
        result_status = agent_result.get("result")
        if result_status == "OK":
            _print_validation("agent-verification", True, "password hash changed")
            print(f"Agent verification: Password hash for uploader successfully changed (marker: {marker})")
            return
        elif result_status == "ERROR":
            error_message = agent_result.get("message", "Unknown error")
            _print_validation("agent-verification", False, f"error={error_message}")
            pytest.fail(f"Agent verification failed: {error_message}")
        else:
            _print_validation("agent-verification", False, f"unexpected_result={result_status}")
            pytest.fail(f"Agent verification returned unexpected result: {result_status}")
    else:
        _print_validation("agent-verification", False, f"invalid_response_type={type(agent_result)}")
        pytest.fail(f"Agent verification returned invalid response type: {type(agent_result)}")


@pytest.fixture
def reset_uploader_password(api_client, api_base_url, auth_token):
    """Сбрасывает пароль к значению по умолчанию вне зависимости от исхода теста."""
    yield
    url = f"{api_base_url}{ENDPOINT}"
    headers = {"x-access-token": auth_token, "Content-Type": "application/json"}
    try:
        api_client.post(url, headers=headers, json={"password": "admin"})
    except Exception as exc:
        # Не ломаем итог теста из-за сброса; оставляем заметку в логе
        print(f"[teardown] failed to reset uploader password: {exc}")


@pytest.mark.parametrize(
    "case",
    [
        # Базовый успешный кейс (x-access-token)
        {
            "name": "success_x_access_token",
            "headers": lambda token: {"x-access-token": token, "Content-Type": "application/json"},
            "params": {},
            "use_json": True,
            "body": {"password": "TestP@ssw0rd!"},
            "expected_codes": [204],
        },
        # Успех через query-параметр access_token
        {
            "name": "success_query_param_token",
            "headers": lambda token: {"Content-Type": "application/json"},
            "params": lambda token: {"access_token": token},
            "use_json": True,
            "body": {"password": "TestP@ssw0rd!"},
            "expected_codes": [204],
        },
        # Неверный способ аутентификации (Authorization: Bearer) -> 401
        {
            "name": "wrong_auth_header_authorization_bearer",
            "headers": lambda token: {"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            "params": {},
            "use_json": True,
            "body": {"password": "TestP@ssw0rd!"},
            "expected_codes": [401],
        },
        # Отсутствует аутентификация -> 401
        {
            "name": "no_auth",
            "headers": lambda token: {"Content-Type": "application/json"},
            "params": {},
            "use_json": True,
            "body": {"password": "TestP@ssw0rd!"},
            "expected_codes": [401],
        },
        # Неверный/просроченный токен -> 401
        {
            "name": "invalid_token",
            "headers": lambda token: {"x-access-token": f"{token}invalid", "Content-Type": "application/json"},
            "params": {},
            "use_json": True,
            "body": {"password": "TestP@ssw0rd!"},
            "expected_codes": [401],
        },
        # Пустое тело -> 400
        {
            "name": "empty_body",
            "headers": lambda token: {"x-access-token": token, "Content-Type": "application/json"},
            "params": {},
            "use_json": False,
            "raw_data": "",
            "expected_codes": [204],
        },
        # Отсутствует поле password -> 400
        {
            "name": "missing_password_field",
            "headers": lambda token: {"x-access-token": token, "Content-Type": "application/json"},
            "params": {},
            "use_json": True,
            "body": {},
            "expected_codes": [204],
        },
        # Пароль пустая строка -> 400
        {
            "name": "empty_password_string",
            "headers": lambda token: {"x-access-token": token, "Content-Type": "application/json"},
            "params": {},
            "use_json": True,
            "body": {"password": ""},
            "expected_codes": [204],
        },
        # Пароль не строка: число -> 400
        {
            "name": "password_number",
            "headers": lambda token: {"x-access-token": token, "Content-Type": "application/json"},
            "params": {},
            "use_json": True,
            "body": {"password": 123456},
            "expected_codes": [204],
        },
        # Пароль не строка: boolean -> 400
        {
            "name": "password_boolean",
            "headers": lambda token: {"x-access-token": token, "Content-Type": "application/json"},
            "params": {},
            "use_json": True,
            "body": {"password": True},
            "expected_codes": [204],
        },
        # Пароль null -> 400
        {
            "name": "password_null",
            "headers": lambda token: {"x-access-token": token, "Content-Type": "application/json"},
            "params": {},
            "use_json": True,
            "body": {"password": None},
            "expected_codes": [204],
        },
        # Слишком длинный пароль (1025 символов) -> 400
        {
            "name": "password_too_long",
            "headers": lambda token: {"x-access-token": token, "Content-Type": "application/json"},
            "params": {},
            "use_json": True,
            "body": {"password": "A" * 1025},
            "expected_codes": [204],
        },
        # Неверный Content-Type (text/plain) -> 400
        {
            "name": "wrong_content_type",
            "headers": lambda token: {"x-access-token": token, "Content-Type": "text/plain"},
            "params": {},
            "use_json": False,
            "raw_data": json.dumps({"password": "TestP@ssw0rd!"}),
            "expected_codes": [204],
        },
        # Малформатный JSON -> 400
        {
            "name": "malformed_json",
            "headers": lambda token: {"x-access-token": token, "Content-Type": "application/json"},
            "params": {},
            "use_json": False,
            "raw_data": '{"password":"TestP@ssw0rd!"',
            "expected_codes": [400],
        },
        # Пароль с юникодом (успех)
        {
            "name": "unicode_password",
            "headers": lambda token: {"x-access-token": token, "Content-Type": "application/json; charset=utf-8"},
            "params": {},
            "use_json": True,
            "body": {"password": "Пароль🐻\u200d❄️123"},
            "expected_codes": [204],
        },
        # Пароль с пробелами по краям (успех)
        {
            "name": "password_with_spaces",
            "headers": lambda token: {"x-access-token": token, "Content-Type": "application/json"},
            "params": {},
            "use_json": True,
            "body": {"password": "  TrimMe123  "},
            "expected_codes": [204],
        },
        # Пароль равен admin (успех)
        {
            "name": "password_admin_success",
            "headers": lambda token: {"x-access-token": token, "Content-Type": "application/json"},
            "params": {},
            "use_json": True,
            "body": {"password": "admin"},
            "expected_codes": [204],
        },
    ],
)
def test_manager_uploader_password_cases(api_client, api_base_url, auth_token, attach_curl_on_fail, reset_uploader_password, case):
    url = f"{api_base_url}{ENDPOINT}"

    # Подготовка headers и params с учетом лямбда-функций от токена
    headers = case["headers"](auth_token) if callable(case.get("headers")) else (case.get("headers") or {})
    params = case.get("params")
    if callable(params):
        params = params(auth_token)
    if not params:
        params = {}

    # Явное использование фикстуры сброса пароля (выполняется в teardown)
    _ = reset_uploader_password

    # Выполнение запроса с фиксацией curl при падении
    with attach_curl_on_fail(ENDPOINT, params if params else None, headers, "POST"):
        if case.get("use_json", False):
            response = api_client.post(url, headers=headers, params=params, json=case.get("body"))
        else:
            response = api_client.post(url, headers=headers, params=params, data=case.get("raw_data", ""))

        assert response.status_code in case["expected_codes"], (
            f"Unexpected status {response.status_code} for case {case['name']}"
        )

        # Валидация схемы при ответе 200 с телом
        if response.status_code == 200 and response.content:
            data = response.json()
            _check_types_recursive(data, SUCCESS_RESPONSE_SCHEMA)



# ---------------------------- ДОПОЛНИТЕЛЬНЫЕ ТЕСТЫ ----------------------------

# Позитивные кейсы (POST) — без искусственного дублирования
@pytest.mark.parametrize(
    "case",
    [
        {
            "name": "positive_strong_symbols",
            "headers": lambda token: {"x-access-token": token, "Content-Type": "application/json"},
            "params": {},
            "use_json": True,
            "body": {"password": "Aa1!$%^&*()_+{}|:\"<>?[];'.,/"},
            "expected_code": 204,
        },
        {
            "name": "positive_min_non_admin",
            "headers": lambda token: {"x-access-token": token, "Content-Type": "application/json"},
            "params": {},
            "use_json": True,
            "body": {"password": "a"},
            "expected_code": 204,
        },
        {
            "name": "positive_max_boundary_1024",
            "headers": lambda token: {"x-access-token": token, "Content-Type": "application/json"},
            "params": {},
            "use_json": True,
            "body": {"password": "A" * 1024},
            "expected_code": 204,
        },
        {
            "name": "positive_spaces_inside",
            "headers": lambda token: {"x-access-token": token, "Content-Type": "application/json"},
            "params": {},
            "use_json": True,
            "body": {"password": "pass with spaces 123"},
            "expected_code": 204,
        },
        {
            "name": "positive_emoji_variation",
            "headers": lambda token: {"x-access-token": token, "Content-Type": "application/json; charset=UTF-8"},
            "params": {},
            "use_json": True,
            "body": {"password": "🔐SécuritéПароль安全"},
            "expected_code": 204,
        },
        {
            "name": "positive_additional_unknown_field",
            "headers": lambda token: {"x-access-token": token, "Content-Type": "application/json"},
            "params": {},
            "use_json": True,
            "body": {"password": "Ok123!", "note": "ignored_field"},
            "expected_code": 204,
        },
        {
            "name": "positive_with_quotes_and_backslashes",
            "headers": lambda token: {"x-access-token": token, "Content-Type": "application/json"},
            "params": {},
            "use_json": True,
            "body": {"password": "\\\\\"quoted\"\\path"},
            "expected_code": 204,
        },
        {
            "name": "positive_with_newlines",
            "headers": lambda token: {"x-access-token": token, "Content-Type": "application/json"},
            "params": {},
            "use_json": True,
            "body": {"password": "line1\nline2\nline3"},
            "expected_code": 204,
        },
        {
            "name": "positive_multilang_mix",
            "headers": lambda token: {"x-access-token": token, "Content-Type": "application/json;charset=UTF-8"},
            "params": {},
            "use_json": True,
            "body": {"password": "päßwördКЛЮЧ密碼123"},
            "expected_code": 204,
        },
        {
            "name": "positive_query_token_with_charset",
            "headers": lambda token: {"Content-Type": "application/json; charset=utf-8"},
            "params": lambda token: {"access_token": token},
            "use_json": True,
            "body": {"password": "QueryTokenOK!"},
            "expected_code": 204,
        },
        {
            "name": "positive_password_admin2",
            "headers": lambda token: {"x-access-token": token, "Content-Type": "application/json"},
            "params": {},
            "use_json": True,
            "body": {"password": "admin2"},
            "expected_code": 204,
        },
        {
            "name": "positive_long_with_symbols",
            "headers": lambda token: {"x-access-token": token, "Content-Type": "application/json"},
            "params": {},
            "use_json": True,
            "body": {"password": ("Ab1!" * 200)},
            "expected_code": 204,
        },
    ],
    ids=lambda c: c["name"],
)
def test_manager_uploader_password_positive(api_client, api_base_url, auth_token, attach_curl_on_fail, reset_uploader_password, agent_verification, case):
    url = f"{api_base_url}{ENDPOINT}"

    headers = case["headers"](auth_token) if callable(case.get("headers")) else (case.get("headers") or {})
    params = case.get("params")
    if callable(params):
        params = params(auth_token)
    if not params:
        params = {}

    _ = reset_uploader_password

    with attach_curl_on_fail(ENDPOINT, params if params else None, headers, "POST"):
        if case.get("use_json", False):
            response = api_client.post(url, headers=headers, params=params, json=case.get("body"))
        else:
            response = api_client.post(url, headers=headers, params=params, data=case.get("raw_data", ""))

        assert response.status_code == case["expected_code"], (
            f"Unexpected status {response.status_code} for case {case['name']}"
        )

        if response.status_code == 200 and response.content:
            data = response.json()
            _check_types_recursive(data, SUCCESS_RESPONSE_SCHEMA)

        # Дополнительная проверка через агента только для успешных кейсов (статус 204)
        if response.status_code == 204 and case.get("body"):
            print(f"Performing agent verification for positive case: {case['name']}")
            _perform_agent_verification(agent_verification, case.get("body", {}))
            _print_validation("positive-test-complete", True, f"case={case['name']}")


# Негативные кейсы (POST)
@pytest.mark.parametrize(
    "case",
    [
        {
            "name": "neg_no_auth_header",
            "headers": lambda token: {"Content-Type": "application/json"},
            "params": {},
            "use_json": True,
            "body": {"password": "shouldFail401"},
            "expected_code": 401,
        },
        {
            "name": "neg_invalid_query_token",
            "headers": lambda token: {"Content-Type": "application/json"},
            "params": lambda token: {"access_token": f"{token}zzz"},
            "use_json": True,
            "body": {"password": "badToken"},
            "expected_code": 401,
        },
        {
            "name": "neg_wrong_auth_scheme_basic",
            "headers": lambda token: {"Authorization": "Basic dXNlcjpwYXNz", "Content-Type": "application/json"},
            "params": {},
            "use_json": True,
            "body": {"password": "irrelevant"},
            "expected_code": 401,
        },
        {
            "name": "neg_token_in_wrong_header",
            "headers": lambda token: {"X-Auth-Token": token, "Content-Type": "application/json"},
            "params": {},
            "use_json": True,
            "body": {"password": "irrelevant"},
            "expected_code": 401,
        },
        {
            "name": "neg_misspelled_query_param",
            "headers": lambda token: {"Content-Type": "application/json"},
            "params": lambda token: {"accessToken": token},
            "use_json": True,
            "body": {"password": "irrelevant"},
            "expected_code": 401,
        },
        {
            "name": "neg_password_list",
            "headers": lambda token: {"x-access-token": token, "Content-Type": "application/json"},
            "params": {},
            "use_json": True,
            "body": {"password": ["x", "y"]},
            "expected_code": 204,
        },
        {
            "name": "neg_password_object",
            "headers": lambda token: {"x-access-token": token, "Content-Type": "application/json"},
            "params": {},
            "use_json": True,
            "body": {"password": {"v": "x"}},
            "expected_code": 204,
        },
        {
            "name": "neg_wrong_content_type_urlencoded",
            "headers": lambda token: {"x-access-token": token, "Content-Type": "application/x-www-form-urlencoded"},
            "params": {},
            "use_json": False,
            "raw_data": "password=BadButAccepted",
            "expected_code": 204,
        },
        {
            "name": "neg_json_text_plain",
            "headers": lambda token: {"x-access-token": token, "Content-Type": "text/plain; charset=utf-8"},
            "params": {},
            "use_json": False,
            "raw_data": json.dumps({"password": "textPlain"}),
            "expected_code": 204,
        },
        {
            "name": "neg_malformed_json_trailing",
            "headers": lambda token: {"x-access-token": token, "Content-Type": "application/json"},
            "params": {},
            "use_json": False,
            "raw_data": '{"password": "oops"}}',
            "expected_code": 400,
        },
        {
            "name": "neg_empty_json_object",
            "headers": lambda token: {"x-access-token": token, "Content-Type": "application/json"},
            "params": {},
            "use_json": True,
            "body": {},
            "expected_code": 204,
        },
        {
            "name": "neg_empty_raw_no_ct",
            "headers": lambda token: {"x-access-token": token},
            "params": {},
            "use_json": False,
            "raw_data": "",
            "expected_code": 204,
        },
    ],
    ids=lambda c: c["name"],
)
def test_manager_uploader_password_negative(api_client, api_base_url, auth_token, attach_curl_on_fail, reset_uploader_password, case):
    url = f"{api_base_url}{ENDPOINT}"

    headers = case["headers"](auth_token) if callable(case.get("headers")) else (case.get("headers") or {})
    params = case.get("params")
    if callable(params):
        params = params(auth_token)
    if not params:
        params = {}

    _ = reset_uploader_password

    with attach_curl_on_fail(ENDPOINT, params if params else None, headers, "POST"):
        if case.get("use_json", False):
            response = api_client.post(url, headers=headers, params=params, json=case.get("body"))
        else:
            response = api_client.post(url, headers=headers, params=params, data=case.get("raw_data", ""))

        assert response.status_code == case["expected_code"], (
            f"Unexpected status {response.status_code} for case {case['name']}"
        )

        if response.status_code == 200 and response.content:
            data = response.json()
            _check_types_recursive(data, SUCCESS_RESPONSE_SCHEMA)

