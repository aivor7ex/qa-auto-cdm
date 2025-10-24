import pytest
import warnings

# ВЕРХ ФАЙЛА: обязательные константы
ENDPOINT = "/notifications/delete-all"
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


# ----- КЕЙСЫ: АУТЕНТИФИКАЦИОННЫЕ ОШИБКИ → 401 -----
@pytest.mark.parametrize(
    "headers, desc",
    [
        (None, "без токена → 401"),
        ({"x-access-token": ""}, "пустой токен → 401"),
        ({"x-access-token": "INVALID.TOKEN"}, "неверный токен → 401"),
    ],
    ids=[
        "без токена → 401",
        "пустой токен → 401",
        "неверный токен → 401",
    ],
)
def test_notifications_delete_all_auth_errors(api_client, api_base_url, headers, desc, attach_curl_on_fail):
    url = f"{api_base_url}{ENDPOINT}"
    with attach_curl_on_fail(ENDPOINT, None, headers or None, "POST"):
        if headers is None:
            response = api_client.post(url)
        else:
            response = api_client.post(url, headers=headers)
        assert response.status_code == 401, f"{desc}; получено {response.status_code}"


# ----- КЕЙСЫ: ОБЩИЕ УСПЕХИ (валидный токен, разные варианты заголовков/тел) → 200 -----
@pytest.mark.parametrize(
    "headers, body, desc",
    [
        (lambda tok: {"x-access-token": tok}, None, "только x-access-token, без тела → 200"),
        (lambda tok: {"x-access-token": tok, "Content-Type": "application/json"}, {}, "с Content-Type и пустым телом → 200"),
    ],
    ids=[
        "x-access-token без тела",
        "x-access-token + Content-Type + пустое тело",
    ],
)
def test_notifications_delete_all_success_variants(api_client, auth_token, api_base_url, headers, body, desc, attach_curl_on_fail):
    url = f"{api_base_url}{ENDPOINT}"
    hdrs = headers(auth_token)
    with attach_curl_on_fail(ENDPOINT, body, hdrs, "POST"):
        if body is None:
            response = api_client.post(url, headers=hdrs)
        else:
            response = api_client.post(url, json=body, headers=hdrs)
        assert response.status_code == 200, f"Ожидается 200 OK; получено {response.status_code}"
        data = response.json()
        _validate_success_response(data)
        assert data["count"] >= 0


# ----- КЕЙС: ИДЕМПОТЕНТНОСТЬ (повторный вызов сразу после удаления) -----
def test_notifications_delete_all_idempotency(api_client, auth_token, api_base_url, attach_curl_on_fail):
    url = f"{api_base_url}{ENDPOINT}"
    headers = {"x-access-token": auth_token, "Content-Type": "application/json"}

    with attach_curl_on_fail(ENDPOINT, {}, headers, "POST"):
        first = api_client.post(url, json={}, headers=headers)
    assert first.status_code == 200, f"Первый запрос: ожидается 200 OK; получено {first.status_code}"
    first_data = first.json()
    _validate_success_response(first_data)

    with attach_curl_on_fail(ENDPOINT, {}, headers, "POST"):
        second = api_client.post(url, json={}, headers=headers)
    assert second.status_code == 200, f"Второй запрос: ожидается 200 OK; получено {second.status_code}"
    second_data = second.json()
    _validate_success_response(second_data)
    assert second_data["count"] == 0, "Повторный вызов после удаления должен вернуть count=0"


# ----- КЕЙС: ЗАГОЛОВОК Authorization вместо x-access-token → 401 -----
def test_notifications_delete_all_wrong_auth_header(api_client, auth_token, api_base_url, attach_curl_on_fail):
    url = f"{api_base_url}{ENDPOINT}"
    headers = {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}
    with attach_curl_on_fail(ENDPOINT, {}, headers, "POST"):
        response = api_client.post(url, json={}, headers=headers)
    assert response.status_code == 401, f"Ожидается 401 Unauthorized; получено {response.status_code}"


# ----- КЕЙС: ТОКЕН В QUERY (?access_token=) → 200 -----
def test_notifications_delete_all_token_in_query(api_client, auth_token, api_base_url, attach_curl_on_fail):
    url = f"{api_base_url}{ENDPOINT}"
    params = {"access_token": auth_token}
    with attach_curl_on_fail(ENDPOINT, None, None, "POST"):
        response = api_client.post(url, params=params)
    assert response.status_code == 200, f"Ожидается 200 OK; получено {response.status_code}"
    data = response.json()
    _validate_success_response(data)
    assert data["count"] >= 0


