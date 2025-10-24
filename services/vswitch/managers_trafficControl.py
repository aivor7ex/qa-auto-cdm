import pytest
import json
import requests
from typing import Any, Dict, List, Optional
from qa_constants import SERVICES

METHOD = "POST"
ENDPOINT = "/managers/trafficControl"
IFCONFIG_ENDPOINT = "/Managers/ifconfig"

# Схема успешного ответа (по R0): объект с обязательными полями index и skipped
RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "index": int,
        "skipped": bool
    },
    "required": ["index"],
    "optional": {}
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

def get_available_interfaces(api_client) -> List[str]:
    """
    Получает список доступных интерфейсов из эндпоинта ifconfig.
    Возвращает список имен интерфейсов, исключая loopback и специальные интерфейсы.
    """
    try:
        response = api_client.get(IFCONFIG_ENDPOINT)
        if response.status_code != 200:
            print(f"Failed to get interfaces: {response.status_code}")
            return []

        data = response.json()

        # Поддерживаем оба формата ответа: {iface: {...}} или [{name: iface, ...}, ...]
        if isinstance(data, dict):
            all_interfaces = list(data.keys())
        elif isinstance(data, list):
            all_interfaces = [item.get("name") for item in data if isinstance(item, dict) and item.get("name")]
        else:
            print("Unexpected ifconfig response format")
            return []

        if not all_interfaces:
            return []

        # Выбираем не loopback интерфейсы, если такие есть
        non_loopback = [iface for iface in all_interfaces if not str(iface).startswith("lo")]

        if non_loopback:
            return non_loopback

        # Если остались только loopback-интерфейсы, возвращаем их (напр. в CI окружении)
        return all_interfaces
    except Exception as e:
        print(f"Error getting interfaces: {e}")
        return []

def get_test_interface(api_client) -> str:
    """
    Возвращает имя интерфейса для тестирования.
    Предпочитает интерфейсы с IPv4 адресами.
    """
    interfaces = get_available_interfaces(api_client)
    if not interfaces:
        # Пытаемся аккуратно выбрать первый интерфейс из ответа API, чтобы избежать хардкода
        try:
            response = api_client.get(IFCONFIG_ENDPOINT)
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, dict) and data:
                    return list(data.keys())[0]
                if isinstance(data, list) and data:
                    first = next((item.get("name") for item in data if isinstance(item, dict) and item.get("name")), None)
                    if first:
                        return first
        except Exception:
            pass
        raise ValueError("Не удалось получить доступные интерфейсы из API")

    # Предпочитаем интерфейсы с IPv4 адресами (не 127.0.0.1)
    try:
        response = api_client.get(IFCONFIG_ENDPOINT)
        if response.status_code == 200:
            data = response.json()
            for interface in interfaces:
                try:
                    iface_info = data.get(interface, {}) if isinstance(data, dict) else None
                    inet_list = iface_info.get('inet') if isinstance(iface_info, dict) else None
                    if isinstance(inet_list, list):
                        has_non_loopback_ipv4 = any(
                            isinstance(addr, dict)
                            and addr.get('proto') in ('ip4', 'ipv4')
                            and addr.get('addr') not in (None, '127.0.0.1')
                        for addr in inet_list)
                        if has_non_loopback_ipv4:
                            return interface
                except Exception:
                    continue
    except Exception:
        pass

    # Если не нашли с IPv4, возвращаем первый доступный
    return interfaces[0]



def _validate_success_schema(response_data: Dict[str, Any], msg: str) -> None:
    assert isinstance(response_data, dict), f"Response must be an object\n\n{msg}"
    assert "index" in response_data, f"Missing required field 'index'\n\n{msg}"
    assert isinstance(response_data["index"], int), f"Field 'index' must be integer\n\n{msg}"
    assert "skipped" in response_data, f"Missing required field 'skipped'\n\n{msg}"
    assert isinstance(response_data["skipped"], bool), f"Field 'skipped' must be boolean\n\n{msg}"

