import pytest
import requests
from urllib.parse import urljoin
from qa_constants import SERVICES
from typing import List, Dict, Any, Union

# =====================================================================================================================
# Constants
# =====================================================================================================================

ENDPOINT = "/connections"

# The schema is defined based on documentation/expectations for when the list is not empty.
# It is not used in current tests but is kept for future reference and maintenance.
CONNECTION_ITEM_SCHEMA = {
    "proto": (str, int), "ether_type": str, "id": int, "dst_addr": str, "src_addr": str,
    "bytes": int, "packets": int, "state": str, "status": str, "repl_dst_port": int,
    "repl_src_port": int, "dst_port": int, "src_port": int,
}

# =====================================================================================================================
# Fixtures
# =====================================================================================================================

@pytest.fixture(scope="module")
def response(api_client):
    """Fetches the API response once per module for basic checks."""
    return api_client.get(ENDPOINT)

@pytest.fixture(scope="module")
def response_data(response) -> Union[List, Dict]:
    """Provides the JSON data from the response."""
    return response.json()

# =====================================================================================================================
# Test Cases
# =====================================================================================================================

def test_connections_status_code(response, attach_curl_on_fail):
    """Test 1: Checks that the response status code is 200."""
    with attach_curl_on_fail(ENDPOINT, method="GET"):
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"

def test_connections_response_is_list(response_data, attach_curl_on_fail):
    """Test 2: Verifies that the response body is a list."""
    with attach_curl_on_fail(ENDPOINT, method="GET"):
        assert isinstance(response_data, list), f"Expected list, got {type(response_data)}"

def test_connections_response_structure(response_data, attach_curl_on_fail):
    """Test 3: Verifies that the response contains valid connection objects with proper structure."""
    with attach_curl_on_fail(ENDPOINT, method="GET"):
        # Проверяем, что это список
        assert isinstance(response_data, list), f"Expected list, got {type(response_data)}"
        
        # Если список не пустой, проверяем структуру каждого элемента
        if response_data:
            for i, connection in enumerate(response_data):
                assert isinstance(connection, dict), f"Connection {i} is not a dict: {type(connection)}"
                
                # Проверяем обязательные поля согласно схеме
                required_fields = ['proto', 'ether_type', 'id', 'dst_addr', 'src_addr', 
                                 'bytes', 'packets', 'state', 'status', 'repl_dst_port', 
                                 'repl_src_port', 'dst_port', 'src_port']
                
                for field in required_fields:
                    assert field in connection, f"Connection {i} missing required field: {field}"
                
                # Проверяем типы ключевых полей
                assert isinstance(connection['proto'], (str, int)), f"Connection {i} proto should be string or int, got {type(connection['proto'])}"
                assert isinstance(connection['ether_type'], str), f"Connection {i} ether_type should be string, got {type(connection['ether_type'])}"
                assert isinstance(connection['id'], int), f"Connection {i} id should be int, got {type(connection['id'])}"
                assert isinstance(connection['dst_addr'], str), f"Connection {i} dst_addr should be string, got {type(connection['dst_addr'])}"
                assert isinstance(connection['src_addr'], str), f"Connection {i} src_addr should be string, got {type(connection['src_addr'])}"
                
                # Проверяем, что порты являются числами
                assert isinstance(connection['dst_port'], int), f"Connection {i} dst_port should be int, got {type(connection['dst_port'])}"
                assert isinstance(connection['src_port'], int), f"Connection {i} src_port should be int, got {type(connection['src_port'])}"
                
                # Проверяем диапазон портов (0-65535)
                assert 0 <= connection['dst_port'] <= 65535, f"Connection {i} dst_port out of range: {connection['dst_port']}"
                assert 0 <= connection['src_port'] <= 65535, f"Connection {i} src_port out of range: {connection['src_port']}"
                
                # Проверяем, что bytes и packets неотрицательные
                assert connection['bytes'] >= 0, f"Connection {i} bytes should be non-negative, got {connection['bytes']}"
                assert connection['packets'] >= 0, f"Connection {i} packets should be non-negative, got {connection['packets']}"

# =====================================================================================================================
# Parametrized Stability Tests
# =====================================================================================================================

def generate_stability_params():
    """Generates 32 diverse parameter sets for stability testing."""
    return [
        ("proto", "tcp"), ("state", "ESTABLISHED"), ("src_addr", "192.168.1.100"),
        ("dst_addr", "10.0.0.5"), ("src_port", "12345"), ("dst_port", "443"),
        ("min_bytes", "1024"), ("min_packets", "10"), ("sort_by", "bytes"), ("sort_order", "desc"),
        ("fuzz_empty", ""), ("fuzz_long", "a" * 256), ("fuzz_special", "!@#$%^&*()"),
        ("fuzz_unicode", "тест"), ("fuzz_sql", "' OR 1=1;"), ("fuzz_xss", "<script>"),
        ("fuzz_path", "../etc/passwd"), ("fuzz_numeric", "12345"), ("fuzz_bool_true", "true"),
        ("fuzz_bool_false", "false"), ("fuzz_null", "null"), ("fuzz_none", None),
        ("fuzz_list[]", "a"), ("fuzz_dict[key]", "value"), ("fuzz_int", 100),
        ("fuzz_float", 99.9), ("fuzz_negative", -1), ("fuzz_zero", 0),
        ("fuzz_large_int", 9999999999), ("fuzz_uuid", "123e4567-e89b-12d3-a456-426614174000"),
        ("fuzz_mac", "00:1B:44:11:3A:B7"), ("fuzz_hostname", "server.local"),
    ]

@pytest.mark.parametrize("param, value", generate_stability_params())
def test_connections_stability_with_params(api_client, param, value, attach_curl_on_fail):
    """
    Tests 4-35: Ensures the endpoint consistently returns a 200 OK with valid response structure,
    regardless of the query parameters provided.
    """
    query_params = {param: value} if value is not None else param
    
    with attach_curl_on_fail(ENDPOINT, method="GET"):
        response = api_client.get(ENDPOINT, params=query_params)
        assert response.status_code == 200, f"Expected 200 for param '{param}', got {response.status_code}"
        
        data = response.json()
        # Проверяем, что это список (может быть пустым или содержать данные)
        assert isinstance(data, list), f"Expected list for param '{param}', got: {type(data)}"
        
        # Если есть данные, проверяем структуру первого элемента
        if data:
            connection = data[0]
            assert isinstance(connection, dict), f"First connection for param '{param}' is not a dict: {type(connection)}"
            
            # Проверяем наличие ключевых полей
            key_fields = ['proto', 'ether_type', 'id', 'dst_addr', 'src_addr']
            for field in key_fields:
                assert field in connection, f"Connection for param '{param}' missing field: {field}"
