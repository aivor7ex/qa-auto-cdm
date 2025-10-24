import pytest
import json
import requests
from typing import Any, Dict, Optional

ENDPOINT = "/utils/traceroute"
METHOD = "POST"

# Assumed response schema per API_EXAMPLE_RESPONSE when 200 OK:
# { "pid": 392 }
RESPONSE_SCHEMA_200 = {
    "required": {
        "pid": int,
    },
    "optional": {
    },
}

# Basic helper to validate schema (recursive not required here, but keep consistent)
def validate_schema(data: Any, schema: Dict[str, Dict[str, Any]]):
    assert isinstance(data, dict), f"Response must be an object, got: {type(data)}"
    for key, expected_type in schema.get("required", {}).items():
        assert key in data, f"Missing required key '{key}' in response: {json.dumps(data, ensure_ascii=False, indent=2)}"
        assert isinstance(data[key], expected_type), (
            f"Key '{key}' has type {type(data[key]).__name__}, expected {expected_type.__name__}"
        )
    for key, expected_type in schema.get("optional", {}).items():
        if key in data and data[key] is not None:
            assert isinstance(data[key], expected_type), (
                f"Optional key '{key}' has type {type(data[key]).__name__}, expected {expected_type.__name__}"
            )


# --- Parameter sets ---
# Each case is unique and meaningful per RULE R16
valid_payloads = [
    # Minimal required
    ({"addr": "8.8.8.8"}, 200, "minimal required only"),
    # With source interface
    ({"addr": "8.8.8.8", "source": "eth0"}, 200, "with source interface"),
    # Explicit icmp True
    ({"addr": "1.1.1.1", "icmp": True}, 200, "explicit icmp true"),
    # Explicit icmp False (even if default is true, ensure handling)
    ({"addr": "1.0.0.1", "icmp": False}, 200, "explicit icmp false"),
    # dontFragmentByte True
    ({"addr": "9.9.9.9", "dontFragmentByte": True}, 200, "DF set true"),
    # dontFragmentByte False
    ({"addr": "9.9.9.9", "dontFragmentByte": False}, 200, "DF set false"),
    # attemptsAmount set to 1
    ({"addr": "8.8.4.4", "attemptsAmount": 1}, 200, "attempts 1"),
    # attemptsAmount set to 5
    ({"addr": "208.67.222.222", "attemptsAmount": 5}, 200, "attempts 5"),
    # All options combined (common)
    ({"addr": "8.8.8.8", "source": "eth0", "icmp": True, "dontFragmentByte": False, "attemptsAmount": 5}, 200, "all options typical"),
    # Source with special characters (valid interface name edge)
    ({"addr": "8.8.8.8", "source": "eth0.100"}, 200, "dot in iface"),
    # Hostname instead of IP
    ({"addr": "dns.google"}, 200, "hostname addr"),
]

# Invalid/edge payloads with exact expected status per live API (R23 single-code)
invalid_payloads = [
    ({}, 400, "missing required addr"),
    ({"addr": ""}, 400, "empty addr"),
    ({"addr": None}, 400, "null addr"),
    ({"addr": 123}, 400, "addr wrong type int"),
    ({"addr": True}, 400, "addr wrong type bool"),
    ({"addr": "8.8.8.8", "source": 123}, 400, "source wrong type int"),
    ({"addr": "8.8.8.8", "source": False}, 400, "source wrong type bool"),
    ({"addr": "8.8.8.8", "icmp": "yes"}, 400, "icmp wrong type str"),
    ({"addr": "8.8.8.8", "dontFragmentByte": "no"}, 400, "DF wrong type str"),
    ({"addr": "8.8.8.8", "attemptsAmount": "five"}, 400, "attempts wrong type str"),
    ({"addr": "8.8.8.8", "attemptsAmount": -1}, 200, "attempts negative"),
    ({"addr": "8.8.8.8", "attemptsAmount": 0}, 200, "attempts zero"),
    ({"addr": "8.8.8.8", "attemptsAmount": 1000}, 200, "attempts too large"),
    # Oversized addr string
    ({"addr": "a" * 2048}, 200, "addr too long"),
    # Special characters in addr
    ({"addr": "8.8.8.8; rm -rf /"}, 200, "addr with shell chars"),
    # Unknown extra field is accepted
    ({"addr": "8.8.8.8", "unexpected": "field"}, 200, "unexpected extra field"),
    # Null for optional fields
    ({"addr": "8.8.8.8", "source": None}, 400, "source null"),
    ({"addr": "8.8.8.8", "icmp": None}, 400, "icmp null"),
    ({"addr": "8.8.8.8", "dontFragmentByte": None}, 400, "DF null"),
    ({"addr": "8.8.8.8", "attemptsAmount": None}, 400, "attempts null"),
]