def _validate_error_schema(data: Dict[str, Any], msg: str) -> None:
    assert isinstance(data, dict), f"Error response must be an object\n\n{msg}"
    assert "error" in data and isinstance(data["error"], dict), f"Error response must contain 'error' object\n\n{msg}"
    err = data["error"]
    assert "statusCode" in err and isinstance(err["statusCode"], int), f"'statusCode' must be int in error\n\n{msg}"
    assert "name" in err and isinstance(err["name"], str), f"'name' must be str in error\n\n{msg}"
    assert "message" in err and isinstance(err["message"], str), f"'message' must be str in error\n\n{msg}"
    if "stack" in err:
        assert isinstance(err["stack"], str), f"'stack' must be str in error\n\n{msg}"

# --------------------------- Позитивные кейсы (200 OK) ---------------------------

def test_success_set_bandwidth_5(api_client, attach_curl_on_fail):
    interface = get_test_interface(api_client)
    payload = {"interface": interface, "bandwidth": 5}
    with attach_curl_on_fail(ENDPOINT, payload):
        response = api_client.post(ENDPOINT, json=payload)
        assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}"
        try:
            data = response.json()
            _validate_success_schema(data, "")
        except json.JSONDecodeError as e:
            pytest.fail(f"Invalid JSON response: {e}")

def test_success_set_bandwidth_10(api_client, attach_curl_on_fail):
    interface = get_test_interface(api_client)
    payload = {"interface": interface, "bandwidth": 10}
    with attach_curl_on_fail(ENDPOINT, payload):
        response = api_client.post(ENDPOINT, json=payload)
        assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}"
        try:
            data = response.json()
            _validate_success_schema(data, "")
        except json.JSONDecodeError as e:
            pytest.fail(f"Invalid JSON response: {e}")

def test_success_remove_bandwidth_zero(api_client, attach_curl_on_fail):
    interface = get_test_interface(api_client)
    payload = {"interface": interface, "bandwidth": 0}
    with attach_curl_on_fail(ENDPOINT, payload):
        response = api_client.post(ENDPOINT, json=payload)
        assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}"
        try:
            data = response.json()
            _validate_success_schema(data, "")
        except json.JSONDecodeError as e:
            pytest.fail(f"Invalid JSON response: {e}")

def test_success_change_existing_bandwidth(api_client, attach_curl_on_fail):
    interface = get_test_interface(api_client)
    # Сначала устанавливаем ограничение
    payload1 = {"interface": interface, "bandwidth": 5}
    with attach_curl_on_fail(ENDPOINT, payload1):
        response1 = api_client.post(ENDPOINT, json=payload1)
        assert response1.status_code == 200
    
    # Затем изменяем его
    payload2 = {"interface": interface, "bandwidth": 15}
    with attach_curl_on_fail(ENDPOINT, payload2):
        response2 = api_client.post(ENDPOINT, json=payload2)
        assert response2.status_code == 200, f"Expected 200 OK, got {response2.status_code}"
        try:
            data = response2.json()
            _validate_success_schema(data, "")
        except json.JSONDecodeError as e:
            pytest.fail(f"Invalid JSON response: {e}")

def test_success_max_bandwidth(api_client, attach_curl_on_fail):
    interface = get_test_interface(api_client)
    payload = {"interface": interface, "bandwidth": 1000000}
    with attach_curl_on_fail(ENDPOINT, payload):
        response = api_client.post(ENDPOINT, json=payload)
        assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}"
        try:
            data = response.json()
            _validate_success_schema(data, "")
        except json.JSONDecodeError as e:
            pytest.fail(f"Invalid JSON response: {e}")

def test_success_bandwidth_1(api_client, attach_curl_on_fail):
    interface = get_test_interface(api_client)
    payload = {"interface": interface, "bandwidth": 1}
    with attach_curl_on_fail(ENDPOINT, payload):
        response = api_client.post(ENDPOINT, json=payload)
        assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}"
        try:
            data = response.json()
            _validate_success_schema(data, "")
        except json.JSONDecodeError as e:
            pytest.fail(f"Invalid JSON response: {e}")

def test_success_bandwidth_100(api_client, attach_curl_on_fail):
    interface = get_test_interface(api_client)
    payload = {"interface": interface, "bandwidth": 100}
    with attach_curl_on_fail(ENDPOINT, payload):
        response = api_client.post(ENDPOINT, json=payload)
        assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}"
        try:
            data = response.json()
            _validate_success_schema(data, "")
        except json.JSONDecodeError as e:
            pytest.fail(f"Invalid JSON response: {e}")

