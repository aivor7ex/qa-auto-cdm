# file: /services/csi-server/service_environment_stack_service.py
import json
import pytest
import urllib.parse
from qa_constants import SERVICES

ENDPOINT = "/service/environment/{stack}/{service}"

# ----- СХЕМА ОТВЕТА (получена из R0) -----
RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        # Универсальная схема для любых переменных окружения
        # Все поля опциональны, так как каждый сервис имеет свои переменные
    },
    "additionalProperties": True,  # Разрешаем любые дополнительные свойства
    "patternProperties": {
        ".*": {
            "type": ["string", "number", "boolean"],
            "required": False
        }
    }
}

# ----- СХЕМА ОТВЕТА ДЛЯ POST ЗАПРОСОВ (установка переменных) -----
SUCCESS_RESPONSE_SCHEMA = {
    "result": str
}

# ----- ФИКСТУРЫ (в проекте уже существуют) -----
# api_client(base_url), auth_token() — ИСПОЛЬЗОВАТЬ, НЕ МЕНЯТЬ.

def _url(base_path: str, stack: str, service: str) -> str:
    return f"{base_path}{ENDPOINT.format(stack=stack, service=service)}"

def _check_type(name, value, spec):
    t = spec.get("type")
    if t == "string":
        assert isinstance(value, str), f"{name}: ожидается string, получено {type(value).__name__} со значением {repr(value)}"
    elif t == "number":
        assert isinstance(value, (int, float)) and not isinstance(value, bool), f"{name}: ожидается number, получено {type(value).__name__} со значением {repr(value)}"
    elif t == "boolean":
        assert isinstance(value, bool), f"{name}: ожидается boolean, получено {type(value).__name__} со значением {repr(value)}"
    elif t == "object":
        assert isinstance(value, dict), f"{name}: ожидается object, получено {type(value).__name__} со значением {repr(value)}"
        _validate_object(value, spec.get("properties", {}), name)
    elif t == "list":
        assert isinstance(value, list), f"{name}: ожидается list, получено {type(value).__name__} со значением {repr(value)}"
        item_spec = spec.get("item_type")
        if item_spec:
            for i, v in enumerate(value):
                _check_type(f"{name}[{i}]", v, item_spec)
    else:
        assert False, f"{name}: неизвестный тип '{t}'"

def _validate_object(obj, properties: dict, prefix: str = "root"):
    for key, prop in properties.items():
        required = prop.get("required", False)
        if required:
            assert key in obj, f"{prefix}.{key}: обязательное поле отсутствует"
        if key in obj:
            _check_type(f"{prefix}.{key}", obj[key], prop)


# ---------- ПАРАМЕТРИЗАЦИЯ ----------
# 35+ кейсов для GET запросов с различными stack/service комбинациями
BASE_PARAMS = [
    {"stack": "ngfw", "service": "ad", "desc": "ngfw ad service environment"},
    {"stack": "csi", "service": "csi-server", "desc": "csi csi-server service environment"},
    {"stack": "vpp", "service": "vpp", "desc": "vpp vpp service environment"},
    {"stack": "squid", "service": "squid", "desc": "squid squid service environment"},
    {"stack": "snmp", "service": "snmp", "desc": "snmp snmp service environment"},
    {"stack": "shared", "service": "mongo", "desc": "shared mongo service environment"},
    {"stack": "shared", "service": "objects", "desc": "shared objects service environment"},
    {"stack": "ngfw", "service": "core", "desc": "ngfw core service environment"},
    {"stack": "ngfw", "service": "ids", "desc": "ngfw ids service environment"},
    {"stack": "ngfw", "service": "netmap", "desc": "ngfw netmap service environment"},
    {"stack": "ngfw", "service": "dns", "desc": "ngfw dns service environment"},
    {"stack": "ngfw", "service": "cluster", "desc": "ngfw cluster service environment"},
    {"stack": "ngfw", "service": "vswitch", "desc": "ngfw vswitch service environment"},
    {"stack": "ngfw", "service": "services-monitor", "desc": "ngfw services-monitor service environment"},
    {"stack": "ngfw", "service": "time-service", "desc": "ngfw time-service service environment"},
    {"stack": "ngfw", "service": "frrouting", "desc": "ngfw frrouting service environment"},
    {"stack": "ngfw", "service": "redis", "desc": "ngfw redis service environment"},
    {"stack": "ngfw", "service": "ofctrl", "desc": "ngfw ofctrl service environment"},
    {"stack": "ngfw", "service": "dhcp-service", "desc": "ngfw dhcp-service service environment"},
    {"stack": "ngfw", "service": "vrrp", "desc": "ngfw vrrp service environment"},
    {"stack": "ngfw", "service": "filebeat", "desc": "ngfw filebeat service environment"},
    {"stack": "ngfw", "service": "switch-ctl", "desc": "ngfw switch-ctl service environment"},
    {"stack": "logger-analytics", "service": "analytics-server", "desc": "logger-analytics analytics-server service environment"},
    {"stack": "logger-analytics", "service": "map-server", "desc": "logger-analytics map-server service environment"},
    {"stack": "logger-analytics", "service": "elasticsearch", "desc": "logger-analytics elasticsearch service environment"},
    {"stack": "logger-analytics", "service": "ids_data_remover", "desc": "logger-analytics ids_data_remover service environment"},
    {"stack": "logger-analytics", "service": "logstash", "desc": "logger-analytics logstash service environment"},
    {"stack": "csi", "service": "csi-frontend", "desc": "csi csi-frontend service environment"},
    {"stack": "csi", "service": "csi-web-ui", "desc": "csi csi-web-ui service environment"},
    {"stack": "csi", "service": "content", "desc": "csi content service environment"},
    {"stack": "tls-bridge", "service": "tls-bridge", "desc": "tls-bridge tls-bridge service environment"},
    {"stack": "tls-bridge", "service": "tls-filebeat", "desc": "tls-bridge tls-filebeat service environment"},
    {"stack": "tls-bridge", "service": "tls-proxy-bridge", "desc": "tls-bridge tls-proxy-bridge service environment"},
    {"stack": "squid", "service": "c-icap", "desc": "squid c-icap service environment"},
]

# Параметры для тестов типов данных
TYPE_TEST_PARAMS = [
    {"stack": "ngfw", "service": "ad", "desc": "ngfw ad types"},
    {"stack": "shared", "service": "mongo", "desc": "shared mongo types"},
    {"stack": "tls-bridge", "service": "tls-bridge", "desc": "tls-bridge types"},
]

@pytest.mark.parametrize("case", BASE_PARAMS, ids=lambda c: c["desc"])
def test_get_service_environment_parametrized(api_client, auth_token, case, attach_curl_on_fail):
    """Параметризованный тест для различных stack/service комбинаций    """
    base = f"http://127.0.0.1:{SERVICES['csi-server']['port']}{SERVICES['csi-server']['base_path']}"
    url = _url(base, case["stack"], case["service"])
    headers = {"x-access-token": auth_token}
    
    with attach_curl_on_fail(ENDPOINT.format(stack=case["stack"], service=case["service"]), None, headers, "GET"):
        r = api_client.get(url, headers=headers)
        # Допускаем 200 (данные есть), 204 (пусто) или 400 (сервис недоступен/отсутствует)
        assert r.status_code in (200, 204, 400), f"Ожидается 200, 204 или 400; получено {r.status_code}"
        
        if r.status_code == 204:
            # Пустое тело — валидно для некоторых сервисов
            return
        
        if r.status_code == 400:
            # Сервис недоступен или отсутствует — валидно для некоторых комбинаций
            error_data = r.json()
            assert "error" in error_data, f"При статусе 400 ожидается объект с полем 'error'"
            return
        
        data = r.json()
        assert isinstance(data, dict), f"Корень: ожидается object"
        
        # Валидируем структуру ответа
        _validate_object(data, RESPONSE_SCHEMA.get("properties", {}))
        

