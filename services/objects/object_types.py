import pytest
from collections.abc import Mapping, Sequence
from services.qa_constants import SERVICES

ENDPOINT = "/object/types"
SERVICE = SERVICES["objects"]
PORT = SERVICE["port"]
BASE_PATH = SERVICE["base_path"]

RESPONSE_SCHEMA = {
    "type": "array",
    "items": {
        "type": "string",
        "minLength": 1
    },
    "minItems": 1,
    "uniqueItems": True
}

def _check_types_recursive(obj, schema):
    if "anyOf" in schema:
        assert any(_try_type(obj, s) for s in schema["anyOf"])
        return
    if schema.get("type") == "object":
        assert isinstance(obj, Mapping)
        for key, prop in schema.get("properties", {}).items():
            if key in obj:
                _check_types_recursive(obj[key], prop)
        for req in schema.get("required", []):
            assert req in obj
    elif schema.get("type") == "array":
        assert isinstance(obj, Sequence) and not isinstance(obj, str)
        for item in obj:
            _check_types_recursive(item, schema["items"])
    else:
        if schema.get("type") == "string":
            assert isinstance(obj, str)
        elif schema.get("type") == "integer":
            assert isinstance(obj, int)
        elif schema.get("type") == "boolean":
            assert isinstance(obj, bool)
        elif schema.get("type") == "null":
            assert obj is None

def _try_type(obj, schema):
    try:
        _check_types_recursive(obj, schema)
        return True
    except AssertionError:
        return False

# 25+ валидных GET-параметров
VALID_PARAMS = [
    pytest.param({}, id="empty"),
    pytest.param({"limit": "10"}, id="limit-10"),
    pytest.param({"offset": "0"}, id="offset-0"),
    pytest.param({"type": "ip"}, id="type-ip"),
    pytest.param({"type": "domain"}, id="type-domain"),
    pytest.param({"q": "test"}, id="q-test"),
    pytest.param({"page": "1"}, id="page-1"),
    pytest.param({"page": "2"}, id="page-2"),
    pytest.param({"per_page": "5"}, id="per-page-5"),
    pytest.param({"per_page": "50"}, id="per-page-50"),
    pytest.param({"fields": "id,name"}, id="fields-id-name"),
    pytest.param({"fields": "all"}, id="fields-all"),
    pytest.param({"search": "abc"}, id="search-abc"),
    pytest.param({"search": "xyz"}, id="search-xyz"),
    pytest.param({"date": "2023-01-01"}, id="date-2023"),
    pytest.param({"date": "2022-12-31"}, id="date-2022"),
    pytest.param({"user": "admin"}, id="user-admin"),
    pytest.param({"user": "guest"}, id="user-guest"),
    pytest.param({"group": "testers"}, id="group-testers"),
    pytest.param({"group": "devs"}, id="group-devs"),
    pytest.param({"active": "true"}, id="active-true"),
    pytest.param({"active": "false"}, id="active-false"),
    pytest.param({"sort": "name"}, id="sort-name"),
    pytest.param({"order": "asc"}, id="order-asc"),
    pytest.param({"order": "desc"}, id="order-desc"),
    pytest.param({"foo": "bar"}, id="simple-param"),
    pytest.param({"limit": "-1"}, id="limit-negative"),
    pytest.param({"offset": "-10"}, id="offset-negative"),
    pytest.param({"type": "unknown"}, id="type-unknown"),
    pytest.param({"q": "x" * 2049}, id="q-too-long"),
    pytest.param({"date": "not-a-date"}, id="date-invalid"),
]

@pytest.mark.parametrize("params", VALID_PARAMS)
def test_object_types_valid(api_client, params, attach_curl_on_fail):
    with attach_curl_on_fail(ENDPOINT, params, method="GET"):
        response = api_client.get(ENDPOINT, params=params)
        assert response.status_code == 200, f"Test with params={params} failed: Expected status 200, got {response.status_code}"
        response_data = response.json()
        _check_types_recursive(response_data, RESPONSE_SCHEMA)

@pytest.mark.parametrize("params", [pytest.param({"q": ""}, id="q-empty")])
def test_object_types_invalid_q_empty(api_client, params, attach_curl_on_fail):
    with attach_curl_on_fail(ENDPOINT, params, method="GET"):
        response = api_client.get(ENDPOINT, params=params)
        assert response.status_code == 400, f"Test with params={params} failed: Expected status 400, got {response.status_code}"
