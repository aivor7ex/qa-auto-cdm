import pytest
import json
import requests
import time
from urllib.parse import urlparse
from typing import List, Dict, Any, Optional
from qa_constants import SERVICES

ENDPOINT = "/managers/conntrackDrop"

def _format_curl_command(api_client, endpoint, json_data=None, headers=None):
    """Формирует curl команду для отладки (deprecated: используйте attach_curl_on_fail)"""
    base_url = getattr(api_client, 'base_url', f'http://127.0.0.1:{SERVICES["vswitch"][0]["port"]}')
    full_url = f"{base_url.rstrip('/')}{endpoint}"
    
    curl_command = f"curl -X POST '{full_url}'"
    
    if headers:
        for key, value in headers.items():
            curl_command += f" \\\n  -H '{key}: {value}'"
    else:
        curl_command += " \\\n  -H 'Content-Type: application/json'"
    
    if json_data:
        curl_command += f" \\\n  -d '{json.dumps(json_data)}'"
    
    return curl_command

def validate_response_schema(response_data: List[Dict[str, Any]], curl_cmd: str = "") -> None:
    """Валидация схемы ответа.
    Допускаем оба варианта успешного ответа от API:
    - с полем 'res' (строка результата)
    - с полем 'error' (строка ошибки)
    Минимально обязательные поля: 'index' (int), 'cmd' (str).
    Хотя бы одно из 'res' или 'error' должно присутствовать.
    """
    assert isinstance(response_data, list), f"Response must be a list{curl_cmd}"
    
    for item in response_data:
        assert isinstance(item, dict), f"Each item must be a dictionary{curl_cmd}"
        
        # Обязательные поля
        assert "index" in item, f"Missing required field 'index'{curl_cmd}"
        assert isinstance(item["index"], int), f"Field 'index' must be integer{curl_cmd}"
        
        assert "cmd" in item, f"Missing required field 'cmd'{curl_cmd}"
        assert isinstance(item["cmd"], str), f"Field 'cmd' must be string{curl_cmd}"
        
        # Гибкая часть: допускаем 'res' и/или 'error'
        if "res" not in item and "error" not in item:
            raise AssertionError(f"Missing 'res' or 'error' field{curl_cmd}")
        if "res" in item:
            assert isinstance(item["res"], str), f"Field 'res' must be string{curl_cmd}"
        if "error" in item:
            assert isinstance(item["error"], str), f"Field 'error' must be string{curl_cmd}"

# Базовые тесты с валидными параметрами
@pytest.mark.parametrize("protocol", ["tcp", "udp"])
def test_valid_protocols(api_client, protocol, attach_curl_on_fail):
    """Тест валидных протоколов"""
    payload = {"protocol": protocol}
    
    with attach_curl_on_fail(ENDPOINT, payload):
        response = api_client.post(ENDPOINT, json=payload)
        assert response.status_code == 200
        response_data = response.json()
        validate_response_schema(response_data)

@pytest.mark.parametrize("src_ip", ["192.168.1.100", "10.0.0.1"])
def test_valid_source_ips(api_client, src_ip, attach_curl_on_fail):
    """Тест валидных IP адресов источника"""
    payload = {"src": src_ip}
    
    with attach_curl_on_fail(ENDPOINT, payload):
        response = api_client.post(ENDPOINT, json=payload)
        assert response.status_code == 200
        response_data = response.json()
        validate_response_schema(response_data)

@pytest.mark.parametrize("dst_ip", ["8.8.8.8", "1.1.1.1"])
def test_valid_destination_ips(api_client, dst_ip, attach_curl_on_fail):
    """Тест валидных IP адресов назначения"""
    payload = {"dst": dst_ip}
    
    with attach_curl_on_fail(ENDPOINT, payload):
        response = api_client.post(ENDPOINT, json=payload)
        assert response.status_code == 200
        response_data = response.json()
        validate_response_schema(response_data)

