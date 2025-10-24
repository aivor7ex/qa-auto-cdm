import pytest
import requests
from typing import Dict, Any


ENDPOINT = "/system-monitor/monitor/state"

SUCCESS_RESPONSE_SCHEMA = {
    "cpu": int,
    "ram": {
        "memory_used_bytes": int,
        "memory_total_bytes": int,
        "swap_used_bytes": int,
        "swap_total_bytes": int
    },
    "block": dict,
    "network": list
}


def validate_response_schema(response_data: Dict[str, Any], schema: Dict[str, Any]) -> bool:
    """Recursively validate response structure against schema"""
    for key, expected_type in schema.items():
        if key not in response_data:
            return False
        if expected_type == dict:
            if not isinstance(response_data[key], dict):
                return False
        elif expected_type == list:
            if not isinstance(response_data[key], list):
                return False
        elif expected_type == int:
            if not isinstance(response_data[key], int):
                return False
        elif expected_type == str:
            if not isinstance(response_data[key], str):
                return False
        elif expected_type == type(None):
            if response_data[key] is not None:
                return False
    return True


@pytest.mark.parametrize("test_case", [
    "valid_request_with_auth_token",
    "valid_request_with_valid_headers",
    "valid_request_returns_200_status",
    "valid_request_has_cpu_field",
    "valid_request_has_ram_field",
    "valid_request_has_block_field", 
    "valid_request_has_network_field",
    "valid_request_cpu_is_integer",
    "valid_request_ram_has_required_fields",
    "valid_request_response_schema_validation"
])
def test_positive_cases(api_client, auth_token, attach_curl_on_fail, test_case):
    """Positive test cases for system monitor state endpoint"""
    headers = {
        "x-access-token": auth_token
    }
    
    with attach_curl_on_fail(ENDPOINT, None, headers, "GET"):
        response = api_client.get(ENDPOINT, headers=headers)
        
        if test_case == "valid_request_with_auth_token":
            assert response.status_code == 200
            assert "cpu" in response.json()
            
        elif test_case == "valid_request_with_valid_headers":
            assert response.status_code == 200
            assert response.headers.get("content-type", "").startswith("application/json")
            
        elif test_case == "valid_request_returns_200_status":
            assert response.status_code == 200
            
        elif test_case == "valid_request_has_cpu_field":
            data = response.json()
            assert "cpu" in data
            assert isinstance(data["cpu"], int)
            
        elif test_case == "valid_request_has_ram_field":
            data = response.json()
            assert "ram" in data
            assert isinstance(data["ram"], dict)
            
        elif test_case == "valid_request_has_block_field":
            data = response.json()
            assert "block" in data
            assert isinstance(data["block"], dict)
            
        elif test_case == "valid_request_has_network_field":
            data = response.json()
            assert "network" in data
            assert isinstance(data["network"], list)
            
        elif test_case == "valid_request_cpu_is_integer":
            data = response.json()
            assert isinstance(data["cpu"], int)
            assert data["cpu"] >= 0
            
        elif test_case == "valid_request_ram_has_required_fields":
            data = response.json()
            ram = data["ram"]
            assert "memory_used_bytes" in ram
            assert "memory_total_bytes" in ram
            assert "swap_used_bytes" in ram
            assert "swap_total_bytes" in ram
            assert all(isinstance(ram[key], int) for key in ram.keys())
            
        elif test_case == "valid_request_response_schema_validation":
            data = response.json()
            assert validate_response_schema(data, SUCCESS_RESPONSE_SCHEMA)


@pytest.mark.parametrize("test_case", [
    "missing_auth_token_returns_401",
    "invalid_auth_token_returns_401", 
    "empty_auth_token_returns_401",
    "malformed_auth_token_returns_401",
    "expired_auth_token_returns_401",
    "wrong_auth_header_name_returns_401",
    "multiple_auth_headers_returns_401",
    "auth_token_with_invalid_chars_returns_401",
    "auth_token_with_special_chars_returns_401",
    "no_headers_returns_401"
])
def test_negative_cases(api_client, attach_curl_on_fail, test_case):
    """Negative test cases for system monitor state endpoint"""
    
    if test_case == "missing_auth_token_returns_401":
        with attach_curl_on_fail(ENDPOINT, None, None, "GET"):
            response = api_client.get(ENDPOINT)
            assert response.status_code == 401
        
    elif test_case == "invalid_auth_token_returns_401":
        headers = {"x-access-token": "invalid_token_12345"}
        with attach_curl_on_fail(ENDPOINT, None, headers, "GET"):
            response = api_client.get(ENDPOINT, headers=headers)
            assert response.status_code == 401
        
    elif test_case == "empty_auth_token_returns_401":
        headers = {"x-access-token": ""}
        with attach_curl_on_fail(ENDPOINT, None, headers, "GET"):
            response = api_client.get(ENDPOINT, headers=headers)
            assert response.status_code == 401
        
    elif test_case == "malformed_auth_token_returns_401":
        headers = {"x-access-token": "malformed_token"}
        with attach_curl_on_fail(ENDPOINT, None, headers, "GET"):
            response = api_client.get(ENDPOINT, headers=headers)
            assert response.status_code == 401
        
    elif test_case == "expired_auth_token_returns_401":
        headers = {"x-access-token": "expired_token_12345"}
        with attach_curl_on_fail(ENDPOINT, None, headers, "GET"):
            response = api_client.get(ENDPOINT, headers=headers)
            assert response.status_code == 401
        
    elif test_case == "wrong_auth_header_name_returns_401":
        headers = {"authorization": "Bearer valid_token"}
        with attach_curl_on_fail(ENDPOINT, None, headers, "GET"):
            response = api_client.get(ENDPOINT, headers=headers)
            assert response.status_code == 401
        
    elif test_case == "multiple_auth_headers_returns_401":
        headers = {
            "x-access-token": "token1",
            "authorization": "Bearer token2"
        }
        with attach_curl_on_fail(ENDPOINT, None, headers, "GET"):
            response = api_client.get(ENDPOINT, headers=headers)
            assert response.status_code == 401
        
    elif test_case == "auth_token_with_invalid_chars_returns_401":
        headers = {"x-access-token": "token_with_spaces"}
        with attach_curl_on_fail(ENDPOINT, None, headers, "GET"):
            response = api_client.get(ENDPOINT, headers=headers)
            assert response.status_code == 401
        
    elif test_case == "auth_token_with_special_chars_returns_401":
        headers = {"x-access-token": "token@#$%^&*()"}
        with attach_curl_on_fail(ENDPOINT, None, headers, "GET"):
            response = api_client.get(ENDPOINT, headers=headers)
            assert response.status_code == 401
        
    elif test_case == "no_headers_returns_401":
        with attach_curl_on_fail(ENDPOINT, None, None, "GET"):
            response = api_client.get(ENDPOINT)
            assert response.status_code == 401
