import pytest

# ----- Constants -----
ENDPOINT = "/update/rules/download-and-apply"
REQUEST_TIMEOUT_SECONDS = 120

# Для 204 No Content успешного ответа тело отсутствует.
# Схема оставляем пустой, так как валидировать нечего при 204.
SUCCESS_RESPONSE_SCHEMA = {
    "required": {},
    "optional": {},
}


def _assert_success_or_rules_not_ready(response):
    """Допускаем 204 (успех) или 422 (правила не готовы/не скачаны)."""
    assert response.status_code in (204, 422), (
        f"Ожидается 204 No Content или 422 Unprocessable Entity; получено {response.status_code}"
    )


def _perform_agent_verification(agent_verification, auth_token):
    """
    Выполняет проверку через агента для update_rules_download-and-apply.
    
    Проверяет по контракту:
    - {"result": "OK"}: успех, правила скачаны и применены
    - {"result": "ERROR", "message": "..."}: ошибка проверки или правила не применены  
    - "unavailable": агент недоступен - тест должен упасть
    
    Args:
        agent_verification: Фикстура для проверки агента
        auth_token: Токен авторизации
        
    Returns:
        None: Проверка пройдена успешно
        
    Raises:
        pytest.fail: Если проверка неуспешна или агент недоступен
    """
    print(f"Starting agent verification for update_rules_download-and-apply")
    
    # Подготавливаем payload для агента
    agent_payload = {
        "x-access-token": auth_token
    }
    
    # Выполняем проверку через агента с увеличенным таймаутом
    agent_result = agent_verification("/update/rules/download-and-apply", agent_payload, timeout=120)
    
    # Обрабатываем ответ агента согласно контракту
    if agent_result == "unavailable":
        pytest.fail(f"Agent verification: AGENT UNAVAILABLE - update_rules_download-and-apply verification failed due to agent unavailability")
    elif isinstance(agent_result, dict) and agent_result.get("result") == "OK":
        print(f"Agent verification: SUCCESS - update_rules_download-and-apply was verified")
    elif isinstance(agent_result, dict) and agent_result.get("result") == "ERROR":
        message = agent_result.get("message", "Unknown error")
        pytest.fail(f"Agent verification: ERROR - update_rules_download-and-apply verification failed: {message}")
    else:
        pytest.fail(f"Agent verification: UNEXPECTED RESULT {agent_result} for update_rules_download-and-apply")


# ----- Auth variants configuration -----
AUTH_VARIANTS_BASIC = {
    "только_x_access_token": lambda token: {"x-access-token": token},
    "токен_и_content_type": lambda token: {"x-access-token": token, "Content-Type": "application/json"}
}

AUTH_VARIANTS_MORE = {
    "токен_и_accept_json": lambda token: {"x-access-token": token, "Accept": "application/json"},
    "токен_и_accept_any": lambda token: {"x-access-token": token, "Accept": "*/*"},
    "токен_и_cache_control": lambda token: {"x-access-token": token, "Cache-Control": "no-cache"},
    "токен_и_pragma": lambda token: {"x-access-token": token, "Pragma": "no-cache"},
    "токен_и_connection": lambda token: {"x-access-token": token, "Connection": "keep-alive"},
    "токен_и_x_debug": lambda token: {"x-access-token": token, "X-Debug": "1"},
    "токен_и_text_plain": lambda token: {"x-access-token": token, "Content-Type": "text/plain"},
    "токен_и_charset": lambda token: {"x-access-token": token, "Content-Type": "application/json; charset=utf-8"},
    "токен_и_user_agent": lambda token: {"x-access-token": token, "User-Agent": "QA-Automation-Client/2.0"},
    "токен_и_content_length_0": lambda token: {"x-access-token": token, "Content-Length": "0"},
    "токен_и_accept_language": lambda token: {"x-access-token": token, "Accept-Language": "ru-RU"}
}

ALT_AUTH_VARIANTS = {
    "authorization_bearer_с_валидным_токеном": lambda token: {"Authorization": f"Bearer {token}"},
    "authorization_bearer_invalid": lambda token: {"Authorization": "Bearer invalid"},
    "оба_заголовка_конфликт": lambda token: {"x-access-token": token, "Authorization": "Bearer invalid"}
}

# 1) Успешные кейсы (аутентифицированные варианты)
@pytest.mark.parametrize("case_id", list(AUTH_VARIANTS_BASIC.keys()))
def test_download_and_apply_authenticated_variants(api_client, auth_token, api_base_url, attach_curl_on_fail, case_id):
    url = f"{api_base_url}{ENDPOINT}"
    resolved_headers = AUTH_VARIANTS_BASIC[case_id](auth_token)

    with attach_curl_on_fail(ENDPOINT, None, resolved_headers, "POST"):
        response = api_client.post(url, headers=resolved_headers, timeout=REQUEST_TIMEOUT_SECONDS)
        _assert_success_or_rules_not_ready(response)


