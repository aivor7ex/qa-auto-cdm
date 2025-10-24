# file: /services/csi-server/manager_settings_timezone.py
import json
import pytest
from qa_constants import SERVICES

ENDPOINT = "/manager/settings/timezone"

# Схема успешного ответа для POST (валидация по R6-R7)
SUCCESS_RESPONSE_SCHEMA = {
    "type": "null"
}

# ----- СХЕМЫ ОТВЕТОВ ДЛЯ РАЗНЫХ HTTP МЕТОДОВ -----
RESPONSE_SCHEMAS = {
    "GET": {
        "type": "string",
        "required": True
    },
    "POST": {
        "type": "null",
        "required": True
    }
}

# ----- ФИКСТУРЫ (в проекте уже существуют) -----
# api_client(base_url), auth_token() — ИСПОЛЬЗОВАТЬ, НЕ МЕНЯТЬ.

def _url(base_path: str) -> str:
    return f"{base_path}{ENDPOINT}"

def _check_type(name, value, spec):
    t = spec.get("type")
    if t == "string":
        assert isinstance(value, str), f"{name}: ожидается string"
    elif t == "number":
        assert isinstance(value, (int, float)) and not isinstance(value, bool), f"{name}: ожидается number"
    elif t == "boolean":
        assert isinstance(value, bool), f"{name}: ожидается boolean"
    elif t == "object":
        assert isinstance(value, dict), f"{name}: ожидается object"
        _validate_object(value, spec.get("properties", {}), name)
    elif t == "list":
        assert isinstance(value, list), f"{name}: ожидается list"
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
            assert key in obj, f"{prefix}.{key}: обязательное поле"
        if key in obj:
            _check_type(f"{prefix}.{key}", obj[key], prop)



# ---------- ПАРАМЕТРИЗАЦИЯ ----------
# 30 осмысленных кейсов для GET запроса с различными query параметрами
BASE_PARAMS = [
    {"q": None, "desc": "базовый запрос без параметров"},
    {"q": {"format": "json"}, "desc": "формат JSON"},
    {"q": {"pretty": "true"}, "desc": "красивый вывод"},
    {"q": {"pretty": "false"}, "desc": "обычный вывод"},
    {"q": {"indent": "2"}, "desc": "отступ 2 пробела"},
    {"q": {"indent": "4"}, "desc": "отступ 4 пробела"},
    {"q": {"timezone": "UTC"}, "desc": "фильтр по UTC"},
    {"q": {"timezone": "GMT"}, "desc": "фильтр по GMT"},
    {"q": {"timezone": "Etc/GMT"}, "desc": "фильтр по Etc/GMT"},
    {"q": {"region": "Etc"}, "desc": "фильтр по региону"},
    {"q": {"offset": "0"}, "desc": "смещение 0"},
    {"q": {"offset": "+0"}, "desc": "смещение +0"},
    {"q": {"offset": "-0"}, "desc": "смещение -0"},
    {"q": {"dst": "false"}, "desc": "без летнего времени"},
    {"q": {"dst": "true"}, "desc": "с летним временем"},
    {"q": {"standard": "GMT"}, "desc": "стандартное время GMT"},
    {"q": {"abbreviation": "GMT"}, "desc": "сокращение GMT"},
    {"q": {"name": "Etc/GMT"}, "desc": "полное имя"},
    {"q": {"search": "GMT"}, "desc": "поиск по GMT"},
    {"q": {"filter": "Etc"}, "desc": "фильтр по Etc"},
    {"q": {"include": "timezone"}, "desc": "включить timezone"},
    {"q": {"exclude": "offset"}, "desc": "исключить offset"},
    {"q": {"sort": "name"}, "desc": "сортировка по имени"},
    {"q": {"sort": "-name"}, "desc": "сортировка по имени убыв"},
    {"q": {"limit": "1"}, "desc": "лимит 1"},
    {"q": {"limit": "10"}, "desc": "лимит 10"},
    {"q": {"page": "1"}, "desc": "страница 1"},
    {"q": {"page": "0"}, "desc": "страница 0"},
    {"q": {"count": "true"}, "desc": "счетчик элементов"},
    {"q": {"count": "false"}, "desc": "без счетчика"},
    {"q": {"verbose": "true"}, "desc": "подробный вывод"},
    {"q": {"verbose": "false"}, "desc": "краткий вывод"}
]

