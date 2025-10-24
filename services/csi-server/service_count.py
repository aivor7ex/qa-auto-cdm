# file: /services/csi-server/service_count.py
import json
import pytest
from qa_constants import SERVICES

ENDPOINT = "/service/count"

# ----- СХЕМА ОТВЕТА (получена из R0) -----
RESPONSE_SCHEMA = {
    "type": "number",
    "required": True
}

# ----- ФИКСТУРЫ (в проекте уже существуют) -----
# api_client(base_url), auth_token() — ИСПОЛЬЗОВАТЬ, НЕ МЕНЯТЬ.

def _url(base_path: str) -> str:
    return f"{base_path}{ENDPOINT}"

def _check_type(name, value, spec):
    t = spec.get("type")
    if t == "string":
        assert isinstance(value, str), f"{name}: ожидается string; curl: curl --location 'http://127.0.0.1:2999/api/service/count' --header 'x-access-token: 9wO53O0bTModkbS3Vhc50kOR2bXafRHg3IA2CBcIt84j'"
    elif t == "number":
        assert isinstance(value, (int, float)) and not isinstance(value, bool), f"{name}: ожидается number; curl: curl --location 'http://127.0.0.1:2999/api/service/count' --header 'x-access-token: 9wO53O0bTModkbS3Vhc50kOR2bXafRHg3IA2CBcIt84j'"
    elif t == "boolean":
        assert isinstance(value, bool), f"{name}: ожидается boolean; curl: curl --location 'http://127.0.0.1:2999/api/service/count' --header 'x-access-token: 9wO53O0bTModkbS3Vhc50kOR2bXafRHg3IA2CBcIt84j'"
    elif t == "object":
        assert isinstance(value, dict), f"{name}: ожидается object; curl: curl --location 'http://127.0.0.1:2999/api/service/count' --header 'x-access-token: 9wO53O0bTModkbS3Vhc50kOR2bXafRHg3IA2CBcIt84j'"
        _validate_object(value, spec.get("properties", {}), name)
    elif t == "list":
        assert isinstance(value, list), f"{name}: ожидается list; curl: curl --location 'http://127.0.0.1:2999/api/service/count' --header 'x-access-token: 9wO53O0bTModkbS3Vhc50kOR2bXafRHg3IA2CBcIt84j'"
        item_spec = spec.get("item_type")
        if item_spec:
            for i, v in enumerate(value):
                _check_type(f"{name}[{i}]", v, item_spec)
    else:
        assert False, f"{name}: неизвестный тип '{t}'; curl: curl --location 'http://127.0.0.1:2999/api/service/count' --header 'x-access-token: 9wO53O0bTModkbS3Vhc50kOR2bXafRHg3IA2CBcIt84j'"

def _validate_object(obj, properties: dict, prefix: str = "root"):
    for key, prop in properties.items():
        required = prop.get("required", False)
        if required:
            assert key in obj, f"{prefix}.{key}: обязательное поле; curl: curl --location 'http://127.0.0.1:2999/api/service/count' --header 'x-access-token: 9wO53O0bTModkbS3Vhc50kOR2bXafRHg3IA2CBcIt84j'"
        if key in obj:
            _check_type(f"{prefix}.{key}", obj[key], prop)

def _format_curl_command(api_client, endpoint, params=None, headers=None):
    """Формирует и возвращает cURL-строку для воспроизведения запроса."""
    base_url = getattr(api_client, "base_url", f"http://127.0.0.1:{SERVICES['csi-server']['port']}{SERVICES['csi-server']['base_path']}")
    full_url = f"{base_url}{endpoint}"
    if params:
        param_str = "&".join([f"{k}={v}" for k, v in params.items() if v is not None])
        if param_str:
            full_url += f"?{param_str}"
    headers = headers or getattr(api_client, 'headers', {})
    headers_str = " \\\n  ".join([f"-H '{k}: {v}'" for k, v in headers.items()])
    curl_command = f"curl -X GET '{full_url}'"
    if headers_str:
        curl_command += f" \\\n  {headers_str}"
    return curl_command

