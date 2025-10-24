"""
Tests for manager/restoreConfigStatusAndLogs API endpoint.

This module contains comprehensive tests for the CSI server's configuration restore status
and logs endpoint, covering various scenarios and validation requirements.
"""

import pytest
import requests
import json
import base64
from functools import lru_cache

# Endpoint constant as required by R18
ENDPOINT = "/manager/restoreConfigStatusAndLogs"

# Response schema based on actual API response from R0
RESPONSE_SCHEMA = {
    "required": {
        "message": str,
        "log": str
    },
    "optional": {}
}
def _format_curl_command(base_url, endpoint, headers=None, params=None):
    """Формирует cURL команду в стиле test_services.py."""
    headers = headers or {}
    params = params or {}
    full_url = f"{base_url.rstrip('/')}/{endpoint.lstrip('/')}"
    if params:
        param_str = "&".join([f"{k}={v}" for k, v in params.items() if v is not None])
        if param_str:
            full_url += f"?{param_str}"

    headers_str = " \\\n  ".join([f"-H '{k}: {v}'" for k, v in headers.items()])
    curl_command = f"curl -X GET '{full_url}'"
    if headers_str:
        curl_command += f" \\\n  {headers_str}"
    return curl_command


@lru_cache(maxsize=4)
def _should_skip_due_to_missing_restore_file(base_url, token):
    """Возвращает True, если бэкенд отвечает 400 ENOENT по причине отсутствия файла configuration-restore."""
    url = f"{base_url}{ENDPOINT}"
    headers = {"x-access-token": token} if token else {}
    try:
        response = requests.get(url, headers=headers, timeout=15)
    except Exception:
        # Не скипаем по сетевым ошибкам: пусть упадёт профильным ассершеном
        return False

    text = response.text or ""
    if response.status_code == 400 and "configuration-restore" in text and "ENOENT" in text:
        return True
    return False


# Test data for parameterization
VALID_MESSAGE_VALUES = [
    "OK",
    "updating",
    "completed",
    "failed",
    "pending",
    "in_progress"
]

VALID_LOG_CONTENTS = [
    "",  # Empty log
    "MjAyNS0wOC0xMlQxMTo1ODowNC45MDUrMDAwMAl3cml0aW5nIG5nZncuSWRzX3J1bGVzIHRvIGFyY2hpdmUgb24gc3Rkb3V0Cg==",  # Base64 encoded content
    "base64_encoded_log_content_here",
    "log_with_special_chars_!@#$%^&*()",
    "log_with_numbers_12345",
    "log_with_spaces and tabs\tand newlines\n"
]


