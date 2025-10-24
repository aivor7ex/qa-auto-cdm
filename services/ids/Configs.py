import pytest
from jsonschema import validate
from services.qa_constants import SERVICES

ENDPOINT = "/Configs"
SERVICE = SERVICES["ids"]
PORT = SERVICE["port"]
BASE_PATH = SERVICE["base_path"]

CONFIG_ITEM_SCHEMA = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
        "value": {}
    },
    "required": ["id", "value"]
}

ROOT_SCHEMA = {
    "type": "array",
    "items": CONFIG_ITEM_SCHEMA
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
def response(api_client):
    return api_client.get(ENDPOINT)

@pytest.fixture(scope="module")
def response_json(response, api_client, attach_curl_on_fail):
    with attach_curl_on_fail(ENDPOINT, method="GET"):
        assert response.status_code == 200, f"Ожидался статус 200, получен {response.status_code}."
        json_data = response.json()
        validate(instance=json_data, schema=ROOT_SCHEMA)
        ids = [item["id"] for item in json_data]
        assert len(ids) == len(set(ids)), f"Duplicate IDs found."
        return json_data

@pytest.mark.parametrize("param, value", PARAM_SCENARIOS)
def test_configs_parametrized(api_client, param, value, attach_curl_on_fail):
    params = {param: value} if value is not None else {param: ""}
    with attach_curl_on_fail(ENDPOINT, payload=params, method="GET"):
        response = api_client.get(ENDPOINT, params=params)
        assert response.status_code == 200, f"Ожидался статус 200, получен {response.status_code}. Ответ: {response.text}"
        json_data = response.json()
        validate(instance=json_data, schema=ROOT_SCHEMA)
        ids = [item["id"] for item in json_data]
        assert len(ids) == len(set(ids)), "Duplicate IDs found."
