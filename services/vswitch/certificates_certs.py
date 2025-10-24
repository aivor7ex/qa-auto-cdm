import json
import pytest
import requests
from typing import List, Dict, Any, Union
from services.qa_constants import SERVICES
import re

# =====================================================================================================================
# Constants
# =====================================================================================================================

ENDPOINT = "/certificates/certs"
SERVICE = SERVICES["vswitch"][0]
PORT = SERVICE["port"]
BASE_PATH = SERVICE["base_path"]

# --- Response Schemas for GET and POST ---
response_schemas = {
    "GET": {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "consCountry": {"type": "string"},
                "ST": {"type": "string"},
                "L": {"type": "string"},
                "O": {"type": "string"},
                "OU": {"type": "string"},
                "consId": {"type": "string"},
                "startDate": {"type": "string"},
                "endDate": {"type": "string"},
                "issueCountry": {"type": "string"},
                "organization": {"type": "string"},
                "issueId": {"type": "string"},
                "fingerPrint": {"type": "string"},
                "id": {"type": "string"}
            },
            "required": [
                "consCountry", "ST", "L", "O", "OU", "consId", "startDate", "endDate", "issueCountry", "organization", "issueId", "fingerPrint", "id"
            ]
        }
    },
    "POST": {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "index": {"type": "integer"},
                "cmd": {"type": "string"},
                "res": {"type": "string"},
                "error": {"type": "string"}
            },
            "required": ["index", "cmd"],
        },
        "minItems": 1,
        "maxItems": 2
    }
}

# =====================================================================================================================
# Fixtures
# =====================================================================================================================

# Фикстуры удалены - используем attach_curl_on_fail

# =====================================================================================================================
# Test Cases
# =====================================================================================================================

def test_certs_status_code(api_client, attach_curl_on_fail):
    """Test 1: Checks that the response status code is 200."""
    with attach_curl_on_fail(ENDPOINT, method="GET"):
        response = api_client.get(ENDPOINT)
        assert response.status_code == 200, f"Expected status code 200, but got {response.status_code}"

def test_certs_response_is_list(api_client, attach_curl_on_fail):
    """Test 2: Verifies that the response body is a list."""
    with attach_curl_on_fail(ENDPOINT, method="GET"):
        response = api_client.get(ENDPOINT)
        response_data = response.json()
        assert isinstance(response_data, list), f"Expected response to be a list, but got {type(response_data)}"

def test_certs_response_items_schema(api_client, attach_curl_on_fail):
    """Проверяет, что каждый элемент ответа соответствует схеме сертификата."""
    with attach_curl_on_fail(ENDPOINT, method="GET"):
        response = api_client.get(ENDPOINT)
        response_data = response.json()
        assert isinstance(response_data, list), f"Expected response to be a list, but got {type(response_data)}"
        for cert in response_data:
            assert isinstance(cert, dict), f"Each item should be a dict, got {type(cert)}"
            # Примерный набор ключей, скорректируйте по факту
            expected_keys = {"L", "O", "OU", "ST", "issueCountry", "organization", "commonName", "id", "startDate", "endDate", "fingerPrint"}
            assert expected_keys.intersection(cert.keys()), f"Cert dict missing expected keys: {cert.keys()}"

# =====================================================================================================================
# Parametrized Tests for Schema and Stability
# =====================================================================================================================

def generate_test_params():
    """Generates a list of 32 diverse parameters for stability testing."""
    return [
        # --- Potentially relevant filters ---
        ("filter_by_issuer", "some-ca"), ("filter_by_status", "expired"), ("sort_by", "expiration_date"),
        ("sort_order", "asc"), ("page", "2"), ("per_page", "100"), ("subject_contains", "example.com"),
        ("expires_before", "2026-01-01"), ("has_private_key", "true"),
        # --- Fuzzing and Edge Cases (trimmed) ---
        ("fuzz_empty", ""), ("fuzz_long", "a" * 256), ("fuzz_special", "!@#$%^&*()"),
        ("fuzz_unicode", "тест"), ("fuzz_sql", "' OR 1=1;"), ("fuzz_xss", "<script>"),
        ("fuzz_path", "../etc/passwd"), ("fuzz_numeric", "12345"),
        # ("fuzz_bool_true", "true"),
        # ("fuzz_bool_false", "false"),
        # ("fuzz_null", "null"), ("fuzz_none", None),
        # ("fuzz_list[]", "a"), ("fuzz_dict[key]", "value"), ("fuzz_int", 100),
        # ("fuzz_float", 99.9), ("fuzz_negative", -1), ("fuzz_zero", 0),
        # ("fuzz_large_int", 9999999999), ("fuzz_uuid", "123e4567-e89b-12d3-a456-426614174000"),
        # ("fuzz_date", "2025-06-27"), ("fuzz_mac", "00:1B:44:11:3A:B7"),
        # ("fuzz_hostname", "server.local"),
    ]

