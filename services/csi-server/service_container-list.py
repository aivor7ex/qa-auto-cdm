# file: /services/csi-server/service_container-list.py
import json
import pytest
from qa_constants import SERVICES

ENDPOINT = "/service/container-list"

# ----- СХЕМА ОТВЕТА (получена из API_EXAMPLE_RESPONSE_200_OK) -----
CONTAINER_ITEM_SCHEMA = {
    "id": {"type": "string", "required": True},
    "container": {"type": "string", "required": True},
    "state": {"type": "string", "required": True},
    "stack": {"type": "string", "required": True}
}

RESPONSE_SCHEMA = {
    "type": "object",
    "patternProperties": {
        ".*": CONTAINER_ITEM_SCHEMA
    },
    "additionalProperties": False
}

# ----- ФИКСТУРЫ (в проекте уже существуют) -----
# api_client(base_url), auth_token() — ИСПОЛЬЗОВАТЬ, НЕ МЕНЯТЬ.

def _url(base_path: str) -> str:
    return f"{base_path}{ENDPOINT}"

def _check_type(name, value, spec):
    t = spec.get("type")
    if t == "string":
        assert isinstance(value, str), f"{name}: ожидается string; curl: curl --location 'http://127.0.0.1:2999/api/service/container-list' --header 'x-access-token: 9wO53O0bTModkbS3Vhc50kOR2bXafRHg3IA2CBcIt84j'"
    elif t == "number":
        assert isinstance(value, (int, float)) and not isinstance(value, bool), f"{name}: ожидается number; curl: curl --location 'http://127.0.0.1:2999/api/service/container-list' --header 'x-access-token: 9wO53O0bTModkbS3Vhc50kOR2bXafRHg3IA2CBcIt84j'"
    elif t == "boolean":
        assert isinstance(value, bool), f"{name}: ожидается boolean; curl: curl --location 'http://127.0.0.1:2999/api/service/container-list' --header 'x-access-token: 9wO53O0bTModkbS3Vhc50kOR2bXafRHg3IA2CBcIt84j'"
    elif t == "object":
        assert isinstance(value, dict), f"{name}: ожидается object; curl: curl --location 'http://127.0.0.1:2999/api/service/container-list' --header 'x-access-token: 9wO53O0bTModkbS3Vhc50kOR2bXafRHg3IA2CBcIt84j'"
        _validate_object(value, spec.get("properties", {}), name)
    elif t == "list":
        assert isinstance(value, list), f"{name}: ожидается list; curl: curl --location 'http://127.0.0.1:2999/api/service/container-list' --header 'x-access-token: 9wO53O0bTModkbS3Vhc50kOR2bXafRHg3IA2CBcIt84j'"
        item_spec = spec.get("item_type")
        if item_spec:
            for i, v in enumerate(value):
                _check_type(f"{name}[{i}]", v, item_spec)
    else:
        assert False, f"{name}: неизвестный тип '{t}'; curl: curl --location 'http://127.0.0.1:2999/api/service/container-list' --header 'x-access-token: 9wO53O0bTModkbS3Vhc50kOR2bXafRHg3IA2CBcIt84j'"

def _validate_object(obj, properties: dict, prefix: str = "root"):
    for key, prop in properties.items():
        required = prop.get("required", False)
        if required:
            assert key in obj, f"{prefix}.{key}: обязательное поле; curl: curl --location 'http://127.0.0.1:2999/api/service/container-list' --header 'x-access-token: 9wO53O0bTModkbS3Vhc50kOR2bXafRHg3IA2CBcIt84j'"
        if key in obj:
            _check_type(f"{prefix}.{key}", obj[key], prop)