# ---------- ПАРАМЕТРИЗАЦИЯ ----------
# 20 кейсов для GET запросов с различными параметрами
BASE_PARAMS = [
    {"q": None, "desc": "базовый запрос без параметров"},
    {"q": {"limit": 1}, "desc": "ограничение вывода одним элементом"},
    {"q": {"limit": 5}, "desc": "ограничение вывода пятью элементами"},
    {"q": {"limit": 0}, "desc": "нулевое ограничение вывода"},
    {"q": {"limit": 100}, "desc": "большое ограничение вывода"},
    {"q": {"offset": 0}, "desc": "смещение 0"},
    {"q": {"offset": 1}, "desc": "смещение 5"},
    {"q": {"page": 1}, "desc": "первая страница"},
    {"q": {"page": 10}, "desc": "десятая страница"},
    {"q": {"sort": "name"}, "desc": "сортировка по имени"},
    {"q": {"sort": "asc"}, "desc": "сортировка по возрастанию"},
    {"q": {"filter": "csi"}, "desc": "фильтр по csi"},
    {"q": {"filter": "logger"}, "desc": "фильтр по ngfw"},
    {"q": {"q": "test"}, "desc": "поисковый запрос test"},
    {"q": {"q": ""}, "desc": "пустой поисковый запрос"},
    {"q": {"count": "true"}, "desc": "параметр count true"},
    {"q": {"verbose": "true"}, "desc": "подробный вывод"},
    {"q": {"format": "json"}, "desc": "формат json"},
    {"q": {"pretty": "true"}, "desc": "красивый вывод"},
]

@pytest.mark.parametrize("case", BASE_PARAMS, ids=lambda c: c["desc"])
def test_get_service_count_schema_conforms(api_client, auth_token, case):
    base = f"http://127.0.0.1:{SERVICES['csi-server']['port']}{SERVICES['csi-server']['base_path']}"
    url = _url(base)
    params = case.get("q") or {}
    headers = {"x-access-token": auth_token}
    
    r = api_client.get(url, headers=headers, params=params)
    assert r.status_code == 200, f"Ожидается 200 OK; получено {r.status_code}; curl: {_format_curl_command(api_client, ENDPOINT, params, headers)}"
    
    data = r.json()
    _check_type("root", data, RESPONSE_SCHEMA)

def test_get_service_count_empty_params(api_client, auth_token):
    """Тест без параметров"""
    base = f"http://127.0.0.1:{SERVICES['csi-server']['port']}{SERVICES['csi-server']['base_path']}"
    url = _url(base)
    headers = {"x-access-token": auth_token}
    
    r = api_client.get(url, headers=headers)
    assert r.status_code == 200, f"Ожидается 200 OK; получено {r.status_code}; curl: {_format_curl_command(api_client, ENDPOINT, None, headers)}"
    
    data = r.json()
    _check_type("root", data, RESPONSE_SCHEMA)

def test_get_service_count_with_limit(api_client, auth_token):
    """Тест с параметром limit"""
    base = f"http://127.0.0.1:{SERVICES['csi-server']['port']}{SERVICES['csi-server']['base_path']}"
    url = _url(base)
    params = {"limit": 3}
    headers = {"x-access-token": auth_token}
    
    r = api_client.get(url, headers=headers, params=params)
    assert r.status_code == 200, f"Ожидается 200 OK; получено {r.status_code}; curl: {_format_curl_command(api_client, ENDPOINT, params, headers)}"
    
    data = r.json()
    _check_type("root", data, RESPONSE_SCHEMA)

def test_get_service_count_with_offset(api_client, auth_token):
    """Тест с параметром offset"""
    base = f"http://127.0.0.1:{SERVICES['csi-server']['port']}{SERVICES['csi-server']['base_path']}"
    url = _url(base)
    params = {"offset": 2}
    headers = {"x-access-token": auth_token}
    
    r = api_client.get(url, headers=headers, params=params)
    assert r.status_code == 200, f"Ожидается 200 OK; получено {r.status_code}; curl: {_format_curl_command(api_client, ENDPOINT, params, headers)}"
    
    data = r.json()
    _check_type("root", data, RESPONSE_SCHEMA)

def test_get_service_count_with_page(api_client, auth_token):
    """Тест с параметром page"""
    base = f"http://127.0.0.1:{SERVICES['csi-server']['port']}{SERVICES['csi-server']['base_path']}"
    url = _url(base)
    params = {"page": 1}
    headers = {"x-access-token": auth_token}
    
    r = api_client.get(url, headers=headers, params=params)
    assert r.status_code == 200, f"Ожидается 200 OK; получено {r.status_code}; curl: {_format_curl_command(api_client, ENDPOINT, params, headers)}"
    
    data = r.json()
    _check_type("root", data, RESPONSE_SCHEMA)