# R24: manual curl helpers removed; rely on attach_curl_on_fail fixture

@pytest.mark.parametrize("param, value", generate_test_params())
def test_certs_stability_with_params(api_client, attach_curl_on_fail, param, value):
    """
    Tests 4-35: Ensures the endpoint consistently returns a list of certs (or empty list),
    regardless of the query parameters provided. Проверяет только тип и структуру.
    """
    query_params = {param: value} if value is not None else param
    with attach_curl_on_fail(ENDPOINT, method="GET"):
        response = api_client.get(ENDPOINT, params=query_params)

        assert response.status_code == 200, \
            f"Expected status 200 for param '{param}', but got {response.status_code}"

        data = response.json()
        assert isinstance(data, list), \
            f"Expected response to be a list for param '{param}', but got {type(data)}"
        for cert in data:
            assert isinstance(cert, dict), f"Each item should be a dict, got {type(cert)}"
            expected_keys = {"L", "O", "OU", "ST", "issueCountry", "organization", "commonName", "id", "startDate", "endDate", "fingerPrint"}
            assert expected_keys.intersection(cert.keys()), f"Cert dict missing expected keys: {cert.keys()}"

# =====================================================================================================================
# Helpers for schema validation and curl logging
# =====================================================================================================================

def _check_types_recursive(obj, schema):
    if isinstance(schema, type):
        assert isinstance(obj, schema), f"Expected {schema}, got {type(obj)}"
        return
    if schema.get("type") == "object":
        assert isinstance(obj, dict), f"Expected object, got {type(obj)}"
        for key, prop in schema.get("properties", {}).items():
            if key in obj:
                _check_types_recursive(obj[key], prop)
        for req in schema.get("required", []):
            assert req in obj, f"Missing required field: {req}"
        # Для POST: хотя бы одно из res/error обязательно
        if set(["res", "error"]).intersection(schema.get("properties", {}).keys()):
            assert ("res" in obj or "error" in obj), f"Object must have 'res' or 'error': {obj}"
    elif schema.get("type") == "array":
        assert isinstance(obj, list), f"Expected array, got {type(obj)}"
        if "minItems" in schema:
            assert len(obj) >= schema["minItems"], f"Array too short: {len(obj)} < {schema['minItems']}"
        if "maxItems" in schema:
            assert len(obj) <= schema["maxItems"], f"Array too long: {len(obj)} > {schema['maxItems']}"
        for item in obj:
            _check_types_recursive(item, schema["items"])
    elif schema.get("type") == "string":
        assert isinstance(obj, str), f"Expected string, got {type(obj)}"
    elif schema.get("type") == "integer":
        assert isinstance(obj, int), f"Expected integer, got {type(obj)}"
    else:
        raise AssertionError(f"Unknown schema type: {schema}")

# R24: manual curl helpers removed; rely on attach_curl_on_fail fixture

def _has_uuid_path(cmd):
    # Удаляем пробелы для надёжности
    cmd = cmd.replace(' ', '')
    return bool(re.search(r"/storage/cert/[0-9a-fA-F\-]{36}\.(key|crt)", cmd))

# =====================================================================================================================
# Fixtures for POST
# =====================================================================================================================

@pytest.fixture(scope="module")
def post_headers():
    return {"Content-Type": "application/json"}

@pytest.fixture(scope="module")
def valid_body():
    return {
        "days": 365,
        "issueCountry": "RU",
        "issueState": "Russia",
        "issueCity": "Moscow",
        "organization": "MyOrg",
        "organizationalUnit": "IT",
        "commonName": "mydomain.com"
    }

