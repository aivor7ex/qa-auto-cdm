"""
Tests for system-report download API endpoint.
"""
import pytest
import requests
from qa_constants import SERVICES


ENDPOINT = "/system-report/download"

# Schema for successful response (ZIP file download)
SUCCESS_RESPONSE_SCHEMA = {
    "content_type": str,
    "content_disposition": str,
    "content_length": int,
    "binary_data": bytes
}


def test_system_report_download_no_auth_quick(api_client, attach_curl_on_fail):
    """
    Quick test without authentication to verify API is accessible.
    """
    with attach_curl_on_fail(ENDPOINT, method="POST"):
        response = api_client.post(ENDPOINT, timeout=5)
    
    # Should return 401 for missing auth
    assert response.status_code == 401, f"Expected 401, got {response.status_code}"


def test_system_report_download_success(api_client, auth_token, attach_curl_on_fail):
    """
    Test successful system report download (positive case).
    """
    headers = {"x-access-token": auth_token}
    
    with attach_curl_on_fail(ENDPOINT, headers=headers, method="POST"):
        response = api_client.post(ENDPOINT, headers=headers, timeout=60)
    
    # Validate response status
    assert response.status_code == 200, (
        f"Expected status 200, got {response.status_code}. Response: {response.text}"
    )
    
    # Validate content type for ZIP file
    content_type = response.headers.get("content-type", "")
    assert "application/zip" in content_type or "application/octet-stream" in content_type, (
        f"Expected content type to contain 'application/zip' or 'application/octet-stream', "
        f"got '{content_type}'"
    )
    
    # Validate that we received binary data (ZIP file)
    assert len(response.content) > 0, "Response should contain binary data"
    
    # Validate response schema structure
    response_data = {
        "content_type": response.headers.get("content-type", ""),
        "content_disposition": response.headers.get("content-disposition", ""),
        "content_length": len(response.content),
        "binary_data": response.content
    }
    
    # Validate schema types
    for field, expected_type in SUCCESS_RESPONSE_SCHEMA.items():
        assert isinstance(response_data[field], expected_type), (
            f"Field '{field}' should be of type {expected_type.__name__}, "
            f"got {type(response_data[field]).__name__}"
        )




@pytest.mark.parametrize("test_case", [
    {
        "name": "missing_auth_token",
        "description": "Request without authentication token should fail",
        "headers": {"Content-Type": "application/json"},
        "expected_status": 401
    },
    {
        "name": "invalid_auth_token",
        "description": "Request with invalid authentication token should fail",
        "headers": {
            "Content-Type": "application/json",
            "x-access-token": "invalid-token"
        },
        "expected_status": 401
    },
    {
        "name": "empty_auth_token",
        "description": "Request with empty authentication token should fail",
        "headers": {
            "Content-Type": "application/json",
            "x-access-token": ""
        },
        "expected_status": 401
    }
])
def test_system_report_download_auth_errors(api_client, attach_curl_on_fail, test_case):
    """
    Test system report download with authentication errors.
    """
    with attach_curl_on_fail(ENDPOINT, headers=test_case["headers"], method="POST"):
        response = api_client.post(ENDPOINT, headers=test_case["headers"])
    
    # Validate response status
    assert response.status_code == test_case["expected_status"], (
        f"Expected status {test_case['expected_status']}, "
        f"got {response.status_code}. Response: {response.text}"
    )


@pytest.mark.parametrize("test_case", [
    {
        "name": "wrong_http_method_get",
        "description": "GET request should not be allowed",
        "method": "get",
        "expected_status": 404
    },
    {
        "name": "wrong_http_method_put",
        "description": "PUT request should not be allowed",
        "method": "put",
        "expected_status": 404
    },
    {
        "name": "wrong_http_method_delete",
        "description": "DELETE request should not be allowed",
        "method": "delete",
        "expected_status": 404
    }
])
def test_system_report_download_method_not_allowed(api_client, attach_curl_on_fail, test_case):
    """
    Test system report download with wrong HTTP methods.
    """
    # Get the appropriate HTTP method
    method_func = getattr(api_client, test_case["method"])
    
    with attach_curl_on_fail(ENDPOINT, method=test_case["method"].upper()):
        response = method_func(ENDPOINT)
    
    # Validate response status
    assert response.status_code == test_case["expected_status"], (
        f"Expected status {test_case['expected_status']}, "
        f"got {response.status_code}. Response: {response.text}"
    )




# -------------------- Helpers and additional POST-only tests (add-only) --------------------

def _check_types_recursive(obj, schema):
    """Рекурсивно проверяет типы данных по упрощенной схеме."""
    if isinstance(schema, dict) and schema.get("type") == "object":
        assert isinstance(obj, dict), f"Expected object, got {type(obj)}"
        properties = schema.get("properties", {})
        for key, prop_schema in properties.items():
            if key in obj:
                _check_types_recursive(obj[key], prop_schema)
        for req in schema.get("required", []):
            assert req in obj, f"Missing required field: {req}"
        return
    if isinstance(schema, dict) and schema.get("type") == "array":
        assert isinstance(obj, list), f"Expected array, got {type(obj)}"
        item_schema = schema.get("items")
        if item_schema is not None:
            for item in obj:
                _check_types_recursive(item, item_schema)
        return
    # Листовые типы: поддерживаем базовые python-типы
    expected_type = schema if not isinstance(schema, dict) else schema.get("py_type")
    if expected_type is not None:
        assert isinstance(obj, expected_type), f"Expected {expected_type.__name__}, got {type(obj).__name__}"