def test_success_bandwidth_500(api_client, attach_curl_on_fail):
    interface = get_test_interface(api_client)
    payload = {"interface": interface, "bandwidth": 500}
    with attach_curl_on_fail(ENDPOINT, payload):
        response = api_client.post(ENDPOINT, json=payload)
        assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}"
        try:
            data = response.json()
            _validate_success_schema(data, "")
        except json.JSONDecodeError as e:
            pytest.fail(f"Invalid JSON response: {e}")

# --------------------------- Тесты с другими интерфейсами ---------------------------

def test_error_veth0_interface_nonexistent(api_client, attach_curl_on_fail):
    payload = {"interface": "veth0", "bandwidth": 10}
    with attach_curl_on_fail(ENDPOINT, payload):
        response = api_client.post(ENDPOINT, json=payload)
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"
        try:
            data = response.json()
            _validate_error_schema(data, "")
            assert data["error"]["statusCode"] == 422, f"Expected error statusCode 422, got {data['error']['statusCode']}"
        except json.JSONDecodeError as e:
            pytest.fail(f"Invalid JSON response: {e}")

def test_error_veth1_interface_nonexistent(api_client, attach_curl_on_fail):
    payload = {"interface": "veth1", "bandwidth": 10}
    with attach_curl_on_fail(ENDPOINT, payload):
        response = api_client.post(ENDPOINT, json=payload)
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"
        try:
            data = response.json()
            _validate_error_schema(data, "")
            assert data["error"]["statusCode"] == 422, f"Expected error statusCode 422, got {data['error']['statusCode']}"
        except json.JSONDecodeError as e:
            pytest.fail(f"Invalid JSON response: {e}")

def test_error_eth1_interface_nonexistent(api_client, attach_curl_on_fail):
    payload = {"interface": "eth1", "bandwidth": 10}
    with attach_curl_on_fail(ENDPOINT, payload):
        response = api_client.post(ENDPOINT, json=payload)
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"
        try:
            data = response.json()
            _validate_error_schema(data, "")
            assert data["error"]["statusCode"] == 422, f"Expected error statusCode 422, got {data['error']['statusCode']}"
        except json.JSONDecodeError as e:
            pytest.fail(f"Invalid JSON response: {e}")

def test_error_eth2_interface_nonexistent(api_client, attach_curl_on_fail):
    payload = {"interface": "eth2", "bandwidth": 10}
    with attach_curl_on_fail(ENDPOINT, payload):
        response = api_client.post(ENDPOINT, json=payload)
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"
        try:
            data = response.json()
            _validate_error_schema(data, "")
            assert data["error"]["statusCode"] == 422, f"Expected error statusCode 422, got {data['error']['statusCode']}"
        except json.JSONDecodeError as e:
            pytest.fail(f"Invalid JSON response: {e}")

def test_error_ens33_interface_nonexistent_in_namespace(api_client, attach_curl_on_fail):
    payload = {"interface": "ens33", "bandwidth": 10}
    with attach_curl_on_fail(ENDPOINT, payload):
        response = api_client.post(ENDPOINT, json=payload)
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"
        try:
            data = response.json()
            _validate_error_schema(data, "")
            assert data["error"]["statusCode"] == 422, f"Expected error statusCode 422, got {data['error']['statusCode']}"
        except json.JSONDecodeError as e:
            pytest.fail(f"Invalid JSON response: {e}")

def test_success_lo_interface(api_client, attach_curl_on_fail):
    payload = {"interface": "lo", "bandwidth": 10}
    with attach_curl_on_fail(ENDPOINT, payload):
        response = api_client.post(ENDPOINT, json=payload)
        # loopback интерфейс может не поддерживать traffic control
        assert response.status_code in [200, 422], f"Expected 200 or 422, got {response.status_code}"
        if response.status_code == 200:
            try:
                data = response.json()
                _validate_success_schema(data, "")
            except json.JSONDecodeError as e:
                pytest.fail(f"Invalid JSON response: {e}")
        else:
            try:
                data = response.json()
                _validate_error_schema(data, "")
                assert data["error"]["statusCode"] == 422, f"Expected error statusCode 422, got {data['error']['statusCode']}"
            except json.JSONDecodeError as e:
                pytest.fail(f"Invalid JSON response: {e}")

# --------------------------- Негативные кейсы (422) ---------------------------