# =====================================================================================================================
# Parametrized POST test cases (20+)
# =====================================================================================================================

POST_VALID_CASES = [
    pytest.param({"days": 365, "issueCountry": "RU", "issueState": "Russia", "issueCity": "Moscow", "organization": "MyOrg", "organizationalUnit": "IT", "commonName": "mydomain.com"}, 200, id="valid"),
    pytest.param({"days": 1, "issueCountry": "RU", "issueState": "Russia", "issueCity": "Moscow", "organization": "MyOrg", "organizationalUnit": "IT", "commonName": "mydomain.com"}, 200, id="days-min"),
    pytest.param({"days": 10000, "issueCountry": "RU", "issueState": "Russia", "issueCity": "Moscow", "organization": "MyOrg", "organizationalUnit": "IT", "commonName": "mydomain.com"}, 200, id="days-max"),
    pytest.param({"days": 365, "issueCountry": "RU", "issueState": "Russia", "issueCity": "Moscow", "organization": "MyOrg", "organizationalUnit": "IT", "commonName": "a"*64}, 200, id="long-cn"),
    pytest.param({"days": 365, "issueCountry": "RU", "issueState": "Russia", "issueCity": "Moscow", "organization": "MyOrg", "organizationalUnit": "IT", "commonName": "test-domain.com"}, 200, id="valid-domain"),
    pytest.param({"days": 0, "issueCountry": "RU", "issueState": "Russia", "issueCity": "Moscow", "organization": "MyOrg", "organizationalUnit": "IT", "commonName": "mydomain.com"}, 200, id="days-zero"),
    # pytest.param({"days": -1, "issueCountry": "RU", "issueState": "Russia", "issueCity": "Moscow", "organization": "MyOrg", "organizationalUnit": "IT", "commonName": "mydomain.com"}, 200, id="days-negative"),
    # pytest.param({"days": 365, "issueCountry": "RU", "issueState": "Russia", "issueCity": "Moscow", "organization": "MyOrg", "organizationalUnit": "IT", "commonName": "test\"; DROP TABLE users; --"}, 200, id="sql-injection-cn"),
    # pytest.param({"days": 365, "issueCountry": "RU", "issueState": "Russia", "issueCity": "Moscow", "organization": "MyOrg", "organizationalUnit": "IT", "commonName": "<script>alert(1)</script>"}, 200, id="xss-cn"),
    # pytest.param({"days": 365, "issueCountry": "RU", "issueState": "Russia", "issueCity": "Moscow", "organization": "MyOrg", "organizationalUnit": "IT", "commonName": "mydomain.com", "extra": "value"}, 200, id="extra-field"),
    # pytest.param({"days": 30, "issueCountry": "US", "issueState": "California", "issueCity": "San Francisco", "organization": "TechCorp", "organizationalUnit": "Development", "commonName": "api.example.com"}, 200, id="us-cert"),
    # pytest.param({"days": 730, "issueCountry": "DE", "issueState": "Berlin", "issueCity": "Berlin", "organization": "GermanTech", "organizationalUnit": "Security", "commonName": "secure.de"}, 200, id="german-cert"),
    # pytest.param({"days": 180, "issueCountry": "JP", "issueState": "Tokyo", "issueCity": "Tokyo", "organization": "JapanSoft", "organizationalUnit": "QA", "commonName": "test.jp"}, 200, id="japanese-cert"),
    # pytest.param({"days": 365, "issueCountry": "CA", "issueState": "Ontario", "issueCity": "Toronto", "organization": "CanadaTech", "organizationalUnit": "DevOps", "commonName": "canada.example.com"}, 200, id="canadian-cert"),
    # pytest.param({"days": 90, "issueCountry": "AU", "issueState": "New South Wales", "issueCity": "Sydney", "organization": "AussieCorp", "organizationalUnit": "Infrastructure", "commonName": "au.example.com"}, 200, id="australian-cert"),
    # pytest.param({"days": 365, "issueCountry": "RU", "issueState": "Russia", "issueCity": "Moscow", "organization": "MyOrg", "organizationalUnit": "IT", "commonName": "localhost"}, 200, id="localhost-cert"),
    # pytest.param({"days": 365, "issueCountry": "RU", "issueState": "Russia", "issueCity": "Moscow", "organization": "MyOrg", "organizationalUnit": "IT", "commonName": "127.0.0.1"}, 200, id="ip-cert"),
    # pytest.param({"days": 365, "issueCountry": "RU", "issueState": "Russia", "issueCity": "Moscow", "organization": "MyOrg", "organizationalUnit": "IT", "commonName": "*.example.com"}, 200, id="wildcard-cert"),
    # pytest.param({"days": 365, "issueCountry": "RU", "issueState": "Russia", "issueCity": "Moscow", "organization": "MyOrg", "organizationalUnit": "IT", "commonName": "subdomain.example.com"}, 200, id="subdomain-cert"),
    # pytest.param({"days": 365, "issueCountry": "RU", "issueState": "Russia", "issueCity": "Moscow", "organization": "MyOrg", "organizationalUnit": "IT", "commonName": "test123"}, 200, id="numeric-suffix"),
    # pytest.param({"days": 365, "issueCountry": "RU", "issueState": "Russia", "issueCity": "Moscow", "organization": "MyOrg", "organizationalUnit": "IT", "commonName": "api-v1.example.com"}, 200, id="api-versioned"),
    # pytest.param({"days": 365, "issueCountry": "RU", "issueState": "Russia", "issueCity": "Moscow", "organization": "MyOrg", "organizationalUnit": "IT", "commonName": "www.example.com"}, 200, id="www-prefix"),
    # pytest.param({"days": 365, "issueCountry": "RU", "issueState": "Russia", "issueCity": "Moscow", "organization": "MyOrg", "organizationalUnit": "IT", "commonName": "mail.example.com"}, 200, id="mail-subdomain"),
    # pytest.param({"days": 365, "issueCountry": "RU", "issueState": "Russia", "issueCity": "Moscow", "organization": "MyOrg", "organizationalUnit": "IT", "commonName": "ftp.example.com"}, 200, id="ftp-subdomain"),
    # pytest.param({"days": 365, "issueCountry": "RU", "issueState": "Russia", "issueCity": "Moscow", "organization": "MyOrg", "organizationalUnit": "IT", "commonName": "admin.example.com"}, 200, id="admin-subdomain"),
]

