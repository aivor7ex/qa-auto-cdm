import pytest
import json
from typing import Dict, Any, List

ENDPOINT = "/managers/iptablesStats"



# Схема ответа на основе API_EXAMPLE_RESPONSE_200_OK
RESPONSE_SCHEMA = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "match": {"type": "array", "items": {"type": "string"}},
            "line": {"type": "string"},
            "chain": {"type": "string"},
            "policy": {"type": "string"},
            "counter_packages": {"type": "integer"},
            "counter_bytes": {"type": "integer"},
            "mark": {"type": "string"},
            "target": {"type": "string"}
        },
        "required": ["match", "line", "chain", "counter_packages", "counter_bytes"],
        "optional": ["policy", "mark", "target"]
    }
}

def validate_response_schema(response_data: List[Dict[str, Any]]) -> None:
    """Валидация схемы ответа"""
    assert isinstance(response_data, list), f"Response must be a list"
    
    for item in response_data:
        assert isinstance(item, dict), f"Each item must be a dictionary"
        
        # Обязательные поля
        assert "match" in item, f"Missing required field 'match'"
        assert "line" in item, f"Missing required field 'line'"
        assert "chain" in item, f"Missing required field 'chain'"
        assert "counter_packages" in item, f"Missing required field 'counter_packages'"
        assert "counter_bytes" in item, f"Missing required field 'counter_bytes'"
        
        # Типы обязательных полей
        assert isinstance(item["match"], list), f"Field 'match' must be a list"
        assert isinstance(item["line"], str), f"Field 'line' must be a string"
        assert isinstance(item["chain"], str), f"Field 'chain' must be a string"
        assert isinstance(item["counter_packages"], int), f"Field 'counter_packages' must be an integer"
        assert isinstance(item["counter_bytes"], int), f"Field 'counter_bytes' must be an integer"
        
        # Валидация элементов match
        for match_item in item["match"]:
            assert isinstance(match_item, str), f"Match items must be strings"
        
        # Необязательные поля (проверяем только при наличии)
        if "policy" in item:
            assert isinstance(item["policy"], str), f"Field 'policy' must be a string"
        if "mark" in item:
            assert isinstance(item["mark"], str), f"Field 'mark' must be a string"
        if "target" in item:
            assert isinstance(item["target"], str), f"Field 'target' must be a string"

# Группа A: Валидные запросы iptables
@pytest.mark.parametrize("table,chain", [
    ("filter", "INPUT"),
    ("filter", "FORWARD"),
    ("nat", "PREROUTING"),
    ("nat", "OUTPUT"),
    ("mangle", "OUTPUT"),
    ("raw", "OUTPUT"),
])
def test_valid_iptables_requests(api_client, attach_curl_on_fail, table, chain):
    """Тест валидных запросов для различных таблиц и цепочек iptables"""
    payload = {"data": {"table": table, "chain": chain}}
    
    with attach_curl_on_fail(ENDPOINT, payload):
        response = api_client.post(ENDPOINT, json=payload)
        assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}"
        
        try:
            response_data = response.json()
        except json.JSONDecodeError as e:
            pytest.fail(f"Invalid JSON response: {e}")
        
        validate_response_schema(response_data)
        
        # Проверяем, что все элементы имеют правильную цепочку
        for item in response_data:
            assert item["chain"] == chain, f"All items must have chain '{chain}'"

# Группа B: Запросы с явным указанием util
@pytest.mark.parametrize("util,table,chain", [
    ("iptables", "filter", "INPUT"),
    ("arptables", "filter", "FORWARD"),
])
def test_with_util_parameter(api_client, attach_curl_on_fail, util, table, chain):
    """Тест запросов с явным указанием util"""
    payload = {"data": {"table": table, "chain": chain, "util": util}}
    
    with attach_curl_on_fail(ENDPOINT, payload):
        response = api_client.post(ENDPOINT, json=payload)
        assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}"
        
        try:
            response_data = response.json()
        except json.JSONDecodeError as e:
            pytest.fail(f"Invalid JSON response: {e}")
        
        validate_response_schema(response_data)

