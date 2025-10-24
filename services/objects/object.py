import json
import pytest
import requests
from collections.abc import Mapping, Sequence
from services.qa_constants import SERVICES
import uuid

ENDPOINT = "/object"
SERVICE = SERVICES["objects"]
PORT = SERVICE["port"]
BASE_PATH = SERVICE["base_path"]

# --- Response Schemas for GET and POST ---
response_schemas = {
    "GET": {
        "type": "object",
        "properties": {
            "data": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "type": {"type": "string"},
                        "name": {"type": "string"},
                        "contents": {
                            "type": "array",
                            "items": [
                                {"type": "string"},
                                {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "minItems": 3,
                                    "maxItems": 3
                                },
                                {"type": "string"}
                            ],
                            "minItems": 3,
                            "maxItems": 3
                        },
                        "count": {"type": "integer"}
                    },
                    "required": ["type", "name", "contents", "count"]
                }
            },
            "next": {
                "anyOf": [
                    {"type": "string"},
                    {"type": "null"}
                ]
            }
        },
        "required": ["data", "next"]
    },
    "POST": {
        "type": "object",
        "properties": {
            "ok": {"type": "boolean"}
        },
        "required": ["ok"]
    }
}

# --- Recursive schema validation ---
def _check_types_recursive(obj, schema):
    if "anyOf" in schema:
        assert any(_try_type(obj, s) for s in schema["anyOf"]), f"Value {obj} does not match anyOf {schema['anyOf']}"
        return
    if schema.get("type") == "object":
        assert isinstance(obj, Mapping), f"Expected object, got {type(obj)}"
        for key, prop in schema.get("properties", {}).items():
            if key in obj:
                _check_types_recursive(obj[key], prop)
        for req in schema.get("required", []):
            assert req in obj, f"Missing required field: {req}"
    elif schema.get("type") == "array":
        assert isinstance(obj, Sequence) and not isinstance(obj, str), f"Expected array, got {type(obj)}"
        if "items" in schema and isinstance(schema["items"], list):
            for idx, (item, item_schema) in enumerate(zip(obj, schema["items"])):
                _check_types_recursive(item, item_schema)
        else:
            for item in obj:
                _check_types_recursive(item, schema["items"])
    else:
        if schema.get("type") == "string":
            assert isinstance(obj, str), f"Expected string, got {type(obj)}"
        elif schema.get("type") == "integer":
            assert isinstance(obj, int), f"Expected integer, got {type(obj)}"
        elif schema.get("type") == "boolean":
            assert isinstance(obj, bool), f"Expected boolean, got {type(obj)}"
        elif schema.get("type") == "null":
            assert obj is None, f"Expected null, got {type(obj)}"

def _try_type(obj, schema):
    try:
        _check_types_recursive(obj, schema)
        return True
    except AssertionError:
        return False

