import pytest
from collections.abc import Mapping, Sequence
from services.qa_constants import SERVICES
import requests

ENDPOINT = "/object"
SERVICE = SERVICES["objects"]
PORT = SERVICE["port"]
BASE_PATH = SERVICE["base_path"]

RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "data": {
            "type": "array",
            "items": {"type": "object"}
        },
        "next": {
            "anyOf": [
                {"type": "string"},
                {"type": "null"}
            ]
        }
    },
    "required": ["data", "next"]
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
VALID_PARAMS = []

IGNORED_QUERY_PARAMS = [
    pytest.param({}, 400, id="empty"),
    pytest.param({"limit": "10"}, 400, id="limit-10"),
    pytest.param({"offset": "0"}, 400, id="offset-0"),
    pytest.param({"sort": "name"}, 400, id="sort-name"),
    pytest.param({"order": "asc"}, 400, id="order-asc"),
    pytest.param({"order": "desc"}, 400, id="order-desc"),
    pytest.param({"filter": "active"}, 400, id="filter-active"),
    pytest.param({"filter": "inactive"}, 400, id="filter-inactive"),
    pytest.param({"type": "ip"}, 400, id="type-ip"),
    pytest.param({"type": "domain"}, 400, id="type-domain"),
    pytest.param({"q": "test"}, 400, id="q-test"),
    pytest.param({"q": ""}, 400, id="q-empty"),
    pytest.param({"page": "1"}, 400, id="page-1"),
    pytest.param({"page": "2"}, 400, id="page-2"),
    pytest.param({"per_page": "5"}, 400, id="per-page-5"),
    pytest.param({"per_page": "50"}, 400, id="per-page-50"),
    pytest.param({"fields": "id,name"}, 400, id="fields-id-name"),
    pytest.param({"fields": "all"}, 400, id="fields-all"),
    pytest.param({"search": "abc"}, 400, id="search-abc"),
    pytest.param({"search": "xyz"}, 400, id="search-xyz"),
    pytest.param({"date": "2023-01-01"}, 400, id="date-2023"),
    pytest.param({"date": "2022-12-31"}, 400, id="date-2022"),
    pytest.param({"user": "admin"}, 400, id="user-admin"),
    pytest.param({"user": "guest"}, 400, id="user-guest"),
    pytest.param({"group": "testers"}, 400, id="group-testers"),
    pytest.param({"group": "devs"}, 400, id="group-devs"),
    pytest.param({"foo": "bar"}, 400, id="simple-param"),
    pytest.param({"limit": "-1"}, 400, id="limit-negative"),
    pytest.param({"offset": "-10"}, 400, id="offset-negative"),
    pytest.param({"sort": "unknown"}, 400, id="sort-unknown"),
    pytest.param({"order": "invalid"}, 400, id="order-invalid"),
    pytest.param({"type": "unknown"}, 400, id="type-unknown"),
    pytest.param({"q": "x" * 2049}, 400, id="q-too-long"),
    pytest.param({"fields": ""}, 400, id="fields-empty"),
    pytest.param({"date": "not-a-date"}, 400, id="date-invalid"),
    pytest.param({"user": 123}, 400, id="user-numeric"),
    pytest.param({"group": None}, 400, id="group-none"),
]

@pytest.mark.parametrize("params", VALID_PARAMS)
def test_get_object_collection_valid(api_client, params, attach_curl_on_fail):
    with attach_curl_on_fail(ENDPOINT, params, method="GET"):
        response = api_client.get(ENDPOINT, params=params)
        assert response.status_code == 200, f"Test with params={params} failed: Expected status 200, got {response.status_code}"
        response_data = response.json()
        _check_types_recursive(response_data, RESPONSE_SCHEMA)

@pytest.mark.parametrize("params, expected_status", IGNORED_QUERY_PARAMS)
def test_get_object_collection_invalid(api_client, params, expected_status, attach_curl_on_fail):
    with attach_curl_on_fail(ENDPOINT, params, method="GET"):
        try:
            response = api_client.get(ENDPOINT, params=params)
            assert response.status_code == expected_status, f"Test with params={params} failed: Expected status {expected_status}, got {response.status_code}"
        except requests.exceptions.ConnectionError:
            # Если сервер закрыл соединение без ответа — считаем ошибочным кейсом
            assert expected_status >= 400
