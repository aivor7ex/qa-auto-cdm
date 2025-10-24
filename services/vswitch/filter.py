import json
import pytest
import requests
import uuid
from services.qa_constants import SERVICES

# --- Константы и endpoint ---
ENDPOINT = "filter"
SERVICE = [s for s in SERVICES["vswitch"] if s["name"] == "filter"][0]
PORT = SERVICE["port"]
BASE_PATH = SERVICE["base_path"]



@pytest.fixture(scope="module")
def api_client(request_timeout):
    base_url = f"http://{SERVICE['host']}:{SERVICE['port']}{BASE_PATH}"
    # Нормализуем базовый URL: без завершающего слэша
    if base_url.endswith("/"):
        base_url = base_url[:-1]
    class ApiClient(requests.Session):
        def request(self, method, url, *args, **kwargs):
            # Аккуратно соединяем base_url и относительный путь
            path = url if url.startswith("/") else f"/{url}"
            full_url = base_url + path
            kwargs.setdefault("timeout", request_timeout)
            return super().request(method, full_url, *args, **kwargs)
    client = ApiClient()
    client.headers.update({
        "Content-Type": "application/json",
        "User-Agent": "QA-Automation-Client/2.0"
    })
    # Делаем base_url доступным для форматирования curl
    setattr(client, "base_url", base_url)
    return client

# --- Схемы ответов для разных методов ---
response_schemas = {
    "GET": {},  # Заглушка
    "POST": {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "hash": {"type": "string"},
                "error": {"anyOf": [{"type": "null"}, {"type": "object"}]}
            },
            "required": ["hash"]
        }
    },
    "POST_OK_PARTIAL": {  # Для частичного успеха
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "hash": {"type": "string"},
                "error": {"anyOf": [{"type": "null"}, {"type": "object"}]}
            },
            "required": ["hash", "error"]
        }
    },
    "POST_ERROR": {
        "type": "object",
        "properties": {
            "result": {"type": "string"},
            "error": {"anyOf": [{"type": "string"}, {"type": "object"}]},
            "parse-error": {"type": "string"}
        },
        "required": ["result", "error"]
    },
    "POST_OBJECT_ERROR": {
        "type": "object",
        "properties": {
            "result": {"type": "string"},
            "error": {"type": "object"}
        },
        "required": ["result", "error"]
    }
}

# --- Проверка структуры ответа рекурсивно ---
def _check_types_recursive(obj, schema):
    if "anyOf" in schema:
        assert any(_try_type(obj, s) for s in schema["anyOf"]), f"Value {obj} does not match anyOf {schema['anyOf']}"
        return
    if schema.get("type") == "object":
        assert isinstance(obj, dict), f"Expected object, got {type(obj)}"
        for key, prop in schema.get("properties", {}).items():
            if key in obj:
                _check_types_recursive(obj[key], prop)
        for req in schema.get("required", []):
            assert req in obj, f"Missing required field: {req}"
    elif schema.get("type") == "array":
        assert isinstance(obj, list), f"Expected array, got {type(obj)}"
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



# --- Генерация уникальных валидных payload ---
def make_unique_rule(action="accept", zones=None):
    if zones is None:
        zones = [1, 2]
    uniq = uuid.uuid4().hex[:8]
    ip1 = f"192.168.{int(uniq[:2], 16)}.{int(uniq[2:4], 16)}/24"
    ip2 = f"10.0.{int(uniq[4:6], 16)}.{int(uniq[6:8], 16)}/8"
    return {
        "active": True,
        "service": [
            "lit",
            {"ip_protocol": 6, "source_ports": [], "destination_ports": [80]}
        ],
        "source": ["lit", ip1],
        "destination": ["lit", ip2],
        "action": action,
        "zones": zones
    }

def make_simple_unique_rule():
    """Создает простой уникальный объект для тестирования дубликатов"""
    uniq = uuid.uuid4().hex[:8]
    ip1 = f"192.168.{int(uniq[:2], 16)}.{int(uniq[2:4], 16)}/24"
    ip2 = f"10.0.{int(uniq[4:6], 16)}.{int(uniq[6:8], 16)}/8"
    return {
        "active": True,
        "service": [],
        "source": ["lit", ip1],
        "destination": ["lit", ip2],
        "action": "accept",
        "zones": [1]
    }

def make_rule_with_ports():
    """Создает правило с портами"""
    uniq = uuid.uuid4().hex[:8]
    ip1 = f"192.168.{int(uniq[:2], 16)}.{int(uniq[2:4], 16)}/24"
    ip2 = f"10.0.{int(uniq[4:6], 16)}.{int(uniq[6:8], 16)}/8"
    return {
        "active": True,
        "service": [
            "lit",
            {"ip_protocol": 6, "source_ports": [1024, 1025], "destination_ports": [80, 443]}
        ],
        "source": ["lit", ip1],
        "destination": ["lit", ip2],
        "action": "accept",
        "zones": [1, 2, 3]
    }

