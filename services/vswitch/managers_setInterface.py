import pytest
import json
from typing import Any, Dict, List, Optional
from qa_constants import SERVICES

METHOD = "POST"
ENDPOINT = "/managers/setInterface"


# Схема успешного ответа (реальная по R0): массив объектов с обязательным index:int и опциональными полями
RESPONSE_SCHEMA = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "index": int,
            "cmd": str,
            "res": str,
            "skipped": bool,
            # error встречается в шагах как строка при ошибке выполнения
            "error": str,
        },
        "required": ["index"],
        "optional": ["cmd", "res", "skipped", "error"],
    },
}


# Схема ошибки (унифицированная)
ERROR_SCHEMA = {
    "required": {
        "error": dict
    },
    "optional": {}
}

ERROR_DETAIL_SCHEMA = {
    "required": {
        "statusCode": int,
        "name": str,
        "message": str
    },
    "optional": {
        "stack": str
    }
}


def _validate_success_schema(response_data: List[Dict[str, Any]], msg: str) -> None:
    assert isinstance(response_data, list), f"Response must be a list\n\n{msg}"
    for item in response_data:
        assert isinstance(item, dict), f"Each item must be an object\n\n{msg}"
        assert "index" in item, f"Missing required field 'index'\n\n{msg}"
        assert isinstance(item["index"], int), f"Field 'index' must be integer\n\n{msg}"
        if "cmd" in item:
            assert isinstance(item["cmd"], str), f"Field 'cmd' must be string\n\n{msg}"
        if "res" in item:
            assert isinstance(item["res"], str), f"Field 'res' must be string\n\n{msg}"
        if "skipped" in item:
            assert isinstance(item["skipped"], bool), f"Field 'skipped' must be boolean\n\n{msg}"
        if "error" in item:
            assert isinstance(item["error"], str), f"Field 'error' must be string\n\n{msg}"


def _validate_error_schema(data: Dict[str, Any], msg: str) -> None:
    # Локальная валидация без импортов
    assert isinstance(data, dict), f"Error response must be an object\n\n{msg}"
    assert "error" in data and isinstance(data["error"], dict), f"Error response must contain 'error' object\n\n{msg}"
    err = data["error"]
    assert "statusCode" in err and isinstance(err["statusCode"], int), f"'statusCode' must be int in error\n\n{msg}"
    assert "name" in err and isinstance(err["name"], str), f"'name' must be str in error\n\n{msg}"
    assert "message" in err and isinstance(err["message"], str), f"'message' must be str in error\n\n{msg}"
    if "stack" in err:
        assert isinstance(err["stack"], str), f"'stack' must be str in error\n\n{msg}"


# Унифицированная проверка результата агента: падать при ошибке агента
def _assert_agent_ok(agent_result: Any) -> None:
    if agent_result == "unavailable":
        pytest.fail("Agent verification failed: agent is unavailable")
    if isinstance(agent_result, dict) and agent_result.get("result") == "ERROR":
        message = agent_result.get("message", "Unknown agent error")
        pytest.fail(f"Agent verification failed: {message}")


@pytest.fixture(scope="module")
def existing_interface(api_client) -> str:
    """Возвращает имя реально существующего интерфейса из ответа Managers/ifconfig."""
    resp = api_client.get("/Managers/ifconfig")
    assert resp.status_code == 200, f"Failed to fetch interfaces, got {resp.status_code}"
    info = resp.json()
    assert isinstance(info, dict) and info, "Managers/ifconfig must return non-empty object"
    # Предпочтем не-loopback интерфейсы
    candidates = [name for name in info.keys() if name not in ("lo",) and not name.startswith("lo:")]
    if not candidates:
        candidates = list(info.keys())
    return candidates[0]


# --------------------------- Позитивные кейсы (200 OK) ---------------------------

def test_success_with_ip_mtu_broadcast(api_client, attach_curl_on_fail, agent_verification, existing_interface):
    payload = {"interface": existing_interface, "ip": "192.0.2.10/24", "mtu": 1500, "broadcast": "192.0.2.255"}
    with attach_curl_on_fail(ENDPOINT, payload):
        response = api_client.post(ENDPOINT, json=payload)
        assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}"
        data = response.json()
        _validate_success_schema(data, "")
        if any(isinstance(item, dict) and item.get("cmd") for item in data):
            assert any(f"ifconfig {existing_interface} mtu" in item.get("cmd", "") for item in data), "Expected MTU command in response"
        
        # Дополнительная проверка через агента для положительных кейсов
        agent_result = agent_verification(ENDPOINT, payload)
        _assert_agent_ok(agent_result)


def test_success_noop_interface_only(api_client, attach_curl_on_fail, agent_verification, existing_interface):
    payload = {"interface": existing_interface}
    with attach_curl_on_fail(ENDPOINT, payload):
        response = api_client.post(ENDPOINT, json=payload)
        assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}"
        data = response.json()
        _validate_success_schema(data, "")
        
        # Дополнительная проверка через агента для положительных кейсов
        agent_result = agent_verification(ENDPOINT, payload)
        _assert_agent_ok(agent_result)