# Дополнительные позитивные кейсы, чтобы суммарно было 15
@pytest.mark.parametrize("case_id", list(AUTH_VARIANTS_MORE.keys()))
def test_download_and_apply_authenticated_more_variants(api_client, auth_token, api_base_url, attach_curl_on_fail, case_id):
    url = f"{api_base_url}{ENDPOINT}"
    resolved_headers = AUTH_VARIANTS_MORE[case_id](auth_token)

    with attach_curl_on_fail(ENDPOINT, None, resolved_headers, "POST"):
        response = api_client.post(url, headers=resolved_headers, timeout=REQUEST_TIMEOUT_SECONDS)
        _assert_success_or_rules_not_ready(response)


# 2) Кейсы с ошибками аутентификации (401 Unauthorized)
@pytest.mark.parametrize(
    "headers, case_id",
    [
        (None, "без_заголовков"),
        ({"Content-Type": "application/json"}, "content_type_без_токена"),
        ({"x-access-token": "invalid"}, "невалидный_токен"),
        ({"x-access-token": ""}, "пустой_токен"),
    ],
    ids=lambda v: v[1] if isinstance(v, tuple) else str(v),
)
def test_download_and_apply_unauthorized_variants(api_client, api_base_url, attach_curl_on_fail, headers, case_id):
    url = f"{api_base_url}{ENDPOINT}"

    with attach_curl_on_fail(ENDPOINT, None, headers, "POST"):
        response = api_client.post(url, headers=headers, timeout=REQUEST_TIMEOUT_SECONDS)
        assert response.status_code == 401, (
            f"Ожидается 401 Unauthorized; получено {response.status_code}"
        )


# Дополнительные негативные кейсы, чтобы суммарно было 15
@pytest.mark.parametrize(
    "headers, case_id",
    [
        ({"Authorization": "Bearer "}, "authorization_bearer_empty"),
        ({"Authorization": "invalid"}, "authorization_no_bearer"),
        ({"Authorization": "Basic dGVzdDp0ZXN0"}, "authorization_basic"),
        ({"x-access-token": "bad.bad.bad"}, "токен_в_формате_jwt_но_левый"),
        ({"x-access-token": "0000000000"}, "токен_нули"),
        ({"x-access-token": "null"}, "токен_строка_null"),
        ({"x-access-token": "0"}, "токен_ноль_строкой"),
        ({"x-token": "something"}, "неверный_заголовок_x_token"),
        ({"Accept": "application/json"}, "accept_без_авторизации"),
    ],
    ids=lambda v: v[1] if isinstance(v, tuple) else str(v),
)
def test_download_and_apply_unauthorized_more_variants(api_client, api_base_url, attach_curl_on_fail, headers, case_id):
    url = f"{api_base_url}{ENDPOINT}"

    with attach_curl_on_fail(ENDPOINT, None, headers, "POST"):
        response = api_client.post(url, headers=headers, timeout=REQUEST_TIMEOUT_SECONDS)
        assert response.status_code == 401, (
            f"Ожидается 401 Unauthorized; получено {response.status_code}"
        )


# 3) Нет версии правил для скачивания — допускаем 422 (или 204 если правила уже готовы)
def test_download_and_apply_rules_may_be_not_ready(api_client, auth_token, api_base_url, attach_curl_on_fail, agent_verification):
    url = f"{api_base_url}{ENDPOINT}"
    headers = {"x-access-token": auth_token}

    with attach_curl_on_fail(ENDPOINT, None, headers, "POST"):
        response = api_client.post(url, headers=headers, timeout=REQUEST_TIMEOUT_SECONDS)
        _assert_success_or_rules_not_ready(response)
        
        # Дополнительная проверка через агента для успешных запросов
        if response.status_code in (204, 422):
            _perform_agent_verification(agent_verification, auth_token)


# 4) Альтернативные стили авторизации, которые должны отклоняться
@pytest.mark.parametrize("case_id", list(ALT_AUTH_VARIANTS.keys()))
def test_download_and_apply_authorization_header_rejected(api_client, auth_token, api_base_url, attach_curl_on_fail, case_id):
    url = f"{api_base_url}{ENDPOINT}"
    resolved = ALT_AUTH_VARIANTS[case_id](auth_token)

    with attach_curl_on_fail(ENDPOINT, None, resolved, "POST"):
        response = api_client.post(url, headers=resolved, timeout=REQUEST_TIMEOUT_SECONDS)
        # Если передан валидный x-access-token вместе с Authorization, сервер обрабатывает по токену
        if resolved.get("x-access-token"):
            _assert_success_or_rules_not_ready(response)
        else:
            assert response.status_code == 401, (
                f"Ожидается 401 Unauthorized для Authorization: Bearer; получено {response.status_code}"
            )


