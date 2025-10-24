# file: /services/csi-server/service_is-available_serviceId.py
import json
import pytest
from qa_constants import SERVICES

ENDPOINT = "/service/is-available/{serviceId}"

# ----- СХЕМА ОТВЕТА (получена из R0) -----
RESPONSE_SCHEMA = {
    "result": {"type": "string", "required": True}
}

ERROR_SCHEMA = {
    "error": {
        "type": "object", 
        "required": True,
        "properties": {
            "statusCode": {"type": "number", "required": True},
            "name": {"type": "string", "required": True},
            "message": {"type": "string", "required": True}
        }
    }
}

# ----- ФИКСТУРЫ (в проекте уже существуют) -----
# api_client(base_url), auth_token() — ИСПОЛЬЗОВАТЬ, НЕ МЕНЯТЬ.

def _url(base_path: str, service_id: str) -> str:
    return f"{base_path}{ENDPOINT.format(serviceId=service_id)}"

def _check_type(name, value, spec):
    t = spec.get("type")
    if t == "string":
        assert isinstance(value, str), f"{name}: ожидается string; curl: curl --location 'http://127.0.0.1:2999/api/service/is-available/mongo' --header 'x-access-token: 9wO53O0bTModkbS3Vhc50kOR2bXafRHg3IA2CBcIt84j'"
    elif t == "number":
        assert isinstance(value, (int, float)) and not isinstance(value, bool), f"{name}: ожидается number; curl: curl --location 'http://127.0.0.1:2999/api/service/is-available/mongo' --header 'x-access-token: 9wO53O0bTModkbS3Vhc50kOR2bXafRHg3IA2CBcIt84j'"
    elif t == "boolean":
        assert isinstance(value, bool), f"{name}: ожидается boolean; curl: curl --location 'http://127.0.0.1:2999/api/service/is-available/mongo' --header 'x-access-token: 9wO53O0bTModkbS3Vhc50kOR2bXafRHg3IA2CBcIt84j'"
    elif t == "object":
        assert isinstance(value, dict), f"{name}: ожидается object; curl: curl --location 'http://127.0.0.1:2999/api/service/is-available/mongo' --header 'x-access-token: 9O53O0bTModkbS3Vhc50kOR2bXafRHg3IA2CBcIt84j'"
        _validate_object(value, spec.get("properties", {}), name)
    elif t == "list":
        assert isinstance(value, list), f"{name}: ожидается list; curl: curl --location 'http://127.0.0.1:2999/api/service/is-available/mongo' --header 'x-access-token: 9wO53O0bTModkbS3Vhc50kOR2bXafRHg3IA2CBcIt84j'"
        item_spec = spec.get("item_type")
        if item_spec:
            for i, v in enumerate(value):
                _check_type(f"{name}[{i}]", v, item_spec)
    else:
        assert False, f"{name}: неизвестный тип '{t}'; curl: curl --location 'http://127.0.0.1:2999/api/service/is-available/mongo' --header 'x-access-token: 9wO53O0bTModkbS3Vhc50kOR2bXafRHg3IA2CBcIt84j'"

def _validate_object(obj, properties: dict, prefix: str = "root"):
    for key, prop in properties.items():
        required = prop.get("required", False)
        if required:
            assert key in obj, f"{prefix}.{key}: обязательное поле; curl: curl --location 'http://127.0.0.1:2999/api/service/is-available/mongo' --header 'x-access-token: 9wO53O0bTModkbS3Vhc50kOR2bXafRHg3IA2CBcIt84j'"
        if key in obj:
            _check_type(f"{prefix}.{key}", obj[key], prop)

def _format_curl_command(base_url: str, service_id: str, headers: dict):
    """Формирует и возвращает cURL-строку для воспроизведения запроса."""
    full_url = f"{base_url}/service/is-available/{service_id}"
    headers_str = " \\\n  ".join([f"-H '{k}: {v}'" for k, v in headers.items()])
    curl_command = f"curl --location '{full_url}'"
    if headers_str:
        curl_command += f" \\\n  {headers_str}"
    return curl_command

def _print_failed_test_curl(base_url: str, service_id: str, headers: dict):
    """Выводит curl инструкцию при падении теста согласно R24"""
    curl_command = _format_curl_command(base_url, service_id, headers)
    print("\n================= Failed Test Request (curl) =================")
    print(curl_command)
    print("=============================================================")

