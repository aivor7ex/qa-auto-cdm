import json
import pytest


ENDPOINT = "/integrity/test"

# Схема успешного ответа для /integrity/test эндпоинта
# Структура: {"state": "success", "items": [{"state": "success", "id": "...", "originalChecksum": "..."}]}
SUCCESS_RESPONSE_SCHEMA = {
    "state": str,
    "items": list
}


def _validate_success_json(data, schema):
    """Рекурсивно валидирует JSON-ответ по схеме словаря вида {field: type}.
    Для /integrity/test проверяет структуру: {"state": str, "items": [{"state": str, "id": str, "originalChecksum": str}]}
    """
    assert isinstance(data, dict), f"JSON root must be object, got {type(data)}"
    for key, expected_type in schema.items():
        assert key in data, f"Missing field: {key}"
        value = data[key]
        if expected_type is dict:
            assert isinstance(value, dict), f"Field '{key}' should be dict, got {type(value)}"
        elif expected_type is list:
            assert isinstance(value, list), f"Field '{key}' should be list, got {type(value)}"
        else:
            assert isinstance(value, expected_type), f"Field '{key}' should be {expected_type}, got {type(value)}"
    
    # Дополнительная валидация для /integrity/test
    if "items" in data and isinstance(data["items"], list):
        for i, item in enumerate(data["items"]):
            assert isinstance(item, dict), f"Item {i} in 'items' should be dict, got {type(item)}"
            assert "state" in item, f"Item {i} missing 'state' field"
            assert "id" in item, f"Item {i} missing 'id' field"
            assert "originalChecksum" in item, f"Item {i} missing 'originalChecksum' field"
            assert isinstance(item["state"], str), f"Item {i} 'state' should be string, got {type(item['state'])}"
            assert isinstance(item["id"], str), f"Item {i} 'id' should be string, got {type(item['id'])}"
            assert isinstance(item["originalChecksum"], str), f"Item {i} 'originalChecksum' should be string, got {type(item['originalChecksum'])}"


# 1) Успешные кейсы (200)
@pytest.mark.parametrize(
    "case",
    [
        pytest.param({"name": "no-body", "headers": None, "json": None, "data": None}, id="200-no-body"),
        pytest.param({"name": "json-body-ignored", "headers": {"Content-Type": "application/json"}, "json": {"note": "autotest"}, "data": None}, id="200-json-body"),
        pytest.param({"name": "no-content-type", "headers": None, "json": None, "data": None}, id="200-no-content-type"),
        pytest.param({"name": "accept-json", "headers": {"Accept": "application/json"}, "json": None, "data": None}, id="200-accept-json"),
        pytest.param({"name": "text-plain-empty", "headers": {"Content-Type": "text/plain"}, "json": None, "data": ""}, id="200-text-plain-empty"),
        pytest.param({"name": "json-empty-object", "headers": {"Content-Type": "application/json"}, "json": {}, "data": None}, id="200-json-empty-object"),
        pytest.param({"name": "json-array", "headers": {"Content-Type": "application/json"}, "json": [1, 2, 3], "data": None}, id="200-json-array"),
        pytest.param({"name": "json-nested", "headers": {"Content-Type": "application/json"}, "json": {"a": {"b": [1, {"c": True}]}, "n": 42}, "data": None}, id="200-json-nested"),
        pytest.param({"name": "json-charset", "headers": {"Content-Type": "application/json; charset=utf-8"}, "json": {"k": "v"}, "data": None}, id="200-json-charset"),
        pytest.param({"name": "accept-language", "headers": {"Accept-Language": "en"}, "json": None, "data": None}, id="200-accept-language"),
        pytest.param({"name": "x-request-id", "headers": {"X-Request-ID": "pytest-req-1"}, "json": None, "data": None}, id="200-x-request-id"),
        pytest.param({"name": "form-urlencoded", "headers": {"Content-Type": "application/x-www-form-urlencoded"}, "json": None, "data": "a=1&b=2"}, id="200-form-urlencoded"),
        pytest.param({"name": "accept-any", "headers": {"Accept": "*/*"}, "json": None, "data": None}, id="200-accept-any"),
        pytest.param({"name": "accept-quality", "headers": {"Accept": "application/json, */*;q=0.8"}, "json": None, "data": None}, id="200-accept-quality"),
        pytest.param({"name": "custom-header", "headers": {"X-Debug": "true"}, "json": {"note": "autotest"}, "data": None}, id="200-custom-header"),
        pytest.param({"name": "cache-control", "headers": {"Cache-Control": "no-cache"}, "json": None, "data": None}, id="200-cache-control"),
    ],
)
def test_integrity_test_success_cases(api_client, auth_token, attach_curl_on_fail, agent_verification, case):
    headers = {"x-access-token": auth_token}
    if case.get("headers"):
        headers.update(case["headers"])  # type: ignore[arg-type]

    with attach_curl_on_fail(ENDPOINT, headers=headers, method="POST"):
        if case.get("json") is not None:
            response = api_client.post(ENDPOINT, headers=headers, json=case["json"])  # type: ignore[index]
        elif case.get("data") is not None:
            response = api_client.post(ENDPOINT, headers=headers, data=case["data"])  # type: ignore[index]
        else:
            response = api_client.post(ENDPOINT, headers=headers)

    assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    # Валидация ответа: ожидаем JSON с определенной структурой
    content_type = response.headers.get("content-type", "")
    assert "application/json" in content_type, f"Expected JSON response, got content-type: {content_type}"
    assert response.content, "Expected non-empty JSON response"
    
    data = response.json()
    _validate_success_json(data, SUCCESS_RESPONSE_SCHEMA)

    # Дополнительная проверка через агента для успешных POST запросов
    print(f"Starting agent verification for integrity test: {case.get('name', 'unknown')}")
    
    # Создаем payload для агента на основе ответа сервера
    agent_payload = {
        "state": "success"  # По умолчанию success для статуса 200
    }
    
    # Если ответ содержит JSON данные, используем их как state
    if response.content and "application/json" in content_type:
        data = response.json()
        if isinstance(data, dict) and data:  # Если ответ содержит данные
            # Используем первое значение из ответа как state
            first_value = next(iter(data.values()))
            agent_payload["state"] = first_value
    
    # Вызываем проверку агента
    agent_result = agent_verification("/integrity/test", agent_payload)
    
    # Обрабатываем ответ агента согласно стандартному формату
    if agent_result == "unavailable":
        pytest.fail(f"Agent verification: AGENT UNAVAILABLE - integrity test '{case.get('name', 'unknown')}' verification failed due to agent unavailability")
    elif isinstance(agent_result, dict) and agent_result.get("result") == "OK":
        print(f"Agent verification: SUCCESS - integrity test '{case.get('name', 'unknown')}' was verified")
    elif isinstance(agent_result, dict) and agent_result.get("result") == "ERROR":
        message = agent_result.get("message", "Unknown error")
        pytest.fail(f"Agent verification: ERROR - integrity test '{case.get('name', 'unknown')}' verification failed: {message}")
    else:
        pytest.fail(f"Agent verification: UNEXPECTED RESULT {agent_result} for integrity test '{case.get('name', 'unknown')}'")