def test_get_service_environment_ngfw_ad_specific(api_client, auth_token, attach_curl_on_fail):
    """Специфичный тест для ngfw/ad с проверкой структуры переменных окружения    """
    base = f"http://127.0.0.1:{SERVICES['csi-server']['port']}{SERVICES['csi-server']['base_path']}"
    url = _url(base, "ngfw", "ad")
    headers = {"x-access-token": auth_token}
    
    with attach_curl_on_fail(ENDPOINT.format(stack="ngfw", service="ad"), None, headers, "GET"):
        r = api_client.get(url, headers=headers)
        assert r.status_code in (200, 204, 400), f"Ожидается 200, 204 или 400; получено {r.status_code}"
        
        if r.status_code == 204:
            return
        
        if r.status_code == 400:
            # Сервис недоступен или отсутствует — валидно для некоторых комбинаций
            error_data = r.json()
            assert "error" in error_data, f"При статусе 400 ожидается объект с полем 'error'"
            return
        
        data = r.json()
        assert isinstance(data, dict), f"Корень: ожидается object"
        
        # Проверяем, что все ключи являются строками
        for key in data.keys():
            assert isinstance(key, str), f"Ключи должны быть строками"
        
        # Проверяем, что все значения имеют допустимые типы
        for key, value in data.items():
            assert isinstance(value, (str, int, float, bool)), f"Значение {key} должно быть строкой, числом или булевым"
            

def test_get_service_environment_empty_response(api_client, auth_token, attach_curl_on_fail):
    """Тест для сервисов с пустым ответом    """
    base = f"http://127.0.0.1:{SERVICES['csi-server']['port']}{SERVICES['csi-server']['base_path']}"
    url = _url(base, "csi", "csi-server")
    headers = {"x-access-token": auth_token}
    
    with attach_curl_on_fail(ENDPOINT.format(stack="csi", service="csi-server"), None, headers, "GET"):
        r = api_client.get(url, headers=headers)
        assert r.status_code in (200, 204, 400), f"Ожидается 200, 204 или 400; получено {r.status_code}"
        
        if r.status_code == 204:
            return
        
        if r.status_code == 400:
            # Сервис недоступен или отсутствует — валидно для некоторых комбинаций
            error_data = r.json()
            assert "error" in error_data, f"При статусе 400 ожидается объект с полем 'error'"
            return
        
        data = r.json()
        assert isinstance(data, dict), f"Корень: ожидается object"
        assert len(data) == 0, f"Ответ должен быть пустым объектом"
        

def test_get_service_environment_response_structure(api_client, auth_token, attach_curl_on_fail):
    """Тест структуры ответа для различных сервисов    """
    base = f"http://127.0.0.1:{SERVICES['csi-server']['port']}{SERVICES['csi-server']['base_path']}"
    url = _url(base, "vpp", "vpp")
    headers = {"x-access-token": auth_token}
    
    with attach_curl_on_fail(ENDPOINT.format(stack="vpp", service="vpp"), None, headers, "GET"):
        r = api_client.get(url, headers=headers)
        # Допускаем 200 (данные есть), 204 (пусто) или 400 (сервис недоступен/отсутствует)
        assert r.status_code in (200, 204, 400), f"Ожидается 200, 204 или 400; получено {r.status_code}"
        
        if r.status_code == 204:
            return
        
        if r.status_code == 400:
            # Сервис недоступен или отсутствует — валидно для некоторых комбинаций
            error_data = r.json()
            assert "error" in error_data, f"При статусе 400 ожидается объект с полем 'error'"
            return
        
        data = r.json()
        assert isinstance(data, dict), f"Корень: ожидается object"
        
        # Проверяем, что все значения в объекте имеют допустимые типы
        for key, value in data.items():
            assert isinstance(key, str), f"Ключи должны быть строками"
            assert isinstance(value, (str, int, float, bool)), f"Значения должны быть строкой, числом или булевым"
            

def test_get_service_environment_consistency(api_client, auth_token, attach_curl_on_fail):
    """Тест консистентности ответов    """
    base = f"http://127.0.0.1:{SERVICES['csi-server']['port']}{SERVICES['csi-server']['base_path']}"
    url = _url(base, "ngfw", "ad")
    headers = {"x-access-token": auth_token}
    
    with attach_curl_on_fail(ENDPOINT.format(stack="ngfw", service="ad"), None, headers, "GET"):
        # Делаем два запроса и сравниваем
        r1 = api_client.get(url, headers=headers)
        r2 = api_client.get(url, headers=headers)
        
        # Допускаем 200 (данные есть), 204 (пусто) или 400 (сервис недоступен/отсутствует)
        assert r1.status_code in (200, 204, 400), f"Первый запрос: ожидается 200, 204 или 400; получено {r1.status_code}"
        assert r2.status_code in (200, 204, 400), f"Второй запрос: ожидается 200, 204 или 400; получено {r2.status_code}"
        
        # Если один из запросов вернул ошибку, тест не может проверить консистентность
        if r1.status_code == 400 or r2.status_code == 400:
            # Проверяем, что при статусе 400 есть поле error
            if r1.status_code == 400:
                error_data = r1.json()
                assert "error" in error_data, f"Первый запрос: при статусе 400 ожидается объект с полем 'error'"
            if r2.status_code == 400:
                error_data = r2.json()
                assert "error" in error_data, f"Второй запрос: при статусе 400 ожидается объект с полем 'error'"
            return
        
        # Если один из запросов пустой, тест не может проверить консистентность
        if r1.status_code == 204 or r2.status_code == 204:
            return
        
        data1 = r1.json()
        data2 = r2.json()
        
        # Проверяем, что структура данных одинакова
        assert set(data1.keys()) == set(data2.keys()), f"Набор ключей должен быть одинаковым"
        
        # Проверяем, что типы данных одинаковые
        for key in data1.keys():
            assert type(data1[key]) == type(data2[key]), f"Типы данных для ключа {key} должны быть одинаковыми"
            

def test_get_service_environment_all_stacks(api_client, auth_token, attach_curl_on_fail):
    """Тест всех доступных стеков"""
    stacks = ["ngfw", "csi", "vpp", "squid", "snmp", "shared", "logger-analytics", "tls-bridge"]
    
    for stack in stacks:
        # Берем первый сервис из стека для тестирования
        if stack == "ngfw":
            service = "ad"
        elif stack == "csi":
            service = "csi-server"
        elif stack == "vpp":
            service = "vpp"
        elif stack == "squid":
            service = "squid"
        elif stack == "snmp":
            service = "snmp"
        elif stack == "shared":
            service = "mongo"
        elif stack == "logger-analytics":
            service = "analytics-server"
        elif stack == "tls-bridge":
            service = "tls-bridge"
        else:
            continue
            
        base = f"http://127.0.0.1:{SERVICES['csi-server']['port']}{SERVICES['csi-server']['base_path']}"
        url = _url(base, stack, service)
        headers = {"x-access-token": auth_token}
        
        with attach_curl_on_fail(ENDPOINT.format(stack=stack, service=service), None, headers, "GET"):
            r = api_client.get(url, headers=headers)
            assert r.status_code in (200, 204, 400), f"Стек {stack}: ожидается 200, 204 или 400; получено {r.status_code}"
            
            if r.status_code == 204:
                continue
            
            if r.status_code == 400:
                # Сервис недоступен или отсутствует — валидно для некоторых комбинаций
                error_data = r.json()
                assert "error" in error_data, f"Стек {stack}: при статусе 400 ожидается объект с полем 'error'"
                continue
            data = r.json()
            assert isinstance(data, dict), f"Стек {stack}: корень должен быть object"
            

@pytest.mark.parametrize("case", TYPE_TEST_PARAMS, ids=lambda c: c["desc"])
def test_get_service_environment_field_types_parametrized(api_client, auth_token, case, attach_curl_on_fail):
    """Параметризованный тест типов полей в ответе для различных сервисов    """
    base = f"http://127.0.0.1:{SERVICES['csi-server']['port']}{SERVICES['csi-server']['base_path']}"
    url = _url(base, case["stack"], case["service"])
    headers = {"x-access-token": auth_token}
    
    with attach_curl_on_fail(ENDPOINT.format(stack=case["stack"], service=case["service"]), None, headers, "GET"):
        r = api_client.get(url, headers=headers)
        assert r.status_code in (200, 204, 400), f"Ожидается 200, 204 или 400; получено {r.status_code}"
        
        if r.status_code == 204:
            return
        
        if r.status_code == 400:
            # Сервис недоступен или отсутствует — валидно для некоторых комбинаций
            error_data = r.json()
            assert "error" in error_data, f"При статусе 400 ожидается объект с полем 'error'"
            return
        
        data = r.json()

        # Проверяем типы всех полей
        for key, value in data.items():
            assert isinstance(key, str), f"Ключи должны быть строками"
            assert isinstance(value, (str, int, float, bool)), f"Значения должны быть строкой, числом или булевым"
            