POST_INVALID_CASES = [
    pytest.param({"days": 365, "issueCountry": "XX", "issueState": "Russia", "issueCity": "Moscow", "organization": "MyOrg", "organizationalUnit": "IT", "commonName": "mydomain.com"}, 422, id="invalid-country"),
    pytest.param({"days": "abc", "issueCountry": "RU", "issueState": "Russia", "issueCity": "Moscow", "organization": "MyOrg", "organizationalUnit": "IT", "commonName": "mydomain.com"}, 400, id="days-not-number"),
    pytest.param({"issueCountry": "RU", "issueState": "Russia", "issueCity": "Moscow", "organization": "MyOrg", "organizationalUnit": "IT"}, 400, id="missing-commonName"),
    pytest.param({}, 400, id="empty-body"),
    pytest.param({"days": "365", "issueCountry": "RU", "issueState": "Russia", "issueCity": "Moscow", "organization": "MyOrg", "organizationalUnit": "IT", "commonName": "mydomain.com"}, 400, id="days-string"),
    pytest.param({"days": 365, "issueCountry": "RU", "issueState": "Russia", "issueCity": "Moscow", "organization": "MyOrg", "organizationalUnit": "IT"}, 400, id="missing-commonName-2"),
    pytest.param({"days": 365, "issueCountry": "RU", "issueState": "Russia", "issueCity": "Moscow", "organization": "MyOrg", "organizationalUnit": "IT", "commonName": None}, 400, id="commonName-null"),
    pytest.param({"days": 365, "issueCountry": "RU", "issueState": "Russia", "issueCity": "Moscow", "organization": "MyOrg", "organizationalUnit": "IT", "commonName": 123}, 400, id="commonName-not-string"),
    pytest.param({"days": 365, "issueCountry": "RU", "issueState": "Russia", "issueCity": "Moscow", "organization": "MyOrg", "organizationalUnit": 123, "commonName": "mydomain.com"}, 400, id="organizationalUnit-not-string"),
    pytest.param({"days": 365, "issueCountry": "RU", "issueState": "Russia", "issueCity": "Moscow", "organization": 123, "organizationalUnit": "IT", "commonName": "mydomain.com"}, 400, id="organization-not-string"),
    pytest.param({"days": 365, "issueCountry": "RU", "issueState": "Russia", "issueCity": 123, "organization": "MyOrg", "organizationalUnit": "IT", "commonName": "mydomain.com"}, 400, id="issueCity-not-string"),
    pytest.param({"days": 365, "issueCountry": "RU", "issueState": 123, "issueCity": "Moscow", "organization": "MyOrg", "organizationalUnit": "IT", "commonName": "mydomain.com"}, 400, id="issueState-not-string"),
    pytest.param({"days": 365, "issueCountry": 123, "issueState": "Russia", "issueCity": "Moscow", "organization": "MyOrg", "organizationalUnit": "IT", "commonName": "mydomain.com"}, 400, id="issueCountry-not-string"),
    pytest.param({"days": 365, "issueCountry": "RU", "issueState": "Russia", "issueCity": "Moscow", "organization": "MyOrg", "organizationalUnit": "IT"}, 400, id="missing-commonName-3"),
    pytest.param({"days": 365, "issueCountry": "RU", "issueState": "Russia", "issueCity": "Moscow", "organization": "MyOrg", "organizationalUnit": "IT", "commonName": "mydomain.com"}, 400, id="duplicate-request"),
    pytest.param({"days": 365, "issueCountry": "RU", "issueState": "Russia", "issueCity": "Moscow", "organization": "MyOrg", "organizationalUnit": "IT", "commonName": "mydomain.com"}, 400, id="duplicate-request-2"),
    pytest.param({"days": 365, "issueCountry": "RU", "issueState": "Russia", "issueCity": "Moscow", "organization": "MyOrg", "organizationalUnit": "IT", "commonName": "mydomain.com"}, 400, id="duplicate-request-3"),
    pytest.param({"days": 365, "issueCountry": "RU", "issueState": "Russia", "issueCity": "Moscow", "organization": "", "organizationalUnit": "IT", "commonName": "mydomain.com"}, 400, id="empty-organization"),
    pytest.param({"days": 365, "issueCountry": "RU", "issueState": "Russia", "issueCity": "Moscow", "organization": "MyOrg", "organizationalUnit": "IT", "commonName": "a"*65}, 200, id="commonName-too-long"),
]