def _validate_container_response(data):
    """Валидирует структуру ответа с контейнерами"""
    assert isinstance(data, dict), f"Корень: ожидается object; curl: curl --location 'http://127.0.0.1:2999/api/service/container-list' --header 'x-access-token: 9wO53O0bTModkbS3Vhc50kOR2bXafRHg3IA2CBcIt84j'"
    
    # Проверяем каждый контейнер
    for container_key, container_data in data.items():
        assert isinstance(container_key, str), f"Ключ контейнера должен быть строкой; curl: curl --location 'http://127.0.0.1:2999/api/service/container-list' --header 'x-access-token: 9wO53O0bTModkbS3Vhc50kOR2bXafRHg3IA2CBcIt84j'"
        _validate_object(container_data, CONTAINER_ITEM_SCHEMA, f"container.{container_key}")

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
# 40 кейсов для GET запросов с различными параметрами
BASE_PARAMS = [
    {"q": None, "desc": "базовый запрос без параметров"},
    {"q": {"limit": 1}, "desc": "ограничение вывода одним элементом"},
    {"q": {"limit": 5}, "desc": "ограничение вывода пятью элементами"},
    {"q": {"limit": 0}, "desc": "нулевое ограничение вывода"},
    {"q": {"limit": 100}, "desc": "большое ограничение вывода"},
    {"q": {"offset": 0}, "desc": "смещение 0"},
    {"q": {"offset": 1}, "desc": "смещение 1"},
    {"q": {"page": 1}, "desc": "первая страница"},
    {"q": {"page": 2}, "desc": "вторая страница"},
    {"q": {"sort": "name"}, "desc": "сортировка по имени"},
    {"q": {"sort": "asc"}, "desc": "сортировка по возрастанию"},
    {"q": {"sort": "desc"}, "desc": "сортировка по убыванию"},
    {"q": {"filter": "csi"}, "desc": "фильтр по csi"},
    {"q": {"filter": "logger"}, "desc": "фильтр по ngfw"},
    {"q": {"filter": "vpp"}, "desc": "фильтр по vpp"},
    {"q": {"filter": "squid"}, "desc": "фильтр по squid"},
    {"q": {"q": "test"}, "desc": "поисковый запрос test"},
    {"q": {"q": ""}, "desc": "пустой поисковый запрос"},
    {"q": {"q": "vpp"}, "desc": "поиск по vpp"},
    {"q": {"count": "true"}, "desc": "параметр count true"},
    {"q": {"count": "false"}, "desc": "параметр count false"},
    {"q": {"verbose": "true"}, "desc": "подробный вывод"},
    {"q": {"format": "json"}, "desc": "формат json"},
    {"q": {"state": "running"}, "desc": "фильтр по состоянию running"},
    {"q": {"state": "stopped"}, "desc": "фильтр по состоянию stopped"},
    {"q": {"limit": 10, "offset": 5}, "desc": "комбинация limit и offset"},
    {"q": {"page": 2, "limit": 20}, "desc": "комбинация page и limit"},
    {"q": {"sort": "name", "filter": "csi"}, "desc": "комбинация sort и filter"},
    {"q": {"q": "vpp", "stack": "vpp"}, "desc": "комбинация поиска и стека"},
    {"q": {"fields": "id,container,state", "limit": 5}, "desc": "комбинация fields и limit"},
    {"q": {"include": "running", "exclude": "stopped", "limit": 10}, "desc": "комбинация include, exclude и limit"},
    {"q": {"stack": "csi", "state": "running", "sort": "name"}, "desc": "комбинация stack, state и sort"},
    {"q": {"limit": 100, "offset": 0, "page": 1, "sort": "id", "filter": "ngfw"}, "desc": "комплексная комбинация параметров"},
]

@pytest.mark.parametrize("case", BASE_PARAMS, ids=lambda c: c["desc"])
def test_get_container_list_schema_conforms(api_client, auth_token, case):
    base = f"http://127.0.0.1:{SERVICES['csi-server']['port']}{SERVICES['csi-server']['base_path']}"
    url = _url(base)
    params = case.get("q") or {}
    headers = {"x-access-token": auth_token}
    
    r = api_client.get(url, headers=headers, params=params)
    assert r.status_code == 200, f"Ожидается 200 OK; получено {r.status_code}; curl: {_format_curl_command(api_client, ENDPOINT, params, headers)}"
    
    data = r.json()
    _validate_container_response(data)