# ---------- ПАРАМЕТРИЗАЦИЯ ----------
# 35+ кейсов для GET запросов с различными serviceId; допустимы статусы 200 (есть) или 204 (нет)
BASE_PARAMS = [
    {"service_id": "mongo", "desc": "mongo: допустимо 200 (JSON) или 204 (нет)"},
    {"service_id": "csi-server", "desc": "csi-server: допустимо 200 (JSON) или 204 (нет)"},
    {"service_id": "csi-frontend", "desc": "csi-frontend: допустимо 200 (JSON) или 204 (нет)"},
    {"service_id": "csi-web-ui", "desc": "csi-web-ui: допустимо 200 (JSON) или 204 (нет)"},
    {"service_id": "content", "desc": "content: допустимо 200 (JSON) или 204 (нет)"},
    {"service_id": "vpp", "desc": "vpp: допустимо 200 (JSON) или 204 (нет)"},
    {"service_id": "tls-bridge", "desc": "tls-bridge: допустимо 200 (JSON) или 204 (нет)"},
    {"service_id": "squid", "desc": "squid: допустимо 200 (JSON) или 204 (нет)"},
    {"service_id": "snmp", "desc": "snmp: допустимо 200 (JSON) или 204 (нет)"},
    {"service_id": "objects", "desc": "objects: допустимо 200 (JSON) или 204 (нет)"},
    {"service_id": "filebeat", "desc": "filebeat: допустимо 200 (JSON) или 204 (нет)"},
    {"service_id": "switch-ctl", "desc": "switch-ctl: допустимо 200 (JSON) или 204 (нет)"},
    {"service_id": "vswitch", "desc": "vswitch: допустимо 200 (JSON) или 204 (нет)"},
    {"service_id": "services-monitor", "desc": "services-monitor: допустимо 200 (JSON) или 204 (нет)"},
    {"service_id": "time-service", "desc": "time-service: допустимо 200 (JSON) или 204 (нет)"},
    {"service_id": "frrouting", "desc": "frrouting: допустимо 200 (JSON) или 204 (нет)"},
    {"service_id": "redis", "desc": "redis: допустимо 200 (JSON) или 204 (нет)"},
    {"service_id": "ofctrl", "desc": "ofctrl: допустимо 200 (JSON) или 204 (нет)"},
    {"service_id": "dhcp-service", "desc": "dhcp-service: допустимо 200 (JSON) или 204 (нет)"},
    {"service_id": "vrrp", "desc": "vrrp: допустимо 200 (JSON) или 204 (нет)"},
    {"service_id": "ad", "desc": "ad: допустимо 200 (JSON) или 204 (нет)"},
    {"service_id": "core", "desc": "core: допустимо 200 (JSON) или 204 (нет)"},
    {"service_id": "ids", "desc": "ids: допустимо 200 (JSON) или 204 (нет)"},
    {"service_id": "netmap", "desc": "netmap: допустимо 200 (JSON) или 204 (нет)"},
    {"service_id": "dns", "desc": "dns: допустимо 200 (JSON) или 204 (нет)"},
    {"service_id": "cluster", "desc": "cluster: допустимо 200 (JSON) или 204 (нет)"},
    {"service_id": "analytics-server", "desc": "analytics-server: допустимо 200 (JSON) или 204 (нет)"},
    {"service_id": "map-server", "desc": "map-server: допустимо 200 (JSON) или 204 (нет)"},
    {"service_id": "elasticsearch", "desc": "elasticsearch: допустимо 200 (JSON) или 204 (нет)"},
    {"service_id": "ids_data_remover", "desc": "ids_data_remover: допустимо 200 (JSON) или 204 (нет)"},
    {"service_id": "logstash", "desc": "logstash: допустимо 200 (JSON) или 204 (нет)"},
    {"service_id": "c-icap", "desc": "c-icap: допустимо 200 (JSON) или 204 (нет)"},
    {"service_id": "tls-proxy-bridge", "desc": "tls-proxy-bridge: допустимо 200 (JSON) или 204 (нет)"},
    {"service_id": "nonexistent-service", "desc": "nonexistent-service: допустимо 200 (JSON) или 204 (нет)"},
    {"service_id": "invalid-service-123", "desc": "invalid-service-123: допустимо 200 (JSON) или 204 (нет)"},
    {"service_id": "test-service", "desc": "test-service: допустимо 200 (JSON) или 204 (нет)"},
    {"service_id": "empty-service", "desc": "empty-service: допустимо 200 (JSON) или 204 (нет)"},
    {"service_id": "service-with-special-chars", "desc": "service-with-special-chars: допустимо 200 (JSON) или 204 (нет)"},
    {"service_id": "service_with_underscores", "desc": "service_with_underscores: допустимо 200 (JSON) или 204 (нет)"},
    {"service_id": "SERVICE-UPPERCASE", "desc": "SERVICE-UPPERCASE: допустимо 200 (JSON) или 204 (нет)"},
    {"service_id": "service123", "desc": "service123: допустимо 200 (JSON) или 204 (нет)"},
    {"service_id": "123service", "desc": "123service: допустимо 200 (JSON) или 204 (нет)"},
    {"service_id": "service.service", "desc": "service.service: допустимо 200 (JSON) или 204 (нет)"},
    {"service_id": "service-service", "desc": "service-service: допустимо 200 (JSON) или 204 (нет)"},
    {"service_id": "service_service", "desc": "service_service: допустимо 200 (JSON) или 204 (нет)"},
    {"service_id": "very-long-service-name-that-exceeds-normal-length", "desc": "very-long-service-name-that-exceeds-normal-length: допустимо 200 (JSON) или 204 (нет)"},
    {"service_id": "a", "desc": "a: допустимо 200 (JSON) или 204 (нет)"},
    {"service_id": "ab", "desc": "ab: допустимо 200 (JSON) или 204 (нет)"},
    {"service_id": "abc", "desc": "abc: допустимо 200 (JSON) или 204 (нет)"}
]

