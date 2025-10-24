import pytest
import re
from typing import Dict, Any

# =====================================================================================================================
# CA Certificates API Tests
# =====================================================================================================================
# Схема разделена на обязательные и опциональные поля для гибкости API
# Обязательные: startDate, endDate, fingerPrint, id
# Опциональные: consCountry, ST, L, O, OU, consId, issueCountry, issueId, organization
# =====================================================================================================================

# =====================================================================================================================
# Constants
# =====================================================================================================================

ENDPOINT = "/certificates/ca"

# Обязательные поля - всегда должны присутствовать
REQUIRED_FIELDS = {
    "startDate": str, "endDate": str, "fingerPrint": str, "id": str
}

# Опциональные поля - могут отсутствовать
OPTIONAL_FIELDS = {
    "consCountry": str, "ST": str, "L": str, "O": str, "OU": str,
    "consId": str, "issueCountry": str, "issueId": str, "organization": str
}

# Полная схема для проверки типов всех полей
RESPONSE_SCHEMA = {**REQUIRED_FIELDS, **OPTIONAL_FIELDS}

# =====================================================================================================================
# Fixtures
# =====================================================================================================================

@pytest.fixture(scope="module")
def response(api_client):
    """Provides the response from the endpoint."""
    return api_client.get(ENDPOINT)

@pytest.fixture(scope="module")
def response_data(response) -> Dict[str, Any]:
    """Provides the JSON data from the response, validating basic structure."""
    assert response.status_code == 200, f"Expected status 200, got {response.status_code}"
    data = response.json()
    assert isinstance(data, dict), f"Response root is not a dict, but {type(data).__name__}"
    return data

# =====================================================================================================================
# Test Cases
# =====================================================================================================================

def test_ca_status_code(response, attach_curl_on_fail):
    """Test 1: Checks that the response status code is 200."""
    with attach_curl_on_fail(ENDPOINT, method="GET"):
        assert response.status_code == 200

def test_ca_no_unexpected_fields(response_data, attach_curl_on_fail):
    """Test 2: Ensures no unexpected fields are in the response."""
    with attach_curl_on_fail(ENDPOINT, method="GET"):
        schema_keys = set(RESPONSE_SCHEMA.keys())
        response_keys = set(response_data.keys())
        unexpected = response_keys - schema_keys
        assert not unexpected, f"Found unexpected fields: {sorted(list(unexpected))}"
        
        # Проверяем, что все обязательные поля присутствуют
        missing_required = set(REQUIRED_FIELDS.keys()) - response_keys
        assert not missing_required, f"Missing required fields: {sorted(list(missing_required))}"

# --- Parameterized Tests for Field Validation ---

@pytest.mark.parametrize("field_name", REQUIRED_FIELDS.keys())
def test_ca_required_field_presence(response_data, field_name, attach_curl_on_fail):
    """Tests 3-6: Checks for the presence of each required field."""
    with attach_curl_on_fail(ENDPOINT, method="GET"):
        assert field_name in response_data, f"Required field '{field_name}' is missing."

@pytest.mark.parametrize("field_name", OPTIONAL_FIELDS.keys())
def test_ca_optional_field_presence(response_data, field_name, attach_curl_on_fail):
    """Tests 7-14: Checks for the presence of optional fields if they exist."""
    with attach_curl_on_fail(ENDPOINT, method="GET"):
        # Опциональные поля могут отсутствовать, но если присутствуют - должны быть корректными
        if field_name in response_data:
            field_value = response_data[field_name]
            assert isinstance(field_value, OPTIONAL_FIELDS[field_name]), \
                f"Optional field '{field_name}' should be type {OPTIONAL_FIELDS[field_name].__name__}, but is {type(field_value).__name__}."

@pytest.mark.parametrize("field_name, expected_type", RESPONSE_SCHEMA.items())
def test_ca_field_type(response_data, field_name, expected_type, attach_curl_on_fail):
    """Tests 15-24: Validates the data type of each field that is present."""
    with attach_curl_on_fail(ENDPOINT, method="GET"):
        if field_name in response_data:
            field_value = response_data[field_name]
            assert isinstance(field_value, expected_type), \
                f"Field '{field_name}' should be type {expected_type.__name__}, but is {type(field_value).__name__}."

@pytest.mark.parametrize("field_name", [k for k, v in RESPONSE_SCHEMA.items() if v is str])
def test_ca_string_field_not_empty(response_data, field_name, attach_curl_on_fail):
    """Tests 25-34: Ensures that string fields are not empty if present."""
    with attach_curl_on_fail(ENDPOINT, method="GET"):
        if field_name in response_data:
            field_value = response_data[field_name]
            assert field_value.strip() != "", f"String field '{field_name}' should not be empty if present."

@pytest.mark.parametrize("field_name", ["startDate", "endDate"])
def test_ca_date_format(response_data, field_name, attach_curl_on_fail):
    """Tests 35-36: Validates the format of date fields."""
    with attach_curl_on_fail(ENDPOINT, method="GET"):
        date_value = response_data[field_name]
        # API возвращает даты с переменным количеством пробелов перед днем
        # Например: "Aug  1 06:58:23 2025 GMT" (двойной пробел) или "Jul 30 06:58:23 2035 GMT" (одинарный пробел)
        pattern = r"^[A-Z][a-z]{2}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}\s+\d{4}\s+GMT$"
        assert re.match(pattern, date_value), \
            f"Field '{field_name}' value '{date_value}' does not match expected date format."

def test_ca_fingerprint_format(response_data, attach_curl_on_fail):
    """Test 37: Validates the format of the fingerPrint field."""
    with attach_curl_on_fail(ENDPOINT, method="GET"):
        fp_value = response_data["fingerPrint"]
        pattern = r"^([0-9A-F]{2}:){19}[0-9A-F]{2}$"
        assert re.match(pattern, fp_value), \
            f"Field 'fingerPrint' value '{fp_value}' does not match expected format."
