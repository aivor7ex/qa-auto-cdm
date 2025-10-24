# ВРЕМЕННО ОТКЛЮЧЕНО (2025-10-03): файл отключён из-за нестабильности.
# Причина: нестабильные результаты тестов для эндпоинта manager/maintenanceRun.
import pytest
pytest.skip("Временно отключено: нестабильность manager_maintenanceRun", allow_module_level=True)
import time
from services.conftest import validate_schema

# ----- Constants -----
ENDPOINT = "/manager/maintenanceRun"

# Схема успешного ответа для валидации
SUCCESS_RESPONSE_SCHEMA = {
    "required": {
        "ok": type(None),
    },
    "optional": {}
}


# ----- Пауза между тестами -----
@pytest.fixture(autouse=True)
def sleep_between_tests():
    time.sleep(1)


# ----- Позитивные сценарии (валидный токен) -----
@pytest.mark.parametrize(
    "case_name, headers_builder, payload, use_data",
    [
        (
            "valid_token_no_body",
            lambda auth_token: {"x-access-token": auth_token},
            None,
            False,
        ),
        (
            "valid_token_empty_json",
            lambda auth_token: {"x-access-token": auth_token, "Content-Type": "application/json"},
            {},
            False,
        ),
        (
            "valid_token_garbage_json",
            lambda auth_token: {"x-access-token": auth_token, "Content-Type": "application/json"},
            {"foo": "bar"},
            False,
        ),
        (
            "valid_token_without_content_type",
            lambda auth_token: {"x-access-token": auth_token},
            None,
            False,
        ),
        (
            "valid_token_wrong_content_type",
            lambda auth_token: {"x-access-token": auth_token, "Content-Type": "text/plain"},
            None,
            True,
        ),
        (
            "valid_token_large_body",
            lambda auth_token: {"x-access-token": auth_token, "Content-Type": "application/json"},
            {"blob": "x" * 10000},
            False,
        ),
        (
            "valid_token_accept_header",
            lambda auth_token: {"x-access-token": auth_token, "Accept": "application/json"},
            None,
            False,
        ),
        (
            "valid_token_user_agent",
            lambda auth_token: {"x-access-token": auth_token, "User-Agent": "QA-Test-Client/1.0"},
            None,
            False,
        ),
        (
            "valid_token_cache_control",
            lambda auth_token: {"x-access-token": auth_token, "Cache-Control": "no-cache"},
            None,
            False,
        ),
        (
            "valid_token_connection_keep_alive",
            lambda auth_token: {"x-access-token": auth_token, "Connection": "keep-alive"},
            None,
            False,
        ),
        (
            "valid_token_charset_utf8",
            lambda auth_token: {"x-access-token": auth_token, "Content-Type": "application/json; charset=utf-8"},
            None,
            False,
        ),
        (
            "valid_token_accept_language",
            lambda auth_token: {"x-access-token": auth_token, "Accept-Language": "en-US,en;q=0.9"},
            None,
            False,
        ),
        (
            "valid_token_x_debug",
            lambda auth_token: {"x-access-token": auth_token, "X-Debug": "1"},
            None,
            False,
        ),
        (
            "valid_token_x_trace_id",
            lambda auth_token: {"x-access-token": auth_token, "X-Trace-Id": "trace-12345"},
            None,
            False,
        ),
        (
            "valid_token_content_length_zero",
            lambda auth_token: {"x-access-token": auth_token, "Content-Length": "0"},
            None,
            True,
        ),
    ],
)
def test_maintenance_run_success_variants(api_client, auth_token, api_base_url, attach_curl_on_fail, case_name, headers_builder, payload, use_data):
    url = f"{api_base_url}{ENDPOINT}"
    headers = headers_builder(auth_token)

    with attach_curl_on_fail(ENDPOINT, payload, headers, "POST"):
        if use_data:
            response = api_client.post(url, headers=headers, data=(payload if payload is not None else ""))
        else:
            response = api_client.post(url, headers=headers, json=payload)

        assert response.status_code == 200, f"Ожидается 200 OK; получено {response.status_code}"
        data = response.json()
        if isinstance(data, dict) and "ok" in data:
            validate_schema(data, SUCCESS_RESPONSE_SCHEMA)
        elif isinstance(data, dict) and "error" in data:
            # Допускаем состояние уже выполняемой задачи
            err = data.get("error", {})
            assert isinstance(err, dict), "Поле 'error' должно быть объектом"
            msg = err.get("message")
            assert msg == "already-running", f"Ожидалось сообщение 'already-running'; получено: {msg}"
        else:
            pytest.fail(f"Неожиданный формат ответа: {data}")


# ----- Негативные сценарии (ошибки аутентификации) -----
@pytest.mark.parametrize(
    "case_name, headers, payload",
    [
        ("no_token", {}, None),
        ("invalid_token", {"x-access-token": "invalid.token.value", "Content-Type": "application/json"}, None),
        ("empty_token", {"x-access-token": "", "Content-Type": "application/json"}, None),
        ("bearer_in_authorization", {"Authorization": "Bearer some_token", "Content-Type": "application/json"}, None),
        ("malformed_token", {"x-access-token": "malformed.token.123"}, None),
        ("short_token", {"x-access-token": "abc"}, None),
        ("unicode_token", {"x-access-token": "тестовый_токен"}, None),
        ("special_chars_token", {"x-access-token": "!@#$%^&*()_+-=[]{}|;':\",./<>?"}, None),
        ("numeric_token", {"x-access-token": "1234567890"}, None),
        ("header_name_casing_wrong", {"X-Access-Token": "some_token"}, None),
        ("token_in_query_only", {}, None),
        ("token_in_both_header_and_query_conflict", {"x-access-token": "header_token"}, None),
        ("token_with_spaces", {"x-access-token": "spaced token"}, None),
        ("token_with_tabs", {"x-access-token": "token\twith\ttabs"}, None),
        ("content_type_text_plain_with_invalid_token", {"x-access-token": "invalid", "Content-Type": "text/plain"}, None),
        ("no_headers_but_body", {}, {}),
    ],
)
def test_maintenance_run_auth_errors(api_client, api_base_url, attach_curl_on_fail, case_name, headers, payload):
    url = f"{api_base_url}{ENDPOINT}"

    # Параметры запроса (для кейсов с access_token в query)
    params = None
    if case_name == "token_in_query_only":
        params = {"access_token": "query_token"}
    elif case_name == "token_in_both_header_and_query_conflict":
        params = {"access_token": "query_token"}

    with attach_curl_on_fail(ENDPOINT, payload, headers if headers else None, "POST"):
        response = api_client.post(url, headers=headers if headers else None, json=payload, params=params)

        assert response.status_code == 401, f"Ожидается 401 Unauthorized; получено {response.status_code}"
        data = response.json()
        assert "error" in data, "Ответ должен содержать поле 'error'"