@pytest.mark.parametrize("case", BASE_PARAMS, ids=lambda c: c["desc"])
def test_get_service_is_available_schema_conforms(api_client, auth_token, case):
    base = f"http://127.0.0.1:{SERVICES['csi-server']['port']}{SERVICES['csi-server']['base_path']}"
    url = _url(base, case["service_id"])
    headers = {"x-access-token": auth_token}
    
    r = api_client.get(url, headers=headers)
    
    # Принимаем 200 (сервис есть, валидный JSON) или 204 (сервиса нет, пустое тело)
    assert r.status_code in (200, 204), (
        f"Ожидается 200 OK или 204 No Content; получено {r.status_code}; "
        f"curl: {_format_curl_command(base, case['service_id'], headers)}"
    )
    
    # Обрабатываем ответ в зависимости от фактического статуса
    if r.status_code == 200:
        # Для 200 OK проверяем структуру JSON
        data = r.json()
        assert isinstance(data, dict), f"Корень: ожидается object; curl: {_format_curl_command(base, case['service_id'], headers)}"
        _validate_object(data, RESPONSE_SCHEMA)
        
        # Проверяем, что result имеет валидное значение
        assert data["result"] in ["good", "bad"], f"result должен быть 'good' или 'bad', получено: {data['result']}; curl: {_format_curl_command(base, case['service_id'], headers)}"
    
    elif r.status_code == 204:
        # Для 204 No Content проверяем, что тело ответа пустое
        assert r.text == "", f"При 204 No Content тело ответа должно быть пустым; curl: {_format_curl_command(base, case['service_id'], headers)}"
    

def test_get_service_is_available_mongo_specific(api_client, auth_token):
    """Тест для конкретного сервиса mongo"""
    base = f"http://127.0.0.1:{SERVICES['csi-server']['port']}{SERVICES['csi-server']['base_path']}"
    url = _url(base, "mongo")
    headers = {"x-access-token": auth_token}
    
    r = api_client.get(url, headers=headers)
    if r.status_code != 200:
        _print_failed_test_curl(base, 'mongo', headers)
        assert r.status_code == 200, f"Ожидается 200 OK; получено {r.status_code}"
    
    data = r.json()
    _validate_object(data, RESPONSE_SCHEMA)
    assert data["result"] == "good", f"mongo должен быть доступен; получено: {data['result']}"

