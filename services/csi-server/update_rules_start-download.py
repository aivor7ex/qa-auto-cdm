import pytest

# ----- Constants -----
ENDPOINT = "/update/rules/start-download"

# Схема успешного ответа: {"ok": 0|1}
# Используется validate_schema из services/conftest.py
SUCCESS_RESPONSE_SCHEMA = {
    "required": {
        "ok": int,
    },
    "optional": {},
}


# ----- Local schema validator (recursive for dict/list if needed) -----
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


# ----- Tests: Authenticated POST variants (body is ignored by API) -----
@pytest.mark.parametrize(
    "payload,case_id",
    [
        (None, "без_тела_запроса"),
        ({"any": "thing"}, "произвольное_тело_игнорируется"),
        ({}, "пустой_объект"),
        ({"unused": True}, "булево_поле"),
        ({"array": []}, "пустой_массив"),
        ({"obj": {}}, "пустой_вложенный_объект"),
        ({"number": 0}, "ноль_в_поле"),
        ({"string": ""}, "пустая_строка"),
        ({"nested": {"a": 1}}, "простая_вложенность"),
        ({"list": [1, 2, 3]}, "список_чисел"),
        ({"null": None}, "null_значение"),
        ({"unicode": "тест"}, "юникод_в_строке"),
        ({"long": "x" * 100}, "длинная_строка"),
        ({"mixed": {"a": [{"b": 2}]}}, "сложная_структура"),
        ({"deep_list": [{"k": "v"}]}, "вложенный_список_объектов"),
    ],
    ids=lambda v: v[1] if isinstance(v, tuple) else str(v),
)
def test_start_download_authenticated_variants(api_client, auth_token, api_base_url, attach_curl_on_fail, payload, case_id):
    url = f"{api_base_url}{ENDPOINT}"
    headers = {"x-access-token": auth_token}

    with attach_curl_on_fail(ENDPOINT, payload, headers, "POST"):
        if payload is None:
            response = api_client.post(url, headers=headers)
        else:
            response = api_client.post(url, json=payload, headers=headers)

        assert response.status_code == 200, f"Ожидается 200 OK; получено {response.status_code}"

        data = response.json()
        _validate_schema_recursive(data, SUCCESS_RESPONSE_SCHEMA)

        # Локальная валидация результата шага
        assert isinstance(data.get("ok"), int), "Поле 'ok' должно быть int"
        print(f"Валидация ответа API прошла, ok={data.get('ok')}. Продолжаем.")


# ----- Tests: Authentication errors (15 negative cases) -----
@pytest.mark.parametrize(
    "headers,payload,case_id",
    [
        (None, None, "без_токена_и_тела"),
        (None, {}, "без_токена_пустое_тело"),
        (None, {"any": "thing"}, "без_токена_произвольное_тело"),
        (None, {"login": "test"}, "без_токена_login_только"),
        ({"x-access-token": "invalid_token"}, None, "неверный_токен_без_тела"),
        ({"x-access-token": "invalid_token"}, {}, "неверный_токен_пустое_тело"),
        ({"x-access-token": "invalid_token"}, {"any": "thing"}, "неверный_токен_произвольное_тело"),
        ({"x-access-token": "invalid_token"}, {"login": "test"}, "неверный_токен_login_только"),
        ({"x-access-token": ""}, None, "пустой_токен_без_тела"),
        ({"x-access-token": ""}, {}, "пустой_токен_пустое_тело"),
        ({"x-access-token": ""}, {"any": "thing"}, "пустой_токен_произвольное_тело"),
        ({"x-access-token": "bad.bad.bad"}, None, "формально_похожий_токен_без_тела"),
        ({"x-access-token": "bad.bad.bad"}, {"obj": {}}, "формально_похожий_токен_объект"),
        ({"x-access-token": "invalid_token", "Content-Type": "application/json"}, {"x": 1}, "неверный_токен_с_content_type"),
        (None, {"nested": {"a": 1}}, "без_токена_вложенное_тело"),
    ],
    ids=lambda v: v[2] if isinstance(v, tuple) else str(v),
)
def test_start_download_unauthorized_variants(api_client, api_base_url, attach_curl_on_fail, headers, payload, case_id):
    url = f"{api_base_url}{ENDPOINT}"

    with attach_curl_on_fail(ENDPOINT, payload, headers, "POST"):
        if payload is None:
            response = api_client.post(url, headers=headers)
        else:
            response = api_client.post(url, json=payload, headers=headers)
        assert response.status_code == 401, f"Ожидается 401 Unauthorized; получено {response.status_code}"


# ----- Independent Agent Verification Test -----
def test_start_download_agent_verification(api_client, auth_token, api_base_url, attach_curl_on_fail, agent_verification):
    """
    Независимый тест проверяет, что после вызова POST /update/rules/start-download
    агент подтверждает успешный старт скачивания правил.
    """
    url = f"{api_base_url}{ENDPOINT}"
    headers = {"x-access-token": auth_token}

    with attach_curl_on_fail(ENDPOINT, None, headers, "POST"):
        response = api_client.post(url, headers=headers)
        assert response.status_code == 200, f"Ожидается 200 OK; получено {response.status_code}"

        data = response.json()
        _validate_schema_recursive(data, SUCCESS_RESPONSE_SCHEMA)
        assert isinstance(data.get("ok"), int), "Поле 'ok' должно быть int"
        print("API шаг валиден. Переходим к проверке агента.")

    # Запрос к агенту выполняется отдельным шагом
    agent_payload = {"x-access-token": auth_token}
    agent_result = agent_verification("/update/rules/start-download", agent_payload, timeout=180)

    # Обработка ответов агента согласно требованиям
    if agent_result == "unavailable":
        pytest.fail("Агент недоступен. Тест проваливается.")
    elif isinstance(agent_result, dict) and agent_result.get("result") == "OK":
        print("Проверка агента: Успешно. Продолжаем.")
    elif isinstance(agent_result, dict) and agent_result.get("result") == "ERROR":
        pytest.fail(f"Проверка агента не прошла: {agent_result.get('message', 'Неизвестная ошибка')}")
    else:
        pytest.fail(f"Неожиданный ответ агента: {agent_result}")


