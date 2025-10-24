import pytest

# ----- Constants -----
ENDPOINT = "/update/rules/cancel-download"

# Схема успешного ответа: 204 No Content (тело отсутствует)
SUCCESS_RESPONSE_SCHEMA = {
    "required": {},
    "optional": {},
}


# ----- Local schema validator (kept for consistency if тело появится) -----
def _validate_schema_recursive(data, schema):
    required = schema.get("required", {})
    optional = schema.get("optional", {})

    assert isinstance(data, dict), f"Ответ должен быть объектом: {type(data)}"

    for key, expected_type in required.items():
        assert key in data, f"Отсутствует обязательное поле '{key}'"
        assert isinstance(data[key], expected_type), (
            f"Поле '{key}' имеет тип {type(data[key]).__name__}, ожидался {expected_type.__name__}"
        )

    for key, expected_type in optional.items():
        if key in data and data[key] is not None:
            assert isinstance(data[key], expected_type), (
                f"Необязательное поле '{key}' имеет тип {type(data[key]).__name__}, ожидался {expected_type.__name__}"
            )


# 1) Успех с валидным токеном (+ вариации заголовков/тела, которое игнорируется)
@pytest.mark.parametrize(
    "payload,headers_extra,case_id",
    [
        (None, {"Accept": "application/json"}, "успех_без_тела"),
        ({}, {"Content-Type": "application/json"}, "успех_пустое_тело"),
        ({}, {}, "успех_без_content_type"),
        ({}, {"Accept": "*/*"}, "успех_accept_any"),
        ({}, {"X-Debug": "1"}, "успех_лишний_заголовок"),
        ({"any": "thing"}, {}, "успех_произвольное_тело"),
        ({"unused": True}, {}, "успех_булево_поле"),
        ({"array": []}, {}, "успех_пустой_массив"),
        ({"obj": {}}, {}, "успех_пустой_объект"),
        ({"number": 0}, {}, "успех_ноль_в_поле"),
        ({"string": ""}, {}, "успех_пустая_строка"),
        ({"nested": {"a": 1}}, {}, "успех_простая_вложенность"),
        ({"list": [1, 2, 3]}, {}, "успех_список_чисел"),
        ({"null": None}, {}, "успех_null_значение"),
    ],
    ids=lambda v: v[2] if isinstance(v, tuple) else str(v),
)
def test_cancel_download_success_variants(api_client, auth_token, api_base_url, attach_curl_on_fail, payload, headers_extra, case_id):
    url = f"{api_base_url}{ENDPOINT}"
    headers = {"x-access-token": auth_token}
    headers.update(headers_extra)

    with attach_curl_on_fail(ENDPOINT, payload, headers, "POST"):
        if payload is None:
            response = api_client.post(url, headers=headers)
        else:
            response = api_client.post(url, json=payload, headers=headers)

        assert response.status_code == 204, f"Ожидается 204 No Content; получено {response.status_code}"


# 3) Идемпотентность: повторный вызов
def test_cancel_download_idempotent(api_client, auth_token, api_base_url, attach_curl_on_fail):
    url = f"{api_base_url}{ENDPOINT}"
    headers = {"x-access-token": auth_token}

    with attach_curl_on_fail(ENDPOINT, None, headers, "POST"):
        response1 = api_client.post(url, headers=headers)
        assert response1.status_code == 204, f"Первый вызов: ожидается 204; получено {response1.status_code}"

    with attach_curl_on_fail(ENDPOINT, None, headers, "POST"):
        response2 = api_client.post(url, headers=headers)
        assert response2.status_code == 204, f"Второй вызов: ожидается 204; получено {response2.status_code}"


# 4-5) Ошибки аутентификации: нет токена / невалидный токен
@pytest.mark.parametrize(
    "headers,payload,case_id",
    [
        (None, None, "без_токена_и_тела"),
        (None, {}, "без_токена_пустое_тело"),
        (None, {"any": "thing"}, "без_токена_произвольное_тело"),
        (None, {"nested": {"a": 1}}, "без_токена_вложенное_тело"),
        ({"x-access-token": "invalid_token"}, None, "неверный_токен_без_тела"),
        ({"x-access-token": "invalid_token"}, {}, "неверный_токен_пустое_тело"),
        ({"x-access-token": "invalid_token"}, {"any": "thing"}, "неверный_токен_произвольное_тело"),
        ({"x-access-token": "invalid_token"}, {"login": "test"}, "неверный_токен_login_только"),
        ({"x-access-token": ""}, None, "пустой_токен_без_тела"),
        ({"x-access-token": ""}, {}, "пустой_токен_пустое_тело"),
        ({"x-access-token": "bad.bad.bad"}, None, "формально_похожий_токен_без_тела"),
        ({"x-access-token": "bad.bad.bad"}, {"obj": {}}, "формально_похожий_токен_объект"),
        ({"x-access-token": "invalid_token", "Content-Type": "application/json"}, {"x": 1}, "неверный_токен_с_content_type"),
        (None, {"list": [{"k": "v"}]}, "без_токена_вложенный_список"),
    ],
    ids=lambda v: v[2] if isinstance(v, tuple) else str(v),
)
def test_cancel_download_unauthorized(api_client, api_base_url, attach_curl_on_fail, headers, payload, case_id):
    url = f"{api_base_url}{ENDPOINT}"

    with attach_curl_on_fail(ENDPOINT, payload, headers, "POST"):
        if payload is None:
            response = api_client.post(url, headers=headers)
        else:
            response = api_client.post(url, json=payload, headers=headers)
        assert response.status_code == 401, f"Ожидается 401 Unauthorized; получено {response.status_code}"


# 8) Неверный путь (ошибка в rules/rule)
def test_cancel_download_wrong_path(api_client, auth_token, api_base_url, attach_curl_on_fail):
    wrong_url = f"{api_base_url}{ENDPOINT}".replace("/rules/", "/rule/")
    headers = {"x-access-token": auth_token}

    with attach_curl_on_fail(ENDPOINT, None, headers, "POST"):
        response = api_client.post(wrong_url, headers=headers)
        assert response.status_code == 404, f"Ожидается 404 Not Found; получено {response.status_code}"


# ----- Agent verification test -----
def test_cancel_download_agent_verification(agent_verification, auth_token):
    """
    Отдельный независимый тест для проверки агента.
    
    Проверяет через агента, что операция cancel-download действительно была выполнена в системе.
    Тело запроса к агенту содержит x-access-token как требуется.
    
    Обработка ответов агентов:
    - {"result": "OK"}: успех
    - {"result": "ERROR", "message": "..."}: тест не прошел
    - Агент недоступен: тест падает
    """
    print("Running agent verification test for cancel-download operation")
    
    # Тело запроса к агенту согласно требованиям
    agent_payload = {"x-access-token": auth_token}
    
    # Выполняем проверку через агента
    agent_result = agent_verification("/update/rules/cancel-download", agent_payload, timeout=120)
    
    # Обработка ответов агентов согласно требованиям
    if agent_result == "unavailable":
        pytest.fail("Agent verification unavailable: agent is not reachable for cancel-download operation")
    elif isinstance(agent_result, dict):
        if agent_result.get("result") == "OK":
            print("Agent verification: Cancel download operation was successfully verified")
        elif agent_result.get("result") == "ERROR":
            message = agent_result.get("message", "Unknown error")
            pytest.fail(f"Agent verification failed: Cancel download operation failed with error: {message}")
        else:
            pytest.fail(f"Agent verification: Unexpected result for cancel download operation: {agent_result}")
    else:
        pytest.fail(f"Agent verification: Invalid response format for cancel download operation: {agent_result}")