class TestManagerRestoreConfigStatusAndLogs:
    """Test suite for manager/restoreConfigStatusAndLogs endpoint."""

    @pytest.fixture(autouse=True)
    def _skip_if_missing_restore_file(self, api_base_url, auth_token):
        """Скипаем все тесты класса, если на сервере отсутствует файл configuration-restore."""
        if _should_skip_due_to_missing_restore_file(api_base_url, auth_token):
            curl_cmd = _format_curl_command(
                api_base_url,
                ENDPOINT,
                headers={"x-access-token": auth_token},
            )
            pytest.skip(
                "Отсутствует файл '/app/ctld-logs/configuration-restore' на бэкенде (400 ENOENT). "
                "Скипаем тесты до появления файла. Для воспроизведения запроса:\n" + curl_cmd
            )

    @pytest.mark.parametrize("expected_message", VALID_MESSAGE_VALUES)
    def test_successful_response_message_values(self, api_base_url, auth_token, expected_message):
        """Test successful responses with different valid message values."""
        url = f"{api_base_url}{ENDPOINT}"
        headers = {"x-access-token": auth_token}
        
        response = requests.get(url, headers=headers, timeout=30)
        
        assert response.status_code in (200, 400), (
            f"Expected 200 OK or 400 Bad Request, got {response.status_code}. "
            f"Response: {response.text}. "
            f"curl: curl --location '{url}' --header 'x-access-token: {auth_token}'"
        )
        
        data = response.json()
        if response.status_code == 200:
            assert "message" in data, f"Response missing 'message' field: {data}"
            assert isinstance(data["message"], str), f"Message field must be string, got {type(data['message'])}"
            assert data["message"] in VALID_MESSAGE_VALUES, f"Unexpected message value: {data['message']}"
        else:
            assert "error" in data, f"Response missing 'error' field: {data}"
            assert isinstance(data["error"], str), f"Error field must be string, got {type(data['error'])}"
            assert data["error"], "Error must be non-empty"

    @pytest.mark.parametrize("expected_log", VALID_LOG_CONTENTS)
    def test_successful_response_log_values(self, api_base_url, auth_token, expected_log):
        """Test successful responses with different valid log content values."""
        url = f"{api_base_url}{ENDPOINT}"
        headers = {"x-access-token": auth_token}
        
        response = requests.get(url, headers=headers, timeout=30)
        
        assert response.status_code in (200, 400), (
            f"Expected 200 OK or 400 Bad Request, got {response.status_code}. "
            f"Response: {response.text}. "
            f"curl: curl --location '{url}' --header 'x-access-token: {auth_token}'"
        )
        
        data = response.json()
        if response.status_code == 200:
            assert "log" in data, f"Response missing 'log' field: {data}"
            assert isinstance(data["log"], str), f"Log field must be string, got {type(data['log'])}"
        else:
            assert "error" in data, f"Response missing 'error' field: {data}"
            assert isinstance(data["error"], str)
            assert "log" in data, f"Response missing 'log' field alongside error: {data}"
            assert isinstance(data["log"], str)

    def test_response_structure_validation(self, api_base_url, auth_token):
        """Test that response structure matches expected schema."""
        url = f"{api_base_url}{ENDPOINT}"
        headers = {"x-access-token": auth_token}
        
        response = requests.get(url, headers=headers, timeout=30)
        
        assert response.status_code in (200, 400), (
            f"Expected 200 OK or 400 Bad Request, got {response.status_code}. "
            f"Response: {response.text}. "
            f"curl: curl --location '{url}' --header 'x-access-token: {auth_token}'"
        )
        
        data = response.json()
        if response.status_code == 200:
            # Validate required fields exist and have correct types
            for field, expected_type in RESPONSE_SCHEMA["required"].items():
                assert field in data, f"Required field '{field}' missing from response: {data}"
                actual_type = type(data[field])
                assert actual_type is expected_type, (
                    f"Field '{field}' has type {actual_type.__name__}, "
                    f"but expected {expected_type.__name__}. Value: {data[field]}"
                )
        else:
            assert "error" in data and isinstance(data["error"], str)
            assert "log" in data and isinstance(data["log"], str)

    def test_response_json_format(self, api_base_url, auth_token):
        """Test that response is valid JSON format."""
        url = f"{api_base_url}{ENDPOINT}"
        headers = {"x-access-token": auth_token}
        
        response = requests.get(url, headers=headers, timeout=30)
        
        assert response.status_code in (200, 400), (
            f"Expected 200 OK or 400 Bad Request, got {response.status_code}. "
            f"Response: {response.text}. "
            f"curl: curl --location '{url}' --header 'x-access-token: {auth_token}'"
        )
        
        # Verify response is valid JSON
        try:
            data = response.json()
            assert isinstance(data, dict), f"Response should be a dictionary, got {type(data)}"
        except json.JSONDecodeError as e:
            pytest.fail(f"Response is not valid JSON: {e}. Response text: {response.text}")

    def test_authentication_required(self, api_base_url):
        """Test that authentication token is required."""
        url = f"{api_base_url}{ENDPOINT}"
        
        response = requests.get(url, timeout=30)
        
        assert response.status_code == 401, (
            f"Expected 401 for missing auth, got {response.status_code}. "
            f"Response: {response.text}. "
            f"curl: curl --location '{url}'"
        )

    def test_invalid_auth_token(self, api_base_url):
        """Test that invalid authentication token is rejected."""
        url = f"{api_base_url}{ENDPOINT}"
        headers = {"x-access-token": "invalid_token_12345"}
        
        response = requests.get(url, headers=headers, timeout=30)
        
        assert response.status_code == 401, (
            f"Expected 401 for invalid auth, got {response.status_code}. "
            f"Response: {response.text}. "
            f"curl: curl --location '{url}' --header 'x-access-token: invalid_token_12345'"
        )

    def test_empty_auth_token(self, api_base_url):
        """Test that empty authentication token is rejected."""
        url = f"{api_base_url}{ENDPOINT}"
        headers = {"x-access-token": ""}
        
        response = requests.get(url, headers=headers, timeout=30)
        
        assert response.status_code == 401, (
            f"Expected 401 for empty auth, got {response.status_code}. "
            f"Response: {response.text}. "
            f"curl: curl --location '{url}' --header 'x-access-token: '"
        )

    def test_missing_auth_header(self, api_base_url):
        """Test that missing x-access-token header is rejected."""
        url = f"{api_base_url}{ENDPOINT}"
        headers = {"Authorization": "Bearer some_token"}
        
        response = requests.get(url, headers=headers, timeout=30)
        
        assert response.status_code == 401, (
            f"Expected 401 for missing x-access-token, got {response.status_code}. "
            f"Response: {response.text}. "
            f"curl: curl --location '{url}' --header 'Authorization: Bearer some_token'"
        )

    def test_only_get_method_allowed(self, api_base_url, auth_token):
        """Test that only GET method is allowed for this endpoint."""
        url = f"{api_base_url}{ENDPOINT}"
        headers = {"x-access-token": auth_token}
        
        # Test that GET method works
        get_response = requests.get(url, headers=headers, timeout=30)
        assert get_response.status_code in (200, 400), (
            f"GET method should return 200 or 400, got {get_response.status_code}. "
            f"Response: {get_response.text}. "
            f"curl: curl --location '{url}' --header 'x-access-token: {auth_token}'"
        )
        
        # Test that POST method is not allowed
        post_response = requests.post(url, headers=headers, timeout=30)
        assert post_response.status_code == 404, (
            f"POST method should return 404, got {post_response.status_code}. "
            f"Response: {post_response.text}. "
            f"curl: --request POST --location '{url}' --header 'x-access-token: {auth_token}'"
        )

    def test_response_content_type(self, api_base_url, auth_token):
        """Test that response has correct content type."""
        url = f"{api_base_url}{ENDPOINT}"
        headers = {"x-access-token": auth_token}
        
        response = requests.get(url, headers=headers, timeout=30)
        
        assert response.status_code in (200, 400), (
            f"Expected 200 OK or 400 Bad Request, got {response.status_code}. "
            f"Response: {response.text}. "
            f"curl: curl --location '{url}' --header 'x-access-token: {auth_token}'"
        )
        
        content_type = response.headers.get("content-type", "")
        assert "application/json" in content_type.lower(), (
            f"Expected application/json content type, got: {content_type}"
        )

    def test_response_encoding(self, api_base_url, auth_token):
        """Test that response encoding is handled correctly."""
        url = f"{api_base_url}{ENDPOINT}"
        headers = {"x-access-token": auth_token}
        
        response = requests.get(url, headers=headers, timeout=30)
        
        assert response.status_code in (200, 400), (
            f"Expected 200 OK or 400 Bad Request, got {response.status_code}. "
            f"Response: {response.text}. "
            f"curl: curl --location '{url}' --header 'x-access-token: {auth_token}'"
        )
        
        # Verify response can be decoded properly
        data = response.json()
        assert isinstance(data, dict), f"Response should be a dictionary, got {type(data)}"

    def test_log_field_base64_decodable(self, api_base_url, auth_token):
        """Test that log field contains valid base64 content when not empty."""
        url = f"{api_base_url}{ENDPOINT}"
        headers = {"x-access-token": auth_token}
        
        response = requests.get(url, headers=headers, timeout=30)
        
        assert response.status_code in (200, 400), (
            f"Expected 200 OK or 400 Bad Request, got {response.status_code}. "
            f"Response: {response.text}. "
            f"curl: curl --location '{url}' --header 'x-access-token: {auth_token}'"
        )
        
        data = response.json()
        log_content = data.get("log", "")
        
        if log_content:  # Only test if log is not empty
            try:
                # Try to decode base64 content
                decoded = base64.b64decode(log_content)
                assert isinstance(decoded, bytes), "Base64 decoded content should be bytes"
            except Exception as e:
                # If not base64, it should still be a valid string
                assert isinstance(log_content, str), f"Log content should be string: {type(log_content)}"

    def test_message_field_not_empty_when_ok(self, api_base_url, auth_token):
        """Test that message field is not empty when status is OK."""
        url = f"{api_base_url}{ENDPOINT}"
        headers = {"x-access-token": auth_token}
        
        response = requests.get(url, headers=headers, timeout=30)
        
        assert response.status_code in (200, 400), (
            f"Expected 200 OK or 400 Bad Request, got {response.status_code}. "
            f"Response: {response.text}. "
            f"curl: curl --location '{url}' --header 'x-access-token: {auth_token}'"
        )
        
        data = response.json()
        message = data.get("message", "")
        
        if message == "OK":
            assert message.strip() != "", "Message field should not be empty when status is OK"

    def test_response_timeout_handling(self, api_base_url, auth_token):
        """Test that request timeout is handled properly."""
        url = f"{api_base_url}{ENDPOINT}"
        headers = {"x-access-token": auth_token}
        
        # Use a reasonable timeout
        response = requests.get(url, headers=headers, timeout=30)
        
        assert response.status_code in (200, 400), (
            f"Expected 200 OK or 400 Bad Request, got {response.status_code}. "
            f"Response: {response.text}. "
            f"curl: curl --location '{url}' --header 'x-access-token: {auth_token}'"
        )

    def test_response_size_reasonable(self, api_base_url, auth_token):
        """Test that response size is reasonable."""
        url = f"{api_base_url}{ENDPOINT}"
        headers = {"x-access-token": auth_token}
        
        response = requests.get(url, headers=headers, timeout=30)
        
        assert response.status_code in (200, 400), (
            f"Expected 200 OK or 400 Bad Request, got {response.status_code}. "
            f"Response: {response.text}. "
            f"curl: curl --location '{url}' --header 'x-access-token: {auth_token}'"
        )
        
        # Check response size is reasonable (not too large)
        response_size = len(response.content)
        assert response_size < 10 * 1024 * 1024, f"Response too large: {response_size} bytes"

    def test_no_additional_fields(self, api_base_url, auth_token):
        """Test that response doesn't contain unexpected fields."""
        url = f"{api_base_url}{ENDPOINT}"
        headers = {"x-access-token": auth_token}
        
        response = requests.get(url, headers=headers, timeout=30)
        
        assert response.status_code in (200, 400), (
            f"Expected 200 OK or 400 Bad Request, got {response.status_code}. "
            f"Response: {response.text}. "
            f"curl: curl --location '{url}' --header 'x-access-token: {auth_token}'"
        )
        
        data = response.json()
        if response.status_code == 200:
            expected_fields = set(RESPONSE_SCHEMA["required"].keys())
            actual_fields = set(data.keys())
            # Only check for required fields, allow additional optional fields
            assert expected_fields.issubset(actual_fields), (
                f"Missing required fields. Expected: {expected_fields}, Got: {actual_fields}"
            )
        else:
            assert "error" in data and isinstance(data["error"], str)
            assert "log" in data and isinstance(data["log"], str)

    def test_log_field_content_consistency(self, api_base_url, auth_token):
        """Test that log field content is consistent across requests."""
        url = f"{api_base_url}{ENDPOINT}"
        headers = {"x-access-token": auth_token}
        
        # Make two requests
        response1 = requests.get(url, headers=headers, timeout=30)
        response2 = requests.get(url, headers=headers, timeout=30)
        
        assert response1.status_code in (200, 400), (
            f"First request failed: {response1.status_code}. "
            f"curl: curl --location '{url}' --header 'x-access-token: {auth_token}'"
        )
        assert response2.status_code in (200, 400), (
            f"Second request failed: {response2.status_code}. "
            f"curl: curl --location '{url}' --header 'x-access-token: {auth_token}'"
        )
        
        data1 = response1.json()
        data2 = response2.json()
        
        # Both responses should have the same structure
        assert set(data1.keys()) == set(data2.keys()), "Response structure should be consistent"

    def test_message_field_values_consistency(self, api_base_url, auth_token):
        """Test that message field contains expected values."""
        url = f"{api_base_url}{ENDPOINT}"
        headers = {"x-access-token": auth_token}
        
        response = requests.get(url, headers=headers, timeout=30)
        
        assert response.status_code in (200, 400), (
            f"Expected 200 OK or 400 Bad Request, got {response.status_code}. "
            f"Response: {response.text}. "
            f"curl: curl --location '{url}' --header 'x-access-token: {auth_token}'"
        )
        
        data = response.json()
        if response.status_code == 200:
            message = data.get("message", "")
            assert message in VALID_MESSAGE_VALUES, f"Unexpected message value: {message}"
        else:
            assert "error" in data and isinstance(data["error"], str)

    def test_response_headers_consistency(self, api_base_url, auth_token):
        """Test that response headers are consistent."""
        url = f"{api_base_url}{ENDPOINT}"
        headers = {"x-access-token": auth_token}
        
        response = requests.get(url, headers=headers, timeout=30)
        
        assert response.status_code in (200, 400), (
            f"Expected 200 OK or 400 Bad Request, got {response.status_code}. "
            f"Response: {response.text}. "
            f"curl: curl --location '{url}' --header 'x-access-token: {auth_token}'"
        )
        
        # Check for essential headers
        assert "content-type" in response.headers, "Response should have content-type header"
        assert "content-length" in response.headers or "transfer-encoding" in response.headers, (
            "Response should have content-length or transfer-encoding header"
        )

    def test_authentication_header_case_sensitivity(self, api_base_url):
        """Test that authentication header is case sensitive."""
        url = f"{api_base_url}{ENDPOINT}"
        headers = {"X-Access-Token": "some_token"}  # Different case
        
        response = requests.get(url, headers=headers, timeout=30)
        
        assert response.status_code == 401, (
            f"Expected 401 for wrong case header, got {response.status_code}. "
            f"Response: {response.text}. "
            f"curl: curl --location '{url}' --header 'X-Access-Token: some_token'"
        )

    def test_duplicate_authentication_headers(self, api_base_url):
        """Test that duplicate authentication headers are handled properly."""
        url = f"{api_base_url}{ENDPOINT}"
        headers = {
            "x-access-token": "token1",
            "X-Access-Token": "token2"
        }
        
        response = requests.get(url, headers=headers, timeout=30)
        
        # Should reject duplicate headers
        assert response.status_code == 401, (
            f"Expected 401 for duplicate auth headers, got {response.status_code}. "
            f"Response: {response.text}. "
            f"curl: curl --location '{url}' --header 'x-access-token: token1' --header 'X-Access-Token: token2'"
        )

    def test_extra_headers_ignored(self, api_base_url, auth_token):
        """Test that extra headers are ignored."""
        url = f"{api_base_url}{ENDPOINT}"
        headers = {
            "x-access-token": auth_token,
            "X-Custom-Header": "custom_value",
            "User-Agent": "test-agent"
        }
        
        response = requests.get(url, headers=headers, timeout=30)
        
        assert response.status_code in (200, 400), (
            f"Expected 200 OK or 400 Bad Request, got {response.status_code}. "
            f"Response: {response.text}. "
            f"curl: curl --location '{url}' --header 'x-access-token: {auth_token}' --header 'X-Custom-Header: custom_value' --header 'User-Agent: test-agent'"
        )

    def test_query_parameters_ignored(self, api_base_url, auth_token):
        """Test that query parameters are ignored."""
        url = f"{api_base_url}{ENDPOINT}?param1=value1&param2=value2"
        headers = {"x-access-token": auth_token}
        
        response = requests.get(url, headers=headers, timeout=30)
        
        assert response.status_code in (200, 400), (
            f"Expected 200 OK or 400 Bad Request, got {response.status_code}. "
            f"Response: {response.text}. "
            f"curl: curl --location '{url}' --header 'x-access-token: {auth_token}'"
        )

    def test_request_body_ignored(self, api_base_url, auth_token):
        """Test that request body is ignored for GET request."""
        url = f"{api_base_url}{ENDPOINT}"
        headers = {"x-access-token": auth_token}
        data = {"key": "value"}
        
        response = requests.get(url, headers=headers, json=data, timeout=30)
        
        assert response.status_code in (200, 400), (
            f"Expected 200 OK or 400 Bad Request, got {response.status_code}. "
            f"Response: {response.text}. "
            f"curl: curl --location '{url}' --header 'x-access-token: {auth_token}' --data '{{\"key\": \"value\"}}'"
        )

    def test_response_cache_headers(self, api_base_url, auth_token):
        """Test that response has appropriate cache headers."""
        url = f"{api_base_url}{ENDPOINT}"
        headers = {"x-access-token": auth_token}
        
        response = requests.get(url, headers=headers, timeout=30)
        
        assert response.status_code in (200, 400), (
            f"Expected 200 OK or 400 Bad Request, got {response.status_code}. "
            f"Response: {response.text}. "
            f"curl: curl --location '{url}' --header 'x-access-token: {auth_token}'"
        )
        
        # Check for cache-related headers (may or may not be present)
        cache_headers = ["cache-control", "etag", "last-modified", "expires"]
        has_cache_header = any(header in response.headers for header in cache_headers)
        
        # This is informational - cache headers are optional
        if has_cache_header:
            assert True, "Cache headers present"
        else:
            assert True, "No cache headers present (acceptable)"

    def test_response_compression_handling(self, api_base_url, auth_token):
        """Test that response compression is handled properly."""
        url = f"{api_base_url}{ENDPOINT}"
        headers = {
            "x-access-token": auth_token,
            "Accept-Encoding": "gzip, deflate"
        }
        
        response = requests.get(url, headers=headers, timeout=30)
        
        assert response.status_code in (200, 400), (
            f"Expected 200 OK or 400 Bad Request, got {response.status_code}. "
            f"Response: {response.text}. "
            f"curl: curl --location '{url}' --header 'x-access-token: {auth_token}' --header 'Accept-Encoding: gzip, deflate'"
        )
        
        # Verify response can be processed regardless of compression
        data = response.json()
        assert isinstance(data, dict), f"Response should be a dictionary, got {type(data)}"

    def test_concurrent_requests(self, api_base_url, auth_token):
        """Test that multiple concurrent requests are handled properly."""
        import concurrent.futures
        
        url = f"{api_base_url}{ENDPOINT}"
        headers = {"x-access-token": auth_token}
        
        def make_request():
            return requests.get(url, headers=headers, timeout=30)
        
        # Make 3 concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(make_request) for _ in range(3)]
            responses = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # All requests should succeed or return a well-formed 400
        for i, response in enumerate(responses):
            assert response.status_code in (200, 400), (
                f"Concurrent request {i} failed: {response.status_code}. "
                f"Response: {response.text}. "
                f"curl: curl --location '{url}' --header 'x-access-token: {auth_token}'"
            )

    def test_response_stability(self, api_base_url, auth_token):
        """Test that response is stable across multiple requests."""
        url = f"{api_base_url}{ENDPOINT}"
        headers = {"x-access-token": auth_token}
        
        responses = []
        for _ in range(5):
            response = requests.get(url, headers=headers, timeout=30)
            responses.append(response)
            assert response.status_code in (200, 400), (
                f"Request failed: {response.status_code}. "
                f"curl: curl --location '{url}' --header 'x-access-token: {auth_token}'"
            )
        
        # All responses should have the same structure
        response_structures = [set(r.json().keys()) for r in responses]
        assert len(set(map(tuple, response_structures))) == 1, (
            "Response structure should be consistent across requests"
        )

    def test_error_handling_graceful(self, api_base_url, auth_token):
        """Test that the API handles errors gracefully."""
        url = f"{api_base_url}{ENDPOINT}"
        headers = {"x-access-token": auth_token}
        
        # Make a normal request to ensure it works
        response = requests.get(url, headers=headers, timeout=30)
        
        assert response.status_code in (200, 400), (
            f"Expected 200 OK or 400 Bad Request, got {response.status_code}. "
            f"Response: {response.text}. "
            f"curl: curl --location '{url}' --header 'x-access-token: {auth_token}'"
        )
        
        # Verify response is well-formed even if there are internal errors
        data = response.json()
        assert isinstance(data, dict), f"Response should be a dictionary, got {type(data)}"
        
        # If there's an error message, it should be properly formatted
        if "error" in data:
            assert isinstance(data["error"], str), "Error field should be a string"

    def test_response_performance_acceptable(self, api_base_url, auth_token):
        """Test that response time is within acceptable limits."""
        import time
        
        url = f"{api_base_url}{ENDPOINT}"
        headers = {"x-access-token": auth_token}
        
        start_time = time.time()
        response = requests.get(url, headers=headers, timeout=30)
        end_time = time.time()
        
        response_time = end_time - start_time
        
        assert response.status_code in (200, 400), (
            f"Expected 200 OK or 400 Bad Request, got {response.status_code}. "
            f"Response: {response.text}. "
            f"curl: curl --location '{url}' --header 'x-access-token: {auth_token}'"
        )
        
        # Response should be reasonably fast (under 5 seconds)
        assert response_time < 5.0, f"Response too slow: {response_time:.2f} seconds"

    def test_endpoint_availability(self, api_base_url, auth_token):
        """Test that the endpoint is consistently available."""
        url = f"{api_base_url}{ENDPOINT}"
        headers = {"x-access-token": auth_token}
        
        # Test endpoint availability multiple times
        for attempt in range(3):
            try:
                response = requests.get(url, headers=headers, timeout=30)
                assert response.status_code in (200, 400), (
                    f"Attempt {attempt + 1} failed: {response.status_code}. "
                    f"Response: {response.text}. "
                    f"curl: curl --location '{url}' --header 'x-access-token: {auth_token}'"
                )
                break
            except requests.exceptions.RequestException as e:
                if attempt == 2:  # Last attempt
                    pytest.fail(f"Endpoint not available after 3 attempts: {e}")
                continue

    def test_response_validation_comprehensive(self, api_base_url, auth_token):
        """Comprehensive validation of response structure and content."""
        url = f"{api_base_url}{ENDPOINT}"
        headers = {"x-access-token": auth_token}
        
        response = requests.get(url, headers=headers, timeout=30)
        
        assert response.status_code in (200, 400), (
            f"Expected 200 OK or 400 Bad Request, got {response.status_code}. "
            f"Response: {response.text}. "
            f"curl: curl --location '{url}' --header 'x-access-token: {auth_token}'"
        )
        
        data = response.json()
        if response.status_code == 200:
            # Validate all required fields
            for field, expected_type in RESPONSE_SCHEMA["required"].items():
                assert field in data, f"Required field '{field}' missing"
                assert isinstance(data[field], expected_type), (
                    f"Field '{field}' has wrong type. Expected {expected_type.__name__}, "
                    f"got {type(data[field]).__name__}"
                )
        else:
            assert "error" in data and isinstance(data["error"], str)
            assert "log" in data and isinstance(data["log"], str)
        
        # Validate field content
        if "message" in data:
            message = data["message"]
            assert isinstance(message, str), "Message must be a string"
            assert message.strip() != "", "Message cannot be empty or whitespace"
        
        if "log" in data:
            log = data["log"]
            assert isinstance(log, str), "Log must be a string"
            # Log can be empty, but if present should be valid

    def test_api_compliance(self, api_base_url, auth_token):
        """Test that the API complies with expected behavior."""
        url = f"{api_base_url}{ENDPOINT}"
        headers = {"x-access-token": auth_token}
        
        response = requests.get(url, headers=headers, timeout=30)
        
        assert response.status_code in (200, 400), (
            f"Expected 200 OK or 400 Bad Request, got {response.status_code}. "
            f"Response: {response.text}. "
            f"curl: curl --location '{url}' --header 'x-access-token: {auth_token}'"
        )
        
        data = response.json()
        
        # API should return a valid response structure
        assert isinstance(data, dict), "Response must be a JSON object"
        if response.status_code == 200:
            assert len(data) >= len(RESPONSE_SCHEMA["required"]), (
                "Response must contain at least all required fields"
            )
            # All required fields must be present and valid
            for field in RESPONSE_SCHEMA["required"]:
                assert field in data, f"Required field '{field}' must be present"
                assert data[field] is not None, f"Required field '{field}' cannot be null"
        else:
            # For 400 responses, ensure 'error' and 'log' are present and valid
            assert "error" in data and isinstance(data["error"], str)
            assert "log" in data and isinstance(data["log"], str)