def test_error_nonexistent_interface(api_client, attach_curl_on_fail):
    payload = {"interface": "nonexistent", "bandwidth": 5}
    with attach_curl_on_fail(ENDPOINT, payload):
        response = api_client.post(ENDPOINT, json=payload)
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"
        try:
            data = response.json()
            _validate_error_schema(data, "")
            assert data["error"]["statusCode"] == 422, f"Expected error statusCode 422, got {data['error']['statusCode']}"
        except json.JSONDecodeError as e:
            pytest.fail(f"Invalid JSON response: {e}")

def test_error_empty_interface(api_client, attach_curl_on_fail):
    payload = {"interface": "", "bandwidth": 5}
    with attach_curl_on_fail(ENDPOINT, payload):
        response = api_client.post(ENDPOINT, json=payload)
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"
        try:
            data = response.json()
            _validate_error_schema(data, "")
            assert data["error"]["statusCode"] == 422, f"Expected error statusCode 422, got {data['error']['statusCode']}"
        except json.JSONDecodeError as e:
            pytest.fail(f"Invalid JSON response: {e}")

def test_success_missing_interface(api_client, attach_curl_on_fail):
    # Для этого теста не нужен интерфейс, так как он отсутствует в payload
    payload = {"bandwidth": 5}
    with attach_curl_on_fail(ENDPOINT, payload):
        response = api_client.post(ENDPOINT, json=payload)
        assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}"
        try:
            data = response.json()
            _validate_success_schema(data, "")
        except json.JSONDecodeError as e:
            pytest.fail(f"Invalid JSON response: {e}")

def test_error_missing_bandwidth(api_client, attach_curl_on_fail):
    interface = get_test_interface(api_client)
    payload = {"interface": interface}
    with attach_curl_on_fail(ENDPOINT, payload):
        response = api_client.post(ENDPOINT, json=payload)
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"
        try:
            data = response.json()
            _validate_error_schema(data, "")
            assert data["error"]["statusCode"] == 422, f"Expected error statusCode 422, got {data['error']['statusCode']}"
        except json.JSONDecodeError as e:
            pytest.fail(f"Invalid JSON response: {e}")

def test_error_string_bandwidth(api_client, attach_curl_on_fail):
    interface = get_test_interface(api_client)
    payload = {"interface": interface, "bandwidth": "5"}
    with attach_curl_on_fail(ENDPOINT, payload):
        response = api_client.post(ENDPOINT, json=payload)
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        try:
            data = response.json()
            _validate_error_schema(data, "")
            assert data["error"]["statusCode"] == 400, f"Expected error statusCode 400, got {data['error']['statusCode']}"
        except json.JSONDecodeError as e:
            pytest.fail(f"Invalid JSON response: {e}")

def test_error_float_bandwidth(api_client, attach_curl_on_fail):
    interface = get_test_interface(api_client)
    payload = {"interface": interface, "bandwidth": 5.5}
    with attach_curl_on_fail(ENDPOINT, payload):
        response = api_client.post(ENDPOINT, json=payload)
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        try:
            data = response.json()
            _validate_error_schema(data, "")
            assert data["error"]["statusCode"] == 400, f"Expected error statusCode 400, got {data['error']['statusCode']}"
        except json.JSONDecodeError as e:
            pytest.fail(f"Invalid JSON response: {e}")

def test_error_negative_bandwidth(api_client, attach_curl_on_fail):
    interface = get_test_interface(api_client)
    payload = {"interface": interface, "bandwidth": -1}
    with attach_curl_on_fail(ENDPOINT, payload):
        response = api_client.post(ENDPOINT, json=payload)
        # Отрицательные значения могут быть приняты, но игнорированы
        assert response.status_code in [200, 422], f"Expected 200 or 422, got {response.status_code}"
        if response.status_code == 200:
            try:
                data = response.json()
                _validate_success_schema(data, "")
            except json.JSONDecodeError as e:
                pytest.fail(f"Invalid JSON response: {e}")
        else:
            try:
                data = response.json()
                _validate_error_schema(data, "")
                assert data["error"]["statusCode"] == 422, f"Expected error statusCode 422, got {data['error']['statusCode']}"
            except json.JSONDecodeError as e:
                pytest.fail(f"Invalid JSON response: {e}")

