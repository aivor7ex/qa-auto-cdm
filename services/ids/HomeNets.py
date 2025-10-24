import pytest
from jsonschema import validate
from services.qa_constants import SERVICES

ENDPOINT = "/HomeNets"
SERVICE = SERVICES["ids"]
PORT = SERVICE["port"]
BASE_PATH = SERVICE["base_path"]

HOMENET_ITEM_SCHEMA = {
    "type": "object",
    "properties": {
        "enabled": {"type": "boolean"},
        "name": {"type": "string"},
        "net": {"type": "string"},
        "id": {"type": "string"}
    },
    "required": ["enabled", "name", "net", "id"]
}

ROOT_SCHEMA = {
    "type": "array",
    "items": HOMENET_ITEM_SCHEMA
}

PARAM_SCENARIOS = [
    ("enabled", True), ("enabled", False), ("name", "My Local Network"), ("net", "192.168.1.0/24"),
    ("sort", "name"), ("sort", "-name"), ("sort", "net"), ("sort", "-net"), ("sort", "id"), ("sort", "-id"),
    ("limit", 1), ("limit", 10), ("offset", 1), ("limit", 1), ("offset", 1), ("limit", 0), ("limit", 9999),
    ("offset", 9999), ("name", "non_existent_name_xyz"), ("net", "10.255.255.1/32"), ("id", "non_existent_id_xyz"),
    ("enabled", [True, False]), ("sort", ["-name", "net"]), ("name", ["My Local Network", "Another Network"]),
    ("net", ["192.168.1.0/24", "10.0.0.0/8"]), ("id", ["685c01a7a64b4f003de5b5ba", "nonexistent"]),
    ("sort", "invalid_field"), ("unexpected_param", "value"), ("limit", -1), ("offset", -1), ("limit", "abc"),
    ("offset", "abc"), ("name", "сеть ✓"), ("net", "2001:db8::/32"), ("q", "test"), ("q", ""), ("q", "тест"),
    ("q", "!@#$%^&*()"), ("q", "x"*100), ("count", "string"), ("count", "123"), ("count", ""), ("special", "!@#$%^&*()"),
    ("unicode", "тест"), ("verylong", "x"*100), ("bool", "true"), ("bool", "false"), ("null", "null"),
    ("array", "[1,2,3]"), ("json", '{"a":1}'), ("slash", "/"), ("dot", "."), ("space", " "), ("tab", "\t"),
    ("newline", "\n"), ("empty_param", None), ("empty_key", ""), ("zero", 0), ("negative", -1), ("large", 999999),
    ("float", 1.23), ("scientific", 1e6), ("bool_num", True), ("bool_num", False)
]

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
        return json_data

@pytest.mark.parametrize("param, value", PARAM_SCENARIOS)
def test_homenets_parametrized(api_client, param, value, attach_curl_on_fail):
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