def test_get_service_count_with_sort(api_client, auth_token):
    """Тест с параметром sort"""
    base = f"http://127.0.0.1:{SERVICES['csi-server']['port']}{SERVICES['csi-server']['base_path']}"
    url = _url(base)
    params = {"sort": "name"}
    headers = {"x-access-token": auth_token}
    
    r = api_client.get(url, headers=headers, params=params)
    assert r.status_code == 200, f"Ожидается 200 OK; получено {r.status_code}; curl: {_format_curl_command(api_client, ENDPOINT, params, headers)}"
    
    data = r.json()
    _check_type("root", data, RESPONSE_SCHEMA)

def test_get_service_count_with_filter(api_client, auth_token):
    """Тест с параметром filter"""
    base = f"http://127.0.0.1:{SERVICES['csi-server']['port']}{SERVICES['csi-server']['base_path']}"
    url = _url(base)
    params = {"filter": "csi"}
    headers = {"x-access-token": auth_token}
    
    r = api_client.get(url, headers=headers, params=params)
    assert r.status_code == 200, f"Ожидается 200 OK; получено {r.status_code}; curl: {_format_curl_command(api_client, ENDPOINT, params, headers)}"
    
    data = r.json()
    _check_type("root", data, RESPONSE_SCHEMA)

def test_get_service_count_with_search(api_client, auth_token):
    """Тест с параметром поиска q"""
    base = f"http://127.0.0.1:{SERVICES['csi-server']['port']}{SERVICES['csi-server']['base_path']}"
    url = _url(base)
    params = {"q": "analytics"}
    headers = {"x-access-token": auth_token}
    
    r = api_client.get(url, headers=headers, params=params)
    assert r.status_code == 200, f"Ожидается 200 OK; получено {r.status_code}; curl: {_format_curl_command(api_client, ENDPOINT, params, headers)}"
    
    data = r.json()
    _check_type("root", data, RESPONSE_SCHEMA)

def test_get_service_count_with_count_param(api_client, auth_token):
    """Тест с параметром count"""
    base = f"http://127.0.0.1:{SERVICES['csi-server']['port']}{SERVICES['csi-server']['base_path']}"
    url = _url(base)
    params = {"count": "true"}
    headers = {"x-access-token": auth_token}
    
    r = api_client.get(url, headers=headers, params=params)
    assert r.status_code == 200, f"Ожидается 200 OK; получено {r.status_code}; curl: {_format_curl_command(api_client, ENDPOINT, params, headers)}"
    
    data = r.json()
    _check_type("root", data, RESPONSE_SCHEMA)

def test_get_service_count_with_verbose(api_client, auth_token):
    """Тест с параметром verbose"""
    base = f"http://127.0.0.1:{SERVICES['csi-server']['port']}{SERVICES['csi-server']['base_path']}"
    url = _url(base)
    params = {"verbose": "true"}
    headers = {"x-access-token": auth_token}
    
    r = api_client.get(url, headers=headers, params=params)
    assert r.status_code == 200, f"Ожидается 200 OK; получено {r.status_code}; curl: {_format_curl_command(api_client, ENDPOINT, params, headers)}"
    
    data = r.json()
    _check_type("root", data, RESPONSE_SCHEMA)

def test_get_service_count_with_format(api_client, auth_token):
    """Тест с параметром format"""
    base = f"http://127.0.0.1:{SERVICES['csi-server']['port']}{SERVICES['csi-server']['base_path']}"
    url = _url(base)
    params = {"format": "json"}
    headers = {"x-access-token": auth_token}
    
    r = api_client.get(url, headers=headers, params=params)
    assert r.status_code == 200, f"Ожидается 200 OK; получено {r.status_code}; curl: {_format_curl_command(api_client, ENDPOINT, params, headers)}"
    
    data = r.json()
    _check_type("root", data, RESPONSE_SCHEMA)