@pytest.mark.parametrize("case", BASE_PARAMS, ids=lambda c: c["desc"])
def test_get_schema_conforms(api_client, auth_token, case, attach_curl_on_fail):
    base = f"http://127.0.0.1:{SERVICES['csi-server']['port']}{SERVICES['csi-server']['base_path']}"
    url = _url(base)
    params = case.get("q") or {}
    headers = {'x-access-token': auth_token}
    
    with attach_curl_on_fail(ENDPOINT, None, headers, "GET"):
        r = api_client.get(url, headers=headers, params=params)
        assert r.status_code == 200, f"Ожидается 200 OK; получено {r.status_code}"
        data = r.json()
        if data is None:
            return
        assert isinstance(data, str), f"Корень: ожидается string"
        _check_type("root", data, RESPONSE_SCHEMAS["GET"])

# ----- НОВЫЕ ТЕСТЫ ДЛЯ POST ЗАПРОСОВ -----

# 1. Успешные кейсы - валидные часовые пояса
VALID_TIMEZONES = [
    "UTC",
    "Europe/Moscow",
    "America/New_York",
    "Asia/Tokyo",
    "Australia/Sydney",
    "Africa/Cairo",
    "Pacific/Auckland"
]

@pytest.mark.parametrize("timezone", VALID_TIMEZONES, ids=lambda tz: f"valid_timezone_{tz}")
def test_post_valid_timezones(api_client, auth_token, timezone, attach_curl_on_fail, agent_verification):
    """Тест успешных POST запросов с валидными часовыми поясами"""
    base = f"http://127.0.0.1:{SERVICES['csi-server']['port']}{SERVICES['csi-server']['base_path']}"
    url = _url(base)
    headers = {
        'Content-Type': 'application/json',
        'x-access-token': auth_token
    }
    data = {"data": timezone}
    
    with attach_curl_on_fail(ENDPOINT, data, headers, "POST"):
        r = api_client.post(url, headers=headers, json=data)
        assert r.status_code == 200, f"Ожидается 200 OK; получено {r.status_code}"
        
        # Проверяем схему ответа
        response_data = r.json()
        if response_data is not None:
            _check_type("root", response_data, RESPONSE_SCHEMAS["POST"])
        
        # Дополнительная проверка через агента для успешных запросов
        print(f"Starting agent verification for timezone: {timezone}")
        
        # Создаем payload для агента с телом основного запроса
        agent_payload = data.copy()
        
        # Вызываем агента с эндпоинтом /manager/settings/timezone
        agent_result = agent_verification("/manager/settings/timezone", agent_payload)
        
        # Обрабатываем ответ агента согласно контракту
        if agent_result == "unavailable":
            pytest.fail(f"Agent verification: AGENT UNAVAILABLE - timezone '{timezone}' verification failed due to agent unavailability")
        elif isinstance(agent_result, dict) and agent_result.get("result") == "OK":
            print(f"Agent verification: SUCCESS - timezone '{timezone}' was verified")
        elif isinstance(agent_result, dict) and agent_result.get("result") == "ERROR":
            message = agent_result.get("message", "Unknown error")
            pytest.fail(f"Agent verification: ERROR - timezone '{timezone}' verification failed: {message}")
        else:
            pytest.fail(f"Agent verification: UNEXPECTED RESULT {agent_result} for timezone '{timezone}'")

# 2. Кейсы с ошибками аутентификации
@pytest.mark.parametrize("auth_case", [
    {"headers": {}, "desc": "no_token"},
    {"headers": {"x-access-token": "INVALID_TOKEN"}, "desc": "invalid_token"}
], ids=lambda c: c["desc"])
def test_post_auth_errors(api_client, auth_case, attach_curl_on_fail):
    """Тест POST запросов с ошибками аутентификации"""
    base = f"http://127.0.0.1:{SERVICES['csi-server']['port']}{SERVICES['csi-server']['base_path']}"
    url = _url(base)
    headers = {
        'Content-Type': 'application/json',
        **auth_case["headers"]
    }
    data = {"data": "UTC"}
    
    with attach_curl_on_fail(ENDPOINT, data, headers, "POST"):
        r = api_client.post(url, headers=headers, json=data)
        assert r.status_code in [401, 403], f"Ожидается 401 или 403; получено {r.status_code}"

