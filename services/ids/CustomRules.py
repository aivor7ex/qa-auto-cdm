import pytest
from jsonschema import validate
from services.qa_constants import SERVICES
from datetime import datetime

ENDPOINT = "/CustomRules"
SERVICE = SERVICES["ids"]
PORT = SERVICE["port"]
BASE_PATH = SERVICE["base_path"]

CUSTOMRULE_ITEM_SCHEMA = {
    "type": "object",
    "properties": {
        "created": {"type": "string"},
        "modified": {"type": "string"},
        "enabled": {"type": "boolean"},
        "content": {"type": "string"},
        "description": {"type": "string"},
        "id": {"type": "string"}
    },
    "required": ["created", "modified", "enabled", "content", "description", "id"]
}

ROOT_SCHEMA = {
    "type": "array",
    "items": CUSTOMRULE_ITEM_SCHEMA
}

PARAM_SCENARIOS = [
    ("enabled", True), ("enabled", False), ("description", "Мое тестовое правило"), ("content", "alert tcp"),
    ("sort", "created"), ("sort", "-created"), ("sort", "modified"), ("sort", "-modified"), ("sort", "description"), ("sort", "-description"),
    ("sort", "id"), ("sort", "-id"), ("limit", 1), ("limit", 10), ("offset", 1), ("limit", 1), ("offset", 1), ("limit", 0), ("limit", 9999),
    ("offset", 9999), ("description", "non_existent_description_xyz"), ("content", "non_existent_content_xyz"), ("id", "non_existent_id_xyz"),
    ("enabled", [True, False]), ("sort", ["-created", "description"]), ("sort", "invalid_field"), ("unexpected_param", "value"), ("limit", -1),
    ("offset", -1), ("limit", "abc"), ("offset", "abc"), ("description", "тест ✓"), ("content", "a(b|c)d"), ("q", "test"), ("q", ""),
    ("q", "тест"), ("q", "!@#$%^&*()"), ("q", "x"*100), ("count", "string"), ("count", "123"), ("count", ""), ("special", "!@#$%^&*()"),
    ("unicode", "тест"), ("verylong", "x"*100), ("bool", "true"), ("bool", "false"), ("null", "null"), ("array", "[1,2,3]"),
    ("json", '{"a":1}'), ("slash", "/"), ("dot", "."), ("space", " "), ("tab", "\t"), ("newline", "\n"), ("empty_param", None),
    ("empty_key", ""), ("zero", 0), ("negative", -1), ("large", 999999), ("float", 1.23), ("scientific", 1e6), ("bool_num", True), ("bool_num", False)
]

def is_iso8601(date_string):
    try:
        datetime.fromisoformat(date_string.replace("Z", "+00:00"))
        return True
    except (ValueError, TypeError):
        return False

@pytest.fixture(scope="module")
def response(api_client):
    return api_client.get(ENDPOINT)

@pytest.fixture(scope="module")
def response_json(response, attach_curl_on_fail):
    with attach_curl_on_fail(ENDPOINT, method="GET"):
        assert response.status_code == 200, f"Ожидался статус 200, получен {response.status_code}."
        json_data = response.json()
        validate(instance=json_data, schema=ROOT_SCHEMA)
        ids = [item["id"] for item in json_data]
        assert len(ids) == len(set(ids)), f"Duplicate IDs found."
        for item in json_data:
            assert is_iso8601(item["created"]), f"Invalid ISO8601 format for 'created': {item['created']}"
            assert is_iso8601(item["modified"]), f"Invalid ISO8601 format for 'modified': {item['modified']}"
        return json_data

@pytest.mark.parametrize("param, value", PARAM_SCENARIOS)
def test_customrules_parametrized(api_client, param, value, attach_curl_on_fail):
    params = {param: value} if value is not None else {param: ""}
    with attach_curl_on_fail(ENDPOINT, payload=params, method="GET"):
        response = api_client.get(ENDPOINT, params=params)
        assert response.status_code == 200, f"Ожидался статус 200, получен {response.status_code}. Ответ: {response.text}"
        json_data = response.json()
        validate(instance=json_data, schema=ROOT_SCHEMA)
        ids = [item["id"] for item in json_data]
        assert len(ids) == len(set(ids)), "Duplicate IDs found."
        for item in json_data:
            assert is_iso8601(item["created"]), f"Invalid ISO8601 format for 'created': {item['created']}"
            assert is_iso8601(item["modified"]), f"Invalid ISO8601 format for 'modified': {item['modified']}" 