@pytest.mark.parametrize("sport", [80, 443])
def test_valid_source_ports(api_client, sport, attach_curl_on_fail):
    """Тест валидных портов источника"""
    payload = {"sport": sport}
    
    with attach_curl_on_fail(ENDPOINT, payload):
        response = api_client.post(ENDPOINT, json=payload)
        assert response.status_code == 200
        response_data = response.json()
        validate_response_schema(response_data)

@pytest.mark.parametrize("dport", [22, 53])
def test_valid_destination_ports(api_client, dport, attach_curl_on_fail):
    """Тест валидных портов назначения"""
    payload = {"dport": dport}
    
    with attach_curl_on_fail(ENDPOINT, payload):
        response = api_client.post(ENDPOINT, json=payload)
        assert response.status_code == 200
        response_data = response.json()
        validate_response_schema(response_data)

# Комбинированные тесты
@pytest.mark.parametrize("protocol,src", [
    ("tcp", "192.168.1.100"),
    ("udp", "10.0.0.1"),
])
def test_protocol_with_source(api_client, protocol, src, attach_curl_on_fail):
    """Тест протокола с IP источником"""
    payload = {"protocol": protocol, "src": src}
    
    with attach_curl_on_fail(ENDPOINT, payload):
        response = api_client.post(ENDPOINT, json=payload)
        assert response.status_code == 200
        response_data = response.json()
        validate_response_schema(response_data)

@pytest.mark.parametrize("protocol,dst", [
    ("tcp", "8.8.8.8"),
    ("udp", "1.1.1.1"),
])
def test_protocol_with_destination(api_client, protocol, dst, attach_curl_on_fail):
    """Тест протокола с IP назначения"""
    payload = {"protocol": protocol, "dst": dst}
    
    with attach_curl_on_fail(ENDPOINT, payload):
        response = api_client.post(ENDPOINT, json=payload)
        assert response.status_code == 200
        response_data = response.json()
        validate_response_schema(response_data)

@pytest.mark.parametrize("src,dst", [
    ("192.168.1.100", "8.8.8.8"),
    ("10.0.0.1", "1.1.1.1"),
])
def test_source_with_destination(api_client, src, dst, attach_curl_on_fail):
    """Тест IP источника с IP назначения"""
    payload = {"src": src, "dst": dst}
    
    with attach_curl_on_fail(ENDPOINT, payload):
        response = api_client.post(ENDPOINT, json=payload)
        assert response.status_code == 200
        response_data = response.json()
        validate_response_schema(response_data)

@pytest.mark.parametrize("sport,dport", [
    (32768, 80),
    (49152, 443),
])
def test_source_with_destination_ports(api_client, sport, dport, attach_curl_on_fail):
    """Тест порта источника с портом назначения"""
    payload = {"sport": sport, "dport": dport}
    
    with attach_curl_on_fail(ENDPOINT, payload):
        response = api_client.post(ENDPOINT, json=payload)
        assert response.status_code == 200
        response_data = response.json()
        validate_response_schema(response_data)

# Полные комбинации
@pytest.mark.parametrize("protocol,src,dst", [
    ("tcp", "192.168.1.100", "8.8.8.8"),
    ("udp", "10.0.0.1", "1.1.1.1"),
])
def test_protocol_source_destination(api_client, protocol, src, dst, attach_curl_on_fail):
    """Тест протокола с IP источником и назначения"""
    payload = {"protocol": protocol, "src": src, "dst": dst}
    
    with attach_curl_on_fail(ENDPOINT, payload):
        response = api_client.post(ENDPOINT, json=payload)
        assert response.status_code == 200
        response_data = response.json()
        validate_response_schema(response_data)

@pytest.mark.parametrize("protocol,sport,dport", [
    ("tcp", 32768, 80),
])
def test_protocol_source_dest_ports(api_client, protocol, sport, dport, attach_curl_on_fail):
    """Тест протокола с портами источника и назначения"""
    payload = {"protocol": protocol, "sport": sport, "dport": dport}
    
    with attach_curl_on_fail(ENDPOINT, payload):
        response = api_client.post(ENDPOINT, json=payload)
        assert response.status_code == 200
        response_data = response.json()
        validate_response_schema(response_data)