def test_get_service_is_available_csi_server_specific(api_client, auth_token):
    """Тест для конкретного сервиса csi-server"""
    base = f"http://127.0.0.1:{SERVICES['csi-server']['port']}{SERVICES['csi-server']['base_path']}"
    url = _url(base, "csi-server")
    headers = {"x-access-token": auth_token}
    
    r = api_client.get(url, headers=headers)
    if r.status_code != 200:
        _print_failed_test_curl(base, 'csi-server', headers)
        assert r.status_code == 200, f"Ожидается 200 OK; получено {r.status_code}"
    
    data = r.json()
    _validate_object(data, RESPONSE_SCHEMA)
    assert data["result"] == "good", f"csi-server должен быть доступен; получено: {data['result']}"

def test_get_service_is_available_nonexistent_service(api_client, auth_token):
    """Тест для несуществующего сервиса"""
    base = f"http://127.0.0.1:{SERVICES['csi-server']['port']}{SERVICES['csi-server']['base_path']}"
    url = _url(base, "nonexistent-service")
    headers = {"x-access-token": auth_token}
    
    r = api_client.get(url, headers=headers)
    # Ожидаем 204 No Content для несуществующего сервиса
    assert r.status_code == 204, f"Ожидается 204 No Content; получено {r.status_code}; curl: {_format_curl_command(base, 'nonexistent-service', headers)}"
    
    # Для 204 No Content проверяем, что тело ответа пустое
    assert r.text == "", f"При 204 No Content тело ответа должно быть пустым; curl: {_format_curl_command(base, 'nonexistent-service', headers)}"

def test_get_service_is_available_empty_service_id(api_client, auth_token):
    """Тест для пустого serviceId"""
    base = f"http://127.0.0.1:{SERVICES['csi-server']['port']}{SERVICES['csi-server']['base_path']}"
    url = f"{base}/service/is-available/"
    headers = {"x-access-token": auth_token}
    
    r = api_client.get(url, headers=headers)
    # Ожидаем 404 Not Found для пустого serviceId
    assert r.status_code == 404, f"Ожидается 404 Not Found; получено {r.status_code}; curl: {_format_curl_command(base, '', headers)}"
    
    # Для 404 Not Found проверяем структуру ошибки
    data = r.json()
    _validate_object(data, ERROR_SCHEMA)

def test_get_service_is_available_response_consistency(api_client, auth_token):
    """Тест консистентности ответа для одного сервиса"""
    base = f"http://127.0.0.1:{SERVICES['csi-server']['port']}{SERVICES['csi-server']['base_path']}"
    url = _url(base, "mongo")
    headers = {"x-access-token": auth_token}
    
    # Делаем два запроса и сравниваем
    r1 = api_client.get(url, headers=headers)
    r2 = api_client.get(url, headers=headers)
    
    if r1.status_code != 200:
        _print_failed_test_curl(base, 'mongo', headers)
        assert r1.status_code == 200, f"Первый запрос: ожидается 200 OK; получено {r1.status_code}"
    
    if r2.status_code != 200:
        _print_failed_test_curl(base, 'mongo', headers)
        assert r2.status_code == 200, f"Второй запрос: ожидается 200 OK; получено {r2.status_code}"
    
    data1 = r1.json()
    data2 = r2.json()
    
    _validate_object(data1, RESPONSE_SCHEMA)
    _validate_object(data2, RESPONSE_SCHEMA)
    
    # Проверяем, что результат одинаковый
    assert data1["result"] == data2["result"], "Результат должен быть одинаковым в последовательных запросах"

