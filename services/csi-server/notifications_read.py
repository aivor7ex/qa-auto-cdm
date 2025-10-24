import pytest

# ВЕРХ ФАЙЛА: обязательные константы
ENDPOINT = "/notifications/read"

# Схема успешного ответа, встроенная в файл (R7, R10)
SUCCESS_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "count": {"type": "integer"}
    },
    "required": ["count"],
}


# ----- УТИЛИТЫ ДЛЯ ВАЛИДАЦИИ СХЕМЫ (R6) -----
def _check_types_recursive(obj, schema):
    if "anyOf" in schema:
        assert any(_try_type(obj, s) for s in schema["anyOf"]), f"Value {obj} does not match anyOf {schema['anyOf']}"
        return

    s_type = schema.get("type")
    if s_type == "object":
        assert isinstance(obj, dict), f"Expected object, got {type(obj)}"
        for key, prop in schema.get("properties", {}).items():
            if key in obj:
                _check_types_recursive(obj[key], prop)
        for req in schema.get("required", []):
            assert req in obj, f"Missing required field: {req}"
    elif s_type == "array":
        assert isinstance(obj, list) and not isinstance(obj, str), f"Expected array, got {type(obj)}"
        items_schema = schema.get("items")
        if isinstance(items_schema, list):
            for item, item_schema in zip(obj, items_schema):
                _check_types_recursive(item, item_schema)
        elif items_schema is not None:
            for item in obj:
                _check_types_recursive(item, items_schema)
    else:
        if s_type == "string":
            assert isinstance(obj, str), f"Expected string, got {type(obj)}"
        elif s_type == "integer":
            assert isinstance(obj, int), f"Expected integer, got {type(obj)}"
        elif s_type == "number":
            assert isinstance(obj, (int, float)), f"Expected number, got {type(obj)}"
        elif s_type == "boolean":
            assert isinstance(obj, bool), f"Expected boolean, got {type(obj)}"
        elif s_type == "null":
            assert obj is None, f"Expected null, got {type(obj)}"


def _try_type(obj, schema):
    try:
        _check_types_recursive(obj, schema)
        return True
    except AssertionError:
        return False


def _validate_success_response(data):
    _check_types_recursive(data, SUCCESS_RESPONSE_SCHEMA)


# ----- КЕЙСЫ: УСПЕШНЫЕ С НУЛЕВЫМ COUNT -----
@pytest.mark.parametrize(
    "payload, desc",
    [
        ({"ids": []}, "пустой список id → count=0"),
        ({"ids": ["not-exist-1", "not-exist-2"]}, "несуществующие id → count=0"),
        ({"ids": ["$ne:1", "{\"$gt\":\"\"}"]}, "потенциально вредоносные id → count=0"),
        ({"ids": [123, True, None, {"a": 1}]}, "не-строки в ids → count=0"),
    ],
    ids=[
        "пустой список id → count=0",
        "несуществующие id → count=0",
        "потенциально вредоносные id → count=0",
        "не-строки в ids → count=0",
    ],
)
def test_notifications_read_success_zero_count(api_client, auth_token, api_base_url, payload, desc, attach_curl_on_fail):
    url = f"{api_base_url}{ENDPOINT}"
    headers = {"x-access-token": auth_token, "Content-Type": "application/json"}
    with attach_curl_on_fail(ENDPOINT, payload, headers, "POST"):
        response = api_client.post(url, json=payload, headers=headers)
        assert response.status_code == 200, f"Ожидается 200 OK; получено {response.status_code}"
        data = response.json()
        _validate_success_response(data)
        assert data["count"] == 0, f"{desc}: ожидается count=0"