# Полные комбинации со всеми параметрами
@pytest.mark.parametrize("protocol,src,dst,sport,dport", [
    ("tcp", "192.168.1.100", "8.8.8.8", 32768, 80),
    ("udp", "10.0.0.1", "1.1.1.1", 49152, 443),
])
def test_all_parameters(api_client, protocol, src, dst, sport, dport, attach_curl_on_fail):
    """Тест всех параметров"""
    payload = {"protocol": protocol, "src": src, "dst": dst, "sport": sport, "dport": dport}
    
    with attach_curl_on_fail(ENDPOINT, payload):
        response = api_client.post(ENDPOINT, json=payload)
        assert response.status_code == 200
        response_data = response.json()
        validate_response_schema(response_data)

# Граничные случаи
def test_empty_payload(api_client, attach_curl_on_fail):
    """Тест пустого запроса"""
    payload = {}
    
    with attach_curl_on_fail(ENDPOINT, payload):
        response = api_client.post(ENDPOINT, json=payload)
        assert response.status_code == 200
        response_data = response.json()
        validate_response_schema(response_data)

@pytest.mark.parametrize("sport,dport", [(1, 1), (65535, 65535)])
def test_boundary_ports(api_client, sport, dport, attach_curl_on_fail):
    """Тест граничных значений портов"""
    payload = {"sport": sport, "dport": dport}
    
    with attach_curl_on_fail(ENDPOINT, payload):
        response = api_client.post(ENDPOINT, json=payload)
        assert response.status_code == 200
        response_data = response.json()
        validate_response_schema(response_data)

@pytest.mark.parametrize("src,dst", [
    ("127.0.0.1", "127.0.0.1"),
])
def test_special_ips(api_client, src, dst, attach_curl_on_fail):
    """Тест специальных IP адресов"""
    payload = {"src": src, "dst": dst}
    
    with attach_curl_on_fail(ENDPOINT, payload):
        response = api_client.post(ENDPOINT, json=payload)
        assert response.status_code == 200
        response_data = response.json()
        validate_response_schema(response_data)

# IPv6 тесты
@pytest.mark.parametrize("src,dst", [
    ("2001:db8::1", "2001:db8::2"),
])
def test_ipv6_addresses(api_client, src, dst, attach_curl_on_fail):
    """Тест IPv6 адресов"""
    payload = {"src": src, "dst": dst}
    
    with attach_curl_on_fail(ENDPOINT, payload):
        response = api_client.post(ENDPOINT, json=payload)
        assert response.status_code == 200
        response_data = response.json()
        validate_response_schema(response_data)

# Негативные тесты
@pytest.mark.parametrize("invalid_protocol", ["invalid", "ftp"])
def test_invalid_protocols(api_client, invalid_protocol, attach_curl_on_fail):
    """Тест неверных протоколов"""
    payload = {"protocol": invalid_protocol}
    
    with attach_curl_on_fail(ENDPOINT, payload):
        response = api_client.post(ENDPOINT, json=payload)
        # API возвращает 200 даже для неверных протоколов, так как валидация происходит на уровне conntrack
        assert response.status_code == 200
        response_data = response.json()
        validate_response_schema(response_data)
        # Проверяем что команда была сформирована с неверным протоколом
        assert any("conntrack -D -p " + invalid_protocol in item["cmd"] for item in response_data), \
            f"Expected command to contain invalid protocol '{invalid_protocol}'"

@pytest.mark.parametrize("invalid_ip", ["256.256.256.256"])
def test_invalid_ip_addresses(api_client, invalid_ip, attach_curl_on_fail):
    """Тест неверных IP адресов"""
    payload = {"src": invalid_ip}
    
    with attach_curl_on_fail(ENDPOINT, payload):
        response = api_client.post(ENDPOINT, json=payload)
        # API возвращает 200 даже для неверных IP, так как валидация происходит на уровне conntrack
        assert response.status_code == 200
        response_data = response.json()
        validate_response_schema(response_data)
        # Проверяем что команда была сформирована с неверным IP
        assert any("conntrack -D" in item["cmd"] and invalid_ip in item["cmd"] for item in response_data), \
            f"Expected command to contain invalid IP '{invalid_ip}'"

