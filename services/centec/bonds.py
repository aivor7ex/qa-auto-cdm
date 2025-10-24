import pytest
from jsonschema import validate
from services.qa_constants import SERVICES

ENDPOINT = "/bonds"
SERVICE = SERVICES["centec"]
PORT = SERVICE["port"]
BASE_PATH = SERVICE["base_path"]
HOST = SERVICE.get("host", "127.0.0.1")

BOND_ITEM_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "id": {"type": "integer"},
        "MAC": {"type": "string"},
        "mode": {"type": "string"},
        "lacp": {"type": "string"},
        "ofport": {"type": "string"},
        "greRef": {"type": "string"},
        "state": {"type": "string"},
        "speed": {"type": "string"},
        "slave": {"type": "array", "items": {"type": "string"}},
        "isShutdown": {"type": "boolean"}
    },
    "required": ["name", "id", "MAC", "mode", "lacp", "ofport", "greRef", "state", "speed", "slave", "isShutdown"]
}

ROOT_SCHEMA = {
    "type": "array",
    "items": BOND_ITEM_SCHEMA
}

PARAM_SCENARIOS = [
    ("limit", "10"), ("limit", "0"), ("limit", "1000"), ("offset", "0"), ("offset", "100"), ("offset", "-1"),
    ("page", "1"), ("page", "999"), ("q", "test"), ("q", ""), ("q", "тест"), ("q", "!@#$%^&*()"),
    ("q", "x"*100), ("count", "string"), ("count", "123"), ("count", ""), ("special", "!@#$%^&*()"),
    ("unicode", "тест"), ("verylong", "x"*100), ("bool", "true"), ("bool", "false"), ("null", "null"),
    ("array", "[1,2,3]"), ("json", '{"a":1}'), ("slash", "/"), ("dot", "."), ("space", " "), ("tab", "\t"),
    ("newline", "\n"), ("empty_param", None), ("empty_key", ""), ("zero", 0), ("negative", -1), ("large", 999999),
    ("float", 1.23), ("scientific", 1e6), ("bool_num", True), ("bool_num", False)
]

@pytest.fixture(scope="module")
def response(api_client, attach_curl_on_fail):
    with attach_curl_on_fail(ENDPOINT, method="GET"):
        return api_client.get(ENDPOINT)

@pytest.fixture(scope="module")
def response_json(response):
    assert response.status_code == 200, f"Ожидался статус 200, получен {response.status_code}."
    json_data = response.json()
    validate(instance=json_data, schema=ROOT_SCHEMA)
    return json_data

@pytest.mark.parametrize("param, value", PARAM_SCENARIOS)
def test_bonds_parametrized(api_client, attach_curl_on_fail, param, value):
    params = {param: value} if value is not None else {param: ""}
    with attach_curl_on_fail(ENDPOINT, params, None, "GET"):
        response = api_client.get(ENDPOINT, params=params)
        assert response.status_code == 200, f"Ожидался статус 200, получен {response.status_code}. Ответ: {response.text}"
        json_data = response.json()
        validate(instance=json_data, schema=ROOT_SCHEMA) 