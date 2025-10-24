import pytest
from jsonschema import validate
from services.qa_constants import SERVICES

ENDPOINT = "/routers/ospf/ospfDatabaseNetwork/count"
SERVICE = SERVICES["centec"]
PORT = SERVICE["port"]
BASE_PATH = SERVICE["base_path"]
HOST = SERVICE.get("host", "127.0.0.1")

SCHEMA = {
    "type": "object",
    "properties": {
        "count": {"type": "integer"}
    },
    "required": ["count"]
}

STABILITY_PARAMS = [
    ("limit", "10"),
    ("offset", "0"),
    ("page", "1"),
    ("q", "test"),
    ("q", ""),
    ("q", "тест"),
    ("q", "!@#$%^&*()"),
    ("q", "x"*100),
    ("count", "string"),
    ("count", "123"),
    ("count", ""),
    ("special", "!@#$%^&*()"),
    ("unicode", "тест"),
    ("verylong", "x"*100),
    ("bool", "true"),
    ("bool", "false"),
    ("null", "null"),
    ("array", "[1,2,3]"),
    ("json", '{"a":1}'),
    ("slash", "/"),
    ("dot", "."),
    ("space", " "),
    ("tab", "\t"),
    ("newline", "\n"),
    ("empty_param", None),
    ("empty_key", ""),
    ("zero", 0),
    ("negative", -1),
    ("large", 999999),
    ("float", 1.23),
    ("scientific", 1e6),
    ("bool_num", True),
    ("bool_num", False),
    ("foo", "bar"),
    ("param1", "val1"),
    ("param2", "val2"),
]

@pytest.mark.parametrize("param, value", STABILITY_PARAMS)
def test_ospf_database_network_count(api_client, attach_curl_on_fail, param, value):
    params = {param: value} if value is not None else {param: ""}
    with attach_curl_on_fail(ENDPOINT, params, None, "GET"):
        response = api_client.get(ENDPOINT, params=params)
        assert response.status_code == 200, f"Ожидался статус 200, получен {response.status_code}. Ответ: {response.text}"
        json_data = response.json()
        validate(instance=json_data, schema=SCHEMA) 