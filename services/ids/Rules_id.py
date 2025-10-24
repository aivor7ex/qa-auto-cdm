import pytest
import string
import urllib.parse
from qa_constants import SERVICES

# --- Constants ---
ENDPOINT = "Rules"
BASE_PATH_FOR_CURL = "/api/"
SERVICE_PORT = SERVICES["ids"]["port"]
VALID_RULE_ID = "CDM-1.rules-15003001"

# --- Schema Definitions ---
SCHEMA = {
    "id": str,
    "sid": str,
    "groupId": str,
    "message": str,
    "classtype": (str, type(None)),
    "details": dict,
    "meta": (dict, type(None))
}

DETAILS_SCHEMA = {
    "msg": str,
    "flow": (str, type(None)),
    "content": (list, type(None)),
    "classtype": (str, type(None)),
    "sid": int,
    "rev": int,
    "depth": (int, type(None)),
    "nocase": (bool, type(None)),
    "distance": (int, type(None)),
    "fast_pattern": (bool, type(None)),
    "within": (int, type(None)),
    "reference": (str, type(None)),
    "threshold": (str, type(None)),
    "flowbits": (list, type(None)),
    "metadata": (dict, type(None))
}

# --- Helper Functions ---
def validate_schema(data, schema, parent_key="root"):
    assert isinstance(data, dict), f"{parent_key} is not a dict."
    for key, expected_type in schema.items():
        is_optional = isinstance(expected_type, tuple)
        if key not in data:
            assert is_optional, f"Mandatory key '{key}' is missing from {parent_key}."
            continue
        value = data[key]
        allowed_types = expected_type if is_optional else (expected_type,)
        assert isinstance(value, allowed_types), \
            f"Key '{key}' in {parent_key} has wrong type. Expected {allowed_types}, got {type(value)}."

# --- Fixtures ---
@pytest.fixture
def rule_data(api_client, attach_curl_on_fail):
    with attach_curl_on_fail(f"/{ENDPOINT}/{VALID_RULE_ID}", method="GET"):
        response = api_client.get(f"/{ENDPOINT}/{VALID_RULE_ID}")
        assert response.status_code == 200, f"Failed to fetch rule with ID '{VALID_RULE_ID}'. Status {response.status_code}."
        data = response.json()
        validate_schema(data, SCHEMA)
        details = data.get("details")
        assert isinstance(details, dict), f"'details' field must be a dictionary."
        validate_schema(details, DETAILS_SCHEMA, parent_key="details")
        return data

# --- Test Data for Parameterization ---
STATUS_CODE_CASES = [
    (VALID_RULE_ID, 200, "valid_id"),
    ("", 200, "empty_id_returns_list"),
    ("non-existent-id", 404, "non_existent_id"),
    ("id_with_special_!@#", 404, "special_chars_id"),
    ("id_with_unicode_тест", 404, "unicode_id"),
    ("id-with-dash", 404, "dash_id"),
    ("id_with_underscore", 404, "underscore_id"),
    ("id.with.dot", 404, "dot_id"),
    ("id/with/slash", 404, "slash_id"),
    ("id\\with\\backslashes", 404, "backslash_id"),
    ("id with space", 404, "space_id"),
    ("id\twith\ttab", 404, "tab_id"),
    ("id\nwith\nnewline", 404, "newline_id"),
    ("id" + "a"*100, 404, "long_id_100"),
    ("id" + "b"*255, 404, "long_id_255"),
    ("id" + "c"*1024, 404, "long_id_1024"),
    ("0", 404, "zero_id"),
    ("-1", 404, "negative_id"),
    ("1.1", 404, "float_id"),
    ("true", 404, "bool_true_id"),
    ("false", 404, "bool_false_id"),
    ("null", 400, "null_string_id"),
    ("undefined", 404, "undefined_string_id"),
    ("CAPITAL-ID", 404, "capital_id"),
    ("MiXeD-CaSe-Id", 404, "mixed_case_id"),
    ("id_with_trailing_space ", 404, "trailing_space_id"),
    (" id_with_leading_space", 404, "leading_space_id"),
    ("id-that-is-exactly-255-chars-long" * 8, 404, "id_255_chars"),
    ("id-that-is-exactly-1024-chars-long" * 32, 404, "id_1024_chars"),
    ("another_nonexistent_id", 404, "another_nonexistent"),
    ("id-with-equals=sign", 404, "equals_sign_id"),
    ("id-with-ampersand&", 404, "ampersand_id"),
    ("id-with-question?mark", 404, "question_mark_id"),
    ("id-with-colon:", 404, "colon_id"),
    ("id-with-semicolon;", 404, "semicolon_id"),
    ("id-with-tilde~", 404, "tilde_id"),
    ("id-with-backtick`", 404, "backtick_id"),
    ("id-with-singlequote'", 404, "singlequote_id"),
    ("id-with-doublequote\"", 404, "doublequote_id"),
]

# --- Tests ---
@pytest.mark.ids
@pytest.mark.rules
def test_rule_by_id_schema_and_consistency(rule_data):
    data = rule_data
    validate_schema(data, SCHEMA)
    details = data.get("details")
    assert isinstance(details, dict), f"'details' field must be a dictionary."
    validate_schema(details, DETAILS_SCHEMA, parent_key="details")
    assert data["id"] == VALID_RULE_ID, f"Response ID doesn't match requested ID."
    assert str(details["sid"]) == data["sid"], f"SID mismatch between details and top-level."
    assert details["msg"] == data["message"], f"Message mismatch between details and top-level."
    assert details["classtype"] == data["classtype"], f"Classtype mismatch between details and top-level."
    assert details["sid"] > 0, f"SID should be positive."
    assert details["rev"] > 0, f"REV should be positive."
    if "content" in details and details["content"] is not None:
        assert all(isinstance(item, str) for item in details["content"]), f"All content items must be strings."

@pytest.mark.ids
@pytest.mark.rules
@pytest.mark.parametrize("rule_id, expected_status, test_id", STATUS_CODE_CASES)
def test_rule_by_id_status_codes(api_client, rule_id, expected_status, test_id, attach_curl_on_fail):
    with attach_curl_on_fail(f"/{ENDPOINT}/{rule_id}", method="GET"):
        response = api_client.get(f"/{ENDPOINT}/{rule_id}")
        assert response.status_code == expected_status, f"Expected {expected_status} for rule_id '{rule_id}', got {response.status_code}."
        if rule_id == "" and response.status_code == 200:
            assert isinstance(response.json(), list), f"Response for empty ID should be a list."