# 3. Кейсы с ошибками валидации
@pytest.mark.parametrize("validation_case", [
    {"data": {}, "desc": "missing_data_field", "expected_status": [500]},
    {"data": {"data": ""}, "desc": "empty_data_field", "expected_status": [200]},
    {"data": {"data": "Invalid/Timezone"}, "desc": "invalid_timezone_format", "expected_status": [200]}
], ids=lambda c: c["desc"])
def test_post_validation_errors(api_client, auth_token, validation_case, attach_curl_on_fail):
    """Тест POST запросов с ошибками валидации"""
    base = f"http://127.0.0.1:{SERVICES['csi-server']['port']}{SERVICES['csi-server']['base_path']}"
    url = _url(base)
    headers = {
        'Content-Type': 'application/json',
        'x-access-token': auth_token
    }
    
    with attach_curl_on_fail(ENDPOINT, validation_case["data"], headers, "POST"):
        r = api_client.post(url, headers=headers, json=validation_case["data"])
        expected_statuses = validation_case["expected_status"]
        assert r.status_code in expected_statuses, f"Ожидается один из {expected_statuses}; получено {r.status_code}"
        
        # Если запрос успешен, проверяем схему ответа
        if r.status_code == 200:
            response_data = r.json()
            if response_data is not None:
                _check_type("root", response_data, RESPONSE_SCHEMAS["POST"])

# 4. Кейсы с ошибками формата
@pytest.mark.parametrize("format_case", [
    {"headers": {"Content-Type": "text/plain"}, "desc": "wrong_content_type", "expected_status": [500]},
    {"data": '{"data": "UTC"', "desc": "invalid_json", "expected_status": [400, 500]}
], ids=lambda c: c["desc"])
def test_post_format_errors(api_client, auth_token, format_case, attach_curl_on_fail):
    """Тест POST запросов с ошибками формата"""
    base = f"http://127.0.0.1:{SERVICES['csi-server']['port']}{SERVICES['csi-server']['base_path']}"
    url = _url(base)
    headers = {
        'Content-Type': format_case.get('headers', {}).get('Content-Type', 'application/json'),
        'x-access-token': auth_token
    }
    
    # Для невалидного JSON используем raw data
    if 'data' in format_case:
        data = format_case['data']
        headers.pop('Content-Type', None)  # Убираем Content-Type для raw data
    else:
        data = {"data": "UTC"}
    
    with attach_curl_on_fail(ENDPOINT, data, headers, "POST"):
        if 'data' in format_case and format_case['data'] == '{"data": "UTC"':
            # Для невалидного JSON используем data параметр
            r = api_client.post(url, headers=headers, data=data)
        else:
            r = api_client.post(url, headers=headers, json=data)
        
        expected_statuses = format_case["expected_status"]
        assert r.status_code in expected_statuses, f"Ожидается один из {expected_statuses}; получено {r.status_code}"

# ===== ДОБАВЛЕНО: ТЕСТЫ ТОЛЬКО ДЛЯ POST ПО R5 =====

def _check_types_recursive(obj, schema):
    """Рекурсивно проверяет типы данных по схеме (расширение под тип null)."""
    if schema.get("type") == "object":
        assert isinstance(obj, dict), f"Expected object, got {type(obj)}"
        for key, prop in schema.get("properties", {}).items():
            if key in obj:
                _check_types_recursive(obj[key], prop)
        for req in schema.get("required", []):
            assert req in obj, f"Missing required field: {req}"
    elif schema.get("type") == "array":
        assert isinstance(obj, list) and not isinstance(obj, str), f"Expected array, got {type(obj)}"
        item_schema = schema.get("items")
        if isinstance(item_schema, list):
            for item, sch in zip(obj, item_schema):
                _check_types_recursive(item, sch)
        elif item_schema is not None:
            for item in obj:
                _check_types_recursive(item, item_schema)
    else:
        t = schema.get("type")
        if t == "string":
            assert isinstance(obj, str), f"Expected string, got {type(obj)}"
        elif t == "integer":
            assert isinstance(obj, int), f"Expected integer, got {type(obj)}"
        elif t == "number":
            assert isinstance(obj, (int, float)) and not isinstance(obj, bool), f"Expected number, got {type(obj)}"
        elif t == "boolean":
            assert isinstance(obj, bool), f"Expected boolean, got {type(obj)}"
        elif t == "null":
            assert obj is None, f"Expected null, got {type(obj)}"