# ----- КЕЙС: ТОКЕН В ТЕЛЕ JSON → 200 -----
def test_notifications_delete_all_token_in_body_json(api_client, auth_token, api_base_url, attach_curl_on_fail):
    url = f"{api_base_url}{ENDPOINT}"
    payload = {"access_token": auth_token}
    headers = {"Content-Type": "application/json"}
    with attach_curl_on_fail(ENDPOINT, payload, headers, "POST"):
        response = api_client.post(url, json=payload, headers=headers)
    assert response.status_code == 200, f"Ожидается 200 OK; получено {response.status_code}"
    data = response.json()
    _validate_success_response(data)
    assert data["count"] >= 0


# ----- ДОПОЛНИТЕЛЬНЫЕ ПОЗИТИВНЫЕ КЕЙСЫ (в сумме должно быть 15) -----
@pytest.mark.parametrize(
    "post_kwargs, desc",
    [
        ({"headers": lambda tok: {"x-access-token": tok}}, "x-access-token без тела и без Content-Type → 200"),
        ({"headers": lambda tok: {"x-access-token": tok, "Content-Type": "application/json"}, "json": {}}, "x-access-token + Content-Type + пустое JSON-тело → 200"),
        ({"params": lambda tok: {"access_token": tok}}, "токен в query-параметре, без тела → 200"),
        ({"json": lambda tok: {"access_token": tok}, "headers": {"Content-Type": "application/json"}}, "токен в JSON-теле → 200"),
        ({"headers": lambda tok: {"x-access-token": tok}, "json": {}}, "x-access-token + пустое JSON-тело без Content-Type → 200"),
        ({"headers": lambda tok: {"x-access-token": tok, "Content-Type": "application/json"}}, "x-access-token + только Content-Type, без тела → 200"),
        ({"headers": lambda tok: {"x-access-token": tok}, "params": lambda tok: {"access_token": tok}}, "токен одновременно в заголовке и query → 200"),
        ({"headers": lambda tok: {"x-access-token": tok, "Content-Type": "application/json"}, "json": {"unused": True}}, "x-access-token + JSON-тело с лишним полем → 200"),
        ({"headers": lambda tok: {"x-access-token": tok}, "params": lambda tok: {"access_token": tok}, "json": {}}, "токен в заголовке и query + пустое JSON-тело → 200"),
        ({"params": lambda tok: {"access_token": tok}, "json": {}}, "токен в query + пустое JSON-тело → 200"),
    ],
    ids=[
        "hdr_only",
        "hdr_ct_json_empty",
        "query_only",
        "json_body_token",
        "hdr_json_empty_no_ct",
        "hdr_ct_only",
        "hdr_and_query",
        "hdr_json_with_extra_field",
        "hdr_query_and_empty_json",
        "query_with_empty_json",
    ],
)
def test_notifications_delete_all_success_matrix(api_client, auth_token, api_base_url, post_kwargs, desc, attach_curl_on_fail):
    url = f"{api_base_url}{ENDPOINT}"

    # Разворачиваем параметры вызова в зависимости от фикстуры токена
    kwargs = {}
    for key, value in post_kwargs.items():
        if callable(value):
            kwargs[key] = value(auth_token)
        else:
            kwargs[key] = value

    headers_for_curl = kwargs.get("headers")
    payload_for_curl = kwargs.get("json", None)

    with attach_curl_on_fail(ENDPOINT, payload_for_curl, headers_for_curl, "POST"):
        response = api_client.post(url, **kwargs)
    assert response.status_code == 200, f"{desc}: ожидается 200 OK; получено {response.status_code}"
    data = response.json()
    _validate_success_response(data)
    assert data["count"] >= 0