# Raw content-type edge cases (not JSON body); expected status is single-code per live API
raw_edge_cases = [
    ("addr=8.8.8.8", 200, {"Content-Type": "application/x-www-form-urlencoded"}, "form urlencoded"),
    ("addr=8.8.8.8&icmp=true", 200, {"Content-Type": "application/x-www-form-urlencoded"}, "form with icmp"),
    ("{not-json}", 400, {"Content-Type": "application/json"}, "malformed json"),
    ("", 400, {"Content-Type": "application/json"}, "empty body json ct"),
    ("", 400, {"Content-Type": "text/plain"}, "empty body text/plain"),
    ("random text body", 400, {"Content-Type": "text/plain"}, "random text body"),
]


@pytest.mark.parametrize("payload,expected_code,case", valid_payloads, ids=[c for _, _, c in valid_payloads])
def test_post_traceroute_valid_cases(api_client, attach_curl_on_fail, agent_verification, agent_base_url, payload, expected_code, case):
    with attach_curl_on_fail(ENDPOINT, payload, {"Content-Type": "application/json"}, METHOD):
        # Agent verification is disabled per instruction
        # # Positive-only agent verification preface: declare goal and minimal inputs before POST
        # agent_payload = {"addr": payload.get("addr")}
        # if isinstance(payload, dict) and payload.get("source"):
        #     agent_payload["source"] = payload.get("source")
        # print("Цель проверки агента: подтвердить успешный запуск traceroute через агент")
        # print(f"Минимальные входные данные для агента: {json.dumps(agent_payload, ensure_ascii=False)}")

        resp = api_client.post(ENDPOINT, json=payload)
        assert resp.status_code == expected_code, (
            f"Unexpected status for case '{case}'.\n"
            f"Got: {resp.status_code}, Body: {resp.text}"
        )
        # Validate 200 schema
        data = resp.json()
        validate_schema(data, RESPONSE_SCHEMA_200)
        assert data["pid"] is not None and isinstance(data["pid"], int)

        # Agent response handling is disabled per instruction
        # result = agent_verification(ENDPOINT, agent_payload)
        # if result == "unavailable":
        #     pytest.fail("Агент недоступен. Тест не может быть выполнен без проверки через агента.")
        # elif result.get("result") == "OK":
        #     print("Проверка агента: Успех. Продолжаем.")
        # elif result.get("result") == "ERROR":
        #     message = result.get("message", "Неизвестная ошибка")
        #     pytest.fail(f"Проверка агента: {message}")
        # else:
        #     pytest.fail(f"Неожиданный результат проверки агента: {result}")


@pytest.mark.parametrize("payload,expected_code,case", invalid_payloads, ids=[c for _, _, c in invalid_payloads])
def test_post_traceroute_invalid_json_cases(api_client, attach_curl_on_fail, payload, expected_code, case):
    with attach_curl_on_fail(ENDPOINT, payload, {"Content-Type": "application/json"}, METHOD):
        resp = api_client.post(ENDPOINT, json=payload)
        assert resp.status_code == expected_code, (
            f"Unexpected status for invalid case '{case}'.\n"
            f"Got: {resp.status_code}, Body: {resp.text}"
        )
        # Error payload should be JSON object or list; ensure JSON if possible
        ct = resp.headers.get("Content-Type", "")
        if "application/json" in ct:
            err = resp.json()
            assert isinstance(err, (dict, list))


@pytest.mark.parametrize("raw_body,expected_code,headers,case", raw_edge_cases, ids=[c for _, _, _, c in raw_edge_cases])
def test_post_traceroute_raw_edge_cases(api_client, attach_curl_on_fail, raw_body, expected_code, headers, case):
    with attach_curl_on_fail(ENDPOINT, raw_body, headers, METHOD):
        resp = api_client.post(ENDPOINT, data=raw_body, headers=headers)
        assert resp.status_code == expected_code, (
            f"Unexpected status for raw case '{case}'.\n"
            f"Got: {resp.status_code}, Body: {resp.text}"
        )
        ct = resp.headers.get("Content-Type", "")
        if resp.status_code == 200:
            # Some servers might still accept and coerce; validate if so
            assert "application/json" in ct, f"Expected JSON content type for 200, got: {ct}"
            data = resp.json()
            validate_schema(data, RESPONSE_SCHEMA_200)
        else:
            if "application/json" in ct:
                # If error is JSON, ensure it decodes
                _ = resp.json()


# Additional focused success edge cases
additional_success_cases = [
    ({"addr": "example.com", "icmp": True, "dontFragmentByte": True, "attemptsAmount": 2}, 200, "all flags small attempts"),
    ({"addr": "localhost"}, 200, "localhost target"),
    ({"addr": "0.0.0.0"}, 200, "unspecified addr"),
]