# Позитивные кейсы (до 15), строго POST
VALID_TZ_CASES = [
    pytest.param({"data": "UTC"}, id="tz-UTC"),
    pytest.param({"data": "Etc/GMT"}, id="tz-Etc-GMT"),
    pytest.param({"data": "Europe/Moscow"}, id="tz-Europe-Moscow"),
    pytest.param({"data": "America/New_York"}, id="tz-America-New_York"),
    pytest.param({"data": "Asia/Tokyo"}, id="tz-Asia-Tokyo"),
    pytest.param({"data": "Australia/Sydney"}, id="tz-Australia-Sydney"),
    pytest.param({"data": "Africa/Cairo"}, id="tz-Africa-Cairo"),
    pytest.param({"data": "Pacific/Auckland"}, id="tz-Pacific-Auckland"),
    pytest.param({"data": "Europe/Berlin"}, id="tz-Europe-Berlin"),
    pytest.param({"data": "Europe/London"}, id="tz-Europe-London"),
    pytest.param({"data": "Asia/Dubai"}, id="tz-Asia-Dubai"),
    pytest.param({"data": "Asia/Kolkata"}, id="tz-Asia-Kolkata"),
    pytest.param({"data": "America/Los_Angeles"}, id="tz-America-Los_Angeles"),
    pytest.param({"data": "America/Chicago"}, id="tz-America-Chicago"),
    pytest.param({"data": "Europe/Paris"}, id="tz-Europe-Paris"),
]

@pytest.mark.parametrize("payload", VALID_TZ_CASES)
def test_post_timezone_positive(api_client, auth_token, api_base_url, payload, attach_curl_on_fail, agent_verification):
    url = f"{api_base_url}{ENDPOINT}"
    headers = {"x-access-token": auth_token, "Content-Type": "application/json"}

    with attach_curl_on_fail(ENDPOINT, payload, headers, "POST"):
        r = api_client.post(url, json=payload, headers=headers)
        assert r.status_code == 200, f"Ожидается 200 OK; получено {r.status_code}"

        # Валидируем структуру ответа по SUCCESS_RESPONSE_SCHEMA
        data = r.json()
        _check_types_recursive(data, SUCCESS_RESPONSE_SCHEMA)
        
        # Дополнительная проверка через агента для успешных запросов
        timezone_value = payload.get("data", "unknown")
        print(f"Starting agent verification for timezone: {timezone_value}")
        
        # Создаем payload для агента с телом основного запроса
        agent_payload = payload.copy()
        
        # Вызываем агента с эндпоинтом /manager/settings/timezone
        agent_result = agent_verification("/manager/settings/timezone", agent_payload)
        
        # Обрабатываем ответ агента согласно контракту
        if agent_result == "unavailable":
            pytest.fail(f"Agent verification: AGENT UNAVAILABLE - timezone '{timezone_value}' verification failed due to agent unavailability")
        elif isinstance(agent_result, dict) and agent_result.get("result") == "OK":
            print(f"Agent verification: SUCCESS - timezone '{timezone_value}' was verified")
        elif isinstance(agent_result, dict) and agent_result.get("result") == "ERROR":
            message = agent_result.get("message", "Unknown error")
            pytest.fail(f"Agent verification: ERROR - timezone '{timezone_value}' verification failed: {message}")
        else:
            pytest.fail(f"Agent verification: UNEXPECTED RESULT {agent_result} for timezone '{timezone_value}'")


# Негативные кейсы (до 15), строго POST — аутентификация
AUTH_NEGATIVE_CASES = [
    pytest.param({"headers": {}}, id="no-token"),
    pytest.param({"headers": {"x-access-token": ""}}, id="empty-token"),
    pytest.param({"headers": {"x-access-token": "invalid"}}, id="invalid-token"),
]

@pytest.mark.parametrize("case", AUTH_NEGATIVE_CASES)
def test_post_timezone_auth_negative(api_client, api_base_url, case, attach_curl_on_fail):
    url = f"{api_base_url}{ENDPOINT}"
    headers = {"Content-Type": "application/json", **case["headers"]}
    payload = {"data": "UTC"}

    with attach_curl_on_fail(ENDPOINT, payload, headers, "POST"):
        r = api_client.post(url, json=payload, headers=headers)
        assert r.status_code == 401, f"Ожидается 401 Unauthorized; получено {r.status_code}"