# ----- КЕЙСЫ: ОБЩИЕ УСПЕШНЫЕ -----
@pytest.mark.parametrize(
    "payload, expected_max, desc",
    [
        ({"ids": ["notif-id-1"]}, 1, "один валидный id пользователя → count в [0,1]"),
        ({"ids": ["notif-id-1", "notif-id-2"]}, 2, "несколько валидных id пользователя → count в [0,2]"),
        ({"ids": ["own-1", "foreign-1", "own-2"]}, 3, "смешанные id → count в [0,3] (только свои)"),
        ({"ids": ["foreign-1", "foreign-2"]}, 2, "все чужие id → возможно 0"),
        ({"ids": ["notif-id-1", "notif-id-1"]}, 1, "дубликаты id → как для уникальных"),
        ({"ids": ["already-read-1", "already-read-2"]}, 2, "id уже read=true → идемпотентно"),
        ({"ids": [f"id-{i}" for i in range(1, 11)]}, 10, "большой список id → count в [0,10]"),
        ({"ids": ["own-1", "own-1", "own-2", "own-2"]}, 2, "много дубликатов своих id → как для уникальных"),
        ({"ids": ["foreign-1"]}, 1, "один чужой id → возможно 0"),
        ({"ids": ["already-read-1"]}, 1, "один уже прочитанный id → идемпотентно"),
    ],
    ids=[
        "один валидный id пользователя",
        "несколько валидных id пользователя",
        "смешанные id",
        "все чужие id",
        "дубликаты id",
        "уже прочитанные id",
        "большой список id",
        "много дубликатов",
        "один чужой id",
        "один уже прочитанный id",
    ],
)
def test_notifications_read_success_general(api_client, auth_token, api_base_url, payload, expected_max, desc, attach_curl_on_fail):
    url = f"{api_base_url}{ENDPOINT}"
    headers = {"x-access-token": auth_token, "Content-Type": "application/json"}
    with attach_curl_on_fail(ENDPOINT, payload, headers, "POST"):
        response = api_client.post(url, json=payload, headers=headers)
        assert response.status_code == 200, f"Ожидается 200 OK; получено {response.status_code}"
        data = response.json()
        _validate_success_response(data)

        # Проверяем разумные границы: 0 <= count <= число уникальных строковых id
        string_ids = [x for x in payload.get("ids", []) if isinstance(x, str)]
        unique_count = len(set(string_ids))
        assert 0 <= data["count"] <= min(unique_count, expected_max), f"{desc}: count вне ожидаемых границ"


# ----- КЕЙСЫ: АУТЕНТИФИКАЦИЯ -----
@pytest.mark.parametrize(
    "headers, expected_status, desc",
    [
        ({}, 401, "без токена → 401"),
        ({"x-access-token": "INVALID", "Content-Type": "application/json"}, 401, "невалидный/просроченный токен → 401"),
    ],
    ids=[
        "без токена → 401",
        "невалидный токен → 401",
    ],
)
def test_notifications_read_auth_errors(api_client, api_base_url, headers, expected_status, desc, attach_curl_on_fail):
    url = f"{api_base_url}{ENDPOINT}"
    payload = {"ids": ["notif-id-1"]}
    with attach_curl_on_fail(ENDPOINT, payload if headers else None, headers or None, "POST"):
        if headers:
            response = api_client.post(url, json=payload, headers=headers)
        else:
            response = api_client.post(url, json=payload)
        assert response.status_code == expected_status, f"{desc}; получено {response.status_code}"


# ----- КЕЙС: ТОКЕН В QUERY → УСПЕХ -----
def test_notifications_read_token_in_query(api_client, auth_token, api_base_url, attach_curl_on_fail):
    url = f"{api_base_url}{ENDPOINT}"
    params = {"access_token": auth_token}
    payload = {"ids": []}
    with attach_curl_on_fail(ENDPOINT, payload, None, "POST"):
        response = api_client.post(url, json=payload, params=params)
        assert response.status_code == 200, f"Ожидается 200 OK; получено {response.status_code}"
        data = response.json()
        _validate_success_response(data)
        assert data["count"] == 0


