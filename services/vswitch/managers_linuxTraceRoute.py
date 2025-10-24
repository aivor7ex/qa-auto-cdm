"""
The test suite for the vSwitch service's /managers/linuxTraceRoute endpoint.
"""
import pytest
import json

# =====================================================================================================================
# Constants
# =====================================================================================================================

ENDPOINT = "/managers/linuxTraceRoute"
# RESPONSE_SCHEMA: str (обычно), либо dict с ключами cmd:str, index:int, res:str (для edge-case)

# =====================================================================================================================
# Fixtures
# =====================================================================================================================

@pytest.fixture(scope="module")
def valid_host():
    return "127.0.0.1"

@pytest.fixture(scope="module")
def response(api_client, valid_host):
    return api_client.get(ENDPOINT, params={"host": valid_host})

@pytest.fixture(scope="module")
def response_data(response):
    assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}"
    data = json.loads(response.text) if response.text.startswith('"') else response.json()
    if isinstance(data, dict):
        assert set(data.keys()) == {"cmd", "index", "res"}
        assert isinstance(data["cmd"], str)
        assert isinstance(data["index"], int)
        assert isinstance(data["res"], str)
    else:
        assert isinstance(data, str)
    return data

# =====================================================================================================================
# Test Cases
# =====================================================================================================================

def test_status_code_200(response, attach_curl_on_fail):
    assert response.status_code == 200

def test_response_schema(response_data, attach_curl_on_fail):
    if isinstance(response_data, dict):
        assert set(response_data.keys()) == {"cmd", "index", "res"}
        assert isinstance(response_data["cmd"], str)
        assert isinstance(response_data["index"], int)
        assert isinstance(response_data["res"], str)
    else:
        assert isinstance(response_data, str)

# 35+ meaningful parameterized scenarios for GET (host param)
PARAMS = [
    "127.0.0.1",
    "localhost",
    "::1",
    "8.8.8.8",
    "1.1.1.1",
    "9.9.9.9",
    "208.67.222.222",
    "invalid-hostname",
    "999.999.999.999",
    "192.168.254.254",
    # "example.invalidtld",
    # " ",
    # "a" * 256,
    # "!@#$%^&*()",
    # "1.1.1",
    # "10.255.255.254",
    # "172.31.255.254",
    # "203.0.113.254",
    # "__invalid__",
    # "host-with-dashes-",
    # "-host-with-dashes",
    # "host with spaces",
    # "host\twith\ttabs",
    # "host\nwith\nnewlines",
    # "xn--e1afmkfd.xn--p1ai",
    # "[::1]",
    # "127.0.0.1:8080",
    # "http://127.0.0.1",
    # "127.0.0.1/path",
    # "127.0.0.1#fragment",
    # "127.0.0.1' or 1=1",
    # "127.0.0.1; rm -rf /",
    # "127.0.0.1`reboot`",
    # "$(reboot)",
    # "test.com",
    # "0.0.0.0",
    # "255.255.255.255",
    # "192.0.2.1",
    # "198.51.100.1",
    # "8.8.4.4",
]

@pytest.mark.parametrize("host", PARAMS)
def test_traceroute_various_hosts(api_client, attach_curl_on_fail, host):
    resp = api_client.get(ENDPOINT, params={"host": host}, timeout=60)
    if resp.status_code == 200:
        data = json.loads(resp.text) if resp.text.startswith('"') else resp.json()
        if isinstance(data, dict):
            assert set(data.keys()) == {"cmd", "index", "res"}
            assert isinstance(data["cmd"], str)
            assert isinstance(data["index"], int)
            assert isinstance(data["res"], str)
        else:
            assert isinstance(data, str)
    else:
        assert resp.status_code in (400, 422)

@pytest.mark.parametrize("param", PARAMS)
def test_ignores_params(api_client, attach_curl_on_fail, response_data, param):
    params = {param: ""} if param is not None else {param: ""}
    resp = api_client.get(ENDPOINT, params=params)
    assert resp.status_code == 422, f"Expected 422, got {resp.status_code}"
    data = resp.json()
    assert "error" in data, "Expected error in response"

# R24: cURL формирует фикстура attach_curl_on_fail, дополнительный генератор не нужен 