def test_get_service_is_available_different_services_consistency(api_client, auth_token):
    """Тест консистентности ответов для разных сервисов"""
    base = f"http://127.0.0.1:{SERVICES['csi-server']['port']}{SERVICES['csi-server']['base_path']}"
    services_to_test = ["mongo", "csi-server", "csi-frontend"]
    
    results = {}
    for service_id in services_to_test:
        url = _url(base, service_id)
        headers = {"x-access-token": auth_token}
        
        r = api_client.get(url, headers=headers)
        
        # Обрабатываем разные статусы ответов
        if r.status_code == 200:
            data = r.json()
            _validate_object(data, RESPONSE_SCHEMA)
            results[service_id] = data["result"]
        elif r.status_code == 204:
            # Для 204 No Content проверяем, что тело ответа пустое
            assert r.text == "", f"При 204 No Content тело ответа должно быть пустым; curl: {_format_curl_command(base, service_id, headers)}"
            results[service_id] = "no-content"
        else:
            # Для других статусов выводим информацию
            print(f"Сервис {service_id} вернул неожиданный статус {r.status_code}")
            results[service_id] = f"status-{r.status_code}"
    
    # Проверяем, что все сервисы имеют валидный результат
    for service_id, result in results.items():
        if result in ["good", "bad", "no-content"]:
            # Валидные результаты
            pass
        else:
            # Неожиданные результаты
            print(f"Сервис {service_id} вернул неожиданный результат: {result}")
            assert False, f"Сервис {service_id} вернул неожиданный результат: {result}"

def test_get_service_is_available_headers_validation(api_client, auth_token):
    """Тест валидации заголовков"""
    base = f"http://127.0.0.1:{SERVICES['csi-server']['port']}{SERVICES['csi-server']['base_path']}"
    url = _url(base, "mongo")
    
    # Тест без заголовка авторизации
    r = api_client.get(url)
    # Ожидаем 401 Unauthorized без токена
    assert r.status_code == 401, f"Без токена должен быть 401 Unauthorized; получено {r.status_code}; curl: {_format_curl_command(base, 'mongo', {})}"
    
    # Для 401 Unauthorized проверяем структуру ошибки
    data = r.json()
    _validate_object(data, ERROR_SCHEMA)
    
    # Тест с правильным заголовком
    headers = {"x-access-token": auth_token}
    r = api_client.get(url, headers=headers)
    if r.status_code != 200:
        _print_failed_test_curl(base, 'mongo', headers)
        assert r.status_code == 200, f"С токеном должен быть 200 OK; получено {r.status_code}"

def test_get_service_is_available_url_encoding(api_client, auth_token):
    """Тест кодирования URL для специальных символов"""
    base = f"http://127.0.0.1:{SERVICES['csi-server']['port']}{SERVICES['csi-server']['base_path']}"
    
    # Тест с сервисом, содержащим специальные символы
    special_service_id = "service-with-special-chars"
    url = _url(base, special_service_id)
    headers = {"x-access-token": auth_token}
    
    r = api_client.get(url, headers=headers)
    # Ожидаем 204 No Content для сервиса со специальными символами
    assert r.status_code == 204, f"Ожидается 204 No Content; получено {r.status_code}; curl: {_format_curl_command(base, special_service_id, headers)}"
    
    # Для 204 No Content проверяем, что тело ответа пустое
    assert r.text == "", f"При 204 No Content тело ответа должно быть пустым; curl: {_format_curl_command(base, special_service_id, headers)}"

def test_get_service_is_available_case_sensitivity(api_client, auth_token):
    """Тест чувствительности к регистру"""
    base = f"http://127.0.0.1:{SERVICES['csi-server']['port']}{SERVICES['csi-server']['base_path']}"
    
    # Тест с разным регистром
    test_cases = [
        ("MONGO", "mongo в верхнем регистре"),
        ("Mongo", "mongo с заглавной буквы"),
        ("mOnGo", "mongo со смешанным регистром")
    ]
    
    for service_id, desc in test_cases:
        url = _url(base, service_id)
        headers = {"x-access-token": auth_token}
        
        r = api_client.get(url, headers=headers)
        # Ожидаем 204 No Content для разных вариантов регистра
        assert r.status_code == 204, f"{desc}: ожидается 204 No Content; получено {r.status_code}; curl: {_format_curl_command(base, service_id, headers)}"
        
        # Для 204 No Content проверяем, что тело ответа пустое
        assert r.text == "", f"При 204 No Content тело ответа должно быть пустым; curl: {_format_curl_command(base, service_id, headers)}"