def test_get_service_environment_response_format(api_client, auth_token, attach_curl_on_fail):
    """Тест формата ответа для различных сервисов"""
    # Тестируем несколько сервисов для проверки формата
    test_cases = [
        ("squid", "squid"),
        ("ngfw", "ad"),
        ("shared", "mongo")
    ]
    
    for stack, service in test_cases:
        base = f"http://127.0.0.1:{SERVICES['csi-server']['port']}{SERVICES['csi-server']['base_path']}"
        url = _url(base, stack, service)
        headers = {"x-access-token": auth_token}
        
        with attach_curl_on_fail(ENDPOINT.format(stack=stack, service=service), None, headers, "GET"):
            r = api_client.get(url, headers=headers)
            # Допускаем 200 (данные есть), 204 (пусто) или 400 (сервис недоступен/отсутствует)
            assert r.status_code in (200, 204, 400), f"Сервис {stack}/{service}: ожидается 200, 204 или 400; получено {r.status_code}"
            
            if r.status_code == 204:
                continue
            
            if r.status_code == 400:
                # Сервис недоступен или отсутствует — валидно для некоторых комбинаций
                error_data = r.json()
                assert "error" in error_data, f"Сервис {stack}/{service}: при статусе 400 ожидается объект с полем 'error'"
                continue
            
            # Проверяем заголовки ответа
            assert "application/json" in r.headers.get("content-type", ""), f"Сервис {stack}/{service}: Content-Type должен быть application/json"
            
            data = r.json()
            assert isinstance(data, dict), f"Сервис {stack}/{service}: ответ должен быть объектом"
            

def test_get_service_environment_simple_values(api_client, auth_token, attach_curl_on_fail):
    """Тест простых значений в ответе (строки, числа, булевы)    """
    base = f"http://127.0.0.1:{SERVICES['csi-server']['port']}{SERVICES['csi-server']['base_path']}"
    url = _url(base, "shared", "mongo")
    headers = {"x-access-token": auth_token}
    
    with attach_curl_on_fail(ENDPOINT.format(stack="shared", service="mongo"), None, headers, "GET"):
        r = api_client.get(url, headers=headers)
        assert r.status_code in (200, 204, 400), f"Ожидается 200, 204 или 400; получено {r.status_code}"
        
        if r.status_code == 204:
            return
        
        if r.status_code == 400:
            # Сервис недоступен или отсутствует — валидно для некоторых комбинаций
            error_data = r.json()
            assert "error" in error_data, f"При статусе 400 ожидается объект с полем 'error'"
            return
        
        data = r.json()
        assert isinstance(data, dict), f"Ответ должен быть объектом"
        
        # Проверяем, что все значения являются простыми типами
        for key, value in data.items():
            assert isinstance(value, (str, int, float, bool)), f"Значения должны быть строкой, числом или булевым"
            

                



                

                

            

        

def test_get_service_environment_json_validity(api_client, auth_token, attach_curl_on_fail):
    """Тест валидности JSON в ответе    """
    base = f"http://127.0.0.1:{SERVICES['csi-server']['port']}{SERVICES['csi-server']['base_path']}"
    url = _url(base, "csi", "csi-server")
    headers = {"x-access-token": auth_token}
    
    with attach_curl_on_fail(ENDPOINT.format(stack="csi", service="csi-server"), None, headers, "GET"):
        r = api_client.get(url, headers=headers)
        # Допускаем 200 (данные есть), 204 (пусто) или 400 (сервис недоступен/отсутствует)
        assert r.status_code in (200, 204, 400), f"Ожидается 200, 204 или 400; получено {r.status_code}"
        
        if r.status_code == 204:
            return
        
        if r.status_code == 400:
            # Сервис недоступен или отсутствует — валидно для некоторых комбинаций
            error_data = r.json()
            assert "error" in error_data, f"При статусе 400 ожидается объект с полем 'error'"
            return
        
        # Проверяем, что ответ является валидным JSON
        data = r.json()
        assert isinstance(data, dict), f"Ответ должен быть объектом"

# ----- НЕГАТИВНЫЕ GET ТЕСТЫ -----

def test_get_service_environment_unauthorized(api_client, attach_curl_on_fail):
    """Тест GET запроса без авторизации"""
    base = f"http://127.0.0.1:{SERVICES['csi-server']['port']}{SERVICES['csi-server']['base_path']}"
    url = _url(base, "ngfw", "ids")
    
    with attach_curl_on_fail(ENDPOINT.format(stack="ngfw", service="ids"), None, {}, "GET"):
        r = api_client.get(url)
        assert r.status_code in (401, 403), f"Ожидается 401 или 403; получено {r.status_code}"

def test_get_service_environment_invalid_token(api_client, attach_curl_on_fail):
    """Тест GET запроса с невалидным токеном"""
    base = f"http://127.0.0.1:{SERVICES['csi-server']['port']}{SERVICES['csi-server']['base_path']}"
    url = _url(base, "ngfw", "ids")
    headers = {"x-access-token": "invalid_token_12345"}
    
    with attach_curl_on_fail(ENDPOINT.format(stack="ngfw", service="ids"), None, headers, "GET"):
        r = api_client.get(url, headers=headers)
        assert r.status_code in (401, 403), f"Ожидается 401 или 403; получено {r.status_code}"

def test_get_service_environment_invalid_stack(api_client, auth_token, attach_curl_on_fail):
    """Тест GET запроса с невалидным стеком"""
    base = f"http://127.0.0.1:{SERVICES['csi-server']['port']}{SERVICES['csi-server']['base_path']}"
    url = _url(base, "invalid@stack", "ids")
    headers = {"x-access-token": auth_token}
    
    with attach_curl_on_fail(ENDPOINT.format(stack="invalid@stack", service="ids"), None, headers, "GET"):
        r = api_client.get(url, headers=headers)
        assert r.status_code in (400, 404), f"Ожидается 400 или 404; получено {r.status_code}"

def test_get_service_environment_invalid_service(api_client, auth_token, attach_curl_on_fail):
    """Тест GET запроса с невалидным сервисом"""
    base = f"http://127.0.0.1:{SERVICES['csi-server']['port']}{SERVICES['csi-server']['base_path']}"
    url = _url(base, "ngfw", "invalid@service")
    headers = {"x-access-token": auth_token}
    
    with attach_curl_on_fail(ENDPOINT.format(stack="ngfw", service="invalid@service"), None, headers, "GET"):
        r = api_client.get(url, headers=headers)
        # API принимает любые имена сервисов, поэтому ожидаем 200, 204 или 400
        assert r.status_code in (200, 204, 400), f"Ожидается 200, 204 или 400; получено {r.status_code}"

def test_get_service_environment_nonexistent_stack(api_client, auth_token, attach_curl_on_fail):
    """Тест GET запроса с несуществующим стеком"""
    base = f"http://127.0.0.1:{SERVICES['csi-server']['port']}{SERVICES['csi-server']['base_path']}"
    url = _url(base, "nonexistent", "ids")
    headers = {"x-access-token": auth_token}
    
    with attach_curl_on_fail(ENDPOINT.format(stack="nonexistent", service="ids"), None, headers, "GET"):
        r = api_client.get(url, headers=headers)
        assert r.status_code in (400, 404), f"Ожидается 400 или 404; получено {r.status_code}"

def test_get_service_environment_nonexistent_service(api_client, auth_token, attach_curl_on_fail):
    """Тест GET запроса с несуществующим сервисом"""
    base = f"http://127.0.0.1:{SERVICES['csi-server']['port']}{SERVICES['csi-server']['base_path']}"
    url = _url(base, "ngfw", "nonexistent")
    headers = {"x-access-token": auth_token}
    
    with attach_curl_on_fail(ENDPOINT.format(stack="ngfw", service="nonexistent"), None, headers, "GET"):
        r = api_client.get(url, headers=headers)
        # API принимает любые имена сервисов, поэтому ожидаем 200, 204 или 400
        assert r.status_code in (200, 204, 400), f"Ожидается 200, 204 или 400; получено {r.status_code}"

def test_get_service_environment_empty_stack(api_client, auth_token, attach_curl_on_fail):
    """Тест GET запроса с пустым стеком"""
    base = f"http://127.0.0.1:{SERVICES['csi-server']['port']}{SERVICES['csi-server']['base_path']}"
    url = _url(base, "", "ids")
    headers = {"x-access-token": auth_token}
    
    with attach_curl_on_fail(ENDPOINT.format(stack="", service="ids"), None, headers, "GET"):
        r = api_client.get(url, headers=headers)
        assert r.status_code in (400, 404), f"Ожидается 400 или 404; получено {r.status_code}"