# Группа C: Негативные тесты
def test_missing_data_field(api_client, attach_curl_on_fail):
    """Тест отсутствия поля data"""
    payload = {"table": "filter", "chain": "INPUT"}
    
    with attach_curl_on_fail(ENDPOINT, payload):
        response = api_client.post(ENDPOINT, json=payload)
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        
        try:
            error_data = response.json()
            assert "error" in error_data or "message" in error_data, f"Error response must contain error or message field"
        except json.JSONDecodeError:
            pass  # Некоторые ошибки могут не возвращать JSON

def test_missing_table_in_data(api_client, attach_curl_on_fail):
    """Тест отсутствия table в data"""
    payload = {"data": {"chain": "INPUT"}}
    
    with attach_curl_on_fail(ENDPOINT, payload):
        response = api_client.post(ENDPOINT, json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        try:
            response_data = response.json()
            assert isinstance(response_data, list), f"Response must be a list"
        except json.JSONDecodeError as e:
            pytest.fail(f"Invalid JSON response: {e}")

def test_missing_chain_in_data(api_client, attach_curl_on_fail):
    """Тест отсутствия chain в data"""
    payload = {"data": {"table": "filter"}}
    
    with attach_curl_on_fail(ENDPOINT, payload):
        response = api_client.post(ENDPOINT, json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        try:
            response_data = response.json()
            assert isinstance(response_data, list), f"Response must be a list"
        except json.JSONDecodeError as e:
            pytest.fail(f"Invalid JSON response: {e}")

@pytest.mark.parametrize("invalid_table", [
    "nonexistent_table",
    "invalid",
    "test_table",
    "custom_table"
])
def test_nonexistent_table(api_client, attach_curl_on_fail, invalid_table):
    """Тест несуществующей таблицы"""
    payload = {"data": {"table": invalid_table, "chain": "INPUT"}}
    
    with attach_curl_on_fail(ENDPOINT, payload):
        response = api_client.post(ENDPOINT, json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        try:
            response_data = response.json()
            assert isinstance(response_data, list), f"Response must be a list"
        except json.JSONDecodeError as e:
            pytest.fail(f"Invalid JSON response: {e}")

@pytest.mark.parametrize("invalid_chain", [
    "nonexistent_chain",
    "invalid_chain",
    "test_chain",
    "custom_chain"
])
def test_nonexistent_chain(api_client, attach_curl_on_fail, invalid_chain):
    """Тест несуществующей цепочки"""
    payload = {"data": {"table": "filter", "chain": invalid_chain}}
    
    with attach_curl_on_fail(ENDPOINT, payload):
        response = api_client.post(ENDPOINT, json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        try:
            response_data = response.json()
            assert isinstance(response_data, list), f"Response must be a list"
        except json.JSONDecodeError as e:
            pytest.fail(f"Invalid JSON response: {e}")

@pytest.mark.parametrize("invalid_util", [
    "invalid_util",
    "ebtables",
    "ip6tables",
    "test_util"
])
def test_invalid_util_type(api_client, attach_curl_on_fail, invalid_util):
    """Тест неверного типа util"""
    payload = {"data": {"table": "filter", "chain": "INPUT", "util": invalid_util}}
    
    with attach_curl_on_fail(ENDPOINT, payload):
        response = api_client.post(ENDPOINT, json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        try:
            response_data = response.json()
            validate_response_schema(response_data)
        except json.JSONDecodeError as e:
            pytest.fail(f"Invalid JSON response: {e}")

def test_empty_data_object(api_client, attach_curl_on_fail):
    """Тест пустого объекта data"""
    payload = {"data": {}}
    
    with attach_curl_on_fail(ENDPOINT, payload):
        response = api_client.post(ENDPOINT, json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        try:
            response_data = response.json()
            assert isinstance(response_data, list), f"Response must be a list"
        except json.JSONDecodeError as e:
            pytest.fail(f"Invalid JSON response: {e}")

def test_null_values(api_client, attach_curl_on_fail):
    """Тест null значений"""
    payload = {"data": {"table": None, "chain": None}}
    
    with attach_curl_on_fail(ENDPOINT, payload):
        response = api_client.post(ENDPOINT, json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        try:
            response_data = response.json()
            assert isinstance(response_data, list), f"Response must be a list"
        except json.JSONDecodeError as e:
            pytest.fail(f"Invalid JSON response: {e}")

# Дополнительные edge cases
def test_empty_strings(api_client, attach_curl_on_fail):
    """Тест пустых строк"""
    payload = {"data": {"table": "", "chain": ""}}
    
    with attach_curl_on_fail(ENDPOINT, payload):
        response = api_client.post(ENDPOINT, json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        try:
            response_data = response.json()
            assert isinstance(response_data, list), f"Response must be a list"
        except json.JSONDecodeError as e:
            pytest.fail(f"Invalid JSON response: {e}")

def test_wrong_content_type(api_client, attach_curl_on_fail):
    """Тест неверного Content-Type"""
    payload = {"data": {"table": "filter", "chain": "INPUT"}}
    
    headers = {"Content-Type": "text/plain"}
    
    with attach_curl_on_fail(ENDPOINT, payload, headers):
        response = api_client.post(ENDPOINT, headers=headers, data=json.dumps(payload))
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"

def test_invalid_json(api_client, attach_curl_on_fail):
    """Тест невалидного JSON"""
    with attach_curl_on_fail(ENDPOINT, "invalid json data"):
        response = api_client.post(ENDPOINT, data="invalid json data")
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"

def test_extra_fields_in_data(api_client, attach_curl_on_fail):
    """Тест дополнительных полей в data"""
    payload = {
        "data": {
            "table": "filter",
            "chain": "INPUT",
            "extra_field": "extra_value",
            "another_field": 123
        }
    }
    
    with attach_curl_on_fail(ENDPOINT, payload):
        response = api_client.post(ENDPOINT, json=payload)
        # Должен игнорировать дополнительные поля
        assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}"
        
        try:
            response_data = response.json()
            validate_response_schema(response_data)
        except json.JSONDecodeError as e:
            pytest.fail(f"Invalid JSON response: {e}")

def test_wrong_data_types(api_client, attach_curl_on_fail):
    """Тест неверных типов данных"""
    payload = {"data": {"table": 123, "chain": 456}}
    
    with attach_curl_on_fail(ENDPOINT, payload):
        response = api_client.post(ENDPOINT, json=payload)
        # API не валидирует типы данных, а обрабатывает их как строки или возвращает пустой массив
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        try:
            response_data = response.json()
            assert isinstance(response_data, list), f"Response must be a list"
            # Для чисел API возвращает пустой массив, так как не находит соответствующие правила
            assert len(response_data) == 0, f"Expected empty array for invalid data types"
        except json.JSONDecodeError as e:
            pytest.fail(f"Invalid JSON response: {e}")

def test_long_strings(api_client, attach_curl_on_fail):
    """Тест длинных строк"""
    long_string = "a" * 1000
    payload = {"data": {"table": long_string, "chain": long_string}}
    
    with attach_curl_on_fail(ENDPOINT, payload):
        response = api_client.post(ENDPOINT, json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        try:
            response_data = response.json()
            validate_response_schema(response_data)
        except json.JSONDecodeError as e:
            pytest.fail(f"Invalid JSON response: {e}")

def test_special_characters(api_client, attach_curl_on_fail):
    """Тест специальных символов"""
    payload = {"data": {"table": "filter!@#$%", "chain": "INPUT!@#$%"}}
    
    with attach_curl_on_fail(ENDPOINT, payload):
        response = api_client.post(ENDPOINT, json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        try:
            response_data = response.json()
            validate_response_schema(response_data)
        except json.JSONDecodeError as e:
            pytest.fail(f"Invalid JSON response: {e}")

def test_unicode_characters(api_client, attach_curl_on_fail):
    """Тест Unicode символов"""
    payload = {"data": {"table": "фильтр", "chain": "вход"}}
    
    with attach_curl_on_fail(ENDPOINT, payload):
        response = api_client.post(ENDPOINT, json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        try:
            response_data = response.json()
            validate_response_schema(response_data)
        except json.JSONDecodeError as e:
            pytest.fail(f"Invalid JSON response: {e}")

def test_nested_data_structure(api_client, attach_curl_on_fail):
    """Тест вложенной структуры данных"""
    payload = {
        "data": {
            "table": {"nested": "filter"},
            "chain": {"nested": "INPUT"}
        }
    }
    
    with attach_curl_on_fail(ENDPOINT, payload):
        response = api_client.post(ENDPOINT, json=payload)
        # API не валидирует типы данных, а обрабатывает их как строки или возвращает пустой массив
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        try:
            response_data = response.json()
            assert isinstance(response_data, list), f"Response must be a list"
            # Для объектов API возвращает пустой массив, так как не находит соответствующие правила
            assert len(response_data) == 0, f"Expected empty array for nested data structure"
        except json.JSONDecodeError as e:
            pytest.fail(f"Invalid JSON response: {e}")

def test_array_data_types(api_client, attach_curl_on_fail):
    """Тест массивов вместо строк"""
    payload = {"data": {"table": ["filter"], "chain": ["INPUT"]}}
    
    with attach_curl_on_fail(ENDPOINT, payload):
        response = api_client.post(ENDPOINT, json=payload)
        # API может обрабатывать массивы как строки (берет первый элемент) или возвращать данные
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        try:
            response_data = response.json()
            assert isinstance(response_data, list), f"Response must be a list"
            # API может обработать массивы как строки, поэтому может вернуть данные
            if len(response_data) > 0:
                validate_response_schema(response_data)
        except json.JSONDecodeError as e:
            pytest.fail(f"Invalid JSON response: {e}")

def test_boolean_data_types(api_client, attach_curl_on_fail):
    """Тест булевых значений"""
    payload = {"data": {"table": True, "chain": False}}
    
    with attach_curl_on_fail(ENDPOINT, payload):
        response = api_client.post(ENDPOINT, json=payload)
        # API не валидирует типы данных, а обрабатывает их как строки или возвращает пустой массив
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        try:
            response_data = response.json()
            assert isinstance(response_data, list), f"Response must be a list"
            # Для булевых значений API возвращает пустой массив, так как не находит соответствующие правила
            assert len(response_data) == 0, f"Expected empty array for boolean data types"
        except json.JSONDecodeError as e:
            pytest.fail(f"Invalid JSON response: {e}")

def test_case_sensitivity(api_client, attach_curl_on_fail):
    """Тест чувствительности к регистру"""
    payload = {"data": {"table": "FILTER", "chain": "input"}}
    
    with attach_curl_on_fail(ENDPOINT, payload):
        response = api_client.post(ENDPOINT, json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        try:
            response_data = response.json()
            validate_response_schema(response_data)
        except json.JSONDecodeError as e:
            pytest.fail(f"Invalid JSON response: {e}")

def test_whitespace_handling(api_client, attach_curl_on_fail):
    """Тест обработки пробелов"""
    payload = {"data": {"table": " filter ", "chain": " INPUT "}}
    
    with attach_curl_on_fail(ENDPOINT, payload):
        response = api_client.post(ENDPOINT, json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        try:
            response_data = response.json()
            validate_response_schema(response_data)
        except json.JSONDecodeError as e:
            pytest.fail(f"Invalid JSON response: {e}")

def test_missing_auth_headers(api_client, attach_curl_on_fail):
    """Тест отсутствия заголовков авторизации"""
    payload = {"data": {"table": "filter", "chain": "INPUT"}}
    
    # Создаем клиент без авторизации
    import requests
    base_url = getattr(api_client, 'base_url', 'http://127.0.0.1:7779')
    full_url = f"{base_url.rstrip('/')}/api{ENDPOINT}"
    
    with attach_curl_on_fail(ENDPOINT, payload):
        response = requests.post(full_url, json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"

def test_invalid_auth_token(api_client, attach_curl_on_fail):
    """Тест неверного токена авторизации"""
    payload = {"data": {"table": "filter", "chain": "INPUT"}}
    
    headers = {"Authorization": "Bearer invalid_token", "Content-Type": "application/json"}
    
    # Создаем клиент с неверным токеном
    import requests
    base_url = getattr(api_client, 'base_url', 'http://127.0.0.1:7779')
    full_url = f"{base_url.rstrip('/')}/api{ENDPOINT}"
    
    with attach_curl_on_fail(ENDPOINT, payload, headers):
        response = requests.post(full_url, headers=headers, json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