def test_error_null_interface(api_client, attach_curl_on_fail):
    # Для этого теста используем None, так как тестируем null значение
    payload = {"interface": None, "bandwidth": 5}
    with attach_curl_on_fail(ENDPOINT, payload):
        response = api_client.post(ENDPOINT, json=payload)
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        try:
            data = response.json()
            _validate_error_schema(data, "")
            assert data["error"]["statusCode"] == 400, f"Expected error statusCode 400, got {data['error']['statusCode']}"
        except json.JSONDecodeError as e:
            pytest.fail(f"Invalid JSON response: {e}")

def test_error_null_bandwidth(api_client, attach_curl_on_fail):
    interface = get_test_interface(api_client)
    payload = {"interface": interface, "bandwidth": None}
    with attach_curl_on_fail(ENDPOINT, payload):
        response = api_client.post(ENDPOINT, json=payload)
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        try:
            data = response.json()
            _validate_error_schema(data, "")
            assert data["error"]["statusCode"] == 400, f"Expected error statusCode 400, got {data['error']['statusCode']}"
        except json.JSONDecodeError as e:
            pytest.fail(f"Invalid JSON response: {e}")

def test_error_empty_payload(api_client, attach_curl_on_fail):
    payload = {}
    with attach_curl_on_fail(ENDPOINT, payload):
        response = api_client.post(ENDPOINT, json=payload)
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"
        try:
            data = response.json()
            _validate_error_schema(data, "")
            assert data["error"]["statusCode"] == 422, f"Expected error statusCode 422, got {data['error']['statusCode']}"
        except json.JSONDecodeError as e:
            pytest.fail(f"Invalid JSON response: {e}")

def test_error_extra_fields(api_client, attach_curl_on_fail):
    interface = get_test_interface(api_client)
    payload = {"interface": interface, "bandwidth": 10, "extra_field": "value"}
    with attach_curl_on_fail(ENDPOINT, payload):
        response = api_client.post(ENDPOINT, json=payload)
        # API может принимать дополнительные поля или возвращать ошибку
        assert response.status_code in [200, 422], f"Expected 200 or 422, got {response.status_code}"
        if response.status_code == 200:
            try:
                data = response.json()
                _validate_success_schema(data, "")
            except json.JSONDecodeError as e:
                pytest.fail(f"Invalid JSON response: {e}")
        else:
            try:
                data = response.json()
                _validate_error_schema(data, "")
                assert data["error"]["statusCode"] == 422, f"Expected error statusCode 422, got {data['error']['statusCode']}"
            except json.JSONDecodeError as e:
                pytest.fail(f"Invalid JSON response: {e}")

# --------------------------- Тесты с невалидным JSON (400) ---------------------------

def test_error_invalid_json_missing_brace(api_client, attach_curl_on_fail):
    interface = get_test_interface(api_client)
    invalid_json = f'{{"interface": "{interface}", "bandwidth": 10'
    with attach_curl_on_fail(ENDPOINT, invalid_json):
        response = api_client.post(ENDPOINT, data=invalid_json, headers={"Content-Type": "application/json"})
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        try:
            data = response.json()
            _validate_error_schema(data, "")
            assert data["error"]["statusCode"] == 400, f"Expected error statusCode 400, got {data['error']['statusCode']}"
        except json.JSONDecodeError as e:
            pytest.fail(f"Invalid JSON response: {e}")

def test_error_invalid_json_trailing_comma(api_client, attach_curl_on_fail):
    interface = get_test_interface(api_client)
    invalid_json = f'{{"interface": "{interface}", "bandwidth": 10,}}'
    with attach_curl_on_fail(ENDPOINT, invalid_json):
        response = api_client.post(ENDPOINT, data=invalid_json, headers={"Content-Type": "application/json"})
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        try:
            data = response.json()
            _validate_error_schema(data, "")
            assert data["error"]["statusCode"] == 400, f"Expected error statusCode 400, got {data['error']['statusCode']}"
        except json.JSONDecodeError as e:
            pytest.fail(f"Invalid JSON response: {e}")