def test_get_container_list_empty_params(api_client, auth_token):
    """Тест базового запроса без параметров"""
    base = f"http://127.0.0.1:{SERVICES['csi-server']['port']}{SERVICES['csi-server']['base_path']}"
    url = _url(base)
    headers = {"x-access-token": auth_token}
    
    r = api_client.get(url, headers=headers)
    assert r.status_code == 200, f"Ожидается 200 OK; получено {r.status_code}; curl: {_format_curl_command(api_client, ENDPOINT, {}, headers)}"
    
    data = r.json()
    _validate_container_response(data)
    assert len(data) > 0, "Должен быть хотя бы один контейнер"



def test_get_container_list_all_params_combined(api_client, auth_token):
    """Тест со всеми параметрами одновременно"""
    base = f"http://127.0.0.1:{SERVICES['csi-server']['port']}{SERVICES['csi-server']['base_path']}"
    url = _url(base)
    params = {
        "limit": 50,
        "offset": 0,
        "page": 1,
        "sort": "name",
        "filter": "csi",
        "q": "test",
        "count": "true",
        "verbose": "true",
        "format": "json",
        "pretty": "true",
        "fields": "id,container,state,stack",
        "include": "running",
        "exclude": "stopped",
        "stack": "csi",
        "state": "running"
    }
    headers = {"x-access-token": auth_token}
    
    r = api_client.get(url, headers=headers, params=params)
    assert r.status_code == 200, f"Ожидается 200 OK; получено {r.status_code}; curl: {_format_curl_command(api_client, ENDPOINT, params, headers)}"
    
    data = r.json()
    _validate_container_response(data)

def test_get_container_list_response_structure(api_client, auth_token):
    """Тест структуры ответа"""
    base = f"http://127.0.0.1:{SERVICES['csi-server']['port']}{SERVICES['csi-server']['base_path']}"
    url = _url(base)
    headers = {"x-access-token": auth_token}
    
    r = api_client.get(url, headers=headers)
    assert r.status_code == 200, f"Ожидается 200 OK; получено {r.status_code}; curl: {_format_curl_command(api_client, ENDPOINT, {}, headers)}"
    
    data = r.json()
    _validate_container_response(data)
    
    # Проверяем, что есть хотя бы один контейнер
    assert len(data) > 0, "Должен быть хотя бы один контейнер"
    
    # Проверяем структуру первого контейнера
    first_container = next(iter(data.values()))
    assert "id" in first_container, "Контейнер должен содержать поле id"
    assert "container" in first_container, "Контейнер должен содержать поле container"
    assert "state" in first_container, "Контейнер должен содержать поле state"
    assert "stack" in first_container, "Контейнер должен содержать поле stack"
    
    # Проверяем типы полей
    assert isinstance(first_container["id"], str), "Поле id должно быть строкой"
    assert isinstance(first_container["container"], str), "Поле container должно быть строкой"
    assert isinstance(first_container["state"], str), "Поле state должно быть строкой"
    assert isinstance(first_container["stack"], str), "Поле stack должно быть строкой"

def test_get_container_list_container_names_format(api_client, auth_token):
    """Тест формата имен контейнеров"""
    base = f"http://127.0.0.1:{SERVICES['csi-server']['port']}{SERVICES['csi-server']['base_path']}"
    url = _url(base)
    headers = {"x-access-token": auth_token}
    
    r = api_client.get(url, headers=headers)
    assert r.status_code == 200, f"Ожидается 200 OK; получено {r.status_code}; curl: {_format_curl_command(api_client, ENDPOINT, {}, headers)}"
    
    data = r.json()
    _validate_container_response(data)
    
    # Проверяем формат имен контейнеров (должны содержать точку)
    for container_key in data.keys():
        assert "." in container_key, f"Имя контейнера должно содержать точку: {container_key}"

