import pytest
from jsonschema import validate
from services.qa_constants import SERVICES

ENDPOINT = "/bonds/{id}/lacp-counters"
SERVICE = SERVICES["centec"]
PORT = SERVICE["port"]
BASE_PATH = SERVICE["base_path"]
HOST = SERVICE.get("host", "127.0.0.1")

RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "data": {"type": "string"}
    },
    "required": ["data"]
}

@pytest.fixture(scope="module")
def bond_ids(api_client):
    response = api_client.get("/bonds")
    if response.status_code != 200:
        pytest.skip("Could not retrieve bond list to get IDs.")
    response_json = response.json()
    if not isinstance(response_json, list) or not response_json:
        pytest.skip("Bond list is empty or not a list.")
    ids = [item.get("id") for item in response_json if "id" in item]
    if not ids:
        pytest.skip("No items with 'id' key found in /bonds response.")
    return ids

@pytest.mark.parametrize("bond_id", [pytest.param(None, marks=pytest.mark.skip(reason="dynamic"))])
def test_lacp_counters_per_bond(api_client, attach_curl_on_fail, bond_ids, bond_id):
    for bid in bond_ids:
        endpoint = ENDPOINT.replace("{id}", str(bid))
        with attach_curl_on_fail(endpoint, method="GET"):
            response = api_client.get(endpoint)
            assert response.status_code == 200, f"Ожидался статус 200, получен {response.status_code}."
            json_data = response.json()
            validate(instance=json_data, schema=RESPONSE_SCHEMA)

PARAM_SCENARIOS = [
    ("limit", "10"), ("limit", "0"), ("limit", "1000"), ("offset", "0"), ("offset", "100"), ("offset", "-1"),
    ("page", "1"), ("page", "999"), ("q", "test"), ("q", ""), ("q", "тест"), ("q", "!@#$%^&*()"),
    ("q", "x"*100), ("count", "string"), ("count", "123"), ("count", ""), ("special", "!@#$%^&*()"),
    ("unicode", "тест"), ("verylong", "x"*100), ("bool", "true"), ("bool", "false"), ("null", "null"),
    ("array", "[1,2,3]"), ("json", '{"a":1}'), ("slash", "/"), ("dot", "."), ("space", " "), ("tab", "\t"),
    ("newline", "\n"), ("empty_param", None), ("empty_key", ""), ("zero", 0), ("negative", -1), ("large", 999999),
    ("float", 1.23), ("scientific", 1e6), ("bool_num", True), ("bool_num", False)
]

@pytest.mark.parametrize("param, value", PARAM_SCENARIOS)
def test_lacp_counters_parametrized(api_client, attach_curl_on_fail, bond_ids, param, value):
    bid = bond_ids[0]
    endpoint = ENDPOINT.replace("{id}", str(bid))
    params = {param: value} if value is not None else {param: ""}
    with attach_curl_on_fail(endpoint, params, None, "GET"):
        response = api_client.get(endpoint, params=params)
        assert response.status_code == 200, f"Ожидался статус 200, получен {response.status_code}. Ответ: {response.text}"
        json_data = response.json()
        validate(instance=json_data, schema=RESPONSE_SCHEMA) 