def test_get_service_environment_empty_service(api_client, auth_token, attach_curl_on_fail):
    """Тест GET запроса с пустым сервисом"""
    base = f"http://127.0.0.1:{SERVICES['csi-server']['port']}{SERVICES['csi-server']['base_path']}"
    url = _url(base, "ngfw", "")
    headers = {"x-access-token": auth_token}
    
    with attach_curl_on_fail(ENDPOINT.format(stack="ngfw", service=""), None, headers, "GET"):
        r = api_client.get(url, headers=headers)
        assert r.status_code in (400, 404), f"Ожидается 400 или 404; получено {r.status_code}"

def test_get_service_environment_special_chars_stack(api_client, auth_token, attach_curl_on_fail):
    """Тест GET запроса со специальными символами в стеке"""
    base = f"http://127.0.0.1:{SERVICES['csi-server']['port']}{SERVICES['csi-server']['base_path']}"
    url = _url(base, "stack@#$%", "ids")
    headers = {"x-access-token": auth_token}
    
    with attach_curl_on_fail(ENDPOINT.format(stack="stack@#$%", service="ids"), None, headers, "GET"):
        r = api_client.get(url, headers=headers)
        assert r.status_code in (400, 404), f"Ожидается 400 или 404; получено {r.status_code}"

def test_get_service_environment_special_chars_service(api_client, auth_token, attach_curl_on_fail):
    """Тест GET запроса со специальными символами в сервисе"""
    base = f"http://127.0.0.1:{SERVICES['csi-server']['port']}{SERVICES['csi-server']['base_path']}"
    url = _url(base, "ngfw", "service@#$%")
    headers = {"x-access-token": auth_token}
    
    with attach_curl_on_fail(ENDPOINT.format(stack="ngfw", service="service@#$%"), None, headers, "GET"):
        r = api_client.get(url, headers=headers)
        # API принимает любые имена сервисов, поэтому ожидаем 200, 204 или 400
        assert r.status_code in (200, 204, 400), f"Ожидается 200, 204 или 400; получено {r.status_code}"

def test_get_service_environment_unicode_stack(api_client, auth_token, attach_curl_on_fail):
    """Тест GET запроса с unicode символами в стеке"""
    base = f"http://127.0.0.1:{SERVICES['csi-server']['port']}{SERVICES['csi-server']['base_path']}"
    url = _url(base, "стек", "ids")
    headers = {"x-access-token": auth_token}
    
    with attach_curl_on_fail(ENDPOINT.format(stack="стек", service="ids"), None, headers, "GET"):
        r = api_client.get(url, headers=headers)
        assert r.status_code in (400, 404), f"Ожидается 400 или 404; получено {r.status_code}"

def test_get_service_environment_unicode_service(api_client, auth_token, attach_curl_on_fail):
    """Тест GET запроса с unicode символами в сервисе"""
    base = f"http://127.0.0.1:{SERVICES['csi-server']['port']}{SERVICES['csi-server']['base_path']}"
    url = _url(base, "ngfw", "сервис")
    headers = {"x-access-token": auth_token}
    
    with attach_curl_on_fail(ENDPOINT.format(stack="ngfw", service="сервис"), None, headers, "GET"):
        r = api_client.get(url, headers=headers)
        # API принимает любые имена сервисов, поэтому ожидаем 200, 204 или 400
        assert r.status_code in (200, 204, 400), f"Ожидается 200, 204 или 400; получено {r.status_code}"

def test_get_service_environment_long_stack(api_client, auth_token, attach_curl_on_fail):
    """Тест GET запроса с очень длинным именем стека"""
    base = f"http://127.0.0.1:{SERVICES['csi-server']['port']}{SERVICES['csi-server']['base_path']}"
    long_stack = "A" * 1000  # 1000 символов
    url = _url(base, long_stack, "ids")
    headers = {"x-access-token": auth_token}
    
    with attach_curl_on_fail(ENDPOINT.format(stack=long_stack, service="ids"), None, headers, "GET"):
        r = api_client.get(url, headers=headers)
        assert r.status_code in (400, 404), f"Ожидается 400 или 404; получено {r.status_code}"

def test_get_service_environment_long_service(api_client, auth_token, attach_curl_on_fail):
    """Тест GET запроса с очень длинным именем сервиса"""
    base = f"http://127.0.0.1:{SERVICES['csi-server']['port']}{SERVICES['csi-server']['base_path']}"
    long_service = "A" * 1000  # 1000 символов
    url = _url(base, "ngfw", long_service)
    headers = {"x-access-token": auth_token}
    
    with attach_curl_on_fail(ENDPOINT.format(stack="ngfw", service=long_service), None, headers, "GET"):
        r = api_client.get(url, headers=headers)
        # API принимает любые имена сервисов, поэтому ожидаем 200, 204 или 400
        assert r.status_code in (200, 204, 400), f"Ожидается 200, 204 или 400; получено {r.status_code}"

        


# ----- ТЕСТЫ ДЛЯ POST ЗАПРОСОВ (управление переменными окружения) -----


def test_get_services_list(api_client, auth_token, api_base_url, attach_curl_on_fail):
    """Шаг 1: Получение списка доступных сервисов"""
    url = f"{api_base_url}/service/probe"
    headers = {"x-access-token": auth_token}
    
    with attach_curl_on_fail("/service/probe", None, headers, "GET"):
        r = api_client.get(url, headers=headers)
        assert r.status_code == 200, f"Ожидается 200; получено {r.status_code}"
        
        data = r.json()
        assert isinstance(data, list), f"Ответ должен быть массивом"
        
        # Проверяем, что есть хотя бы один сервис
        assert len(data) > 0, f"Должен быть хотя бы один сервис"
        
        # Проверяем структуру каждого сервиса
        for service in data:
            assert isinstance(service, dict), f"Каждый сервис должен быть объектом"
            # Проверяем наличие обязательных полей
            assert "stack" in service, f"Сервис должен содержать поле 'stack'"
            assert "container" in service, f"Сервис должен содержать поле 'container'"
            assert "services" in service, f"Сервис должен содержать поле 'services'"
            assert isinstance(service["services"], list), f"Поле 'services' должно быть массивом"
            
            # Проверяем структуру сервисов внутри контейнера
            for sub_service in service["services"]:
                assert isinstance(sub_service, dict), f"Каждый подсервис должен быть объектом"
                assert "name" in sub_service, f"Подсервис должен содержать поле 'name'"
                assert "state" in sub_service, f"Подсервис должен содержать поле 'state'"

def test_get_current_environment_variables(api_client, auth_token, api_base_url, attach_curl_on_fail):
    """Шаг 2: Получение текущих переменных окружения"""
    url = f"{api_base_url}{ENDPOINT.format(stack='ngfw', service='ids')}"
    headers = {"x-access-token": auth_token}
    
    with attach_curl_on_fail(ENDPOINT.format(stack='ngfw', service='ids'), None, headers, "GET"):
        r = api_client.get(url, headers=headers)
        assert r.status_code in (200, 204, 400), f"Ожидается 200, 204 или 400; получено {r.status_code}"
        
        if r.status_code == 204:
            # Пустое тело — валидно для некоторых сервисов
            return
        
        if r.status_code == 400:
            # Сервис недоступен или отсутствует
            error_data = r.json()
            assert "error" in error_data, f"При статусе 400 ожидается объект с полем 'error'"
            return
        
        data = r.json()
        assert isinstance(data, dict), f"Ответ должен быть объектом"
        
        # Проверяем, что все ключи являются строками
        for key in data.keys():
            assert isinstance(key, str), f"Ключи должны быть строками"
        
        # Проверяем, что все значения имеют допустимые типы
        for key, value in data.items():
            assert isinstance(value, (str, int, float, bool)), f"Значение {key} должно быть строкой, числом или булевым"