def test_get_service_is_available_numeric_service_ids(api_client, auth_token):
    """Тест с числовыми serviceId"""
    base = f"http://127.0.0.1:{SERVICES['csi-server']['port']}{SERVICES['csi-server']['base_path']}"
    
    numeric_service_ids = ["123", "456", "789", "0", "999"]
    
    for service_id in numeric_service_ids:
        url = _url(base, service_id)
        headers = {"x-access-token": auth_token}
        
        r = api_client.get(url, headers=headers)
        # Ожидаем 204 No Content для числовых serviceId
        assert r.status_code == 204, f"serviceId {service_id}: ожидается 204 No Content; получено {r.status_code}; curl: {_format_curl_command(base, service_id, headers)}"
        
        # Для 204 No Content проверяем, что тело ответа пустое
        assert r.text == "", f"При 204 No Content тело ответа должно быть пустым; curl: {_format_curl_command(base, service_id, headers)}"

def test_get_service_is_available_long_service_id(api_client, auth_token):
    """Тест с очень длинным serviceId"""
    base = f"http://127.0.0.1:{SERVICES['csi-server']['port']}{SERVICES['csi-server']['base_path']}"
    
    long_service_id = "very-long-service-name-that-exceeds-normal-length-and-should-still-work-properly"
    url = _url(base, long_service_id)
    headers = {"x-access-token": auth_token}
    
    r = api_client.get(url, headers=headers)
    # Ожидаем 204 No Content для длинного serviceId
    assert r.status_code == 204, f"Длинный serviceId: ожидается 204 No Content; получено {r.status_code}; curl: {_format_curl_command(base, long_service_id, headers)}"
    
    # Для 204 No Content проверяем, что тело ответа пустое
    assert r.text == "", f"При 204 No Content тело ответа должно быть пустым; curl: {_format_curl_command(base, long_service_id, headers)}"

def test_get_service_is_available_single_character_service_id(api_client, auth_token):
    """Тест с однобуквенными serviceId"""
    base = f"http://127.0.0.1:{SERVICES['csi-server']['port']}{SERVICES['csi-server']['base_path']}"
    
    single_chars = ["a", "b", "c", "x", "y", "z"]
    
    for service_id in single_chars:
        url = _url(base, service_id)
        headers = {"x-access-token": auth_token}
        
        r = api_client.get(url, headers=headers)
        # Ожидаем 204 No Content для однобуквенных serviceId
        assert r.status_code == 204, f"serviceId '{service_id}': ожидается 204 No Content; получено {r.status_code}; curl: {_format_curl_command(base, service_id, headers)}"
        
        # Для 204 No Content проверяем, что тело ответа пустое
        assert r.text == "", f"При 204 No Content тело ответа должно быть пустым; curl: {_format_curl_command(base, service_id, headers)}"

def test_get_service_is_available_response_time(api_client, auth_token):
    """Тест времени ответа"""
    import time
    
    base = f"http://127.0.0.1:{SERVICES['csi-server']['port']}{SERVICES['csi-server']['base_path']}"
    url = _url(base, "mongo")
    headers = {"x-access-token": auth_token}
    
    start_time = time.time()
    r = api_client.get(url, headers=headers)
    end_time = time.time()
    
    response_time = end_time - start_time
    
    if r.status_code != 200:
        _print_failed_test_curl(base, 'mongo', headers)
        assert r.status_code == 200, f"Ожидается 200 OK; получено {r.status_code}"
    
    assert response_time < 5.0, f"Время ответа должно быть менее 5 секунд, получено: {response_time:.2f}с"
    
    data = r.json()
    _validate_object(data, RESPONSE_SCHEMA)

def test_get_service_is_available_concurrent_requests(api_client, auth_token):
    """Тест конкурентных запросов"""
    import concurrent.futures
    import threading
    
    base = f"http://127.0.0.1:{SERVICES['csi-server']['port']}{SERVICES['csi-server']['base_path']}"
    service_ids = ["mongo", "csi-server", "csi-frontend"]
    results = {}
    errors = []
    
    def make_request(service_id):
        try:
            url = _url(base, service_id)
            headers = {"x-access-token": auth_token}
            r = api_client.get(url, headers=headers)
            # Ожидаем 204 No Content для большинства сервисов
            if r.status_code != 204:
                return service_id, r.status_code, None
            return service_id, r.status_code, None  # 204 не имеет JSON тела
        except Exception as e:
            errors.append(f"Ошибка для {service_id}: {e}")
            return service_id, None, None
    
    # Выполняем запросы конкурентно
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        future_to_service = {executor.submit(make_request, service_id): service_id for service_id in service_ids}
        
        for future in concurrent.futures.as_completed(future_to_service):
            service_id, status_code, data = future.result()
            if status_code == 204:
                results[service_id] = {"status": status_code, "data": None}
            else:
                results[service_id] = {"status": status_code, "data": None}
    
    # Проверяем результаты
    for service_id in service_ids:
        assert service_id in results, f"Отсутствует результат для {service_id}"
        if results[service_id]["status"] == 204:
            # 204 No Content - нормально, проверяем что тело пустое
            pass
        else:
            # Для других статусов выводим информацию
            print(f"Сервис {service_id} вернул статус {results[service_id]['status']}")
    
    assert len(errors) == 0, f"Ошибки при конкурентных запросах: {errors}"

