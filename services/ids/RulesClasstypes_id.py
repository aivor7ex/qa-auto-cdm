import pytest
from jsonschema import validate
from services.qa_constants import SERVICES
from datetime import datetime

ENDPOINT = "/RulesClasstypes"
SERVICE = SERVICES["ids"]
PORT = SERVICE["port"]
BASE_PATH = SERVICE["base_path"]

RULESCLASSTYPE_ITEM_SCHEMA = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
        "createdAt": {"type": "string"},
        "rulesCount": {"type": "integer"}
    },
    "required": ["id", "createdAt", "rulesCount"]
}

PARAM_SCENARIOS = [
    ("trojan-activity", 200), ("non-existent-classtype-12345", 404), (" ", 404), ("%20", 404), ("id/with/slashes", 404),
    ("id\\with\\backslashes", 404), ("id?with=query", 404), ("id#with_fragment", 404), ("", 200),
    ("VERY_LONG_ID_" + "A"*500, 404), ("utf8_id_✓", 404), ("id_with_!@#$%^&*()", 404), ("-1", 404), ("0", 404),
    ("1.1", 404), ("true", 404), ("false", 404), ("null", 400), ("undefined", 404), ("CAPITAL-ID", 404),
    ("MiXeD-CaSe-Id", 404), ("id_with_trailing_space ", 404), (" id_with_leading_space", 404), ("\n", 200), ("\t", 200),
    ("\r", 200), ("id-that-is-exactly-255-chars-long" * 8, 404), ("id-that-is-exactly-1024-chars-long" * 32, 404),
    ("another_nonexistent_id", 404), ("id-with-dash", 404), ("id_with_underscore", 404), (".", 200), ("..", 404),
    ("~", 404), ("`", 404), (":", 404)
]

def is_iso8601(date_string):
    try:
        datetime.fromisoformat(date_string.replace("Z", "+00:00"))
        return True
    except (ValueError, TypeError):
        return False

@pytest.mark.parametrize("item_id, expected_status", PARAM_SCENARIOS)
def test_rulesclasstypes_id_parametrized(api_client, item_id, expected_status, attach_curl_on_fail):
    endpoint = f"{ENDPOINT}/{item_id}"
    with attach_curl_on_fail(endpoint, method="GET"):
        response = api_client.get(endpoint)
        assert response.status_code == expected_status, f"Ожидался статус {expected_status}, получен {response.status_code}. Ответ: {response.text}"
        if item_id == "" and expected_status == 200:
            assert isinstance(response.json(), list), f"Expected list for empty ID, got {type(response.json())}."
        elif item_id in ("\n", "\t", "\r", ".") and expected_status == 200:
            assert isinstance(response.json(), list), f"Expected list for special/whitespace ID, got {type(response.json())}."
        elif expected_status == 200:
            json_data = response.json()
            validate(instance=json_data, schema=RULESCLASSTYPE_ITEM_SCHEMA)
            assert json_data["id"] == item_id, f"Response ID doesn't match requested ID."
            assert is_iso8601(json_data["createdAt"]), f"Invalid ISO8601 format for 'createdAt': {json_data['createdAt']}"