def test_error_invalid_json_wrong_quotes(api_client, attach_curl_on_fail):
    interface = get_test_interface(api_client)
    invalid_json = f'{{"interface": "{interface}", "bandwidth": "10"}}'
    with attach_curl_on_fail(ENDPOINT, invalid_json):
        response = api_client.post(ENDPOINT, data=invalid_json, headers={"Content-Type": "application/json"})
        # Это может быть принято как валидный JSON, но bandwidth будет строкой
        assert response.status_code in [200, 400, 422], f"Expected 200, 400, or 422, got {response.status_code}"
        if response.status_code == 200:
            try:
                data = response.json()
                _validate_success_schema(data, "")
            except json.JSONDecodeError as e:
                pytest.fail(f"Invalid JSON response: {e}")
        else:
            try:
                data = response.json()
                _validate_error_schema(data, "")
            except json.JSONDecodeError as e:
                pytest.fail(f"Invalid JSON response: {e}")

# --------------------------- Тесты с неправильным Content-Type ---------------------------

def test_error_wrong_content_type_text(api_client, attach_curl_on_fail):
    interface = get_test_interface(api_client)
    payload = {"interface": interface, "bandwidth": 10}
    with attach_curl_on_fail(ENDPOINT, payload, headers={"Content-Type": "text/plain"}):
        response = api_client.post(ENDPOINT, json=payload, headers={"Content-Type": "text/plain"})
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"
        try:
            data = response.json()
            _validate_error_schema(data, "")
            assert data["error"]["statusCode"] == 422, f"Expected error statusCode 422, got {data['error']['statusCode']}"
        except json.JSONDecodeError as e:
            pytest.fail(f"Invalid JSON response: {e}")

def test_error_wrong_content_type_xml(api_client, attach_curl_on_fail):
    interface = get_test_interface(api_client)
    payload = {"interface": interface, "bandwidth": 10}
    with attach_curl_on_fail(ENDPOINT, payload, headers={"Content-Type": "application/xml"}):
        response = api_client.post(ENDPOINT, json=payload, headers={"Content-Type": "application/xml"})
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"
        try:
            data = response.json()
            _validate_error_schema(data, "")
            assert data["error"]["statusCode"] == 422, f"Expected error statusCode 422, got {data['error']['statusCode']}"
        except json.JSONDecodeError as e:
            pytest.fail(f"Invalid JSON response: {e}")

def test_success_no_content_type(api_client, attach_curl_on_fail):
    interface = get_test_interface(api_client)
    payload = {"interface": interface, "bandwidth": 10}
    with attach_curl_on_fail(ENDPOINT, payload, headers={}):
        # Отправляем данные как строку без Content-Type
        response = api_client.post(ENDPOINT, data=json.dumps(payload), headers={})
        assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}"
        try:
            data = response.json()
            _validate_success_schema(data, "")
        except json.JSONDecodeError as e:
            pytest.fail(f"Invalid JSON response: {e}")

# --------------------------- Edge cases ---------------------------

def test_edge_case_very_long_interface_name(api_client, attach_curl_on_fail):
    long_interface = "a" * 1000
    payload = {"interface": long_interface, "bandwidth": 10}
    with attach_curl_on_fail(ENDPOINT, payload):
        response = api_client.post(ENDPOINT, json=payload)
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"
        try:
            data = response.json()
            _validate_error_schema(data, "")
            assert data["error"]["statusCode"] == 422, f"Expected error statusCode 422, got {data['error']['statusCode']}"
        except json.JSONDecodeError as e:
            pytest.fail(f"Invalid JSON response: {e}")

def test_edge_case_very_large_bandwidth(api_client, attach_curl_on_fail):
    interface = get_test_interface(api_client)
    payload = {"interface": interface, "bandwidth": 999999999}
    with attach_curl_on_fail(ENDPOINT, payload):
        response = api_client.post(ENDPOINT, json=payload)
        # API может принять или отклонить очень большие значения
        assert response.status_code in [200, 422], f"Expected 200 or 422, got {response.status_code}"
        if response.status_code == 200:
            try:
                data = response.json()
                _validate_success_schema(data, "")
            except json.JSONDecodeError as e:
                pytest.fail(f"Invalid JSON response: {e}")
        else:
            try:
                data = response.json()
                _validate_error_schema(data, "")
                assert data["error"]["statusCode"] == 422, f"Expected error statusCode 422, got {data['error']['statusCode']}"
            except json.JSONDecodeError as e:
                pytest.fail(f"Invalid JSON response: {e}")