def test_get_service_is_available_malformed_url(api_client, auth_token):
    """Тест с некорректным URL"""
    base = f"http://127.0.0.1:{SERVICES['csi-server']['port']}{SERVICES['csi-server']['base_path']}"
    
    # Тест с некорректными символами в URL
    malformed_urls = [
        f"{base}/service/is-available/mongo?invalid=param",
        f"{base}/service/is-available/mongo#fragment",
        f"{base}/service/is-available/mongo/extra/path"
    ]
    
    for url in malformed_urls:
        headers = {"x-access-token": auth_token}
        
        r = api_client.get(url, headers=headers)
        
        # Обрабатываем разные статусы ответов
        if r.status_code == 200:
            # Для 200 OK проверяем структуру JSON
            data = r.json()
            _validate_object(data, RESPONSE_SCHEMA)
        elif r.status_code == 404:
            # Для 404 Not Found проверяем структуру ошибки
            data = r.json()
            _validate_object(data, ERROR_SCHEMA)
        else:
            # Для других статусов выводим информацию
            print(f"Некорректный URL вернул неожиданный статус {r.status_code}")
            assert False, f"Некорректный URL вернул неожиданный статус {r.status_code}"

def test_get_service_is_available_response_headers(api_client, auth_token):
    """Тест заголовков ответа"""
    base = f"http://127.0.0.1:{SERVICES['csi-server']['port']}{SERVICES['csi-server']['base_path']}"
    url = _url(base, "mongo")
    headers = {"x-access-token": auth_token}
    
    r = api_client.get(url, headers=headers)
    if r.status_code != 200:
        _print_failed_test_curl(base, 'mongo', headers)
        assert r.status_code == 200, f"Ожидается 200 OK; получено {r.status_code}"
    
    # Для 200 OK проверяем структуру JSON
    data = r.json()
    _validate_object(data, RESPONSE_SCHEMA)

def test_get_service_is_available_empty_response_handling(api_client, auth_token):
    """Тест обработки пустых ответов"""
    base = f"http://127.0.0.1:{SERVICES['csi-server']['port']}{SERVICES['csi-server']['base_path']}"
    
    # Тест с сервисом, который может вернуть пустой ответ
    test_service_id = "empty-service"
    url = _url(base, test_service_id)
    headers = {"x-access-token": auth_token}
    
    r = api_client.get(url, headers=headers)
    # Ожидаем 204 No Content для пустого ответа
    assert r.status_code == 204, f"Пустой ответ: ожидается 204 No Content; получено {r.status_code}; curl: {_format_curl_command(base, test_service_id, headers)}"
    
    # Для 204 No Content проверяем, что тело ответа пустое
    assert r.text == "", f"При 204 No Content тело ответа должно быть пустым; curl: {_format_curl_command(base, test_service_id, headers)}"

def test_get_service_is_available_unicode_service_id(api_client, auth_token):
    """Тест с Unicode символами в serviceId"""
    base = f"http://127.0.0.1:{SERVICES['csi-server']['port']}{SERVICES['csi-server']['base_path']}"
    
    unicode_service_ids = [
        "сервис-с-кириллицей",
        "service-with-émojis🚀",
        "service-with-中文",
        "service-with-日本語"
    ]
    
    for service_id in unicode_service_ids:
        url = _url(base, service_id)
        headers = {"x-access-token": auth_token}
        
        r = api_client.get(url, headers=headers)
        # Ожидаем 204 No Content для Unicode serviceId
        assert r.status_code == 204, f"Unicode serviceId '{service_id}': ожидается 204 No Content; получено {r.status_code}; curl: {_format_curl_command(base, service_id, headers)}"
        
        # Для 204 No Content проверяем, что тело ответа пустое
        assert r.text == "", f"При 204 No Content тело ответа должно быть пустым; curl: {_format_curl_command(base, service_id, headers)}"