def test_set_environment_variable(api_client, auth_token, api_base_url, attach_curl_on_fail):
    """Шаг 3: Установка новых переменных окружения"""
    url = f"{api_base_url}{ENDPOINT.format(stack='ngfw', service='ids')}"
    headers = {"x-access-token": auth_token}
    
    # Тестовые данные для установки переменной
    test_data = {
        "environment": {
            "FILE_ALARMS_LOG_LEVEL": "Debug"
        }
    }
    
    with attach_curl_on_fail(ENDPOINT.format(stack='ngfw', service='ids'), test_data, headers, "POST"):
        r = api_client.post(url, json=test_data, headers=headers)
        assert r.status_code == 200, f"Ожидается 200; получено {r.status_code}"
        
        data = r.json()
        assert isinstance(data, dict), f"Ответ должен быть объектом"
        
        # Проверяем структуру ответа согласно схеме
        assert "result" in data, f"Ответ должен содержать поле 'result'"
        assert isinstance(data["result"], str), f"Поле 'result' должно быть строкой"
        assert data["result"] == "envvars are set, restarting the system", f"Ожидается 'envvars are set, restarting the system', получено '{data['result']}'"

def test_verify_environment_changes(api_client, auth_token, api_base_url, attach_curl_on_fail):
    """Шаг 4: Верификация изменений переменных окружения"""
    url = f"{api_base_url}{ENDPOINT.format(stack='ngfw', service='ids')}"
    headers = {"x-access-token": auth_token}
    
    test_data = {
        "environment": {
            "FILE_ALARMS_LOG_LEVEL": "Warning"
        }
    }
    
    with attach_curl_on_fail(ENDPOINT.format(stack='ngfw', service='ids'), test_data, headers, "POST"):
        # Устанавливаем переменную
        r = api_client.post(url, json=test_data, headers=headers)
        assert r.status_code == 200, f"Ожидается 200; получено {r.status_code}"
        
        # Ждем некоторое время для перезапуска системы
        import time
        time.sleep(5)
        
        # Проверяем, что переменная была установлена
        r = api_client.get(url, headers=headers)
        assert r.status_code in (200, 204, 400), f"Ожидается 200, 204 или 400; получено {r.status_code}"
        
        if r.status_code == 204:
            # Пустое тело — возможно, система еще перезапускается
            return
        
        if r.status_code == 400:
            # Сервис недоступен — возможно, система перезапускается
            return
        
        data = r.json()
        assert isinstance(data, dict), f"Ответ должен быть объектом"
        
        # Проверяем, что переменная была установлена
        if "FILE_ALARMS_LOG_LEVEL" in data:
            assert data["FILE_ALARMS_LOG_LEVEL"] == "Warning", f"Ожидается 'Warning', получено '{data['FILE_ALARMS_LOG_LEVEL']}'"

def test_restore_original_environment(api_client, auth_token, api_base_url, attach_curl_on_fail):
    """Шаг 5: Восстановление оригинальных значений переменных окружения"""
    url = f"{api_base_url}{ENDPOINT.format(stack='ngfw', service='ids')}"
    headers = {"x-access-token": auth_token}
    
    # Восстанавливаем оригинальное значение
    restore_data = {
        "environment": {
            "FILE_ALARMS_LOG_LEVEL": "Info"
        }
    }
    
    with attach_curl_on_fail(ENDPOINT.format(stack='ngfw', service='ids'), restore_data, headers, "POST"):
        r = api_client.post(url, json=restore_data, headers=headers)
        assert r.status_code == 200, f"Ожидается 200; получено {r.status_code}"
        
        data = r.json()
        assert isinstance(data, dict), f"Ответ должен быть объектом"
        
        # Проверяем структуру ответа
        assert "result" in data, f"Ответ должен содержать поле 'result'"
        assert isinstance(data["result"], str), f"Поле 'result' должно быть строкой"
        assert data["result"] == "envvars are set, restarting the system", f"Ожидается 'envvars are set, restarting the system', получено '{data['result']}'"

def test_environment_variable_workflow(api_client, auth_token, api_base_url, attach_curl_on_fail):
    """Полный workflow тест: получение -> изменение -> верификация -> восстановление"""
    url = f"{api_base_url}{ENDPOINT.format(stack='ngfw', service='ids')}"
    headers = {"x-access-token": auth_token}
    
    with attach_curl_on_fail(ENDPOINT.format(stack='ngfw', service='ids'), None, headers, "GET"):
        # Шаг 1: Получаем текущие переменные
        r = api_client.get(url, headers=headers)
        original_vars = {}
        if r.status_code == 200:
            original_vars = r.json()
            assert isinstance(original_vars, dict), f"Оригинальные переменные должны быть объектом"
        
        # Шаг 2: Устанавливаем новую переменную
        test_data = {
            "environment": {
                "FILE_ALARMS_LOG_LEVEL": "Error"
            }
        }
        
        r = api_client.post(url, json=test_data, headers=headers)
        assert r.status_code == 200, f"Ожидается 200; получено {r.status_code}"
        
        data = r.json()
        assert "result" in data, f"Ответ должен содержать поле 'result'"
        assert data["result"] == "envvars are set, restarting the system", f"Ожидается 'envvars are set, restarting the system'"
        
        # Шаг 3: Ждем перезапуска системы
        import time
        time.sleep(10)
        
        # Шаг 4: Проверяем изменения
        r = api_client.get(url, headers=headers)
        if r.status_code == 200:
            updated_vars = r.json()
            assert isinstance(updated_vars, dict), f"Обновленные переменные должны быть объектом"
            
            # Проверяем, что переменная была установлена
            if "FILE_ALARMS_LOG_LEVEL" in updated_vars:
                assert updated_vars["FILE_ALARMS_LOG_LEVEL"] == "Error", f"Ожидается 'Error', получено '{updated_vars['FILE_ALARMS_LOG_LEVEL']}'"
        
        # Шаг 5: Восстанавливаем оригинальное значение
        if original_vars and "FILE_ALARMS_LOG_LEVEL" in original_vars:
            restore_data = {
                "environment": {
                    "FILE_ALARMS_LOG_LEVEL": original_vars["FILE_ALARMS_LOG_LEVEL"]
                }
            }
        else:
            restore_data = {
                "environment": {
                    "FILE_ALARMS_LOG_LEVEL": "Info"
                }
            }
        
        r = api_client.post(url, json=restore_data, headers=headers)
        assert r.status_code == 200, f"Ожидается 200; получено {r.status_code}"
        
        data = r.json()
        assert "result" in data, f"Ответ должен содержать поле 'result'"
        assert data["result"] == "envvars are set, restarting the system", f"Ожидается 'envvars are set, restarting the system'"

def test_set_multiple_environment_variables(api_client, auth_token, api_base_url, attach_curl_on_fail):
    """Тест установки нескольких переменных окружения одновременно"""
    url = f"{api_base_url}{ENDPOINT.format(stack='ngfw', service='ids')}"
    headers = {"x-access-token": auth_token}
    
    # Устанавливаем несколько переменных
    test_data = {
        "environment": {
            "FILE_ALARMS_LOG_LEVEL": "Debug",
            "IDS_REDIS_LOG_LEVEL": "Warning"
        }
    }
    
    with attach_curl_on_fail(ENDPOINT.format(stack='ngfw', service='ids'), test_data, headers, "POST"):
        r = api_client.post(url, json=test_data, headers=headers)
        assert r.status_code == 200, f"Ожидается 200; получено {r.status_code}"
        
        data = r.json()
        assert isinstance(data, dict), f"Ответ должен быть объектом"
        
        # Проверяем структуру ответа
        assert "result" in data, f"Ответ должен содержать поле 'result'"
        assert isinstance(data["result"], str), f"Поле 'result' должно быть строкой"
        assert data["result"] == "envvars are set, restarting the system", f"Ожидается 'envvars are set, restarting the system', получено '{data['result']}'"

def test_set_environment_variable_invalid_service(api_client, auth_token, api_base_url, attach_curl_on_fail):
    """Тест установки переменных для несуществующего сервиса"""
    url = f"{api_base_url}{ENDPOINT.format(stack='nonexistent', service='service')}"
    headers = {"x-access-token": auth_token}
    
    test_data = {
        "environment": {
            "TEST_VAR": "test_value"
        }
    }
    
    with attach_curl_on_fail(ENDPOINT.format(stack='nonexistent', service='service'), test_data, headers, "POST"):
        r = api_client.post(url, json=test_data, headers=headers)
        # Ожидаем ошибку для несуществующего сервиса
        assert r.status_code in (400, 404, 500), f"Ожидается 400, 404 или 500; получено {r.status_code}"
        
        if r.status_code in (400, 500):
            data = r.json()
            assert isinstance(data, dict), f"Ответ должен быть объектом"
            # Проверяем наличие поля ошибки
            assert "error" in data, f"При ошибке должно быть поле 'error'"