@pytest.mark.parametrize("payload,expected_code,case", additional_success_cases, ids=[c for _, _, c in additional_success_cases])
def test_post_traceroute_additional_success(api_client, attach_curl_on_fail, payload, expected_code, case):
    with attach_curl_on_fail(ENDPOINT, payload, {"Content-Type": "application/json"}, METHOD):
        resp = api_client.post(ENDPOINT, json=payload)
        assert resp.status_code == expected_code, (
            f"Unexpected status for case '{case}'.\n"
            f"Got: {resp.status_code}, Body: {resp.text}"
        )
        data = resp.json()
        validate_schema(data, RESPONSE_SCHEMA_200)


# Edge cases with whitespace and unicode in source
unicode_and_whitespace_cases = [
    ({"addr": "8.8.8.8", "source": " eth0 "}, 200, "source with spaces"),
    ({"addr": "8.8.8.8", "source": "интерфейс"}, 200, "unicode iface name"),
]

@pytest.mark.parametrize("payload,expected_code,case", unicode_and_whitespace_cases, ids=[c for _, _, c in unicode_and_whitespace_cases])
def test_post_traceroute_unicode_and_whitespace(api_client, attach_curl_on_fail, payload, expected_code, case):
    with attach_curl_on_fail(ENDPOINT, payload, {"Content-Type": "application/json"}, METHOD):
        resp = api_client.post(ENDPOINT, json=payload)
        assert resp.status_code == expected_code, (
            f"Unexpected status for case '{case}'.\n"
            f"Got: {resp.status_code}, Body: {resp.text}"
        )
        data = resp.json()
        validate_schema(data, RESPONSE_SCHEMA_200)


# Negative boolean coercion cases
boolean_coercion_cases = [
    ({"addr": "8.8.8.8", "icmp": 1}, {400, 422}, "icmp as int 1"),
    ({"addr": "8.8.8.8", "icmp": 0}, {400, 422}, "icmp as int 0"),
    ({"addr": "8.8.8.8", "dontFragmentByte": 1}, {400, 422}, "DF as int 1"),
]

@pytest.mark.parametrize("payload,expected_codes,case", boolean_coercion_cases, ids=[c for _, _, c in boolean_coercion_cases])
def test_post_traceroute_boolean_coercion(api_client, attach_curl_on_fail, payload, expected_codes, case):
    with attach_curl_on_fail(ENDPOINT, payload, {"Content-Type": "application/json"}, METHOD):
        resp = api_client.post(ENDPOINT, json=payload)
        assert resp.status_code in expected_codes, (
            f"Unexpected status for case '{case}'.\n"
            f"Got: {resp.status_code}, Body: {resp.text}"
        )


# Content-Type variations with JSON body
content_type_variations = [
    ({"addr": "8.8.8.8"}, 200, {"Content-Type": "application/json; charset=utf-8"}, "json with charset"),
    ({"addr": "8.8.8.8"}, 400, {"Content-Type": "text/plain"}, "wrong ct text/plain"),
]

@pytest.mark.parametrize("payload,expected_code,headers,case", content_type_variations, ids=[c for _, _, _, c in content_type_variations])
def test_post_traceroute_content_type_variations(api_client, attach_curl_on_fail, payload, expected_code, headers, case):
    with attach_curl_on_fail(ENDPOINT, payload, headers, METHOD):
        resp = api_client.post(ENDPOINT, json=payload, headers=headers)
        assert resp.status_code == expected_code, (
            f"Unexpected status for case '{case}'. Got: {resp.status_code}"
        )
        if expected_code == 200:
            data = resp.json()
            validate_schema(data, RESPONSE_SCHEMA_200)


# Ensure server rejects completely unrelated JSON structure
unrelated_json_cases = [
    ({"foo": "bar"}, 400, "unrelated json object"),
    ({"addr": "8.8.8.8", "nested": {"a": 1}}, 200, "unexpected nested object"),
]

@pytest.mark.parametrize("payload,expected_code,case", unrelated_json_cases, ids=[c for _, _, c in unrelated_json_cases])
def test_post_traceroute_unrelated_json(api_client, attach_curl_on_fail, payload, expected_code, case):
    with attach_curl_on_fail(ENDPOINT, payload, {"Content-Type": "application/json"}, METHOD):
        resp = api_client.post(ENDPOINT, json=payload)
        assert resp.status_code == expected_code, (
            f"Unexpected status for case '{case}'. Got: {resp.status_code}"
        )
        if expected_code == 200:
            data = resp.json()
            validate_schema(data, RESPONSE_SCHEMA_200)