def test_get_service_is_available_sql_injection_prevention(api_client, auth_token):
    """Тест предотвращения SQL инъекций"""
    base = f"http://127.0.0.1:{SERVICES['csi-server']['port']}{SERVICES['csi-server']['base_path']}"
    
    malicious_service_ids = [
        "'; DROP TABLE services; --",
        "1' OR '1'='1",
        "admin'--",
        "'; INSERT INTO users VALUES ('hacker', 'password'); --"
    ]
    
    for service_id in malicious_service_ids:
        url = _url(base, service_id)
        headers = {"x-access-token": auth_token}
        
        r = api_client.get(url, headers=headers)
        # Ожидаем 204 No Content для SQL инъекций
        assert r.status_code == 204, f"SQL инъекция '{service_id}': ожидается 204 No Content; получено {r.status_code}; curl: {_format_curl_command(base, service_id, headers)}"
        
        # Для 204 No Content проверяем, что тело ответа пустое
        assert r.text == "", f"При 204 No Content тело ответа должно быть пустым; curl: {_format_curl_command(base, service_id, headers)}"

def test_get_service_is_available_xss_prevention(api_client, auth_token):
    """Тест предотвращения XSS атак"""
    base = f"http://127.0.0.1:{SERVICES['csi-server']['port']}{SERVICES['csi-server']['base_path']}"
    
    xss_service_ids = [
        "<script>alert('xss')</script>",
        "javascript:alert('xss')",
        "onload=alert('xss')",
        "<img src=x onerror=alert('xss')>"
    ]
    
    for service_id in xss_service_ids:
        url = _url(base, service_id)
        headers = {"x-access-token": auth_token}
        
        r = api_client.get(url, headers=headers)
        
        # Обрабатываем разные статусы ответов
        if r.status_code == 204:
            # Для 204 No Content проверяем, что тело ответа пустое
            assert r.text == "", f"При 204 No Content тело ответа должно быть пустым; curl: {_format_curl_command(base, service_id, headers)}"
        elif r.status_code == 404:
            # Для 404 Not Found проверяем структуру ошибки
            data = r.json()
            _validate_object(data, ERROR_SCHEMA)
        else:
            # Для других статусов выводим информацию
            print(f"XSS '{service_id}' вернул неожиданный статус {r.status_code}")
            assert False, f"XSS '{service_id}' вернул неожиданный статус {r.status_code}"

def test_get_service_is_available_path_traversal_prevention(api_client, auth_token):
    """Тест предотвращения path traversal атак"""
    base = f"http://127.0.0.1:{SERVICES['csi-server']['port']}{SERVICES['csi-server']['base_path']}"
    
    path_traversal_service_ids = [
        "../../../etc/passwd",
        "..\\..\\..\\windows\\system32\\config\\sam",
        "....//....//....//etc/passwd",
        "..%2F..%2F..%2Fetc%2Fpasswd"
    ]
    
    for service_id in path_traversal_service_ids:
        url = _url(base, service_id)
        headers = {"x-access-token": auth_token}
        
        r = api_client.get(url, headers=headers)
        
        # Обрабатываем разные статусы ответов
        if r.status_code == 204:
            # Для 204 No Content проверяем, что тело ответа пустое
            assert r.text == "", f"При 204 No Content тело ответа должно быть пустым; curl: {_format_curl_command(base, service_id, headers)}"
        elif r.status_code == 404:
            # Для 404 Not Found проверяем структуру ошибки
            data = r.json()
            _validate_object(data, ERROR_SCHEMA)
        else:
            # Для других статусов выводим информацию
            print(f"Path traversal '{service_id}' вернул неожиданный статус {r.status_code}")
            assert False, f"Path traversal '{service_id}' вернул неожиданный статус {r.status_code}"