# ----- КЕЙС: ТОКЕН В MULTIPART-FORM → 400 -----
def test_notifications_read_token_in_multipart(api_client, auth_token, api_base_url, attach_curl_on_fail):
    url = f"{api_base_url}{ENDPOINT}"
    # Отправляем как форму: access_token и ids[]
    data = [
        ("access_token", auth_token),
        ("ids[]", "notif-id-1"),
        ("ids[]", "notif-id-2"),
    ]
    with attach_curl_on_fail(ENDPOINT, None, None, "POST"):
        response = api_client.post(url, files=[], data=data)
        # Фактическое поведение API: 400 Bad Request (R16, R17)
        assert response.status_code == 400, f"Ожидается 400 Bad Request; получено {response.status_code}"


# ----- КЕЙС: НЕВЕРНЫЙ CONTENT-TYPE ДЛЯ JSON-ТЕЛА → 400/415 -----
def test_notifications_read_wrong_content_type(api_client, auth_token, api_base_url, attach_curl_on_fail):
    url = f"{api_base_url}{ENDPOINT}"
    headers = {"x-access-token": auth_token, "Content-Type": "text/plain"}
    raw_body = "{\"ids\":[\"notif-id-1\"]}"
    with attach_curl_on_fail(ENDPOINT, raw_body, headers, "POST"):
        response = api_client.post(url, data=raw_body, headers=headers)
        assert response.status_code in (400, 415), f"Ожидается 400 или 415; получено {response.status_code}"


# ----- ДОП. НЕГАТИВНЫЕ: НЕКОРРЕКТНОЕ ТЕЛО И РАЗНЫЕ ВАРИАНТЫ IDS -----
def test_notifications_read_invalid_json_malformed(api_client, auth_token, api_base_url, attach_curl_on_fail):
    url = f"{api_base_url}{ENDPOINT}"
    headers = {"x-access-token": auth_token, "Content-Type": "application/json"}
    raw_body = "{\"ids\":[\"notif-id-1\",]"  # сломанный JSON
    with attach_curl_on_fail(ENDPOINT, raw_body, headers, "POST"):
        response = api_client.post(url, data=raw_body, headers=headers)
        assert response.status_code == 400, f"Ожидается 400 Bad Request; получено {response.status_code}"


def test_notifications_read_empty_body_with_json_type(api_client, auth_token, api_base_url, attach_curl_on_fail):
    url = f"{api_base_url}{ENDPOINT}"
    headers = {"x-access-token": auth_token, "Content-Type": "application/json"}
    with attach_curl_on_fail(ENDPOINT, "", headers, "POST"):
        response = api_client.post(url, data="", headers=headers)
        assert response.status_code == 400, f"Ожидается 400 Bad Request; получено {response.status_code}"


@pytest.mark.parametrize(
    "payload, case_id",
    [
        ({"ids": None}, "ids=null → 400"),
        ({"ids": {}}, "ids=object → 400"),
        ({"ids": 123}, "ids=number → 400"),
        ({"ids": False}, "ids=boolean → 400"),
    ],
    ids=[
        "ids=null → 400",
        "ids=object → 400",
        "ids=number → 400",
        "ids=boolean → 400",
    ],
)
def test_notifications_read_ids_wrong_types(api_client, auth_token, api_base_url, payload, case_id, attach_curl_on_fail):
    url = f"{api_base_url}{ENDPOINT}"
    headers = {"x-access-token": auth_token, "Content-Type": "application/json"}
    with attach_curl_on_fail(ENDPOINT, payload, headers, "POST"):
        response = api_client.post(url, json=payload, headers=headers)
        assert response.status_code == 400, f"{case_id}; получено {response.status_code}"


def test_notifications_read_form_urlencoded_with_json_type(api_client, auth_token, api_base_url, attach_curl_on_fail):
    url = f"{api_base_url}{ENDPOINT}"
    # Несоответствие: application/json, но отправляем form-данные
    headers = {"x-access-token": auth_token, "Content-Type": "application/json"}
    form_data = [("access_token", auth_token), ("ids[]", "notif-id-1")]
    with attach_curl_on_fail(ENDPOINT, form_data, headers, "POST"):
        response = api_client.post(url, data=form_data, headers=headers)
        assert response.status_code == 400, f"Ожидается 400 Bad Request; получено {response.status_code}"


