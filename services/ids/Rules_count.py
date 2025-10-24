import pytest
from jsonschema import validate
from services.qa_constants import SERVICES

ENDPOINT = "/Rules/count"
SERVICE = SERVICES["ids"]
PORT = SERVICE["port"]
BASE_PATH = SERVICE["base_path"]

COUNT_SCHEMA = {
    "type": "object",
    "properties": {
        "count": {"type": "integer", "minimum": 0}
    },
    "required": ["count"]
}

PARAM_SCENARIOS = [
    ("limit", 1), ("limit", 0), ("limit", -1), ("limit", "abc"), ("offset", 1), ("offset", 0), ("offset", -1),
    ("offset", "abc"), ("sort", "id"), ("sort", "-count"), ("sort", "nonexistent_field"), ("q", "test"), ("q", ""),
    ("filter", "all"), ("filter", ""), ("filter", "{" + "a"*100 + ":1}"), ("param", "!@#$%^&*()_+-="), ("param", "тест"),
    ("param", "a"*1024), ("param", None), ("param", 123), ("param", True), ("param", [1,2,3]), ("param", {"a": "b"}),
    ("param", "1' OR '1'='1"), ("param", "<script>alert(1)</script>"), ("param", "a\0b"), ("p1", "v1"), ("p2", "v2"),
    ("p3", "v3"), ("a b", "c d"), ("@#$%^", "value"), ("p", "000123"), ("p", "value   "), ("unexpected", "param"),
    ("page", 1), ("limit", 100), ("sort", "asc"), ("q", "some_query"), ("zero", 0), ("negative", -1), ("large", 999999),
    ("float", 1.23), ("scientific", 1e6), ("bool_num", True), ("bool_num", False)
]

@pytest.fixture(scope="module")
def response(api_client):
    return api_client.get(ENDPOINT)

@pytest.fixture(scope="module")
def response_json(api_client, attach_curl_on_fail):
    with attach_curl_on_fail(ENDPOINT, payload=None, method="GET"):
        response = api_client.get(ENDPOINT)
        assert response.status_code == 200, f"Ожидался статус 200, получен {response.status_code}."
        json_data = response.json()
        validate(instance=json_data, schema=COUNT_SCHEMA)
        return json_data

@pytest.mark.parametrize("param, value", PARAM_SCENARIOS)
def test_rules_count_parametrized(api_client, param, value, attach_curl_on_fail):
    params = {param: value} if value is not None else {param: ""}
    with attach_curl_on_fail(ENDPOINT, payload=params, method="GET"):
        response = api_client.get(ENDPOINT, params=params)
        assert response.status_code == 200, f"Ожидался статус 200, получен {response.status_code}."
        json_data = response.json()
        validate(instance=json_data, schema=COUNT_SCHEMA) 