import pytest

# ----- Constants -----
ENDPOINT = "/update/rules/apply-download"

# Для 204 No Content успешного ответа тело отсутствует.
# Схема оставляем пустой, так как валидировать нечего при 204.
SUCCESS_RESPONSE_SCHEMA = {
    "required": {},
    "optional": {},
}


def _assert_success_or_rules_not_ready(response):
    """Допускаем 204 (успех) или 422 (правила не скачаны/не готовы)."""
    assert response.status_code in (204, 422), (
        f"Ожидается 204 No Content или 422 Unprocessable Entity; получено {response.status_code}"
    )


# ----- Auth variants configuration -----
AUTH_VARIANTS_CONFIG = {
    "только_x_access_token": {
        "headers": lambda token: {"x-access-token": token},
        "timeout": None
    },
    "токен_и_content_type": {
        "headers": lambda token: {"x-access-token": token, "Content-Type": "application/json"},
        "timeout": None
    },
    "увеличенный_timeout": {
        "headers": lambda token: {"x-access-token": token},
        "timeout": 1800
    }
}

# ----- Authenticated POST variants (from CASES) -----
@pytest.mark.parametrize("case_id", list(AUTH_VARIANTS_CONFIG.keys()))
def test_apply_download_authenticated_variants(api_client, auth_token, api_base_url, attach_curl_on_fail, case_id):
    url = f"{api_base_url}{ENDPOINT}"
    config = AUTH_VARIANTS_CONFIG[case_id]
    resolved_headers = config["headers"](auth_token)

    with attach_curl_on_fail(ENDPOINT, None, resolved_headers, "POST"):
        if config["timeout"] is None:
            response = api_client.post(url, headers=resolved_headers)
        else:
            response = api_client.post(url, headers=resolved_headers, timeout=config["timeout"])

        _assert_success_or_rules_not_ready(response)


# ----- Unauthenticated/invalid auth variants -----
@pytest.mark.parametrize(
    "headers, case_id",
    [
        (None, "без_авторизации_без_тела"),
        ({"Content-Type": "application/json"}, "content_type_без_авторизации"),
        ({"x-access-token": ""}, "пустой_токен"),
        ({"x-access-token": "invalid_token"}, "невалидный_токен"),
    ],
    ids=lambda v: v[1] if isinstance(v, tuple) else str(v),
)
def test_apply_download_unauthorized_variants(api_client, api_base_url, attach_curl_on_fail, headers, case_id):
    url = f"{api_base_url}{ENDPOINT}"

    with attach_curl_on_fail(ENDPOINT, None, headers, "POST"):
        response = api_client.post(url, headers=headers)
        assert response.status_code == 401, (
            f"Ожидается 401 Unauthorized; получено {response.status_code}"
        )


# ----- Alternative auth variants -----
ALT_AUTH_VARIANTS = {
    "оба_заголовка_конфликт": {
        "headers": lambda token: {"x-access-token": token, "Authorization": "Bearer invalid"}
    }
}

# ----- Extra positive variants -----
EXTRA_POSITIVE_VARIANTS = {
    "токен_и_accept_json": {
        "headers": lambda token: {"x-access-token": token, "Accept": "application/json"},
        "timeout": None
    },
    "токен_и_accept_any": {
        "headers": lambda token: {"x-access-token": token, "Accept": "*/*"},
        "timeout": None
    },
    "токен_и_cache_control": {
        "headers": lambda token: {"x-access-token": token, "Cache-Control": "no-cache"},
        "timeout": None
    },
    "токен_и_pragma": {
        "headers": lambda token: {"x-access-token": token, "Pragma": "no-cache"},
        "timeout": None
    },
    "токен_и_connection": {
        "headers": lambda token: {"x-access-token": token, "Connection": "keep-alive"},
        "timeout": None
    },
    "токен_и_x_debug": {
        "headers": lambda token: {"x-access-token": token, "X-Debug": "1"},
        "timeout": None
    },
    "токен_и_text_plain": {
        "headers": lambda token: {"x-access-token": token, "Content-Type": "text/plain"},
        "timeout": None
    },
    "токен_и_charset": {
        "headers": lambda token: {"x-access-token": token, "Content-Type": "application/json; charset=utf-8"},
        "timeout": None
    },
    "токен_и_user_agent": {
        "headers": lambda token: {"x-access-token": token, "User-Agent": "QA-Automation-Client/2.0"},
        "timeout": None
    },
    "токен_и_content_length_0": {
        "headers": lambda token: {"x-access-token": token, "Content-Length": "0"},
        "timeout": None
    },
    "токен_и_accept_language": {
        "headers": lambda token: {"x-access-token": token, "Accept-Language": "ru-RU"},
        "timeout": None
    },
    "оба_заголовка_конфликт_с_токеном": {
        "headers": lambda token: {"x-access-token": token, "Authorization": "Bearer invalid"},
        "timeout": None
    }
}