def test_get_service_count_combined_params(api_client, auth_token):
    """Тест с комбинированными параметрами"""
    base = f"http://127.0.0.1:{SERVICES['csi-server']['port']}{SERVICES['csi-server']['base_path']}"
    url = _url(base)
    params = {"limit": 5, "offset": 1, "sort": "name"}
    headers = {"x-access-token": auth_token}
    
    r = api_client.get(url, headers=headers, params=params)
    assert r.status_code == 200, f"Ожидается 200 OK; получено {r.status_code}; curl: {_format_curl_command(api_client, ENDPOINT, params, headers)}"
    
    data = r.json()
    _check_type("root", data, RESPONSE_SCHEMA)

def test_get_service_count_large_limit(api_client, auth_token):
    """Тест с большим значением limit"""
    base = f"http://127.0.0.1:{SERVICES['csi-server']['port']}{SERVICES['csi-server']['base_path']}"
    url = _url(base)
    params = {"limit": 1000}
    headers = {"x-access-token": auth_token}
    
    r = api_client.get(url, headers=headers, params=params)
    assert r.status_code == 200, f"Ожидается 200 OK; получено {r.status_code}; curl: {_format_curl_command(api_client, ENDPOINT, params, headers)}"
    
    data = r.json()
    _check_type("root", data, RESPONSE_SCHEMA)

def test_get_service_count_negative_offset(api_client, auth_token):
    """Тест с отрицательным offset"""
    base = f"http://127.0.0.1:{SERVICES['csi-server']['port']}{SERVICES['csi-server']['base_path']}"
    url = _url(base)
    params = {"offset": -1}
    headers = {"x-access-token": auth_token}
    
    r = api_client.get(url, headers=headers, params=params)
    assert r.status_code == 200, f"Ожидается 200 OK; получено {r.status_code}; curl: {_format_curl_command(api_client, ENDPOINT, params, headers)}"
    
    data = r.json()
    _check_type("root", data, RESPONSE_SCHEMA)

def test_get_service_count_zero_page(api_client, auth_token):
    """Тест с нулевой страницей"""
    base = f"http://127.0.0.1:{SERVICES['csi-server']['port']}{SERVICES['csi-server']['base_path']}"
    url = _url(base)
    params = {"page": 0}
    headers = {"x-access-token": auth_token}
    
    r = api_client.get(url, headers=headers, params=params)
    assert r.status_code == 200, f"Ожидается 200 OK; получено {r.status_code}; curl: {_format_curl_command(api_client, ENDPOINT, params, headers)}"
    
    data = r.json()
    _check_type("root", data, RESPONSE_SCHEMA)

def test_get_service_count_empty_string_filter(api_client, auth_token):
    """Тест с пустой строкой в filter"""
    base = f"http://127.0.0.1:{SERVICES['csi-server']['port']}{SERVICES['csi-server']['base_path']}"
    url = _url(base)
    params = {"filter": ""}
    headers = {"x-access-token": auth_token}
    
    r = api_client.get(url, headers=headers, params=params)
    assert r.status_code == 200, f"Ожидается 200 OK; получено {r.status_code}; curl: {_format_curl_command(api_client, ENDPOINT, params, headers)}"
    
    data = r.json()
    _check_type("root", data, RESPONSE_SCHEMA)

def test_get_service_count_special_chars_filter(api_client, auth_token):
    """Тест с специальными символами в filter"""
    base = f"http://127.0.0.1:{SERVICES['csi-server']['port']}{SERVICES['csi-server']['base_path']}"
    url = _url(base)
    params = {"filter": "!@#$%^&*()"}
    headers = {"x-access-token": auth_token}
    
    r = api_client.get(url, headers=headers, params=params)
    assert r.status_code == 200, f"Ожидается 200 OK; получено {r.status_code}; curl: {_format_curl_command(api_client, ENDPOINT, params, headers)}"
    
    data = r.json()
    _check_type("root", data, RESPONSE_SCHEMA)

def test_get_service_count_unicode_filter(api_client, auth_token):
    """Тест с unicode символами в filter"""
    base = f"http://127.0.0.1:{SERVICES['csi-server']['port']}{SERVICES['csi-server']['base_path']}"
    url = _url(base)
    params = {"filter": "тест"}
    headers = {"x-access-token": auth_token}
    
    r = api_client.get(url, headers=headers, params=params)
    assert r.status_code == 200, f"Ожидается 200 OK; получено {r.status_code}; curl: {_format_curl_command(api_client, ENDPOINT, params, headers)}"
    
    data = r.json()
    _check_type("root", data, RESPONSE_SCHEMA)

