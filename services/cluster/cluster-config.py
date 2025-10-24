import pytest
from collections.abc import Mapping, Sequence
from qa_constants import SERVICES

ENDPOINT = "/cluster-config"

NODE_SCHEMA = {
    "type": "object",
    "properties": {
        "id": {"type": "string"}, "name": {"type": "string"}, "status": {"type": "string"},
        "role": {"type": "string"}, "ip": {"type": "string"}, "uptime": {"type": "string"},
        "version": {"type": "string"}, "labels": {"type": "array", "items": {"type": "string"}},
        "meta": {"type": "object"},
    },
    "required": ["id", "name", "status", "role", "ip", "uptime", "version", "labels", "meta"],
}

NETWORK_SCHEMA = {
    "type": "object",
    "properties": {
        "id": {"type": "string"}, "name": {"type": "string"}, "cidr": {"type": "string"},
        "type": {"type": "string"}, "vlan": {"type": "integer"}, "gateway": {"type": "string"},
    },
    "required": ["id", "name", "cidr", "type", "vlan", "gateway"],
}

CLUSTER_INFO_SCHEMA = {
    "type": "object",
    "properties": {
        "id": {"type": "string"}, "name": {"type": "string"}, "type": {"type": "string"},
        "status": {"type": "string"}, "created": {"type": "string"}, "modified": {"type": "string"},
    },
    "required": ["id", "name", "type", "status", "created", "modified"],
}

ROOT_SCHEMA = {
    "type": "object",
    "properties": {
        "nodes": {"type": "array", "items": NODE_SCHEMA},
        "networks": {"type": "array", "items": NETWORK_SCHEMA},
        "cluster": CLUSTER_INFO_SCHEMA,
        "shards": {"type": "array", "items": {"type": "object"}},
        "services": {"type": "array", "items": {"type": "object"}},
        "_id": {"type": "string"}, "name": {"type": "string"}, "type": {"type": "string"},
        "description": {"type": "string"}, "config": {"type": "object"},
        "created": {"type": "string"}, "modified": {"type": "string"},
    },
    "required": ["nodes", "networks", "cluster", "_id", "name", "type", "created", "modified"],
}

ERROR_400_SCHEMA = {
    "type": "object",
    "properties": {
        "statusCode": {"type": "integer", "const": 400},
        "message": {"type": "string"}
    },
    "required": ["statusCode", "message"]
}

PARAMS = [
    ({}, 400),
    ({"filter": '{"nodes.role":"master"}'}, 400),
    ({"sort": "cluster.name"}, 400),
    ({"limit": 5}, 400),
    ({"offset": 1}, 400),
    ({"page": 2, "perPage": 10}, 400),
    ({"q": "search"}, 400),
    ({"fields": "nodes,networks"}, 400),
    ({"param_with_space": "a b"}, 400),
    ({"param_with_special": "!@$*()"}, 400),
    ({"unicode_param": "тест"}, 400),
    ({"numeric_param": 123}, 400),
    ({"bool_param": False}, 400),
    ({"null_param": None}, 400),
    ({"empty_param": ""}, 400),
    ({"long_param": "c" * 1024}, 400),
    ({"very_long_value": "z" * 2048}, 400),
    ({"injection_sqli": "' OR 1=1 --"}, 400),
    ({"injection_nosql": '{"$where": "true"}'}, 400),
    ({"UPPER_CASE": "VALUE"}, 400),
    ({"lower_case": "value"}, 400),
    ({"_t": 987654321}, 400),
    ({"id-with-dashes": "id-1"}, 400),
    ({"param.with.dots": "v.1"}, 400),
    ({"mix": "str", "num": 987, "b": True}, 400),
    ({"k1": "v1", "k2": "v2", "k3": "v3"}, 400),
    ({"p1": "v1", "p2": "v2"}, 400),
    ({"filter[field][op]": "value"}, 400),
    ({"array[]": "item1,item2"}, 400),
    ({"nested[deep][level]": "val"}, 400),
    ({"cluster_id": "some-id"}, 400),
    ({"version": "1.2.3"}, 400),
    ({"show_details": "true"}, 400),
    ({"include_meta": "false"}, 400),
    ({"check_if_created": "true"}, 200),
]

def _check_types_recursive(obj, schema):
    if "anyOf" in schema:
        assert any(_try_type(obj, s) for s in schema["anyOf"]), f"Тип {type(obj)} не соответствует anyOf"
        return
    if schema.get("type") == "object":
        assert isinstance(obj, Mapping), f"Ожидался объект, получено: {type(obj)}"
        for key, prop in schema.get("properties", {}).items():
            if key in obj:
                _check_types_recursive(obj[key], prop)
        for req in schema.get("required", []):
            assert req in obj, f"Обязательное поле '{req}' отсутствует"
    elif schema.get("type") == "array":
        assert isinstance(obj, Sequence) and not isinstance(obj, str), f"Ожидался список, получено: {type(obj)}"
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

@pytest.mark.parametrize("params, expected_status", PARAMS)
def test_cluster_config_robustness(api_client, params, expected_status, attach_curl_on_fail):
    with attach_curl_on_fail(ENDPOINT, params, method="GET"):
        response = api_client.get(ENDPOINT, params=params)
        # Искусственно вызовем ошибку для проверки вывода cURL (убрать после проверки):
        # if params == {}:
        #     assert False, "Проверка вывода cURL"
        if expected_status == 200 and response.status_code == 400:
            data = response.json()
            assert data.get("message") == "CLUSTER_IS_NOT_CREATED"
            return
        if expected_status == 400 and response.status_code == 400:
            data = response.json()
            _check_types_recursive(data, ERROR_400_SCHEMA)
            return
        assert response.status_code == expected_status
        if response.status_code == 200:
            data = response.json()
            _check_types_recursive(data, ROOT_SCHEMA)