# ----- ДОПОЛНИТЕЛЬНЫЕ НЕГАТИВНЫЕ КЕЙСЫ (в сумме должно быть 15) -----
@pytest.mark.parametrize(
    "post_kwargs, expected_status, desc",
    [
        ({}, 401, "без токена вообще → 401"),
        ({"headers": {"x-access-token": ""}}, 401, "пустой токен в заголовке → 401"),
        ({"headers": {"x-access-token": "INVALID.TOKEN"}}, 401, "неверный/поддельный токен в заголовке → 401"),
        ({"params": {"access_token": ""}}, 401, "пустой токен в query → 401"),
        ({"params": {"access_token": "INVALID"}}, 401, "неверный токен в query → 401"),
        ({"json": {"access_token": ""}, "headers": {"Content-Type": "application/json"}}, 401, "пустой токен в JSON-теле → 401"),
        ({"json": {"access_token": "INVALID"}, "headers": {"Content-Type": "application/json"}}, 401, "неверный токен в JSON-теле → 401"),
        ({"headers": {"Authorization": "Bearer INVALID"}}, 401, "заголовок Authorization вместо x-access-token → 401"),
        ({"headers": {"Authorization": "Bearer "}}, 401, "Authorization с пустым значением → 401"),
        ({"headers": {"X-Access-Token": "INVALID"}}, 401, "неверное имя заголовка (X-Access-Token) → 401"),
        ({"headers": {"x-access-token": "invalid token"}}, 401, "токен с пробелом внутри → 401"),
        ({"headers": {"x-access-token": "Bearer INVALID"}}, 401, "токен с префиксом Bearer в x-access-token → 401"),
        ({"data": {"access_token": "SOME"}}, 400, "токен в form-urlencoded теле → 400"),
        ({"files": [], "data": {"access_token": "SOME"}}, 400, "токен в multipart/form-data → 400"),
        ({"headers": {"Content-Type": "application/json"}, "json": {}}, 401, "только Content-Type и тело без токена → 401"),
    ],
    ids=[
        "no_token_anywhere",
        "empty_hdr",
        "invalid_hdr",
        "empty_query",
        "invalid_query",
        "empty_body_json",
        "invalid_body_json",
        "auth_header_instead",
        "auth_header_empty",
        "wrong_header_name_capitalized",
        "invalid_hdr_with_space",
        "bearer_in_hdr_value",
        "form_urlencoded_token_bad_request",
        "multipart_form_token_bad_request",
        "json_body_no_token",
    ],
)
def test_notifications_delete_all_auth_negatives_matrix(api_client, api_base_url, post_kwargs, expected_status, desc, attach_curl_on_fail):
    url = f"{api_base_url}{ENDPOINT}"

    headers_for_curl = post_kwargs.get("headers") if post_kwargs else None
    payload_for_curl = post_kwargs.get("json") if post_kwargs else None

    with attach_curl_on_fail(ENDPOINT, payload_for_curl, headers_for_curl, "POST"):
        response = api_client.post(url, **post_kwargs)
    assert response.status_code == expected_status, f"{desc}; получено {response.status_code}"


# ----- ДОПОЛНИТЕЛЬНЫЙ ПОЗИТИВНЫЙ ТЕСТ: ПРОВЕРКА ЧЕРЕЗ АГЕНТА С ТОКЕНОМ В ТЕЛЕ -----
def test_notifications_delete_all_agent_verification_body_token(agent_verification, auth_token):
    """
    Запрос к агенту выполняется отдельным тестом.
    Отправляем токен в теле запроса: {"x-access-token": "[token]"}.
    Обработка ответа агента:
      - {"result":"OK"} → успех
      - {"result":"ERROR","message":"..."} → зафиксировать предупреждение и провалить тест
      - "unavailable" → НЕ пропускать, тест должен упасть
    После каждого шага — краткая валидация результата и решение продолжить/завершить.
    """

    # Шаг 1: Подготовка payload
    payload = {"x-access-token": auth_token}
    assert isinstance(payload["x-access-token"], str) and payload["x-access-token"].strip(), \
        "Валидация: токен должен быть непустой строкой"

    # Шаг 2: Вызов проверки агента
    result = agent_verification("/notifications/delete-all", payload)
    assert result is not None, "Валидация: ответ агента должен быть не None"

    # Шаг 3: Анализ результата
    if result == "unavailable":
        # Агент недоступен — тест падает (не пропускать)
        warnings.warn("Агент \"доступ\": недоступен. Тест проваливается.")
        pytest.fail("Agent is unavailable (not allowed to skip)")

    assert isinstance(result, dict), "Валидация: ответ агента должен быть объектом"
    assert "result" in result, "Валидация: ответ агента должен содержать поле 'result'"

    if result.get("result") == "OK":
        # Успех
        return

    if result.get("result") == "ERROR":
        msg = result.get("message", "")
        warnings.warn(f"Агент \"доступ\". Ошибка: {msg}. Тест проваливается.")
        pytest.fail(f"Agent returned ERROR: {msg}")

    # Неожиданный формат
    pytest.fail(f"Unexpected agent response: {result}")