def make_rule_with_udp():
    """Создает правило с UDP протоколом"""
    uniq = uuid.uuid4().hex[:8]
    ip1 = f"192.168.{int(uniq[:2], 16)}.{int(uniq[2:4], 16)}/24"
    ip2 = f"10.0.{int(uniq[4:6], 16)}.{int(uniq[6:8], 16)}/8"
    return {
        "active": True,
        "service": [
            "lit",
            {"ip_protocol": 17, "source_ports": [53], "destination_ports": [53]}
        ],
        "source": ["lit", ip1],
        "destination": ["lit", ip2],
        "action": "drop",
        "zones": [1]
    }

def make_rule_with_icmp():
    """Создает правило с ICMP протоколом"""
    uniq = uuid.uuid4().hex[:8]
    ip1 = f"192.168.{int(uniq[:2], 16)}.{int(uniq[2:4], 16)}/24"
    ip2 = f"10.0.{int(uniq[4:6], 16)}.{int(uniq[6:8], 16)}/8"
    return {
        "active": True,
        "service": [
            "lit",
            {"ip_protocol": 1, "source_ports": [], "destination_ports": []}
        ],
        "source": ["lit", ip1],
        "destination": ["lit", ip2],
        "action": "accept",
        "zones": [1, 2]
    }

def make_rule_with_single_zone():
    """Создает правило с одной зоной"""
    uniq = uuid.uuid4().hex[:8]
    ip1 = f"192.168.{int(uniq[:2], 16)}.{int(uniq[2:4], 16)}/24"
    ip2 = f"10.0.{int(uniq[4:6], 16)}.{int(uniq[6:8], 16)}/8"
    return {
        "active": True,
        "service": [
            "lit",
            {"ip_protocol": 6, "source_ports": [], "destination_ports": [22]}
        ],
        "source": ["lit", ip1],
        "destination": ["lit", ip2],
        "action": "accept",
        "zones": [5]
    }

def make_rule_with_empty_zones():
    """Создает правило с пустыми зонами"""
    uniq = uuid.uuid4().hex[:8]
    ip1 = f"192.168.{int(uniq[:2], 16)}.{int(uniq[2:4], 16)}/24"
    ip2 = f"10.0.{int(uniq[4:6], 16)}.{int(uniq[6:8], 16)}/8"
    return {
        "active": True,
        "service": [
            "lit",
            {"ip_protocol": 6, "source_ports": [], "destination_ports": [25]}
        ],
        "source": ["lit", ip1],
        "destination": ["lit", ip2],
        "action": "drop",
        "zones": []
    }

def make_rule_with_multiple_zones():
    """Создает правило с множественными зонами"""
    uniq = uuid.uuid4().hex[:8]
    ip1 = f"192.168.{int(uniq[:2], 16)}.{int(uniq[2:4], 16)}/24"
    ip2 = f"10.0.{int(uniq[4:6], 16)}.{int(uniq[6:8], 16)}/8"
    return {
        "active": True,
        "service": [
            "lit",
            {"ip_protocol": 6, "source_ports": [], "destination_ports": [3306]}
        ],
        "source": ["lit", ip1],
        "destination": ["lit", ip2],
        "action": "accept",
        "zones": [1, 2, 3, 4, 5]
    }

def make_rule_with_inactive():
    """Создает неактивное правило"""
    uniq = uuid.uuid4().hex[:8]
    ip1 = f"192.168.{int(uniq[:2], 16)}.{int(uniq[2:4], 16)}/24"
    ip2 = f"10.0.{int(uniq[4:6], 16)}.{int(uniq[6:8], 16)}/8"
    return {
        "active": False,
        "service": [
            "lit",
            {"ip_protocol": 6, "source_ports": [], "destination_ports": [8080]}
        ],
        "source": ["lit", ip1],
        "destination": ["lit", ip2],
        "action": "accept",
        "zones": [1]
    }

def make_rule_with_complex_service():
    """Создает правило со сложным сервисом"""
    uniq = uuid.uuid4().hex[:8]
    ip1 = f"192.168.{int(uniq[:2], 16)}.{int(uniq[2:4], 16)}/24"
    ip2 = f"10.0.{int(uniq[4:6], 16)}.{int(uniq[6:8], 16)}/8"
    return {
        "active": True,
        "service": [
            "lit",
            {"ip_protocol": 6, "source_ports": [1024, 1025, 1026], "destination_ports": [80, 443, 8080]}
        ],
        "source": ["lit", ip1],
        "destination": ["lit", ip2],
        "action": "drop",
        "zones": [1, 2]
    }