# Схема метаданных ответа (заголовки и бинарные данные) для POST-скачивания
RESPONSE_META_SCHEMA = {
    "type": "object",
    "properties": {
        "content_type": {"py_type": str},
        "content_disposition": {"py_type": str},
        "content_length": {"py_type": int},
        "binary_data": {"py_type": (bytes, bytearray)},
    },
    "required": ["content_type", "content_length", "binary_data"],
}


@pytest.mark.parametrize(
    "payload, extra_headers",
    [
        pytest.param(None, {}, id="no-body"),
        pytest.param({}, {"Content-Type": "application/json"}, id="empty-json-body"),
        pytest.param({"include_logs": True}, {"Content-Type": "application/json"}, id="include-logs"),
        pytest.param({"format": "zip"}, {"Content-Type": "application/json"}, id="format-zip"),
        pytest.param({"compression": {"level": 6}}, {"Content-Type": "application/json"}, id="compression-level-6"),
        pytest.param({"filters": {"severity": "high"}}, {"Content-Type": "application/json"}, id="filters-severity-high"),
        pytest.param({"metadata": {"request_id": "req-1"}}, {"Content-Type": "application/json"}, id="metadata-request-id"),
        pytest.param({"options": {"pretty": False}}, {"Content-Type": "application/json"}, id="options-pretty-false"),
        pytest.param({}, {"X-Request-ID": "abc-123", "Content-Type": "application/json"}, id="extra-headers"),
        pytest.param({}, {"Content-Type": "application/octet-stream"}, id="octet-stream-request"),
    ],
)
def test_system_report_download_positive_cases(
    api_client,
    api_base_url,
    auth_token,
    attach_curl_on_fail,
    payload,
    extra_headers,
):
    url = f"{api_base_url}{ENDPOINT}"
    headers = {"x-access-token": auth_token}
    headers.update(extra_headers or {})

    with attach_curl_on_fail(ENDPOINT, payload, headers, "POST"):
        if payload is None:
            response = api_client.post(url, headers=headers, timeout=60)
        else:
            # Отправляем JSON, если явный Content-Type application/json; иначе как данные
            if headers.get("Content-Type", "").startswith("application/json"):
                response = api_client.post(url, headers=headers, json=payload, timeout=60)
            else:
                response = api_client.post(url, headers=headers, data=payload, timeout=60)

    assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    # Проверяем заголовки и бинарные данные
    content_type = response.headers.get("content-type", "")
    assert any(x in content_type for x in ["application/zip", "application/octet-stream", "binary"]), (
        f"Unexpected content-type: {content_type}"
    )
    assert len(response.content) > 0, "Empty binary payload"

    response_meta = {
        "content_type": content_type,
        "content_disposition": response.headers.get("content-disposition", ""),
        "content_length": len(response.content),
        "binary_data": response.content,
    }
    _check_types_recursive(response_meta, RESPONSE_META_SCHEMA)


@pytest.mark.parametrize(
    "headers",
    [
        pytest.param({}, id="no-auth"),
        pytest.param({"x-access-token": ""}, id="empty-token"),
        pytest.param({"x-access-token": "invalid_token"}, id="invalid-token"),
        pytest.param({"x-access-token": "expired_token_123"}, id="expired-token"),
        pytest.param({"x-access-token": "malformed.token.value"}, id="malformed-token"),
        pytest.param({"x-access-token": " "+"a"*10}, id="leading-space"),
        pytest.param({"x-access-token": "a"*2048}, id="very-long-token"),
        pytest.param({"x-access-token": "invalid!@#"}, id="special-chars"),
        pytest.param({"x-access-token": "null"}, id="literal-null"),
        pytest.param({"x-access-token": "undefined"}, id="literal-undefined"),
        pytest.param({"x-access-token": "0"}, id="zero-token"),
        pytest.param({"x-access-token": "False"}, id="false-token"),
        pytest.param({"x-access-token": "NaN"}, id="nan-token"),
        pytest.param({"x-access-token": "token with spaces"}, id="spaces-in-token"),
    ],
)
def test_system_report_download_negative_auth_cases(api_client, api_base_url, attach_curl_on_fail, headers):
    url = f"{api_base_url}{ENDPOINT}"
    # Добавляем тип по умолчанию для единообразия, но тело не требуется
    req_headers = {"Content-Type": "application/json"}
    req_headers.update(headers)

    with attach_curl_on_fail(ENDPOINT, None, req_headers, "POST"):
        try:
            response = api_client.post(url, headers=req_headers)
        except requests.exceptions.InvalidHeader:
            # Клиентская библиотека отклонила некорректный заголовок (например, ведущий пробел).
            # Это допустимый отрицательный сценарий аутентификации.
            return

    assert response.status_code == 401, f"Expected 401, got {response.status_code}"