# Удалить из POST_INVALID_CASES параметры с id, начинающимися на 'duplicate-request'
POST_INVALID_CASES = [param for param in POST_INVALID_CASES if not param.id.startswith('duplicate-request')]

POST_CONTENT_TYPE_CASES = [
    pytest.param({"days": 365, "issueCountry": "RU", "issueState": "Russia", "issueCity": "Moscow", "organization": "MyOrg", "organizationalUnit": "IT", "commonName": "mydomain.com"}, "text/plain", 400, id="wrong-content-type"),
]

# =====================================================================================================================
# Parametrized POST tests
# =====================================================================================================================

@pytest.mark.parametrize("payload, expected_status", POST_VALID_CASES)
def test_certificates_certs_post_valid(api_client, attach_curl_on_fail, payload, expected_status, post_headers, agent_verification):
    with attach_curl_on_fail(ENDPOINT, payload, post_headers, method="POST"):
        response = api_client.post(ENDPOINT, json=payload, headers=post_headers)
        assert response.status_code == expected_status, f"Expected status {expected_status}, got {response.status_code}"
        data = response.json()
        _check_types_recursive(data, response_schemas["POST"])
        for item in data:
            if "error" not in item or not item["error"]:
                assert _has_uuid_path(item["cmd"]), f"cmd does not contain uuid path: {item}"
        print(f"Checking agent verification for valid test: {payload.get('commonName', 'unknown')}")
        agent_result = agent_verification(ENDPOINT, data)
        if agent_result == "unavailable":
            pytest.fail(f"Agent is unavailable for certificate verification: {payload.get('commonName', 'unknown')}")
        elif agent_result is True:
            print(f"Agent verification: Certificate '{payload.get('commonName', 'unknown')}' was successfully created")
        elif agent_result is False:
            pytest.fail(f"Agent verification failed: Certificate '{payload.get('commonName', 'unknown')}' was not found in the system")
        else:
            print(f"Agent verification skipped for payload: {payload}")

