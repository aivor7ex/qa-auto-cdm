"""
Тесты для эндпоинта /security-settings сервиса csi-server.

Проверяется:
- Статус-код 200 OK
- Соответствие структуры ответа схеме (объект security settings)
- Устойчивость к 35+ различным query-параметрам
- Вывод cURL-команды при ошибке в параметризованных тестах
"""
import pytest
import json
from collections.abc import Mapping, Sequence

ENDPOINT = "/security-settings"

PARAMS = [
    pytest.param({}, 200, id="P01: no_params"),
    pytest.param({"format": "json"}, 200, id="P02: format_json"),
    pytest.param({"pretty": "true"}, 200, id="P03: pretty_true"),
    pytest.param({"pretty": "false"}, 200, id="P04: pretty_false"),
    pytest.param({"indent": "2"}, 200, id="P05: indent_2"),
    pytest.param({"indent": "4"}, 200, id="P06: indent_4"),
    pytest.param({"fields": "bad_auth_decay_s"}, 200, id="P07: fields_bad_auth_decay"),
    pytest.param({"fields": "block_time_s"}, 200, id="P08: fields_block_time"),
    pytest.param({"fields": "max_bad_auth_attempts"}, 200, id="P09: fields_max_attempts"),
    pytest.param({"fields": "bad_auth_decay_s,block_time_s"}, 200, id="P10: fields_multiple"),
    pytest.param({"expand": "details"}, 200, id="P11: expand_details"),
    pytest.param({"expand": "stats"}, 200, id="P12: expand_stats"),
    pytest.param({"expand": "details,stats"}, 200, id="P13: expand_multiple"),
    pytest.param({"include": "details"}, 200, id="P14: include_details"),
    pytest.param({"include": "stats"}, 200, id="P15: include_stats"),
    pytest.param({"include": "details,stats"}, 200, id="P16: include_multiple"),
]


def _check_types_recursive(obj, schema):
    """Рекурсивно проверяет типы данных в объекте на соответствие схеме."""
    if "anyOf" in schema:
        assert any(_try_type(obj, s) for s in schema["anyOf"]), f"Тип {type(obj)} не соответствует ни одной из схем в anyOf"
        return

    schema_type = schema.get("type")
    if schema_type == "object":
        assert isinstance(obj, Mapping), f"Ожидался объект (dict), получено: {type(obj).__name__}"
        for key, prop_schema in schema.get("properties", {}).items():
            if key in obj:
                _check_types_recursive(obj[key], prop_schema)
        for required_key in schema.get("required", []):
            assert required_key in obj, f"Обязательное поле '{required_key}' отсутствует в объекте"
    elif schema_type == "array":
        assert isinstance(obj, Sequence) and not isinstance(obj, str), f"Ожидался список (list/tuple), получено: {type(obj).__name__}"
        for item in obj:
            _check_types_recursive(item, schema["items"])
    elif schema_type == "string":
        assert isinstance(obj, str), f"Поле должно быть строкой (string), получено: {type(obj).__name__}"
    elif schema_type == "integer":
        assert isinstance(obj, int), f"Поле должно быть целым числом (integer), получено: {type(obj).__name__}"
    elif schema_type == "boolean":
        assert isinstance(obj, bool), f"Поле должно быть булевым (boolean), получено: {type(obj).__name__}"
    elif schema_type == "null":
        assert obj is None, "Поле должно быть null"


def _try_type(obj, schema):
    """Вспомогательная функция для проверки типа в 'anyOf'."""
    try:
        _check_types_recursive(obj, schema)
        return True
    except AssertionError:
        return False


# ----- ОБЪЕДИНЕННЫЕ СХЕМЫ ОТВЕТА ДЛЯ GET И POST МЕТОДОВ -----
response_schemas = {
    "GET": {
        "type": "object",
        "properties": {
            "bad_auth_decay_s": {"type": "integer"},
            "block_time_s": {"type": "integer"},
            "max_bad_auth_attempts": {"type": "integer"}
        }
    },
    "POST": {
        "type": "object",
        "properties": {
            "bad_auth_decay_s": {"type": "integer"},
            "block_time_s": {"type": "integer"},
            "max_bad_auth_attempts": {"type": "integer"}
        }
        # POST может возвращать только изменённые поля или пустой объект {}
    }
}