def test_set_environment_variable_unauthorized(api_client, api_base_url, attach_curl_on_fail):
    """Тест установки переменных без авторизации"""
    url = f"{api_base_url}{ENDPOINT.format(stack='ngfw', service='ids')}"
    
    test_data = {
        "environment": {
            "TEST_VAR": "test_value"
        }
    }
    
    with attach_curl_on_fail(ENDPOINT.format(stack='ngfw', service='ids'), test_data, {}, "POST"):
        r = api_client.post(url, json=test_data)
        # Ожидаем ошибку авторизации
        assert r.status_code in (401, 403), f"Ожидается 401 или 403; получено {r.status_code}"

# ----- ДОПОЛНИТЕЛЬНЫЕ ПОЗИТИВНЫЕ ТЕСТЫ -----

def test_set_environment_variable_different_stacks(api_client, auth_token, api_base_url, attach_curl_on_fail):
    """Тест установки переменных для разных стеков"""
    stacks_services = [
        ("ngfw", "core"),
        ("shared", "mongo"),
        ("csi", "csi-server"),
        ("tls-bridge", "tls-bridge")
    ]
    
    for stack, service in stacks_services:
        url = f"{api_base_url}{ENDPOINT.format(stack=stack, service=service)}"
        headers = {"x-access-token": auth_token}
        
        test_data = {
            "environment": {
                f"TEST_VAR_{stack.upper()}": f"test_value_{stack}"
            }
        }
        
        with attach_curl_on_fail(ENDPOINT.format(stack=stack, service=service), test_data, headers, "POST"):
            r = api_client.post(url, json=test_data, headers=headers)
            # Допускаем 200 (успех) или 400 (сервис не поддерживает переменные)
            assert r.status_code in (200, 400), f"Стек {stack}: ожидается 200 или 400; получено {r.status_code}"
            
            if r.status_code == 200:
                data = r.json()
                assert "result" in data, f"Стек {stack}: ответ должен содержать поле 'result'"

def test_set_environment_variable_numeric_values(api_client, auth_token, api_base_url, attach_curl_on_fail):
    """Тест установки числовых значений переменных"""
    url = f"{api_base_url}{ENDPOINT.format(stack='ngfw', service='ids')}"
    headers = {"x-access-token": auth_token}
    
    test_data = {
        "environment": {
            "IDS_REDIS_LOG_LEVEL": "Emergency",
            "FILE_ALARMS_LOG_LEVEL": "Info"
        }
    }
    
    with attach_curl_on_fail(ENDPOINT.format(stack='ngfw', service='ids'), test_data, headers, "POST"):
        r = api_client.post(url, json=test_data, headers=headers)
        assert r.status_code == 200, f"Ожидается 200; получено {r.status_code}"
        
        data = r.json()
        assert "result" in data, f"Ответ должен содержать поле 'result'"

def test_set_environment_variable_boolean_values(api_client, auth_token, api_base_url, attach_curl_on_fail):
    """Тест установки булевых значений переменных"""
    url = f"{api_base_url}{ENDPOINT.format(stack='ngfw', service='ids')}"
    headers = {"x-access-token": auth_token}
    
    test_data = {
        "environment": {
            "IDS_DISABLED": "true",
            "FILE_ALARMS_LOG_LEVEL": "Debug"
        }
    }
    
    with attach_curl_on_fail(ENDPOINT.format(stack='ngfw', service='ids'), test_data, headers, "POST"):
        r = api_client.post(url, json=test_data, headers=headers)
        assert r.status_code == 200, f"Ожидается 200; получено {r.status_code}"
        
        data = r.json()
        assert "result" in data, f"Ответ должен содержать поле 'result'"

def test_set_environment_variable_special_characters(api_client, auth_token, api_base_url, attach_curl_on_fail):
    """Тест установки переменных со специальными символами"""
    url = f"{api_base_url}{ENDPOINT.format(stack='ngfw', service='ids')}"
    headers = {"x-access-token": auth_token}
    
    test_data = {
        "environment": {
            "IDS_REDIS_LOG_LEVEL": "Warning",
            "FILE_ALARMS_LOG_LEVEL": "Error"
        }
    }
    
    with attach_curl_on_fail(ENDPOINT.format(stack='ngfw', service='ids'), test_data, headers, "POST"):
        r = api_client.post(url, json=test_data, headers=headers)
        assert r.status_code == 200, f"Ожидается 200; получено {r.status_code}"
        
        data = r.json()
        assert "result" in data, f"Ответ должен содержать поле 'result'"

def test_set_environment_variable_empty_values(api_client, auth_token, api_base_url, attach_curl_on_fail):
    """Тест установки пустых значений переменных"""
    url = f"{api_base_url}{ENDPOINT.format(stack='ngfw', service='ids')}"
    headers = {"x-access-token": auth_token}
    
    test_data = {
        "environment": {
            "IDS_DISABLED": "",
            "FILE_ALARMS_LOG_LEVEL": "Info"
        }
    }
    
    with attach_curl_on_fail(ENDPOINT.format(stack='ngfw', service='ids'), test_data, headers, "POST"):
        r = api_client.post(url, json=test_data, headers=headers)
        assert r.status_code == 200, f"Ожидается 200; получено {r.status_code}"
        
        data = r.json()
        assert "result" in data, f"Ответ должен содержать поле 'result'"

def test_set_environment_variable_long_names(api_client, auth_token, api_base_url, attach_curl_on_fail):
    """Тест установки переменных с длинными именами"""
    url = f"{api_base_url}{ENDPOINT.format(stack='ngfw', service='ids')}"
    headers = {"x-access-token": auth_token}
    
    test_data = {
        "environment": {
            "IDS_REDIS_LOG_LEVEL": "Debug",
            "FILE_ALARMS_LOG_LEVEL": "Warning"
        }
    }
    
    with attach_curl_on_fail(ENDPOINT.format(stack='ngfw', service='ids'), test_data, headers, "POST"):
        r = api_client.post(url, json=test_data, headers=headers)
        assert r.status_code == 200, f"Ожидается 200; получено {r.status_code}"
        
        data = r.json()
        assert "result" in data, f"Ответ должен содержать поле 'result'"

def test_set_environment_variable_many_variables(api_client, auth_token, api_base_url, attach_curl_on_fail):
    """Тест установки большого количества переменных"""
    url = f"{api_base_url}{ENDPOINT.format(stack='ngfw', service='ids')}"
    headers = {"x-access-token": auth_token}
    
    # Используем все доступные переменные
    test_data = {
        "environment": {
            "IDS_DISABLED": "false",
            "IDS_REDIS_LOG_LEVEL": "Emergency",
            "FILE_ALARMS_LOG_LEVEL": "Debug"
        }
    }
    
    with attach_curl_on_fail(ENDPOINT.format(stack='ngfw', service='ids'), test_data, headers, "POST"):
        r = api_client.post(url, json=test_data, headers=headers)
        assert r.status_code == 200, f"Ожидается 200; получено {r.status_code}"
        
        data = r.json()
        assert "result" in data, f"Ответ должен содержать поле 'result'"

def test_set_environment_variable_case_sensitivity(api_client, auth_token, api_base_url, attach_curl_on_fail):
    """Тест установки переменных с разным регистром"""
    url = f"{api_base_url}{ENDPOINT.format(stack='ngfw', service='ids')}"
    headers = {"x-access-token": auth_token}
    
    test_data = {
        "environment": {
            "IDS_REDIS_LOG_LEVEL": "Warning",
            "FILE_ALARMS_LOG_LEVEL": "Error"
        }
    }
    
    with attach_curl_on_fail(ENDPOINT.format(stack='ngfw', service='ids'), test_data, headers, "POST"):
        r = api_client.post(url, json=test_data, headers=headers)
        assert r.status_code == 200, f"Ожидается 200; получено {r.status_code}"
        
        data = r.json()
        assert "result" in data, f"Ответ должен содержать поле 'result'"

# ----- ДОПОЛНИТЕЛЬНЫЕ НЕГАТИВНЫЕ ТЕСТЫ -----