# 2) Ошибки аутентификации (401)
@pytest.mark.parametrize(
    "headers",
    [
        pytest.param({}, id="no-token"),
        pytest.param({"x-access-token": "invalid-token"}, id="invalid-token"),
        pytest.param({"Authorization": "Bearer something"}, id="wrong-header"),
        pytest.param({"x-access-token": ""}, id="empty-token"),
        pytest.param({"x-access-token": "0"}, id="short-token"),
        pytest.param({"X-ACCESS-TOKEN": "invalid"}, id="wrong-case-header"),
        pytest.param({"x-access-token": "Bearer invalid"}, id="bearer-in-x-access-token"),
        pytest.param({"Content-Type": "application/json"}, id="only-content-type"),
        pytest.param({"Accept": "application/json"}, id="only-accept"),
        pytest.param({"Content-Type": "application/json", "Accept": "application/json"}, id="json-headers-no-token"),
        pytest.param({"x-access-token": "invalid", "Content-Type": "application/json"}, id="invalid-token-with-json"),
        pytest.param({"x-access-token": "invalid", "Accept": "*/*"}, id="invalid-token-with-accept"),
        pytest.param({"x-access-token": "invalid", "X-Request-ID": "pytest-req-2"}, id="invalid-token-with-x-request-id"),
        pytest.param({"x-access-token": "invalid", "Accept-Language": "ru"}, id="invalid-token-with-lang"),
    ],
)
def test_integrity_test_auth_errors(api_client, attach_curl_on_fail, headers):
    with attach_curl_on_fail(ENDPOINT, headers=headers, method="POST"):
        response = api_client.post(ENDPOINT, headers=headers)
    assert response.status_code == 401, f"Expected 401, got {response.status_code}"


# 3) Неверный путь (404)
@pytest.mark.parametrize(
    "endpoint",
    [
        pytest.param(f"{ENDPOINT}typo", id="typo-1"),
        pytest.param("/integrify/test", id="wrong-parent"),
        pytest.param("/integrity/test_wrong", id="wrong-suffix"),
        pytest.param("/integrity/tes", id="missing-char"),
        pytest.param("/integrity/tests", id="extra-char"),
    ],
)
def test_integrity_test_wrong_path_404(api_client, auth_token, attach_curl_on_fail, endpoint):
    headers = {"x-access-token": auth_token}
    with attach_curl_on_fail(endpoint, headers=headers, method="POST"):
        response = api_client.post(endpoint, headers=headers)
    assert response.status_code == 404, f"Expected 404, got {response.status_code}"