def test_get_container_list_state_values(api_client, auth_token):
    """Тест значений поля state"""
    base = f"http://127.0.0.1:{SERVICES['csi-server']['port']}{SERVICES['csi-server']['base_path']}"
    url = _url(base)
    headers = {"x-access-token": auth_token}
    
    r = api_client.get(url, headers=headers)
    assert r.status_code == 200, f"Ожидается 200 OK; получено {r.status_code}; curl: {_format_curl_command(api_client, ENDPOINT, {}, headers)}"
    
    data = r.json()
    _validate_container_response(data)
    
    # Проверяем, что все контейнеры имеют валидное состояние
    valid_states = {"running", "stopped", "exited", "created", "restarting", "paused"}
    for container_key, container_data in data.items():
        assert container_data["state"] in valid_states, f"Невалидное состояние контейнера {container_key}: {container_data['state']}"

def test_get_container_list_stack_values(api_client, auth_token):
    """Тест значений поля stack"""
    base = f"http://127.0.0.1:{SERVICES['csi-server']['port']}{SERVICES['csi-server']['base_path']}"
    url = _url(base)
    headers = {"x-access-token": auth_token}
    
    r = api_client.get(url, headers=headers)
    assert r.status_code == 200, f"Ожидается 200 OK; получено {r.status_code}; curl: {_format_curl_command(api_client, ENDPOINT, {}, headers)}"
    
    data = r.json()
    _validate_container_response(data)
    
    # Проверяем, что все контейнеры имеют валидный стек
    valid_stacks = {"csi", "ngfw", "logger-analytics", "vpp", "squid", "snmp", "shared", "tls-bridge"}
    for container_key, container_data in data.items():
        assert container_data["stack"] in valid_stacks, f"Невалидный стек контейнера {container_key}: {container_data['stack']}"

def test_get_container_list_id_format(api_client, auth_token):
    """Тест формата поля id"""
    base = f"http://127.0.0.1:{SERVICES['csi-server']['port']}{SERVICES['csi-server']['base_path']}"
    url = _url(base)
    headers = {"x-access-token": auth_token}
    
    r = api_client.get(url, headers=headers)
    assert r.status_code == 200, f"Ожидается 200 OK; получено {r.status_code}; curl: {_format_curl_command(api_client, ENDPOINT, {}, headers)}"
    
    data = r.json()
    _validate_container_response(data)
    
    # Проверяем, что ID контейнеров имеют правильный формат (12 символов hex)
    for container_key, container_data in data.items():
        assert len(container_data["id"]) == 12, f"ID контейнера {container_key} должен быть длиной 12 символов: {container_data['id']}"
        assert all(c in "0123456789abcdef" for c in container_data["id"]), f"ID контейнера {container_key} должен содержать только hex символы: {container_data['id']}"

def test_get_container_list_response_consistency(api_client, auth_token):
    """Тест консистентности ответа"""
    base = f"http://127.0.0.1:{SERVICES['csi-server']['port']}{SERVICES['csi-server']['base_path']}"
    url = _url(base)
    headers = {"x-access-token": auth_token}
    
    # Делаем два запроса и сравниваем
    r1 = api_client.get(url, headers=headers)
    r2 = api_client.get(url, headers=headers)
    
    assert r1.status_code == 200, f"Первый запрос: ожидается 200 OK; получено {r1.status_code}; curl: {_format_curl_command(api_client, ENDPOINT, {}, headers)}"
    assert r2.status_code == 200, f"Второй запрос: ожидается 200 OK; получено {r2.status_code}; curl: {_format_curl_command(api_client, ENDPOINT, {}, headers)}"
    
    data1 = r1.json()
    data2 = r2.json()
    
    _validate_container_response(data1)
    _validate_container_response(data2)
    
    # Проверяем, что количество контейнеров одинаково
    assert len(data1) == len(data2), "Количество контейнеров должно быть одинаковым в последовательных запросах"
    
    # Проверяем, что структура данных одинакова
    for key in data1.keys():
        assert key in data2, f"Ключ {key} должен присутствовать в обоих ответах"
        assert data1[key]["id"] == data2[key]["id"], f"ID контейнера {key} должен быть одинаковым"
        assert data1[key]["container"] == data2[key]["container"], f"Имя контейнера {key} должно быть одинаковым"
        assert data1[key]["stack"] == data2[key]["stack"], f"Стек контейнера {key} должен быть одинаковым"
