import pytest

# ----- Constants -----
ENDPOINT = "/update/rules/apply-from-dir"

# Для 204 No Content успешного ответа тело отсутствует.
# Схема оставляется пустой, так как валидировать нечего при 204.
SUCCESS_RESPONSE_SCHEMA = {
    "required": {},
    "optional": {},
}


# ----- Success variants configuration -----
SUCCESS_VARIANTS = {
    "x_access_token": {
        "headers": lambda token: {"x-access-token": token, "Content-Type": "application/json"},
        "params": lambda token: None,
        "payload": {"versionId": "2025-09-16T12:00:00Z"}
    },
    "query_access_token": {
        "headers": lambda token: {"Content-Type": "application/json"},
        "params": lambda token: {"access_token": token},
        "payload": {"versionId": "2025-09-16T12:00:00Z"}
    },
    "accept_json": {
        "headers": lambda token: {"x-access-token": token, "Content-Type": "application/json", "Accept": "application/json"},
        "params": lambda token: None,
        "payload": {"versionId": "v1-local-test"}
    },
    "accept_any": {
        "headers": lambda token: {"x-access-token": token, "Content-Type": "application/json", "Accept": "*/*"},
        "params": lambda token: None,
        "payload": {"versionId": "v2"}
    },
    "cache_control": {
        "headers": lambda token: {"x-access-token": token, "Content-Type": "application/json", "Cache-Control": "no-cache"},
        "params": lambda token: None,
        "payload": {"versionId": "release-2025"}
    },
    "pragma": {
        "headers": lambda token: {"x-access-token": token, "Content-Type": "application/json", "Pragma": "no-cache"},
        "params": lambda token: None,
        "payload": {"versionId": "rc1"}
    },
    "connection": {
        "headers": lambda token: {"x-access-token": token, "Content-Type": "application/json", "Connection": "keep-alive"},
        "params": lambda token: None,
        "payload": {"versionId": "build-001"}
    },
    "x_debug": {
        "headers": lambda token: {"x-access-token": token, "Content-Type": "application/json", "X-Debug": "1"},
        "params": lambda token: None,
        "payload": {"versionId": "debug"}
    },
    "content_type_charset": {
        "headers": lambda token: {"x-access-token": token, "Content-Type": "application/json; charset=utf-8"},
        "params": lambda token: None,
        "payload": {"versionId": "utf8"}
    },
    "user_agent": {
        "headers": lambda token: {"x-access-token": token, "Content-Type": "application/json", "User-Agent": "QA-Automation-Client/2.0"},
        "params": lambda token: None,
        "payload": {"versionId": "ua"}
    },
    "content_length": {
        "headers": lambda token: {"x-access-token": token, "Content-Type": "application/json", "Content-Length": "20"},
        "params": lambda token: None,
        "payload": {"versionId": "len"}
    },
    "accept_language": {
        "headers": lambda token: {"x-access-token": token, "Content-Type": "application/json", "Accept-Language": "ru-RU"},
        "params": lambda token: None,
        "payload": {"versionId": "ru"}
    },
    "x_trace_id": {
        "headers": lambda token: {"x-access-token": token, "Content-Type": "application/json", "X-Trace-Id": "trace-123"},
        "params": lambda token: None,
        "payload": {"versionId": "trace"}
    },
    "version_numeric_str": {
        "headers": lambda token: {"x-access-token": token, "Content-Type": "application/json"},
        "params": lambda token: None,
        "payload": {"versionId": "1"}
    },
    "version_long": {
        "headers": lambda token: {"x-access-token": token, "Content-Type": "application/json"},
        "params": lambda token: None,
        "payload": {"versionId": "v" * 64}
    }
}

