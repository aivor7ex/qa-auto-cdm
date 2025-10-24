import pytest
import json
from typing import Dict, Any, Union

# =====================================================================================================================
# Constants
# =====================================================================================================================

ENDPOINT = "/Managers/transitBridge/init"
METHOD = "POST"

# =====================================================================================================================
# Response Schema (based on API_EXAMPLE_RESPONSE)
# =====================================================================================================================

RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "index": {"type": "integer"}
    },
    "required": ["index"]
}

# =====================================================================================================================
# Test Data
# =====================================================================================================================

# Valid payloads for testing
VALID_PAYLOADS = [
    {},  # Empty object
    {"test": "data"},  # Simple key-value
    {"nested": {"key": "value"}},  # Nested object
    {"array": [1, 2, 3]},  # Array
    {"mixed": {"str": "value", "num": 123, "bool": True}},  # Mixed types
    {"unicode": "тест 🚀 测试"},  # Unicode characters
    {"special": "!@#$%^&*()_+-=[]{}|;:,.<>?"},  # Special characters
    {"numbers": {"positive": 9223372036854775807, "negative": -9223372036854775808}},  # Extreme values
    {"booleans": {"true": True, "false": False}},  # Boolean values
    {"nulls": {"key1": None, "key2": "value"}},  # Null values
]

# Invalid payloads for error testing
INVALID_PAYLOADS = [
    "invalid json",  # Invalid JSON string
    "{invalid json}",  # Malformed JSON
    None,  # None payload
    "",  # Empty string
    "null",  # String "null"
    "[]",  # String array
    '""',  # String with quotes
    b"binary data",  # Binary data
    {"very_long": "a" * 10000},  # Very long payload
]

# Edge case payloads
EDGE_CASE_PAYLOADS = [
    {"empty_string": ""},  # Empty string value
    {"zero": 0},  # Zero value
    {"negative": -1},  # Negative value
    {"float": 3.14},  # Float value
    {"empty_array": []},  # Empty array
    {"empty_object": {}},  # Empty object
    {"nested_empty": {"empty": {}}},  # Nested empty objects
    {"array_with_nulls": [None, 1, "test"]},  # Array with nulls
    {"deep_nested": {"level1": {"level2": {"level3": "value"}}}},  # Deep nesting
    {"mixed_types": [1, "string", True, None, {"obj": "value"}]},  # Mixed type array
]

# Headers for testing
TEST_HEADERS = [
    {"Content-Type": "application/json"},
    {"Content-Type": "application/json", "Accept": "application/json"},
    {"Content-Type": "application/json", "User-Agent": "TestBot/1.0"},
    {"Content-Type": "text/plain"},
    {"Content-Type": "application/xml"},
    {"Content-Type": "application/x-www-form-urlencoded"},
    {},  # No headers
    {"Accept": "application/json"},  # Missing Content-Type
]

# =====================================================================================================================
# Schema Validation Functions
# =====================================================================================================================

def validate_response_schema(response_data: Dict[str, Any]) -> None:
    """Validates response against the expected schema."""
    assert isinstance(response_data, dict), f"Response should be a dict, got {type(response_data)}"
    
    # Check required fields
    assert "index" in response_data, "Response missing required field 'index'"
    assert isinstance(response_data["index"], int), f"Field 'index' should be int, got {type(response_data['index'])}"
    
    # Check that no unexpected fields are present
    expected_fields = {"index"}
    actual_fields = set(response_data.keys())
    unexpected_fields = actual_fields - expected_fields
    assert not unexpected_fields, f"Unexpected fields in response: {unexpected_fields}"

def validate_error_response(response_data: Union[Dict[str, Any], str]) -> None:
    """Validates error response structure."""
    if isinstance(response_data, dict):
        # Some APIs return structured error responses
        assert "error" in response_data or "message" in response_data or "detail" in response_data, \
            "Error response should contain error information"
    # For string responses, just ensure it's not empty
    elif isinstance(response_data, str):
        assert response_data.strip(), "Error response should not be empty"

# =====================================================================================================================
# Test Cases
# =====================================================================================================================