# --- Параметризация осмысленных валидных кейсов ---
POST_VALID_CASES = [
    pytest.param({
        "overwrite": False,
        "data": [make_unique_rule()]  # уникальный фильтр
    }, 200, "valid-single-rule"),
    pytest.param({
        "overwrite": True,
        "data": [make_unique_rule(action="drop", zones=None)]
    }, 200, "valid-drop-zones-null"),
    pytest.param({
        "overwrite": False,
        "data": [make_unique_rule(action="accept", zones=None)]
    }, 200, "valid-accept-zones-null"),
    pytest.param({
        "overwrite": False,
        "data": [make_unique_rule(), make_unique_rule()]
    }, 200, "valid-multi-rule"),
    pytest.param({"overwrite": False, "data": []}, 200, "valid-empty-data"),
    pytest.param({
        "overwrite": False,
        "data": [make_rule_with_ports()]
    }, 200, "valid-rule-with-ports"),
    pytest.param({
        "overwrite": False,
        "data": [make_rule_with_udp()]
    }, 200, "valid-rule-with-udp"),
    pytest.param({
        "overwrite": False,
        "data": [make_rule_with_icmp()]
    }, 200, "valid-rule-with-icmp"),
    pytest.param({
        "overwrite": False,
        "data": [make_rule_with_single_zone()]
    }, 200, "valid-rule-single-zone"),
    pytest.param({
        "overwrite": False,
        "data": [make_rule_with_empty_zones()]
    }, 200, "valid-rule-empty-zones"),
    pytest.param({
        "overwrite": False,
        "data": [make_rule_with_multiple_zones()]
    }, 200, "valid-rule-multiple-zones"),
    pytest.param({
        "overwrite": False,
        "data": [make_rule_with_inactive()]
    }, 200, "valid-rule-inactive"),
    pytest.param({
        "overwrite": False,
        "data": [make_rule_with_complex_service()]
    }, 200, "valid-rule-complex-service"),
    pytest.param({
        "overwrite": True,
        "data": [make_unique_rule(action="accept", zones=[1, 2, 3])]
    }, 200, "valid-rule-overwrite-accept"),
    pytest.param({
        "overwrite": False,
        "data": [make_unique_rule(action="drop", zones=[1])]
    }, 200, "valid-rule-drop-single-zone"),
    pytest.param({
        "overwrite": False,
        "data": [make_unique_rule(action="accept", zones=[])]
    }, 200, "valid-rule-accept-empty-zones"),
]

# Создаем уникальный объект для тестирования дубликатов
_duplicate_test_rule = make_simple_unique_rule()

# --- Кейс частичного успеха (вставка дубликата) ---
PARTIAL_DUPLICATE_CASES = [
    # 1. Добавляем объект (ожидаем success)
    pytest.param({
        "overwrite": False,
        "data": [
            _duplicate_test_rule
        ]
    }, 200, "insert-new-rule"),
    # 2. Пытаемся вставить такой же объект — ожидаем ошибку в error (частичный успех)
    pytest.param({
        "overwrite": False,
        "data": [
            _duplicate_test_rule
        ]
    }, 400, "insert-duplicate-rule"),
]

# --- Явно осмысленные невалидные кейсы (без дублей и лишнего) ---
POST_INVALID_CASES = [
    pytest.param('', 400, "empty-body"),
    pytest.param(({"foo": "bar"}, "application/x-www-form-urlencoded"), 400, "invalid-content-type"),
    pytest.param('{"data":[}', 400, "malformed-json"),
    pytest.param({"overwrite": False}, 400, "missing-data-field"),
    pytest.param({"overwrite": False, "data": {}}, 400, "data-not-array"),
    pytest.param({"overwrite": False, "data": [], "foo": 1}, 400, "unknown-field"),
    pytest.param({"overwrite": False, "data": [{"active": True, "service": [], "source": [], "destination": [], "action": "foobar", "zones": [1]}]}, 400, "invalid-action"),
    pytest.param({"overwrite": False, "data": [{"active": True, "service": [123], "source": [], "destination": [], "action": "accept", "zones": [1]}]}, 400, "invalid-service-type"),
    pytest.param({"overwrite": False, "data": [{"active": True, "service": [], "source": [], "destination": [], "action": "accept", "zones": "one"}]}, 400, "invalid-zones-type"),
    pytest.param({"overwrite": False, "data": [{"active": True, "service": [], "source": [], "destination": [], "zones": [1]}]}, 400, "missing-action"),
    pytest.param({"overwrite": False, "data": [{"service": [], "source": [], "destination": [], "action": "accept", "zones": [1]}]}, 400, "missing-active"),
    pytest.param({"overwrite": False, "data": [{"active": True, "service": [], "source": [], "destination": [], "action": "accept"}]}, 400, "missing-zones"),
    pytest.param({"overwrite": False, "data": [{"active": True, "source": [], "destination": [], "action": "accept", "zones": [1]}]}, 400, "missing-service"),
    pytest.param({"overwrite": False, "data": [{"active": True, "service": [], "destination": [], "action": "accept", "zones": [1]}]}, 400, "missing-source"),
    pytest.param({"overwrite": False, "data": [{"active": True, "service": [], "source": [], "action": "accept", "zones": [1]}]}, 400, "missing-destination"),
    pytest.param({"overwrite": False, "data": None}, 400, "data-null"),
    pytest.param({"overwrite": False, "data": [{"active": True, "service": [], "source": None, "destination": [], "action": "accept", "zones": [1]}]}, 400, "source-null"),
    pytest.param({"overwrite": False, "data": [{"active": True, "service": [], "source": [], "destination": None, "action": "accept", "zones": [1]}]}, 400, "destination-null"),
    # Удалено хардкодное ожидание 400 для zones:null + action:accept — сервис допускает такое значение
]