def test_success_remove_ip_zero(api_client, attach_curl_on_fail, agent_verification, existing_interface):
    payload = {"interface": existing_interface, "ip": "0"}
    with attach_curl_on_fail(ENDPOINT, payload):
        response = api_client.post(ENDPOINT, json=payload)
        assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}"
        data = response.json()
        _validate_success_schema(data, "")
        
        # Дополнительная проверка через агента для положительных кейсов
        agent_result = agent_verification(ENDPOINT, payload)
        _assert_agent_ok(agent_result)


def test_success_set_only_mtu(api_client, attach_curl_on_fail, agent_verification, existing_interface):
    payload = {"interface": existing_interface, "mtu": 1400}
    with attach_curl_on_fail(ENDPOINT, payload):
        response = api_client.post(ENDPOINT, json=payload)
        assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}"
        data = response.json()
        _validate_success_schema(data, "")
        if any(isinstance(item, dict) and item.get("cmd") for item in data):
            assert any(f"ifconfig {existing_interface} mtu 1400" in item.get("cmd", "") for item in data), "Expected MTU 1400 command"
        
        # Дополнительная проверка через агента для положительных кейсов
        agent_result = agent_verification(ENDPOINT, payload)
        _assert_agent_ok(agent_result)


def test_success_set_mac_with_ip(api_client, attach_curl_on_fail, agent_verification, existing_interface):
    payload = {"interface": existing_interface, "ip": "192.0.2.11/24", "mac": "02:00:00:00:00:01"}
    with attach_curl_on_fail(ENDPOINT, payload):
        response = api_client.post(ENDPOINT, json=payload)
        assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}"
        data = response.json()
        _validate_success_schema(data, "")
        
        # Дополнительная проверка через агента для положительных кейсов
        agent_result = agent_verification(ENDPOINT, payload)
        _assert_agent_ok(agent_result)


def test_success_ignores_unknown_fields(api_client, attach_curl_on_fail, agent_verification, existing_interface):
    payload = {"interface": existing_interface, "ip": "192.0.2.12/24", "unknown": "value", "another": 123}
    with attach_curl_on_fail(ENDPOINT, payload):
        response = api_client.post(ENDPOINT, json=payload)
        assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}"
        data = response.json()
        _validate_success_schema(data, "")
        
        # Дополнительная проверка через агента для положительных кейсов
        agent_result = agent_verification(ENDPOINT, payload)
        _assert_agent_ok(agent_result)


@pytest.mark.parametrize("ip", [
    "192.0.2.10/24",
    "198.51.100.5/31",
    "203.0.113.1/32",
    "10.0.0.10/16",
    "172.16.0.5/12",
])
def test_success_various_valid_ips(api_client, attach_curl_on_fail, agent_verification, ip, existing_interface):
    payload = {"interface": existing_interface, "ip": ip}
    with attach_curl_on_fail(ENDPOINT, payload):
        response = api_client.post(ENDPOINT, json=payload)
        assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}"
        data = response.json()
        _validate_success_schema(data, "")
        
        # Дополнительная проверка через агента для положительных кейсов
        agent_result = agent_verification(ENDPOINT, payload)
        _assert_agent_ok(agent_result)


@pytest.mark.parametrize("mtu", [576, 1200, 1492, 1500])
def test_success_various_mtu_values(api_client, attach_curl_on_fail, agent_verification, mtu, existing_interface):
    payload = {"interface": existing_interface, "mtu": mtu}
    with attach_curl_on_fail(ENDPOINT, payload):
        response = api_client.post(ENDPOINT, json=payload)
        assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}"
        data = response.json()
        _validate_success_schema(data, "")
        
        # Дополнительная проверка через агента для положительных кейсов
        agent_result = agent_verification(ENDPOINT, payload)
        _assert_agent_ok(agent_result)


@pytest.mark.parametrize("mtu_high", [1501, 2000, 9000, 16384, 65535])
def test_success_mtu_values_are_clamped_to_1500(api_client, attach_curl_on_fail, agent_verification, mtu_high, existing_interface):
    payload = {"interface": existing_interface, "mtu": mtu_high}
    with attach_curl_on_fail(ENDPOINT, payload):
        response = api_client.post(ENDPOINT, json=payload)
        assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}"
        data = response.json()
        _validate_success_schema(data, "")
        if any(isinstance(item, dict) and item.get("cmd") for item in data):
            assert any(f"ifconfig {existing_interface} mtu 1500" in item.get("cmd", "") for item in data), "MTU should be clamped to 1500"
        
        # Дополнительная проверка через агента для положительных кейсов
        agent_result = agent_verification(ENDPOINT, payload)
        _assert_agent_ok(agent_result)