# ----- Alternative auth header styles from CASES -----
@pytest.mark.parametrize("case_id", list(ALT_AUTH_VARIANTS.keys()))
def test_apply_download_alternative_auth_headers(api_client, auth_token, api_base_url, attach_curl_on_fail, case_id):
    url = f"{api_base_url}{ENDPOINT}"
    config = ALT_AUTH_VARIANTS[case_id]
    resolved_headers = config["headers"](auth_token)

    with attach_curl_on_fail(ENDPOINT, None, resolved_headers, "POST"):
        response = api_client.post(url, headers=resolved_headers)
        _assert_success_or_rules_not_ready(response)


# ----- Extra positives to reach 15 total positive cases -----
@pytest.mark.parametrize("case_id", list(EXTRA_POSITIVE_VARIANTS.keys()))
def test_apply_download_authenticated_more_variants(api_client, auth_token, api_base_url, attach_curl_on_fail, case_id):
    url = f"{api_base_url}{ENDPOINT}"
    config = EXTRA_POSITIVE_VARIANTS[case_id]
    resolved_headers = config["headers"](auth_token)

    with attach_curl_on_fail(ENDPOINT, None, resolved_headers, "POST"):
        if config["timeout"] is None:
            response = api_client.post(url, headers=resolved_headers)
        else:
            response = api_client.post(url, headers=resolved_headers, timeout=config["timeout"])

        _assert_success_or_rules_not_ready(response)


# ----- Extra negatives to reach 15 total negative cases -----
@pytest.mark.parametrize(
    "headers, case_id",
    [
        ({"Authorization": "Bearer "}, "authorization_bearer_empty"),
        ({"Authorization": "Bearer invalid"}, "authorization_bearer_invalid"),
        ({"Authorization": "invalid"}, "authorization_no_bearer"),
        ({"Authorization": "Basic dGVzdDp0ZXN0"}, "authorization_basic"),
        ({"x-access-token": "bad.bad.bad"}, "токен_в_формате_jwt_но_левый"),
        ({"x-access-token": "0000000000"}, "токен_нули"),
        ({"x-access-token": "null"}, "токен_строка_null"),
        ({"x-access-token": "0"}, "токен_ноль_строкой"),
        ({"x-token": "something"}, "неверный_заголовок_x_token"),
        ({"Accept": "application/json"}, "accept_без_авторизации"),
        ({"Cookie": "x-access-token=invalid"}, "cookie_без_авторизации"),
    ],
    ids=lambda v: v[1] if isinstance(v, tuple) else str(v),
)
def test_apply_download_unauthorized_more_variants(api_client, api_base_url, attach_curl_on_fail, headers, case_id):
    url = f"{api_base_url}{ENDPOINT}"

    with attach_curl_on_fail(ENDPOINT, None, headers, "POST"):
        response = api_client.post(url, headers=headers)
        assert response.status_code == 401, (
            f"Ожидается 401 Unauthorized; получено {response.status_code}"
        )


# ----- Explicit negative based on observed behavior -----
def test_apply_download_authorization_bearer_rejected(api_client, auth_token, api_base_url, attach_curl_on_fail):
    url = f"{api_base_url}{ENDPOINT}"
    headers = {"Authorization": f"Bearer {auth_token}"}

    with attach_curl_on_fail(ENDPOINT, None, headers, "POST"):
        response = api_client.post(url, headers=headers)
        assert response.status_code == 401, (
            f"Ожидается 401 Unauthorized для Authorization: Bearer; получено {response.status_code}"
        )