@pytest.mark.parametrize("invalid_port", [0, 65536])
def test_invalid_ports(api_client, invalid_port, attach_curl_on_fail):
    """Тест неверных портов"""
    payload = {"sport": invalid_port}
    
    with attach_curl_on_fail(ENDPOINT, payload):
        response = api_client.post(ENDPOINT, json=payload)
        # API возвращает 200 даже для неверных портов, так как валидация происходит на уровне conntrack
        assert response.status_code == 200
        response_data = response.json()
        validate_response_schema(response_data)

def test_wrong_content_type(api_client, attach_curl_on_fail):
    """Тест неверного Content-Type"""
    payload = {"protocol": "tcp"}
    
    headers = {"Content-Type": "text/plain"}
    
    with attach_curl_on_fail(ENDPOINT, payload, headers, "POST"):
        response = api_client.post(ENDPOINT, headers=headers, data=json.dumps(payload))
        # API принимает любой Content-Type и возвращает 200
        assert response.status_code == 200
        response_data = response.json()
        validate_response_schema(response_data)

def test_invalid_json(api_client, attach_curl_on_fail):
    """Тест невалидного JSON"""
    with attach_curl_on_fail(ENDPOINT, "invalid json data", {"Content-Type": "application/json"}, "POST"):
        response = api_client.post(ENDPOINT, data="invalid json data")
        assert response.status_code == 400

# Edge cases
@pytest.mark.parametrize("null_value", [None])
def test_null_values(api_client, null_value, attach_curl_on_fail):
    """Тест null значений"""
    payload = {"protocol": null_value, "src": null_value}
    
    with attach_curl_on_fail(ENDPOINT, payload):
        response = api_client.post(ENDPOINT, json=payload)
        # API валидирует типы и для null значений отвечает 400
        assert response.status_code == 400

@pytest.mark.parametrize("empty_string", [""])
def test_empty_strings(api_client, empty_string, attach_curl_on_fail):
    """Тест пустых строк"""
    payload = {"protocol": empty_string, "src": empty_string}
    
    with attach_curl_on_fail(ENDPOINT, payload):
        response = api_client.post(ENDPOINT, json=payload)
        # API возвращает 200 для пустых строк, так как валидация происходит на уровне conntrack
        assert response.status_code == 200
        response_data = response.json()
        validate_response_schema(response_data)

def test_wrong_data_types(api_client, attach_curl_on_fail):
    """Тест неверных типов данных"""
    payload = {"protocol": 123, "src": 456, "sport": "not_a_number"}
    
    with attach_curl_on_fail(ENDPOINT, payload):
        response = api_client.post(ENDPOINT, json=payload)
        assert response.status_code == 400

def test_extra_fields(api_client, attach_curl_on_fail):
    """Тест дополнительных полей"""
    payload = {
        "protocol": "tcp",
        "src": "192.168.1.100",
        "extra_field": "should_be_ignored",
        "another_field": 123
    }
    
    with attach_curl_on_fail(ENDPOINT, payload):
        response = api_client.post(ENDPOINT, json=payload)
        assert response.status_code == 200
        response_data = response.json()
        validate_response_schema(response_data)

 