def _check_agent_verification(payload):
    """
    Проверяет через агента, что объект действительно был добавлен в систему.
    
    Args:
        payload: Данные, которые были отправлены в POST запросе
        
    Returns:
        bool: True если объект найден, False если не найден, None если проверка пропущена, "unavailable" если агент недоступен
    """
    try:
        # Извлекаем имя объекта из payload
        if isinstance(payload, dict) and "name" in payload:
            object_name = payload["name"]
        else:
            # Если payload не является словарем или не содержит name, пропускаем проверку
            return None
            
        # Отправляем запрос к агенту
        agent_url = "http://localhost:8000/api/object"
        agent_payload = {
            "name": object_name,
            "type": payload.get("type", "ip"),
            "contents": payload.get("contents", [])
        }
        
        print(f"Agent verification request: {json.dumps(agent_payload, indent=2)}")
        response = requests.post(agent_url, json=agent_payload, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            # Accept both "OK"/"ok" and legacy empty dict as success
            if isinstance(result, dict):
                res_val = result.get("result")
                if isinstance(res_val, str) and res_val.lower() == "ok":
                    return True
                if result == {}:
                    return True
            return False
        else:
            print(f"Agent verification failed with status {response.status_code}: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"Agent verification request failed: {e}")
        return "unavailable"  # Агент недоступен
    except Exception as e:
        print(f"Agent verification error: {e}")
        return "unavailable"  # Агент недоступен

# --- GET tests (оставляем как есть, только схему меняем на response_schemas["GET"]) ---
NEGATIVE_PARAMS = [
    pytest.param({}, 400, id="empty"),
    pytest.param({"type": "ip"}, 400, id="type-ip"),
    pytest.param({"type": "domain"}, 400, id="type-domain"),
    pytest.param({"name": "admins"}, 400, id="name-admins"),
    pytest.param({"name": "guests"}, 400, id="name-guests"),
    pytest.param({"count": "2"}, 400, id="count-2"),
    pytest.param({"count": "0"}, 400, id="count-0"),
    pytest.param({"q": "test"}, 400, id="q-test"),
    pytest.param({"q": "range"}, 400, id="q-range"),
    pytest.param({"q": "10.10.1.1"}, 400, id="q-ip1"),
    pytest.param({"q": "10.10.2.5"}, 400, id="q-ip2"),
    pytest.param({"q": "10.10.0.1/24"}, 400, id="q-cidr"),
    pytest.param({"page": "1"}, 400, id="page-1"),
    pytest.param({"page": "2"}, 400, id="page-2"),
    pytest.param({"per_page": "5"}, 400, id="per-page-5"),
    pytest.param({"per_page": "50"}, 400, id="per-page-50"),
    pytest.param({"fields": "type,name"}, 400, id="fields-type-name"),
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
    pytest.param({"limit": "10"}, 400, id="limit-10"),
    pytest.param({"offset": "0"}, 400, id="offset-0"),
    pytest.param({"sort": "name"}, 400, id="sort-name"),
    pytest.param({"order": "asc"}, 400, id="order-asc"),
    pytest.param({"order": "desc"}, 400, id="order-desc"),
    pytest.param({"filter": "active"}, 400, id="filter-active"),
    pytest.param({"filter": "inactive"}, 400, id="filter-inactive"),
    pytest.param({"type": "unknown"}, 400, id="type-unknown"),
    pytest.param({"q": "x" * 2049}, 400, id="q-too-long"),
    pytest.param({"fields": ""}, 400, id="fields-empty"),
    pytest.param({"date": "not-a-date"}, 400, id="date-invalid"),
    pytest.param({"user": 123}, 400, id="user-numeric"),
    pytest.param({"group": None}, 400, id="group-none"),
]

@pytest.mark.parametrize("params, expected_status", NEGATIVE_PARAMS)
def test_get_object_collection_negative(api_client, params, expected_status, attach_curl_on_fail):
    headers = getattr(api_client, 'headers', {})
    with attach_curl_on_fail(ENDPOINT, params, headers, "GET"):
        response = api_client.get(ENDPOINT, params=params)
        assert response.status_code == expected_status, f"Expected status {expected_status}, got {response.status_code}"

# --- POST tests ---
POST_VALID_CASES = [
    pytest.param({
        "name": f"pytest_obj1_{uuid.uuid4().hex[:8]}",
        "type": "ip",
        "contents": [
            "value",
            ["range", "10.10.1.1", "10.10.2.5"],
            "10.10.0.1/24"
        ]
    }, 200, id="valid-ip-range"),
    pytest.param({
        "name": f"pytest_obj2_{uuid.uuid4().hex[:8]}",
        "type": "ip",
        "contents": [
            "value",
            ["range", "192.168.1.1", "192.168.1.10"],
            "192.168.1.0/24"
        ]
    }, 200, id="valid-ip-range-2"),
    pytest.param({
        "name": f"pytest_ip_list_{uuid.uuid4().hex[:8]}",
        "type": "ip",
        "contents": [
            "value",
            "203.0.113.1",
            "203.0.113.2",
            "203.0.113.3"
        ]
    }, 200, id="valid-ip-list"),
    pytest.param({
        "name": f"pytest_single_ip_{uuid.uuid4().hex[:8]}",
        "type": "ip",
        "contents": [
            "value",
            "8.8.8.8",
            "1.1.1.1"
        ]
    }, 200, id="valid-single-ips"),
    pytest.param({
        "name": f"pytest_cidr_{uuid.uuid4().hex[:8]}",
        "type": "ip",
        "contents": [
            "value",
            "10.0.0.0/8",
            "192.168.0.0/16"
        ]
    }, 200, id="valid-cidr-blocks"),
]

POST_INVALID_CASES = [
    # Неизвестный тип
    pytest.param({
        "name": "pytest_broken1",
        "type": "none",
        "contents": ["value", 1]
    }, 400, id="unknown-type"),
    # Некорректное значение contents
    pytest.param({
        "name": "pytest_broken2",
        "type": "ip",
        "contents": ["xxx"]
    }, 400, id="invalid-contents"),
    # Некорректный JSON (будет отправлен как строка)
    pytest.param('{"name": "broken", "type": "ip", "contents": }', 400, id="invalid-json"),
    # Пустое тело
    pytest.param('', 400, id="empty-body"),
    # Неизвестная команда
    pytest.param({"foo": "bar"}, 400, id="unknown-command"),
]

@pytest.mark.parametrize("payload, expected_status", POST_VALID_CASES + POST_INVALID_CASES)
def test_post_object(api_client, payload, expected_status, attach_curl_on_fail):
    headers = {"Content-Type": "application/json"}
    with attach_curl_on_fail(ENDPOINT, payload, headers, "POST"):
        # Для некорректного JSON и пустого тела отправляем data, иначе json
        if isinstance(payload, str):
            response = api_client.post(ENDPOINT, data=payload, headers=headers)
        else:
            response = api_client.post(ENDPOINT, json=payload, headers=headers)
        assert response.status_code == expected_status, f"Expected status {expected_status}, got {response.status_code}"
        if expected_status == 201:
            _check_types_recursive(response.json(), response_schemas["POST"])
        
        # Дополнительная проверка через агента для валидных случаев
        if expected_status == 200 and isinstance(payload, dict):
            print(f"Checking agent verification for valid test: {payload.get('name', 'unknown')}")
            agent_result = _check_agent_verification(payload)
            if agent_result == "unavailable":
                pytest.fail(f"Agent verification unavailable: agent is not reachable for object: {payload.get('name', 'unknown')}")
            elif agent_result is not None:  # Проверка выполнилась
                if agent_result:
                    print(f"Agent verification: Object '{payload.get('name', 'unknown')}' was successfully added")
                else:
                    pytest.fail(f"Agent verification failed: Object '{payload.get('name', 'unknown')}' was not found in the system")
            else:
                print(f"Agent verification skipped for payload: {payload}")
        elif expected_status == 400:
            print(f"Skipping agent verification for invalid test (status 400): {payload if isinstance(payload, dict) else str(payload)[:50]}")
        else:
            print(f"Test completed with status {expected_status}") 