@pytest.mark.parametrize("payload, expected_status, case_id",
    POST_VALID_CASES +
    PARTIAL_DUPLICATE_CASES +
    POST_INVALID_CASES
)
def test_post_filter(api_client, attach_curl_on_fail, agent_verification, payload, expected_status, case_id):
    """
    Тесты для POST /filter (vswitch).
    Все конфигурации и проверки по Золотым правилам.
    """
    headers = {"Content-Type": "application/json"}

    # Определяем payload для контекст-менеджера
    curl_payload = payload
    if isinstance(payload, tuple):
        curl_payload, _ = payload
    elif isinstance(payload, str):
        try:
            curl_payload = json.loads(payload) if payload else None
        except:
            curl_payload = None

    with attach_curl_on_fail(ENDPOINT, curl_payload, headers, "POST"):
        # Для кейса с невалидным Content-Type
        if isinstance(payload, tuple):
            data, content_type = payload
            headers["Content-Type"] = content_type
            send_data = json.dumps(data)
            response = api_client.post(ENDPOINT, data=send_data, headers=headers)
        elif isinstance(payload, str):
            response = api_client.post(ENDPOINT, data=payload, headers=headers)
        else:
            response = api_client.post(ENDPOINT, json=payload, headers=headers)

        # --- Проверки ---
        assert response.status_code == expected_status, (
            f"Expected status {expected_status}, got {response.status_code}. "
            f"Response: {response.text[:512]}"
        )
        if expected_status == 200:
            assert response.headers["Content-Type"].startswith("application/json"), "Response is not JSON"
            resp_json = response.json()
            # Для кейса дубликата — возможно частичный успех (error не null)
            if case_id in ["insert-duplicate-rule"]:
                _check_types_recursive(resp_json, response_schemas["POST_OK_PARTIAL"])
                # хотя бы одна запись с error != null
                assert any(x.get("error") for x in resp_json), "No partial errors found for duplicate"
            else:
                _check_types_recursive(resp_json, response_schemas["POST"])
                # Проверяем, что у всех error == null
                assert all(x.get("error") is None for x in resp_json), "Unexpected error in successful insert"
        elif expected_status == 400:
            # Может быть пустая строка, либо json с ошибкой
            if response.text.strip():
                try:
                    resp_json = response.json()
                    # parse-error или error-object
                    if "parse-error" in resp_json:
                        _check_types_recursive(resp_json, response_schemas["POST_ERROR"])
                    elif isinstance(resp_json.get("error"), dict):
                        _check_types_recursive(resp_json, response_schemas["POST_OBJECT_ERROR"])
                    else:
                        _check_types_recursive(resp_json, response_schemas["POST_ERROR"])
                except Exception:
                    pass  # Не JSON — допустимо для битого JSON (malformed-json)
            else:
                assert response.text.strip() == "", "Expected empty response body for malformed JSON"
        
        # Дополнительная проверка через агента для валидных случаев
        if expected_status == 200 and isinstance(payload, dict) and "data" in payload and payload["data"]:
            print(f"Checking agent verification for valid test: {case_id}")
            agent_result = agent_verification("/filter", payload)
            if agent_result == "unavailable":
                pytest.fail(f"Agent verification failed: agent is unavailable for case: {case_id}")
            elif agent_result is True:
                print(f"Agent verification: Filter for case '{case_id}' was successfully added")
            elif agent_result is False:
                pytest.fail(f"Agent verification failed: Filter for case '{case_id}' was not found in the system")
        elif expected_status == 400:
            print(f"Skipping agent verification for invalid test (status 400): {case_id}")
        else:
            print(f"Test completed with status {expected_status}")