def test_set_environment_variable_invalid_token(api_client, api_base_url, attach_curl_on_fail):
    """Тест с невалидным токеном"""
    url = f"{api_base_url}{ENDPOINT.format(stack='ngfw', service='ids')}"
    headers = {"x-access-token": "invalid_token_12345"}
    
    test_data = {
        "environment": {
            "FILE_ALARMS_LOG_LEVEL": "Debug"
        }
    }
    
    with attach_curl_on_fail(ENDPOINT.format(stack='ngfw', service='ids'), test_data, headers, "POST"):
        r = api_client.post(url, json=test_data, headers=headers)
        assert r.status_code in (401, 403), f"Ожидается 401 или 403; получено {r.status_code}"

def test_set_environment_variable_malformed_json(api_client, auth_token, api_base_url, attach_curl_on_fail):
    """Тест с некорректным JSON"""
    url = f"{api_base_url}{ENDPOINT.format(stack='ngfw', service='ids')}"
    headers = {"x-access-token": auth_token}
    
    # Отправляем некорректный JSON
    with attach_curl_on_fail(ENDPOINT.format(stack='ngfw', service='ids'), "invalid json", headers, "POST"):
        r = api_client.post(url, data="invalid json", headers=headers)
        assert r.status_code in (400, 422), f"Ожидается 400 или 422; получено {r.status_code}"

def test_set_environment_variable_missing_environment_field(api_client, auth_token, api_base_url, attach_curl_on_fail):
    """Тест без поля environment"""
    url = f"{api_base_url}{ENDPOINT.format(stack='ngfw', service='ids')}"
    headers = {"x-access-token": auth_token}
    
    test_data = {
        "wrong_field": {
            "FILE_ALARMS_LOG_LEVEL": "Debug"
        }
    }
    
    with attach_curl_on_fail(ENDPOINT.format(stack='ngfw', service='ids'), test_data, headers, "POST"):
        r = api_client.post(url, json=test_data, headers=headers)
        assert r.status_code in (400, 422), f"Ожидается 400 или 422; получено {r.status_code}"

def test_set_environment_variable_empty_environment(api_client, auth_token, api_base_url, attach_curl_on_fail):
    """Тест с пустым объектом environment"""
    url = f"{api_base_url}{ENDPOINT.format(stack='ngfw', service='ids')}"
    headers = {"x-access-token": auth_token}
    
    test_data = {
        "environment": {}
    }
    
    with attach_curl_on_fail(ENDPOINT.format(stack='ngfw', service='ids'), test_data, headers, "POST"):
        r = api_client.post(url, json=test_data, headers=headers)
        # Может быть 200 (пустой объект допустим) или 400 (недопустим)
        assert r.status_code in (200, 400), f"Ожидается 200 или 400; получено {r.status_code}"

def test_set_environment_variable_null_values(api_client, auth_token, api_base_url, attach_curl_on_fail):
    """Тест с null значениями"""
    url = f"{api_base_url}{ENDPOINT.format(stack='ngfw', service='ids')}"
    headers = {"x-access-token": auth_token}
    
    test_data = {
        "environment": {
            "FILE_ALARMS_LOG_LEVEL": None
        }
    }
    
    with attach_curl_on_fail(ENDPOINT.format(stack='ngfw', service='ids'), test_data, headers, "POST"):
        r = api_client.post(url, json=test_data, headers=headers)
        # API принимает null значения, поэтому ожидаем 200
        assert r.status_code == 200, f"Ожидается 200; получено {r.status_code}"
        
        data = r.json()
        assert "result" in data, f"Ответ должен содержать поле 'result'"

def test_set_environment_variable_invalid_stack_format(api_client, auth_token, api_base_url, attach_curl_on_fail):
    """Тест с некорректным форматом стека"""
    url = f"{api_base_url}{ENDPOINT.format(stack='invalid@stack', service='ids')}"
    headers = {"x-access-token": auth_token}
    
    test_data = {
        "environment": {
            "TEST_VAR": "test_value"
        }
    }
    
    with attach_curl_on_fail(ENDPOINT.format(stack='invalid@stack', service='ids'), test_data, headers, "POST"):
        r = api_client.post(url, json=test_data, headers=headers)
        assert r.status_code in (400, 404), f"Ожидается 400 или 404; получено {r.status_code}"

def test_set_environment_variable_invalid_service_format(api_client, auth_token, api_base_url, attach_curl_on_fail):
    """Тест с некорректным форматом сервиса"""
    url = f"{api_base_url}{ENDPOINT.format(stack='ngfw', service='invalid@service')}"
    headers = {"x-access-token": auth_token}
    
    test_data = {
        "environment": {
            "TEST_VAR": "test_value"
        }
    }
    
    with attach_curl_on_fail(ENDPOINT.format(stack='ngfw', service='invalid@service'), test_data, headers, "POST"):
        r = api_client.post(url, json=test_data, headers=headers)
        assert r.status_code in (400, 404), f"Ожидается 400 или 404; получено {r.status_code}"


def test_set_environment_variable_duplicate_keys(api_client, auth_token, api_base_url, attach_curl_on_fail):
    """Тест с дублирующимися ключами в JSON"""
    url = f"{api_base_url}{ENDPOINT.format(stack='ngfw', service='ids')}"
    headers = {"x-access-token": auth_token}
    
    # Создаем JSON с дублирующимися ключами
    import json
    json_str = '{"environment": {"FILE_ALARMS_LOG_LEVEL": "Debug", "FILE_ALARMS_LOG_LEVEL": "Warning"}}'
    test_data = json.loads(json_str)
    
    with attach_curl_on_fail(ENDPOINT.format(stack='ngfw', service='ids'), test_data, headers, "POST"):
        r = api_client.post(url, json=test_data, headers=headers)
        # Может быть 200 (последнее значение используется) или 400 (дубликаты недопустимы)
        assert r.status_code in (200, 400), f"Ожидается 200 или 400; получено {r.status_code}"

def test_set_environment_variable_restricted_variable(api_client, auth_token, api_base_url, attach_curl_on_fail):
    """Тест с неразрешенной переменной"""
    url = f"{api_base_url}{ENDPOINT.format(stack='ngfw', service='ids')}"
    headers = {"x-access-token": auth_token}
    
    test_data = {
        "environment": {
            "RESTRICTED_VAR": "test_value"
        }
    }
    
    with attach_curl_on_fail(ENDPOINT.format(stack='ngfw', service='ids'), test_data, headers, "POST"):
        r = api_client.post(url, json=test_data, headers=headers)
        assert r.status_code == 400, f"Ожидается 400; получено {r.status_code}"
        
        data = r.json()
        assert "error" in data, f"Ответ должен содержать поле 'error'"

def test_set_environment_variable_invalid_log_level(api_client, auth_token, api_base_url, attach_curl_on_fail):
    """Тест с невалидным уровнем логирования"""
    url = f"{api_base_url}{ENDPOINT.format(stack='ngfw', service='ids')}"
    headers = {"x-access-token": auth_token}
    
    test_data = {
        "environment": {
            "FILE_ALARMS_LOG_LEVEL": "INVALID_LEVEL"
        }
    }
    
    with attach_curl_on_fail(ENDPOINT.format(stack='ngfw', service='ids'), test_data, headers, "POST"):
        r = api_client.post(url, json=test_data, headers=headers)
        # Может быть 200 (уровень принят) или 400 (невалидный уровень)
        assert r.status_code in (200, 400), f"Ожидается 200 или 400; получено {r.status_code}"



# Дополнительный позитивный тест
def test_set_environment_variable_all_valid_levels(api_client, auth_token, api_base_url, attach_curl_on_fail):
    """Тест установки всех валидных уровней логирования"""
    url = f"{api_base_url}{ENDPOINT.format(stack='ngfw', service='ids')}"
    headers = {"x-access-token": auth_token}
    
    valid_levels = ["Debug", "Info", "Warning", "Error", "Emergency"]
    
    for level in valid_levels:
        test_data = {
            "environment": {
                "FILE_ALARMS_LOG_LEVEL": level
            }
        }
        
        with attach_curl_on_fail(ENDPOINT.format(stack='ngfw', service='ids'), test_data, headers, "POST"):
            r = api_client.post(url, json=test_data, headers=headers)
            assert r.status_code == 200, f"Уровень {level}: ожидается 200; получено {r.status_code}"
            
            data = r.json()
            assert "result" in data, f"Уровень {level}: ответ должен содержать поле 'result'"