def test_success_ip_zero_with_mtu(api_client, attach_curl_on_fail, agent_verification, existing_interface):
    payload = {"interface": existing_interface, "ip": "0", "mtu": 1400}
    with attach_curl_on_fail(ENDPOINT, payload):
        response = api_client.post(ENDPOINT, json=payload)
        assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}"
        data = response.json()
        _validate_success_schema(data, "")
        
        # Дополнительная проверка через агента для положительных кейсов
        agent_result = agent_verification(ENDPOINT, payload)
        _assert_agent_ok(agent_result)


# --------------------------- Негативные и валидационные кейсы ---------------------------

def test_missing_required_interface_field(api_client, attach_curl_on_fail):
    payload = {"ip": "192.0.2.10/24"}
    with attach_curl_on_fail(ENDPOINT, payload):
        response = api_client.post(ENDPOINT, json=payload)
        assert response.status_code == 400, f"Expected 400 Bad Request, got {response.status_code}"
        err = response.json()
        _validate_error_schema(err, "")


def test_empty_body_returns_400(api_client, attach_curl_on_fail):
    payload = {}
    with attach_curl_on_fail(ENDPOINT, payload):
        response = api_client.post(ENDPOINT, json=payload)
        assert response.status_code == 400, f"Expected 400 Bad Request, got {response.status_code}"
        err = response.json()
        _validate_error_schema(err, "")


def test_invalid_json_syntax_returns_400(api_client, attach_curl_on_fail):
    headers = {"Content-Type": "application/json"}
    raw_body = "{ \"interface\": \"dummy0\", \"ip\": \"192.0.2.10/24\" "  # пропущена скобка
    with attach_curl_on_fail(ENDPOINT, raw_body, headers):
        response = api_client.post(ENDPOINT, headers=headers, data=raw_body)
        assert response.status_code == 400, f"Expected 400 Bad Request, got {response.status_code}"


def test_wrong_content_type_returns_400(api_client, attach_curl_on_fail):
    payload = {"interface": "dummy0", "ip": "192.0.2.10/24"}
    headers = {"Content-Type": "text/plain"}
    with attach_curl_on_fail(ENDPOINT, payload, headers):
        response = api_client.post(ENDPOINT, headers=headers, data=json.dumps(payload))
        assert response.status_code == 400, f"Expected 400 Bad Request, got {response.status_code}"


@pytest.mark.parametrize("payload", [
    {"interface": "nonexist0", "ip": "192.0.2.10/24"},  # интерфейс не существует
    {"interface": "dummy0", "ip": "bad-ip"},            # некорректный IP
    {"interface": "dummy0", "netmask": "255.255.255.0"},# только netmask
    {"interface": "dummy0", "mac": "zz:zz:zz:zz:zz:zz"}, # некорректный MAC
    {"interface": "dummy0", "ip": "192.0.2.10/33"},     # некорректная маска
    {"interface": "", "ip": "192.0.2.10/24"},           # пустое имя интерфейса
])
def test_server_errors_and_validation_failures(api_client, attach_curl_on_fail, payload, existing_interface):
    with attach_curl_on_fail(ENDPOINT, payload):
        # Заменим placeholder интерфейс на существующий для соответствующих кейсов
        if payload.get("interface") == "dummy0":
            payload["interface"] = existing_interface
        response = api_client.post(ENDPOINT, json=payload)

        if payload.get("interface") == "":
            assert response.status_code == 400, f"Expected 400 Bad Request, got {response.status_code}"
            err = response.json()
            _validate_error_schema(err, "")
            return

        assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}"
        data = response.json()
        _validate_success_schema(data, "")
        if payload.get("interface") == "nonexist0":
            assert any(isinstance(item, dict) and ("error" in item) for item in data), (
                f"Expected at least one step to contain 'error'"
            )
        for item in data:
            if "error" in item:
                assert isinstance(item["error"], str), "Field 'error' must be string"


@pytest.mark.parametrize("payload,expected_status", [
    ({"interface": "dummy0", "mtu": "1500"}, 400),      # mtu неверного типа
    ({"interface": "dummy0", "broadcast": 12345}, 400),   # broadcast неверного типа
    ({"interface": "dummy0", "ip": None}, 400),           # ip null
    ({"interface": "dummy0", "mtu": -1}, 200),            # mtu слишком мал -> 200 с ошибкой в шагах
])
def test_wrong_types_and_bounds(api_client, attach_curl_on_fail, payload, expected_status, existing_interface):
    with attach_curl_on_fail(ENDPOINT, payload):
        if payload.get("interface") == "dummy0":
            payload["interface"] = existing_interface
        response = api_client.post(ENDPOINT, json=payload)
        assert response.status_code == expected_status, f"Expected {expected_status}, got {response.status_code}"
        if expected_status == 400:
            err = response.json()
            _validate_error_schema(err, "")
        elif expected_status == 200 and payload.get("mtu") == -1:
            data = response.json()
            _validate_success_schema(data, "")
            assert any(isinstance(item, dict) and ("error" in item) for item in data), (
                "Expected step error for MTU -1 payload"
            )