def test_get_service_count_long_filter(api_client, auth_token):
    """Тест с длинной строкой в filter"""
    base = f"http://127.0.0.1:{SERVICES['csi-server']['port']}{SERVICES['csi-server']['base_path']}"
    url = _url(base)
    params = {"filter": "a" * 100}
    headers = {"x-access-token": auth_token}
    
    r = api_client.get(url, headers=headers, params=params)
    assert r.status_code == 200, f"Ожидается 200 OK; получено {r.status_code}; curl: {_format_curl_command(api_client, ENDPOINT, params, headers)}"
    
    data = r.json()
    _check_type("root", data, RESPONSE_SCHEMA)

def test_get_service_count_numeric_string_params(api_client, auth_token):
    """Тест с числовыми строками в параметрах"""
    base = f"http://127.0.0.1:{SERVICES['csi-server']['port']}{SERVICES['csi-server']['base_path']}"
    url = _url(base)
    params = {"limit": "10", "offset": "5", "page": "2"}
    headers = {"x-access-token": auth_token}
    
    r = api_client.get(url, headers=headers, params=params)
    assert r.status_code == 200, f"Ожидается 200 OK; получено {r.status_code}; curl: {_format_curl_command(api_client, ENDPOINT, params, headers)}"
    
    data = r.json()
    _check_type("root", data, RESPONSE_SCHEMA)

def test_get_service_count_boolean_string_params(api_client, auth_token):
    """Тест с булевыми строками в параметрах"""
    base = f"http://127.0.0.1:{SERVICES['csi-server']['port']}{SERVICES['csi-server']['base_path']}"
    url = _url(base)
    params = {"sort": "true", "filter": "false"}
    headers = {"x-access-token": auth_token}
    
    r = api_client.get(url, headers=headers, params=params)
    assert r.status_code == 200, f"Ожидается 200 OK; получено {r.status_code}; curl: {_format_curl_command(api_client, ENDPOINT, params, headers)}"
    
    data = r.json()
    _check_type("root", data, RESPONSE_SCHEMA)

def test_get_service_count_json_filter(api_client, auth_token):
    """Тест с JSON строкой в filter"""
    base = f"http://127.0.0.1:{SERVICES['csi-server']['port']}{SERVICES['csi-server']['base_path']}"
    url = _url(base)
    params = {"filter": '{"service": "csi"}'}
    headers = {"x-access-token": auth_token}
    
    r = api_client.get(url, headers=headers, params=params)
    assert r.status_code == 200, f"Ожидается 200 OK; получено {r.status_code}; curl: {_format_curl_command(api_client, ENDPOINT, params, headers)}"
    
    data = r.json()
    _check_type("root", data, RESPONSE_SCHEMA)

def test_get_service_count_array_filter(api_client, auth_token):
    """Тест с массивом в filter"""
    base = f"http://127.0.0.1:{SERVICES['csi-server']['port']}{SERVICES['csi-server']['base_path']}"
    url = _url(base)
    params = {"filter": "[1,2,3]"}
    headers = {"x-access-token": auth_token}
    
    r = api_client.get(url, headers=headers, params=params)
    assert r.status_code == 200, f"Ожидается 200 OK; получено {r.status_code}; curl: {_format_curl_command(api_client, ENDPOINT, params, headers)}"
    
    data = r.json()
    _check_type("root", data, RESPONSE_SCHEMA)

def test_get_service_count_all_params_combined(api_client, auth_token):
    """Тест со всеми параметрами одновременно"""
    base = f"http://127.0.0.1:{SERVICES['csi-server']['port']}{SERVICES['csi-server']['base_path']}"
    url = _url(base)
    params = {
        "limit": 10,
        "offset": 2,
        "page": 1,
        "sort": "name",
        "filter": "csi",
        "q": "server",
        "count": "true",
        "verbose": "true",
        "format": "json",
        "pretty": "true"
    }
    headers = {"x-access-token": auth_token}
    
    r = api_client.get(url, headers=headers, params=params)
    assert r.status_code == 200, f"Ожидается 200 OK; получено {r.status_code}; curl: {_format_curl_command(api_client, ENDPOINT, params, headers)}"
    
    data = r.json()
    _check_type("root", data, RESPONSE_SCHEMA)