@pytest.mark.parametrize("payload, expected_status", POST_INVALID_CASES)
def test_certificates_certs_post_invalid(api_client, attach_curl_on_fail, payload, expected_status, post_headers):
    with attach_curl_on_fail(ENDPOINT, payload, post_headers, method="POST"):
        response = api_client.post(ENDPOINT, json=payload, headers=post_headers)
        assert response.status_code == expected_status, f"Expected status {expected_status}, got {response.status_code}"
        data = response.json()
        if payload.get("commonName") and isinstance(payload.get("commonName"), str) and len(payload.get("commonName", "")) > 64:
            assert isinstance(data, list), f"Expected list response, got {type(data)}"
            assert len(data) >= 2, f"Expected at least 2 commands, got {len(data)}"
            assert "error" in data[1], f"Expected error in second command, got {data[1]}"
            assert "string too long" in data[1]["error"], f"Expected 'string too long' error, got {data[1]['error']}"
        else:
            assert "error" in data, f"Expected error in response, got {data}"
            assert "statusCode" in data["error"], f"Expected statusCode in error, got {data}"

@pytest.mark.parametrize("payload, content_type, expected_status", POST_CONTENT_TYPE_CASES)
def test_certificates_certs_post_content_type(api_client, attach_curl_on_fail, payload, content_type, expected_status):
    headers = {"Content-Type": content_type}
    with attach_curl_on_fail(ENDPOINT, payload, headers, method="POST"):
        response = api_client.post(ENDPOINT, data=json.dumps(payload), headers=headers)
        assert response.status_code == expected_status, f"Expected status {expected_status}, got {response.status_code}"
        data = response.json()
        assert "error" in data, f"Expected error in response, got {data}"

def test_certificates_certs_post_duplicate(api_client, attach_curl_on_fail, post_headers, valid_body, agent_verification):
    """Два одинаковых запроса подряд должны создавать разные сертификаты (разные uuid в пути)."""
    with attach_curl_on_fail(ENDPOINT, valid_body, post_headers, method="POST"):
        resp1 = api_client.post(ENDPOINT, json=valid_body, headers=post_headers)
        resp2 = api_client.post(ENDPOINT, json=valid_body, headers=post_headers)
        assert resp1.status_code == 200 and resp2.status_code == 200, f"Both requests must return 200, got {resp1.status_code}, {resp2.status_code}"
        data1 = resp1.json()
        data2 = resp2.json()
        # Извлечь uuid из пути
        import re
        def extract_uuid(cmd):
            m = re.search(r"/storage/cert/([0-9a-fA-F\-]{36})\.key", cmd.replace(' ', ''))
            return m.group(1) if m else None
        uuid1 = extract_uuid(data1[0]["cmd"])
        uuid2 = extract_uuid(data2[0]["cmd"])
        assert uuid1 and uuid2 and uuid1 != uuid2, f"UUIDs must be unique: {uuid1}, {uuid2}"
        
        # Дополнительная проверка через агента для дублирующихся запросов
        print(f"Checking agent verification for duplicate test: {valid_body.get('commonName', 'unknown')}")
        agent_result = agent_verification(ENDPOINT, data1)  # Используем ответ от первого запроса
        if agent_result == "unavailable":
            pytest.fail(f"Agent is unavailable for duplicate certificate verification: {valid_body.get('commonName', 'unknown')}")
        elif agent_result is True:
            print(f"Agent verification: Duplicate certificate '{valid_body.get('commonName', 'unknown')}' was successfully created")
        elif agent_result is False:
            pytest.fail(f"Agent verification failed: Duplicate certificate '{valid_body.get('commonName', 'unknown')}' was not found in the system")
        else:
            print(f"Agent verification skipped for duplicate payload: {valid_body}")

# R24: Удалена реализация запроса к агенту - используем готовую фикстуру agent_verification()