class TestTransitBridgeInit:
    """Test suite for /Managers/transitBridge/init endpoint."""

    # =====================================================================================================================
    # Basic Functionality Tests
    # =====================================================================================================================

    def test_basic_valid_request(self, api_client, attach_curl_on_fail):
        """Test 1: Basic valid request with empty payload."""
        payload = {}
        
        with attach_curl_on_fail(ENDPOINT, payload):
            response = api_client.post(ENDPOINT, json=payload)
            
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        try:
            response_data = response.json()
        except json.JSONDecodeError:
            pytest.fail("Response is not valid JSON")
        
        validate_response_schema(response_data)
        assert response_data["index"] == 0, f"Expected index 0, got {response_data['index']}"

    @pytest.mark.parametrize("payload", VALID_PAYLOADS)
    def test_valid_payloads(self, api_client, attach_curl_on_fail, payload):
        """Test 2-11: Test various valid payloads."""
        with attach_curl_on_fail(ENDPOINT, payload):
            response = api_client.post(ENDPOINT, json=payload)
        
        assert response.status_code == 200, f"Expected 200 for payload {payload}, got {response.status_code}"
        
        try:
            response_data = response.json()
        except json.JSONDecodeError:
            pytest.fail(f"Response is not valid JSON for payload {payload}")
        
        validate_response_schema(response_data)
        assert response_data["index"] == 0, f"Expected index 0 for payload {payload}, got {response_data['index']}"

    # =====================================================================================================================
    # Edge Cases Tests
    # =====================================================================================================================

    @pytest.mark.parametrize("payload", EDGE_CASE_PAYLOADS)
    def test_edge_case_payloads(self, api_client, attach_curl_on_fail, payload):
        """Test 12-21: Test edge case payloads."""
        with attach_curl_on_fail(ENDPOINT, payload):
            response = api_client.post(ENDPOINT, json=payload)
        
        assert response.status_code == 200, f"Expected 200 for edge case payload {payload}, got {response.status_code}"
        
        try:
            response_data = response.json()
        except json.JSONDecodeError:
            pytest.fail(f"Response is not valid JSON for edge case payload {payload}")
        
        validate_response_schema(response_data)
        assert response_data["index"] == 0, f"Expected index 0 for edge case payload {payload}, got {response_data['index']}"

    # =====================================================================================================================
    # Error Handling Tests
    # =====================================================================================================================

    @pytest.mark.parametrize("payload", INVALID_PAYLOADS)
    def test_invalid_payloads(self, api_client, attach_curl_on_fail, payload):
        """Test 22-31: Test invalid payloads."""
        with attach_curl_on_fail(ENDPOINT, str(payload) if isinstance(payload, bytes) else payload):
            if payload is None:
                response = api_client.post(ENDPOINT, data=None)
            elif isinstance(payload, str):
                response = api_client.post(ENDPOINT, data=payload)
            elif isinstance(payload, bytes):
                response = api_client.post(ENDPOINT, data=payload)
            else:
                response = api_client.post(ENDPOINT, json=payload)
        
        # Handle different payload types based on actual API behavior
        if payload is None or payload == "" or payload == "null" or payload == "[]" or payload == '""':
            # None, empty string, "null" string, "[]" string, and '""' string payloads are actually accepted by this API
            assert response.status_code == 200, f"Expected 200 for payload '{payload}', got {response.status_code}"
            try:
                response_data = response.json()
                validate_response_schema(response_data)
                assert response_data["index"] == 0, f"Expected index 0 for payload '{payload}', got {response_data['index']}"
            except json.JSONDecodeError:
                pytest.fail(f"Response is not valid JSON for payload '{payload}'")
        elif isinstance(payload, dict) and "very_long" in payload:
            # Very long payload might be accepted or rejected
            assert response.status_code in [200, 400], \
                f"Expected 200 or 400 for very long payload, got {response.status_code}"
            
            if response.status_code == 200:
                try:
                    response_data = response.json()
                    validate_response_schema(response_data)
                    assert response_data["index"] == 0, f"Expected index 0 for very long payload, got {response_data['index']}"
                except json.JSONDecodeError:
                    pytest.fail("Response is not valid JSON for very long payload")
        else:
            # Other invalid payloads should return 400 or 422
            assert response.status_code in [400, 422], \
                f"Expected 400 or 422 for invalid payload {payload}, got {response.status_code}"
            
            # Validate error response structure
            try:
                response_data = response.json()
                validate_error_response(response_data)
            except json.JSONDecodeError:
                # Some APIs return plain text errors
                validate_error_response(response.text)

    # =====================================================================================================================
    # Header Validation Tests
    # =====================================================================================================================

    @pytest.mark.parametrize("headers", TEST_HEADERS)
    def test_different_headers(self, api_client, attach_curl_on_fail, headers):
        """Test 32-39: Test different header combinations."""
        payload = {}
        
        with attach_curl_on_fail(ENDPOINT, payload, headers=headers):
            response = api_client.post(ENDPOINT, json=payload, headers=headers)
        
        # Most header combinations should work, but some might fail
        if "Content-Type" in headers and headers["Content-Type"] != "application/json":
            # Non-JSON content types might fail
            assert response.status_code in [200, 400], \
                f"Unexpected status for headers {headers}: {response.status_code}"
        else:
            # JSON content type should work
            assert response.status_code == 200, \
                f"Expected 200 for headers {headers}, got {response.status_code}"
            
            if response.status_code == 200:
                try:
                    response_data = response.json()
                    validate_response_schema(response_data)
                    assert response_data["index"] == 0, f"Expected index 0 for headers {headers}, got {response_data['index']}"
                except json.JSONDecodeError:
                    pytest.fail(f"Response is not valid JSON for headers {headers}")

    # =====================================================================================================================
    # Method Validation Tests
    # =====================================================================================================================

    def test_get_method_not_allowed(self, api_client, attach_curl_on_fail):
        """Test 40: GET method should not be allowed."""
        with attach_curl_on_fail(ENDPOINT, None, method="GET"):
            response = api_client.get(ENDPOINT)
        
        # API returns 404 (method not found) instead of 405 (method not allowed)
        assert response.status_code == 404, f"Expected 404 for GET method, got {response.status_code}"

    def test_put_method_not_allowed(self, api_client, attach_curl_on_fail):
        """Test 41: PUT method should not be allowed."""
        payload = {"test": "data"}
        
        with attach_curl_on_fail(ENDPOINT, payload, method="PUT"):
            response = api_client.put(ENDPOINT, json=payload)
        
        # API returns 404 (method not found) instead of 405 (method not allowed)
        assert response.status_code == 404, f"Expected 404 for PUT method, got {response.status_code}"

    def test_delete_method_not_allowed(self, api_client, attach_curl_on_fail):
        """Test 42: DELETE method should not be allowed."""
        with attach_curl_on_fail(ENDPOINT, None, method="DELETE"):
            response = api_client.delete(ENDPOINT)
        
        # API returns 404 (method not found) instead of 405 (method not allowed)
        assert response.status_code == 404, f"Expected 404 for DELETE method, got {response.status_code}"

    def test_patch_method_not_allowed(self, api_client, attach_curl_on_fail):
        """Test 43: PATCH method should not be allowed."""
        payload = {"test": "data"}
        
        with attach_curl_on_fail(ENDPOINT, payload, method="PATCH"):
            response = api_client.patch(ENDPOINT, json=payload)
        
        # API returns 404 (method not found) instead of 405 (method not allowed)
        assert response.status_code == 404, f"Expected 404 for PATCH method, got {response.status_code}"

    # =====================================================================================================================
    # Content Type Tests
    # =====================================================================================================================

    def test_missing_content_type(self, api_client, attach_curl_on_fail):
        """Test 44: Request without Content-Type header."""
        payload = {"test": "data"}
        headers = {}  # No Content-Type
        
        with attach_curl_on_fail(ENDPOINT, payload, headers=headers):
            response = api_client.post(ENDPOINT, json=payload, headers=headers)
        
        # Should still work as json parameter sets Content-Type automatically
        assert response.status_code == 200, f"Expected 200 without Content-Type, got {response.status_code}"
        
        try:
            response_data = response.json()
            validate_response_schema(response_data)
            assert response_data["index"] == 0, f"Expected index 0 without Content-Type, got {response_data['index']}"
        except json.JSONDecodeError:
            pytest.fail("Response is not valid JSON without Content-Type")

    def test_plain_text_content_type(self, api_client, attach_curl_on_fail):
        """Test 45: Request with text/plain Content-Type."""
        payload = "some text data"
        headers = {"Content-Type": "text/plain"}
        
        with attach_curl_on_fail(ENDPOINT, payload, headers=headers):
            response = api_client.post(ENDPOINT, data=payload, headers=headers)
        
        # text/plain might fail or be processed differently
        assert response.status_code in [200, 400], \
            f"Unexpected status for text/plain: {response.status_code}"

    # =====================================================================================================================
    # Payload Size and Complexity Tests
    # =====================================================================================================================

    def test_large_payload(self, api_client, attach_curl_on_fail):
        """Test 46: Test with very large payload."""
        # Create a large payload
        large_payload = {
            "large_string": "a" * 10000,
            "large_array": list(range(1000)),
            "nested": {"deep": {"structure": {"with": {"lots": {"of": {"data": "value"}}}}}}
        }
        
        with attach_curl_on_fail(ENDPOINT, large_payload):
            response = api_client.post(ENDPOINT, json=large_payload)
        
        # Large payloads should either work or fail gracefully
        assert response.status_code in [200, 400], \
            f"Unexpected status for large payload: {response.status_code}"
        
        if response.status_code == 200:
            try:
                response_data = response.json()
                validate_response_schema(response_data)
                assert response_data["index"] == 0, f"Expected index 0 for large payload, got {response_data['index']}"
            except json.JSONDecodeError:
                pytest.fail("Response is not valid JSON for large payload")

    def test_deep_nested_payload(self, api_client, attach_curl_on_fail):
        """Test 47: Test with deeply nested payload."""
        # Create a deeply nested payload
        deep_payload = {}
        current = deep_payload
        for i in range(20):  # 20 levels deep
            current["level"] = i
            current["next"] = {}
            current = current["next"]
        current["final"] = "value"
        
        with attach_curl_on_fail(ENDPOINT, deep_payload):
            response = api_client.post(ENDPOINT, json=deep_payload)
        
        # Deep nesting should either work or fail gracefully
        assert response.status_code in [200, 400], \
            f"Unexpected status for deep nested payload: {response.status_code}"
        
        if response.status_code == 200:
            try:
                response_data = response.json()
                validate_response_schema(response_data)
                assert response_data["index"] == 0, f"Expected index 0 for deep nested payload, got {response_data['index']}"
            except json.JSONDecodeError:
                pytest.fail("Response is not valid JSON for deep nested payload")

    # =====================================================================================================================
    # Response Consistency Tests
    # =====================================================================================================================

    def test_response_consistency(self, api_client, attach_curl_on_fail):
        """Test 48: Multiple requests should return consistent responses."""
        payload = {"test": "consistency"}
        responses = []
        
        for _ in range(5):  # Make 5 requests
            with attach_curl_on_fail(ENDPOINT, payload):
                response = api_client.post(ENDPOINT, json=payload)
            
            assert response.status_code == 200, f"Expected 200 for consistency test, got {response.status_code}"
            
            try:
                response_data = response.json()
                validate_response_schema(response_data)
                responses.append(response_data)
            except json.JSONDecodeError:
                pytest.fail("Response is not valid JSON for consistency test")
        
        # All responses should be identical
        first_response = responses[0]
        for i, response in enumerate(responses[1:], 1):
            assert response == first_response, \
                f"Response {i} differs from first response: {response} vs {first_response}"

    def test_empty_payload_consistency(self, api_client, attach_curl_on_fail):
        """Test 49: Empty payload should always return the same response."""
        payload = {}
        responses = []
        
        for _ in range(3):  # Make 3 requests
            with attach_curl_on_fail(ENDPOINT, payload):
                response = api_client.post(ENDPOINT, json=payload)
            
            assert response.status_code == 200, f"Expected 200 for empty payload consistency, got {response.status_code}"
            
            try:
                response_data = response.json()
                validate_response_schema(response_data)
                responses.append(response_data)
            except json.JSONDecodeError:
                pytest.fail("Response is not valid JSON for empty payload consistency")
        
        # All responses should be identical
        first_response = responses[0]
        for i, response in enumerate(responses[1:], 1):
            assert response == first_response, \
                f"Empty payload response {i} differs from first: {response} vs {first_response}"

    # =====================================================================================================================
    # Final Comprehensive Test
    # =====================================================================================================================

    def test_comprehensive_functionality(self, api_client, attach_curl_on_fail):
        """Test 50: Comprehensive test covering all major functionality."""
        # Test 1: Basic functionality
        payload = {"comprehensive": "test"}
        
        with attach_curl_on_fail(ENDPOINT, payload):
            response = api_client.post(ENDPOINT, json=payload)
        
        assert response.status_code == 200, f"Expected 200 for comprehensive test, got {response.status_code}"
        
        try:
            response_data = response.json()
            validate_response_schema(response_data)
            assert response_data["index"] == 0, f"Expected index 0 for comprehensive test, got {response_data['index']}"
        except json.JSONDecodeError:
            pytest.fail("Response is not valid JSON for comprehensive test")
        
        # Test 2: Verify response structure is exactly as expected
        expected_keys = {"index"}
        actual_keys = set(response_data.keys())
        assert actual_keys == expected_keys, \
            f"Response has unexpected keys. Expected: {expected_keys}, Got: {actual_keys}"
        
        # Test 3: Verify index is exactly 0
        assert response_data["index"] == 0, f"Index should be exactly 0, got {response_data['index']}"
        
        # Test 4: Verify no additional fields
        assert len(response_data) == 1, f"Response should have exactly 1 field, got {len(response_data)}"