def _validate_response_schema(data, method):
    schema = response_schemas.get(method)
    assert schema is not None, f"Схема для метода {method} не найдена"
    _check_types_recursive(data, schema)

@pytest.mark.parametrize("params, expected_status", PARAMS)
def test_security_settings_parametrized(api_client, auth_token, api_base_url, params, expected_status, attach_curl_on_fail):
    """
    Основной параметризованный тест для эндпоинта /security-settings.
    """
    headers = {
        'x-access-token': auth_token,
        'token': auth_token
    }
    url = f"{api_base_url}{ENDPOINT}"

    with attach_curl_on_fail(ENDPOINT, params, headers, "GET"):
        response = api_client.get(url, params=params, headers=headers, timeout=10)

        assert response.status_code == expected_status, \
            f"Ожидался статус-код {expected_status}, получен {response.status_code}. Ответ: {response.text}"

        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, dict), f"Тело ответа не является объектом JSON, получено: {type(data).__name__}"
            _validate_response_schema(data, "GET")


# ----------------------------- POST TESTS -----------------------------

@pytest.mark.parametrize(
    "payload, expected_status, case_id",
    [
        ({"max_bad_auth_attempts": 5, "bad_auth_decay_s": 300, "block_time_s": 600}, 200, "valid_all_three"),
        ({"max_bad_auth_attempts": 3}, 200, "valid_only_max_bad_auth_attempts"),
        ({"bad_auth_decay_s": 120}, 200, "valid_only_bad_auth_decay_s"),
        ({"block_time_s": 900}, 200, "valid_only_block_time_s"),
        ({"max_bad_auth_attempts": 5, "bad_auth_decay_s": 300}, 200, "valid_two_fields_attempts_decay"),
        ({"max_bad_auth_attempts": 5, "block_time_s": 600}, 200, "valid_two_fields_attempts_block"),
        ({"bad_auth_decay_s": 300, "block_time_s": 600}, 200, "valid_two_fields_decay_block"),
        ({}, 200, "valid_empty_body"),
        ({"foo": 1, "max_bad_auth_attempts": 5}, 200, "valid_extra_unknown_field"),
        ({"max_bad_auth_attempts": 1, "bad_auth_decay_s": 1, "block_time_s": 1}, 200, "valid_min_values"),
        ({"max_bad_auth_attempts": 10}, 200, "valid_only_max_10"),
        ({"bad_auth_decay_s": 86400}, 200, "valid_only_decay_86400"),
        ({"block_time_s": 3600}, 200, "valid_only_block_3600"),
        ({"max_bad_auth_attempts": 2, "bad_auth_decay_s": 60, "block_time_s": 120, "extra": "ignored"}, 200, "valid_all_three_with_extra"),
        ({"max_bad_auth_attempts": 4, "bad_auth_decay_s": 300, "foo": 0}, 200, "valid_two_fields_with_unknown"),
    ],
    ids=lambda x: x if isinstance(x, str) else None,
)
def test_post_security_settings_valid_cases(api_client, auth_token, api_base_url, payload, expected_status, case_id, attach_curl_on_fail, agent_verification):
    url = f"{api_base_url}{ENDPOINT}"
    headers = {"x-access-token": auth_token, "Content-Type": "application/json"}

    with attach_curl_on_fail(ENDPOINT, payload, headers, "POST"):
        response = api_client.post(url, json=payload, headers=headers)
        assert response.status_code == expected_status, f"Ожидается {expected_status}; получено {response.status_code}"

        # Шаг 1: валидация ответа API для позитивных кейсов
        if expected_status == 200:
            data = response.json()
            _validate_response_schema(data, "POST")
            print("Валидация схемы ответа API: OK — продолжаем к проверке агента")

            # Шаг 2: дополнительная проверка через агента
            # Агенту отправляем ТЕЛО ОТВЕТА основного API (а не исходный payload)
            agent_payload = data if isinstance(data, dict) else {}
            agent_result = agent_verification("/security-settings", agent_payload)

            # Шаг 3: обработка ответов агента по контракту
            if agent_result == "unavailable":
                # Агент недоступен — тест должен падать, не пропускаем
                pytest.fail("Агент недоступен. Тест в данном случае проваливается. Не пропускать тест, если агент недоступен.")
            elif isinstance(agent_result, dict):
                result_value = agent_result.get("result")
                if result_value == "OK":
                    print("Проверка агента: OK — продолжаем")
                elif result_value == "ERROR":
                    message = agent_result.get("message", "Неизвестная ошибка")
                    pytest.fail(f"Проверка агента: ERROR — {message}")
                else:
                    pytest.fail(f"Проверка агента: неожиданный ответ — {agent_result}")
            else:
                pytest.fail(f"Проверка агента: неожиданный формат ответа — {agent_result}")