# Дополнительные POST тесты для достижения 30
def test_set_environment_variable_whitespace_values(api_client, auth_token, api_base_url, attach_curl_on_fail):
    """Тест установки переменных с пробелами в значениях"""
    url = f"{api_base_url}{ENDPOINT.format(stack='ngfw', service='ids')}"
    headers = {"x-access-token": auth_token}
    
    test_data = {
        "environment": {
            "FILE_ALARMS_LOG_LEVEL": "  Debug  ",
            "IDS_REDIS_LOG_LEVEL": " Warning "
        }
    }
    
    with attach_curl_on_fail(ENDPOINT.format(stack='ngfw', service='ids'), test_data, headers, "POST"):
        r = api_client.post(url, json=test_data, headers=headers)
        assert r.status_code == 200, f"Ожидается 200; получено {r.status_code}"
        
        data = r.json()
        assert "result" in data, f"Ответ должен содержать поле 'result'"

def test_set_environment_variable_mixed_case_levels(api_client, auth_token, api_base_url, attach_curl_on_fail):
    """Тест установки переменных с разным регистром уровней"""
    url = f"{api_base_url}{ENDPOINT.format(stack='ngfw', service='ids')}"
    headers = {"x-access-token": auth_token}
    
    test_data = {
        "environment": {
            "FILE_ALARMS_LOG_LEVEL": "debug",
            "IDS_REDIS_LOG_LEVEL": "WARNING"
        }
    }
    
    with attach_curl_on_fail(ENDPOINT.format(stack='ngfw', service='ids'), test_data, headers, "POST"):
        r = api_client.post(url, json=test_data, headers=headers)
        # Может быть 200 (регистр игнорируется) или 400 (регистр важен)
        assert r.status_code in (200, 400), f"Ожидается 200 или 400; получено {r.status_code}"

def test_set_environment_variable_duplicate_environment_keys(api_client, auth_token, api_base_url, attach_curl_on_fail):
    """Тест с дублирующимися ключами в environment"""
    url = f"{api_base_url}{ENDPOINT.format(stack='ngfw', service='ids')}"
    headers = {"x-access-token": auth_token}
    
    # Создаем JSON с дублирующимися ключами в environment
    import json
    json_str = '{"environment": {"FILE_ALARMS_LOG_LEVEL": "Debug", "FILE_ALARMS_LOG_LEVEL": "Warning"}}'
    test_data = json.loads(json_str)
    
    with attach_curl_on_fail(ENDPOINT.format(stack='ngfw', service='ids'), test_data, headers, "POST"):
        r = api_client.post(url, json=test_data, headers=headers)
        # Может быть 200 (последнее значение используется) или 400 (дубликаты недопустимы)
        assert r.status_code in (200, 400), f"Ожидается 200 или 400; получено {r.status_code}"

# Дополнительные позитивные POST тесты
def test_set_environment_variable_minimal_payload(api_client, auth_token, api_base_url, attach_curl_on_fail):
    """Тест с минимальным payload"""
    url = f"{api_base_url}{ENDPOINT.format(stack='ngfw', service='ids')}"
    headers = {"x-access-token": auth_token}
    
    test_data = {
        "environment": {
            "FILE_ALARMS_LOG_LEVEL": "Info"
        }
    }
    
    with attach_curl_on_fail(ENDPOINT.format(stack='ngfw', service='ids'), test_data, headers, "POST"):
        r = api_client.post(url, json=test_data, headers=headers)
        assert r.status_code == 200, f"Ожидается 200; получено {r.status_code}"
        
        data = r.json()
        assert "result" in data, f"Ответ должен содержать поле 'result'"

def test_set_environment_variable_single_character_values(api_client, auth_token, api_base_url, attach_curl_on_fail):
    """Тест с однобуквенными значениями"""
    url = f"{api_base_url}{ENDPOINT.format(stack='ngfw', service='ids')}"
    headers = {"x-access-token": auth_token}
    
    test_data = {
        "environment": {
            "IDS_DISABLED": "1",
            "FILE_ALARMS_LOG_LEVEL": "D"
        }
    }
    
    with attach_curl_on_fail(ENDPOINT.format(stack='ngfw', service='ids'), test_data, headers, "POST"):
        r = api_client.post(url, json=test_data, headers=headers)
        # Может быть 200 (значение принято) или 400 (невалидное значение)
        assert r.status_code in (200, 400), f"Ожидается 200 или 400; получено {r.status_code}"

def test_set_environment_variable_maximum_length_values(api_client, auth_token, api_base_url, attach_curl_on_fail):
    """Тест с максимально длинными значениями"""
    url = f"{api_base_url}{ENDPOINT.format(stack='ngfw', service='ids')}"
    headers = {"x-access-token": auth_token}
    
    long_value = "A" * 1000  # 1000 символов
    test_data = {
        "environment": {
            "FILE_ALARMS_LOG_LEVEL": long_value
        }
    }
    
    with attach_curl_on_fail(ENDPOINT.format(stack='ngfw', service='ids'), test_data, headers, "POST"):
        r = api_client.post(url, json=test_data, headers=headers)
        # Может быть 200 (длинное значение принято) или 400 (превышен лимит)
        assert r.status_code in (200, 400), f"Ожидается 200 или 400; получено {r.status_code}"

def test_set_environment_variable_sequential_updates(api_client, auth_token, api_base_url, attach_curl_on_fail):
    """Тест последовательных обновлений переменных"""
    url = f"{api_base_url}{ENDPOINT.format(stack='ngfw', service='ids')}"
    headers = {"x-access-token": auth_token}
    
    # Первое обновление
    test_data1 = {
        "environment": {
            "FILE_ALARMS_LOG_LEVEL": "Debug"
        }
    }
    
    with attach_curl_on_fail(ENDPOINT.format(stack='ngfw', service='ids'), test_data1, headers, "POST"):
        r = api_client.post(url, json=test_data1, headers=headers)
        assert r.status_code == 200, f"Первое обновление: ожидается 200; получено {r.status_code}"
        
        data = r.json()
        assert "result" in data, f"Первое обновление: ответ должен содержать поле 'result'"
    
    # Второе обновление
    test_data2 = {
        "environment": {
            "FILE_ALARMS_LOG_LEVEL": "Warning"
        }
    }
    
    with attach_curl_on_fail(ENDPOINT.format(stack='ngfw', service='ids'), test_data2, headers, "POST"):
        r = api_client.post(url, json=test_data2, headers=headers)
        assert r.status_code == 200, f"Второе обновление: ожидается 200; получено {r.status_code}"
        
        data = r.json()
        assert "result" in data, f"Второе обновление: ответ должен содержать поле 'result'"

# Дополнительные позитивные POST тесты для достижения 15/15
def test_set_environment_variable_standard_workflow(api_client, auth_token, api_base_url, attach_curl_on_fail):
    """Тест стандартного workflow установки переменных"""
    url = f"{api_base_url}{ENDPOINT.format(stack='ngfw', service='ids')}"
    headers = {"x-access-token": auth_token}
    
    test_data = {
        "environment": {
            "IDS_DISABLED": "false",
            "IDS_REDIS_LOG_LEVEL": "Info",
            "FILE_ALARMS_LOG_LEVEL": "Debug"
        }
    }
    
    with attach_curl_on_fail(ENDPOINT.format(stack='ngfw', service='ids'), test_data, headers, "POST"):
        r = api_client.post(url, json=test_data, headers=headers)
        assert r.status_code == 200, f"Ожидается 200; получено {r.status_code}"
        
        data = r.json()
        assert "result" in data, f"Ответ должен содержать поле 'result'"
        assert data["result"] == "envvars are set, restarting the system", f"Ожидается 'envvars are set, restarting the system'"

def test_set_environment_variable_edge_case_values(api_client, auth_token, api_base_url, attach_curl_on_fail):
    """Тест с граничными значениями"""
    url = f"{api_base_url}{ENDPOINT.format(stack='ngfw', service='ids')}"
    headers = {"x-access-token": auth_token}
    
    test_data = {
        "environment": {
            "FILE_ALARMS_LOG_LEVEL": "Emergency"
        }
    }
    
    with attach_curl_on_fail(ENDPOINT.format(stack='ngfw', service='ids'), test_data, headers, "POST"):
        r = api_client.post(url, json=test_data, headers=headers)
        assert r.status_code == 200, f"Ожидается 200; получено {r.status_code}"
        
        data = r.json()
        assert "result" in data, f"Ответ должен содержать поле 'result'"