def test_notifications_read_query_token_invalid(api_client, api_base_url, attach_curl_on_fail):
    url = f"{api_base_url}{ENDPOINT}"
    params = {"access_token": "INVALID"}
    payload = {"ids": ["notif-id-1"]}
    with attach_curl_on_fail(ENDPOINT, payload, None, "POST"):
        response = api_client.post(url, json=payload, params=params)
        assert response.status_code == 401, f"Ожидается 401 Unauthorized; получено {response.status_code}"


def test_notifications_read_query_token_absent(api_client, api_base_url, attach_curl_on_fail):
    url = f"{api_base_url}{ENDPOINT}"
    # Нет access_token в query и заголовках
    payload = {"ids": ["notif-id-1"]}
    with attach_curl_on_fail(ENDPOINT, payload, None, "POST"):
        response = api_client.post(url, json=payload)
        assert response.status_code == 401, f"Ожидается 401 Unauthorized; получено {response.status_code}"


# ----- КЕЙСЫ: ВАЛИДАЦИОННЫЕ ОШИБКИ ТЕЛА (400) -----
@pytest.mark.parametrize(
    "payload, desc",
    [
        ({}, "отсутствует поле ids → 400"),
        ({"ids": "notif-id-1"}, "ids не массив → 400"),
    ],
    ids=[
        "отсутствует поле ids → 400",
        "ids не массив → 400",
    ],
)
def test_notifications_read_validation_errors(api_client, auth_token, api_base_url, payload, desc, attach_curl_on_fail):
    url = f"{api_base_url}{ENDPOINT}"
    headers = {"x-access-token": auth_token, "Content-Type": "application/json"}
    with attach_curl_on_fail(ENDPOINT, payload, headers, "POST"):
        response = api_client.post(url, json=payload, headers=headers)
        assert response.status_code == 400, f"{desc}; получено {response.status_code}"


# ----- ДОПОЛНИТЕЛЬНАЯ ПРОВЕРКА ЧЕРЕЗ АГЕНТА -----
def test_notifications_read_agent_verification(agent_verification, auth_token):
    """Отдельный тест запроса к агенту для /notifications/read.

    Правила обработки результата агента:
      - {"result":"OK"} → успех
      - {"result":"ERROR","message":"..."} → регистрируем предупреждение и падаем
      - агент недоступен → тест не пропускаем, падаем
    """
    # Шаг 1: подготовка запроса к агенту
    agent_endpoint = "/notifications/read"
    agent_payload = {
        "x-access-token": auth_token,
        "ids": ["n1", "n2"]
    }
    print("[agent-check] Подготовлен payload для агента; продолжаем к запросу")

    # Шаг 2: запрос к агенту
    result = agent_verification(agent_endpoint, agent_payload, timeout=30)
    print(f"[agent-check] Ответ агента получен: {result}")

    # Шаг 3: валидация ответа агента и решение о продолжении
    if result == "unavailable":
        print("[agent-check][WARN] Агент недоступен. Тест не пропускается и будет помечен как проваленный.")
        import pytest as _pytest
        _pytest.fail("Agent verification unavailable for /notifications/read")

    if isinstance(result, dict):
        if result.get("result") == "OK":
            print("[agent-check] Валидация OK: продолжаем")
            return
        if result.get("result") == "ERROR":
            message = result.get("message", "Неизвестная ошибка")
            print(f"[agent-check][WARN] Агент вернул ошибку: {message}. Тест провален.")
            import pytest as _pytest
            _pytest.fail(f"Agent verification failed: {message}")

    # Неожиданный формат результата агента — считаем ошибкой
    print(f"[agent-check][WARN] Неожиданный формат ответа агента: {type(result)}. Тест провален.")
    import pytest as _pytest
    _pytest.fail("Unexpected agent verification result format")