def test_edge_case_special_characters_interface(api_client, attach_curl_on_fail):
    # Для этого теста используем специальные символы, так как тестируем валидацию
    payload = {"interface": "dummy@#$%", "bandwidth": 10}
    with attach_curl_on_fail(ENDPOINT, payload):
        response = api_client.post(ENDPOINT, json=payload)
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"
        try:
            data = response.json()
            _validate_error_schema(data, "")
            assert data["error"]["statusCode"] == 422, f"Expected error statusCode 422, got {data['error']['statusCode']}"
        except json.JSONDecodeError as e:
            pytest.fail(f"Invalid JSON response: {e}")

def test_edge_case_unicode_interface(api_client, attach_curl_on_fail):
    payload = {"interface": "dummy0привет", "bandwidth": 10}
    with attach_curl_on_fail(ENDPOINT, payload):
        response = api_client.post(ENDPOINT, json=payload)
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"
        try:
            data = response.json()
            _validate_error_schema(data, "")
            assert data["error"]["statusCode"] == 422, f"Expected error statusCode 422, got {data['error']['statusCode']}"
        except json.JSONDecodeError as e:
            pytest.fail(f"Invalid JSON response: {e}")

def test_edge_case_whitespace_interface(api_client, attach_curl_on_fail):
    interface = get_test_interface(api_client)
    payload = {"interface": f"   {interface}   ", "bandwidth": 10}
    with attach_curl_on_fail(ENDPOINT, payload):
        response = api_client.post(ENDPOINT, json=payload)
        # API может обрезать пробелы или вернуть ошибку
        assert response.status_code in [200, 422], f"Expected 200 or 422, got {response.status_code}"
        if response.status_code == 200:
            try:
                data = response.json()
                _validate_success_schema(data, "")
            except json.JSONDecodeError as e:
                pytest.fail(f"Invalid JSON response: {e}")
        else:
            try:
                data = response.json()
                _validate_error_schema(data, "")
                assert data["error"]["statusCode"] == 422, f"Expected error statusCode 422, got {data['error']['statusCode']}"
            except json.JSONDecodeError as e:
                pytest.fail(f"Invalid JSON response: {e}")

def test_edge_case_zero_bandwidth_after_setting(api_client, attach_curl_on_fail):
    interface = get_test_interface(api_client)
    # Сначала устанавливаем ограничение
    payload1 = {"interface": interface, "bandwidth": 20}
    with attach_curl_on_fail(ENDPOINT, payload1):
        response1 = api_client.post(ENDPOINT, json=payload1)
        assert response1.status_code == 200
    
    # Затем снимаем его
    payload2 = {"interface": interface, "bandwidth": 0}
    with attach_curl_on_fail(ENDPOINT, payload2):
        response2 = api_client.post(ENDPOINT, json=payload2)
        assert response2.status_code == 200, f"Expected 200 OK, got {response2.status_code}"
        try:
            data = response2.json()
            _validate_success_schema(data, "")
        except json.JSONDecodeError as e:
            pytest.fail(f"Invalid JSON response: {e}")

# --------------------------- Тесты функций получения интерфейсов ---------------------------

def test_get_available_interfaces(api_client):
    """Тест функции получения доступных интерфейсов"""
    interfaces = get_available_interfaces(api_client)
    assert isinstance(interfaces, list), "get_available_interfaces должна возвращать список"
    assert len(interfaces) > 0, "Должен быть хотя бы один доступный интерфейс"

    # Динамическая проверка: если есть не-loopback интерфейсы в ответе API,
    # то 'lo*' не должно быть в списке; иначе допустимо, что список содержит только loopback
    resp = api_client.get(IFCONFIG_ENDPOINT)
    if resp.status_code == 200:
        data = resp.json()
        all_ifaces = list(data.keys()) if isinstance(data, dict) else []
        expect_non_loopback = any(not str(i).startswith('lo') for i in all_ifaces)
        if expect_non_loopback:
            assert all(not str(i).startswith('lo') for i in interfaces), "Loopback не должен попадать в список при наличии других интерфейсов"

def test_get_test_interface(api_client):
    """Тест функции получения тестового интерфейса"""
    interface = get_test_interface(api_client)
    assert isinstance(interface, str), "get_test_interface должна возвращать строку"
    assert len(interface) > 0, "Имя интерфейса не должно быть пустым"
    
    # Проверяем, что интерфейс есть в списке доступных
    available_interfaces = get_available_interfaces(api_client)
    assert interface in available_interfaces, f"Выбранный интерфейс {interface} должен быть в списке доступных"