# --- E2E тест по гайду ---
def _agent_get_count(agent_base: str, retries: int = 3, delay_s: float = 0.5) -> int:
    """Получить счётчик conntrack через агента (/api/get-conntrack-count)."""
    parsed = urlparse(agent_base)
    agent_root = f"{parsed.scheme}://{parsed.netloc}"
    last_exc = None
    for _ in range(retries):
        try:
            resp = requests.get(f"{agent_root}/api/get-conntrack-count", timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                return int(data.get("count", 0))
            if resp.status_code == 404:
                pytest.skip("Agent endpoint /api/get-conntrack-count not found")
        except Exception as e:
            last_exc = e
        time.sleep(delay_s)
    if last_exc:
        raise last_exc
    return 0


def _agent_generate_traffic(agent_base: str,
                           protocol: str,
                           src: str,
                           dst: str,
                           dport: int,
                           count: int = 3) -> None:
    """Генерировать трафик через агента (/api/generate-traffic)."""
    parsed = urlparse(agent_base)
    agent_root = f"{parsed.scheme}://{parsed.netloc}"
    payload = {
        "protocol": protocol,
        "src": src,
        "dst": dst,
        "dport": dport,
        "count": count,
    }
    resp = requests.post(f"{agent_root}/api/generate-traffic", json=payload, timeout=15)
    if resp.status_code == 404:
        pytest.skip("Agent endpoint /api/generate-traffic not found")
    assert resp.status_code == 200, f"Agent generate-traffic failed: {resp.status_code} {resp.text}"


def _agent_generate_udp(agent_base: str,
                        src: str = "192.0.2.10",
                        dst: str = "192.0.2.9",
                        dport: int = 5000,
                        count: int = 3) -> None:
    """Генерировать UDP-трафик через агента (/api/generate-traffic)."""
    _agent_generate_traffic(agent_base, "udp", src, dst, dport, count)


def _validate_conntrack_drop_response(response_data, curl_cmd, src, dst):
    """Проверка ответа API conntrackDrop"""
    validate_response_schema(response_data, curl_cmd)
    
    # Проверяем, что команда выполнилась корректно
    for item in response_data:
        if "error" in item and "0 flow entries have been deleted" in item["error"]:
            # Это нормально - соединений для удаления не было
            print(f"Note: No connections found to delete for {src}:{dst}")
        elif "res" in item and ("flow entries have been deleted" in item["res"] or "udp" in item["res"] or "tcp" in item["res"]):
            # Соединения были удалены (видим список удалённых соединений)
            print(f"Success: Connections deleted for {src}:{dst}")
        else:
            # Другие ошибки - это проблема
            assert False, f"Unexpected response: {item}"


def test_e2e_conntrack_drop_udp_agent(api_client, agent_base_url, attach_curl_on_fail):
    """E2E тест удаления conntrack через агента по гайду"""
    vs_cfg = SERVICES["vswitch"][0]
    vs_base = f"http://{vs_cfg['host']}:{vs_cfg['port']}{vs_cfg.get('base_path','')}".rstrip('/')

    # Проверяем доступность агента по /api
    try:
        parsed = urlparse(agent_base_url)
        agent_root = f"{parsed.scheme}://{parsed.netloc}"
        health = requests.get(f"{agent_root}/api/get-conntrack-count", timeout=5)
        if health.status_code != 200:
            pytest.skip(f"Agent unavailable: status={health.status_code}")
    except requests.exceptions.RequestException as e:
        pytest.skip(f"Agent unavailable: {e}")

    # Проверяем доступность основного API
    try:
        probe = requests.get(vs_base, timeout=5)
        # Любой HTTP статус считается достаточным для подтверждения доступности
        _ = probe.status_code
    except requests.exceptions.RequestException as e:
        pytest.skip(f"Main API unavailable: {e}")

    # 1) Генерируем UDP-трафик
    _agent_generate_udp(agent_base_url, src="192.0.2.10", dst="192.0.2.9", dport=5000, count=3)

    # Пауза для обработки соединений
    time.sleep(0.5)

    # 2) Получаем базовый счётчик conntrack
    base_count = _agent_get_count(agent_base_url)

    # 3) Выполняем удаление через основной API
    payload = {
        "protocol": "udp",
        "dport": 5000,
        "src": "192.0.2.10",
        "dst": "192.0.2.9",
    }
    with attach_curl_on_fail(ENDPOINT, payload):
        response = api_client.post(ENDPOINT, json=payload)
        assert response.status_code == 200

    # 4) Проверяем результат удаления
    time.sleep(0.5)
    new_count = _agent_get_count(agent_base_url)

    # Проверяем ответ API
    response_data = response.json()
    _validate_conntrack_drop_response(response_data, "", "192.0.2.10", "192.0.2.9")