# ----- Успешные кейсы (204) -----
@pytest.mark.parametrize("case_id", list(SUCCESS_VARIANTS.keys()))
def test_apply_from_dir_success_variants(api_client, auth_token, api_base_url, attach_curl_on_fail, case_id):
    url = f"{api_base_url}{ENDPOINT}"
    config = SUCCESS_VARIANTS[case_id]
    headers = config["headers"](auth_token)
    params = config["params"](auth_token)
    payload = config["payload"]

    with attach_curl_on_fail(ENDPOINT, payload, headers, "POST"):
        if params:
            response = api_client.post(url, headers=headers, json=payload, params=params)
        else:
            response = api_client.post(url, headers=headers, json=payload)

        assert response.status_code == 204, (
            f"Ожидается 204 No Content; получено {response.status_code}"
        )


  


# ----- Negative auth variants configuration -----
NEGATIVE_VARIANTS = {
    "без_заголовков_вообще": {
        "headers": lambda token: None,
        "payload": {"versionId": "2025-09-16T12:00:00Z"}
    },
    "content_type_без_авторизации": {
        "headers": lambda token: {"Content-Type": "application/json"},
        "payload": {"versionId": "v1"}
    },
    "пустой_токен": {
        "headers": lambda token: {"x-access-token": "", "Content-Type": "application/json"},
        "payload": {"versionId": "v1"}
    },
    "невалидный_токен": {
        "headers": lambda token: {"x-access-token": "invalid", "Content-Type": "application/json"},
        "payload": {"versionId": "v1"}
    },
    "authorization_bearer_empty": {
        "headers": lambda token: {"Authorization": "Bearer ", "Content-Type": "application/json"},
        "payload": {"versionId": "v1"}
    },
    "authorization_bearer_invalid": {
        "headers": lambda token: {"Authorization": "Bearer invalid", "Content-Type": "application/json"},
        "payload": {"versionId": "v1"}
    },
    "authorization_no_bearer": {
        "headers": lambda token: {"Authorization": "invalid", "Content-Type": "application/json"},
        "payload": {"versionId": "v1"}
    },
    "authorization_bearer_valid_but_rejected": {
        "headers": lambda token: {"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        "payload": {"versionId": "v1"}
    },
    "неверный_заголовок_x_token": {
        "headers": lambda token: {"x-token": "something", "Content-Type": "application/json"},
        "payload": {"versionId": "v1"}
    },
    "accept_без_авторизации": {
        "headers": lambda token: {"Accept": "application/json"},
        "payload": {"versionId": "v1"}
    },
    "cookie_без_авторизации": {
        "headers": lambda token: {"Cookie": "x-access-token=invalid"},
        "payload": {"versionId": "v1"}
    },
    "токен_псевдо_jwt": {
        "headers": lambda token: {"x-access-token": "bad.bad.bad", "Content-Type": "application/json"},
        "payload": {"versionId": "v1"}
    },
    "токен_нули": {
        "headers": lambda token: {"x-access-token": "0000000000", "Content-Type": "application/json"},
        "payload": {"versionId": "v1"}
    },
    "токен_null": {
        "headers": lambda token: {"x-access-token": "null", "Content-Type": "application/json"},
        "payload": {"versionId": "v1"}
    },
    "токен_ноль_строкой": {
        "headers": lambda token: {"x-access-token": "0", "Content-Type": "application/json"},
        "payload": {"versionId": "v1"}
    }
}

# ----- Дополнительные негативные: авторизация (401) до 15 кейсов -----
@pytest.mark.parametrize("case_id", list(NEGATIVE_VARIANTS.keys()))
def test_apply_from_dir_unauthorized_more_variants(api_client, api_base_url, auth_token, attach_curl_on_fail, case_id):
    url = f"{api_base_url}{ENDPOINT}"
    config = NEGATIVE_VARIANTS[case_id]
    built = config["headers"](auth_token)
    payload = config["payload"]

    with attach_curl_on_fail(ENDPOINT, payload, built, "POST"):
        response = api_client.post(url, headers=built, json=payload) if built is not None else api_client.post(url, json=payload)
        assert response.status_code == 401, (
            f"Ожидается 401 Unauthorized; получено {response.status_code}"
        )


  


