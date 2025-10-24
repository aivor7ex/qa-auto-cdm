import pytest
import requests
import json
from urllib.parse import quote

ENDPOINT = "/vlanInfos/{id}/exists"
SERVICE_NAME = "core"

RESPONSE_SCHEMA = {
    "required": {"exists": bool},
    "optional": {}
}

def format_curl_command(method, url, headers=None, body=None):
    """Многострочная cURL-инструкция строго по шаблону."""
    lines = [f"curl -X {method} '{url}'"]
    if headers:
        for k, v in headers.items():
            lines.append(f"  -H '{k}: {v}'")
    if body:
        body_str = body
        if isinstance(body, bytes):
            body_str = body.decode('utf-8', errors='replace')
        # Пытаемся красиво отформатировать как JSON
        try:
            pretty = json.dumps(json.loads(body_str), ensure_ascii=False, indent=2)
            lines.append(f"  -d '{pretty}'")
        except Exception:
            lines.append(f"  -d '{body_str}'")
    return (
        "================= Failed Test Request (cURL) ================\n"
        + " \\\n".join(lines) +
        "\n============================================================="
    )

def validate_response_schema(response: requests.Response, schema: dict):
    """Проверяет JSON-ответ согласно простой схеме."""
    curl_command = format_curl_command(
        response.request.method,
        response.request.url,
        response.request.headers,
        response.request.body
    )
    try:
        data = response.json()
    except json.JSONDecodeError as e:
        print(curl_command)
        pytest.fail(
            f"Response is not valid JSON.\n"
            f"Status: {response.status_code}\n"
            f"Content: {response.text}",
            pytrace=False
        )
    for key, expected_type in schema.get("required", {}).items():
        if key not in data:
            print(curl_command)
            pytest.fail(f"Required key '{key}' is missing from response.", pytrace=False)
        actual_type = type(data[key])
        if actual_type is not expected_type:
            print(curl_command)
            pytest.fail(
                f"Key '{key}' has type '{actual_type.__name__}', but expected '{expected_type.__name__}'.",
                pytrace=False
            )

@pytest.fixture(scope="module")
def vlan_ids(api_client):
    """Получить все доступные VLAN ID из /vlanInfos."""
    response = api_client.get("/vlanInfos")
    if response.status_code != 200:
        pytest.skip(f"Could not retrieve VLANs from /vlanInfos. Status code: {response.status_code}")
    try:
        data = response.json()
        if not data:
            pytest.skip("No VLANs found in /vlanInfos.")
    except json.JSONDecodeError:
        pytest.skip("Response from /vlanInfos was not valid JSON.")
    ids = [item['vlanId'] for item in data if isinstance(item, dict) and 'vlanId' in item]
    if not ids:
        pytest.skip("No 'vlanId' found in items from /vlanInfos.")
    return ids

class TestVlanExists:
    """Тесты для GET /vlanInfos/{id}/exists"""

    def test_existing_vlan_returns_true(self, api_client, vlan_ids):
        """Позитив: endpoint возвращает exists: true для всех актуальных VLAN ID."""
        for vlan_id in vlan_ids:
            url = ENDPOINT.format(id=quote(str(vlan_id)))
            response = api_client.get(url)
            if response.status_code != 200:
                print(format_curl_command(
                    response.request.method,
                    response.request.url,
                    response.request.headers,
                    response.request.body
                ))
                pytest.fail(
                    f"Expected status 200, but got {response.status_code} for VLAN ID {vlan_id}.",
                    pytrace=False
                )
            try:
                validate_response_schema(response, RESPONSE_SCHEMA)
            except Exception:
                # validate_response_schema уже печатает cURL, здесь повторно не нужно
                raise
            data = response.json()
            if data.get("exists") is not True:
                print(format_curl_command(
                    response.request.method,
                    response.request.url,
                    response.request.headers,
                    response.request.body
                ))
                pytest.fail(
                    f"Expected 'exists' to be true for VLAN ID {vlan_id}.",
                    pytrace=False
                )

    @pytest.mark.parametrize("vlan_id, description", [
        (999999, "Non-existent numeric ID"),
        (99999999999999999, "Very large non-existent numeric ID"),
        (-1, "Negative ID"),
        (-99999, "Large negative ID"),
        ("abc", "String ID"),
        ("null", "String 'null' as ID"),
        ("undefined", "String 'undefined' as ID"),
        ("!@#$%^&*()", "Special characters as ID"),
        ("1.5", "Float string as ID"),
        ("../etc/passwd", "Path traversal attempt"),
        ("' OR 1=1; --", "Simple SQL injection attempt"),
        ("", "Empty string ID"),
        (" leading_space", "ID with leading space"),
        ("trailing_space ", "ID with trailing space"),
        ("✅", "Unicode emoji as ID"),
        ("é", "Unicode accented character as ID"),
        ("中国", "Unicode multi-byte characters as ID"),
        ("1,000", "ID with comma"),
        ("1_000", "ID with underscore"),
        ("0xFF", "Hex string as ID"),
        ("0o10", "Octal string as ID"),
        (1_000_000_000_000, "Integer with underscores"),
        (None, "None as ID"),
        ('ф', "Cyrillic character 'ф'"),
        ('Ѿ', "Cyrillic character 'Ѿ'"),
        ('☺', "Smiley face unicode"),
        ('a' * 1024, "Long string ID (1024 chars)"),
        ('{}', "JSON object as string ID"),
        ('[]', "JSON array as string ID"),
        ('%', "Percent character as ID"),
        ('&', "Ampersand character as ID"),
        ('?', "Question mark character as ID"),
        ('=', "Equals sign character as ID"),
        (';', "Semicolon character as ID"),
        ('`', "Backtick character as ID"),
        ('\\', "Backslash character as ID"),
        ('1.0.0', "Version-like string ID"),
        ('very_long_string_with_underscores_and_numbers_12345', "Long underscore string"),
        ('string-with-hyphens', "String with hyphens"),
        ('!@#$%^&*()_+-=[]{}|;:\",./<>?`~', "Kitchen sink of special chars")
    ])
    def test_non_existent_and_invalid_vlan_returns_false(self, api_client, vlan_id, description):
        """Для несуществующих/невалидных VLAN endpoint возвращает либо exists: false, либо 400/404."""
        url = ENDPOINT.format(id=quote(str(vlan_id)))
        response = api_client.get(url)
        curl = format_curl_command(
            response.request.method,
            response.request.url,
            response.request.headers,
            response.request.body
        )
        if response.status_code == 200:
            try:
                validate_response_schema(response, RESPONSE_SCHEMA)
                data = response.json()
            except Exception:
                # validate_response_schema уже печатает cURL
                raise
            if data.get("exists") is not False:
                print(curl)
                pytest.fail(
                    f"Expected 'exists' to be false for case '{description}' (ID: {vlan_id}) when status is 200.",
                    pytrace=False
                )
        elif response.status_code in [400, 404]:
            # Acceptable outcomes for non-existent/invalid ID
            pass
        else:
            print(curl)
            pytest.fail(
                f"Expected status 200, 400, or 404 for case '{description}', but got {response.status_code}.",
                pytrace=False
            )