@pytest.mark.parametrize(
    "payload, expected_status, case_id",
    [
        ({"max_bad_auth_attempts": "5"}, 400, "invalid_string_instead_of_number"),
        ({"bad_auth_decay_s": 0}, 400, "invalid_zero"),
        ({"block_time_s": -1}, 400, "invalid_negative"),
        ({"max_bad_auth_attempts": 5.5}, 400, "invalid_float"),
        ({"bad_auth_decay_s": None}, 400, "invalid_null"),
        ({"max_bad_auth_attempts": 5, "block_time_s": "600"}, 400, "invalid_mixed_valid_and_invalid"),
        ({"max_bad_auth_attempts": 0}, 400, "invalid_max_zero"),
        ({"max_bad_auth_attempts": -5}, 400, "invalid_max_negative"),
        ({"bad_auth_decay_s": -10}, 400, "invalid_decay_negative"),
        ({"bad_auth_decay_s": 5.5}, 400, "invalid_decay_float"),
        ({"block_time_s": 0}, 400, "invalid_block_zero"),
        ({"block_time_s": 1.1}, 400, "invalid_block_float"),
        ({"max_bad_auth_attempts": None}, 400, "invalid_max_null"),
        ({"block_time_s": "900"}, 400, "invalid_block_string"),
        ({"bad_auth_decay_s": "300"}, 400, "invalid_decay_string"),
    ],
    ids=lambda x: x if isinstance(x, str) else None,
)
def test_post_security_settings_invalid_cases(api_client, auth_token, api_base_url, payload, expected_status, case_id, attach_curl_on_fail):
    url = f"{api_base_url}{ENDPOINT}"
    headers = {"x-access-token": auth_token, "Content-Type": "application/json"}

    with attach_curl_on_fail(ENDPOINT, payload, headers, "POST"):
        response = api_client.post(url, json=payload, headers=headers)
        assert response.status_code == expected_status, f"Ожидается {expected_status}; получено {response.status_code}"


@pytest.mark.parametrize(
    "payload, headers, expected_status, case_id",
    [
        ({"max_bad_auth_attempts": 5}, {"Content-Type": "application/json"}, 401, "no_token"),
        ({"token": "wrong", "max_bad_auth_attempts": 5}, {"Content-Type": "application/json"}, 401, "unknown_token_field"),
        # auth via query param
        ({"max_bad_auth_attempts": 5, "bad_auth_decay_s": 300, "block_time_s": 600}, {"x-access-token": None, "Content-Type": "application/json"}, 200, "auth_query_param"),
        # auth via body access_token
        ({"access_token": None, "max_bad_auth_attempts": 5, "bad_auth_decay_s": 300, "block_time_s": 600}, {"Content-Type": "application/json"}, 200, "auth_body_field"),
    ],
    ids=lambda x: x if isinstance(x, str) else None,
)
def test_post_security_settings_auth_cases(api_client, auth_token, api_base_url, payload, headers, expected_status, case_id, attach_curl_on_fail):
    # Fill dynamic auth placements
    params = {}
    if case_id == "auth_query_param":
        params = {"access_token": auth_token}
    if case_id == "auth_body_field":
        payload["access_token"] = auth_token

    # Build headers without hardcoding token unless explicitly needed
    final_headers = dict(headers)
    if final_headers.get("x-access-token") is None and case_id not in ("no_token", "unknown_token_field"):
        final_headers.pop("x-access-token", None)
    if case_id not in ("no_token", "unknown_token_field") and final_headers.get("x-access-token"):
        final_headers["x-access-token"] = auth_token

    url = f"{api_base_url}{ENDPOINT}"

    with attach_curl_on_fail(ENDPOINT, payload if payload else None, final_headers if final_headers else None, "POST"):
        response = api_client.post(url, json=payload, headers=final_headers, params=params)
        assert response.status_code == expected_status, f"Ожидается {expected_status}; получено {response.status_code}"
