import json
import pytest
from qa_constants import SERVICES

ENDPOINT = "/system-report/generate"

# Схема ответа для успешного выполнения
SUCCESS_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "status": {"type": "string"}
    },
    "required": ["status"]
}

def _check_types_recursive(obj, schema):
    """Рекурсивно проверяет типы данных по схеме"""
    if schema.get("type") == "object":
        assert isinstance(obj, dict), f"Expected object, got {type(obj)}"
        for key, prop in schema.get("properties", {}).items():
            if key in obj:
                _check_types_recursive(obj[key], prop)
        for req in schema.get("required", []):
            assert req in obj, f"Missing required field: {req}"
    elif schema.get("type") == "string":
        assert isinstance(obj, str), f"Expected string, got {type(obj)}"
    elif schema.get("type") == "number":
        assert isinstance(obj, (int, float)), f"Expected number, got {type(obj)}"
    elif schema.get("type") == "array":
        assert isinstance(obj, list), f"Expected array, got {type(obj)}"
        for item in obj:
            if "items" in schema:
                _check_types_recursive(item, schema["items"])

def test_system_report_generate_positive_case(
    api_client,
    api_base_url,
    auth_token,
    attach_curl_on_fail,
    agent_verification # Добавляем фикстуру agent_verification
):
    """
    Позитивный тестовый случай для POST /system-report/generate без тела запроса,
    ожидающий статус 200 (успех).
    Включает подготовительный запрос к агенту.
    """
    url = f"{api_base_url}{ENDPOINT}"
    headers = {"x-access-token": auth_token, "Content-Type": "application/json"}

    # Проверяем статус генерации
    check_url = f"{api_base_url}/system-report/check"
    check_response = api_client.post(check_url, headers=headers)
    check_data = check_response.json()
    
    import time
    if check_data.get("status") == "GENERATION_IN_PROGRESS":
        # Опрашиваем до тех пор, пока не станет GENERATED
        max_attempts = 180  # 15 минут при 5 сек задержке
        attempt = 0
        while attempt < max_attempts and check_data.get("status") != "GENERATED":
            time.sleep(5)
            check_response = api_client.post(check_url, headers=headers)
            check_data = check_response.json()
            attempt += 1
        if check_data.get("status") != "GENERATED":
            pytest.fail("Timeout: Status did not become GENERATED within 15 minutes")

    # 1) Выполняем подготовительный запрос к агенту (без тела)
    print("Validation: Выполняем подготовительный запрос к агенту по пути '/system-report/generate/prepare' без тела")
    prepare_result = agent_verification("/system-report/generate/prepare", None, timeout=300)

    if prepare_result == "unavailable":
        print("Warning: агент недоступен для подготовительного запроса — тест не пропускается и должен упасть")
        pytest.fail("Agent verification: AGENT UNAVAILABLE - prepare step failed due to agent unavailability")
    elif isinstance(prepare_result, dict) and prepare_result.get("result") == "OK":
        print("Agent verification: Подготовительный запрос успешен — OK")
    elif isinstance(prepare_result, dict) and prepare_result.get("result") == "ERROR":
        message = prepare_result.get("message", "Unknown error")
        pytest.fail(f"Agent verification: ERROR - Подготовительный запрос провален: {message}")
    else:
        pytest.fail(f"Agent verification: UNEXPECTED RESULT для подготовительного запроса: {prepare_result}")

    with attach_curl_on_fail(ENDPOINT, None, headers, "POST"):
        response = api_client.post(url, headers=headers)
    
    assert response.status_code == 200, f"Expected status code 200, got {response.status_code}"

    if response.content:
        response_data = response.json()
        _check_types_recursive(response_data, SUCCESS_RESPONSE_SCHEMA)

    # 3) Запрос агенту на проверку выполнения эндпоинта (без тела)
    print("Validation: Выполняем запрос к агенту на проверку эндпоинта '/system-report/generate' без тела")
    agent_check_result = agent_verification(ENDPOINT, None, timeout=300)

    if agent_check_result == "unavailable":
        print("Warning: агент недоступен для финальной проверки — тест не пропускается и должен упасть")
        pytest.fail("Agent verification: AGENT UNAVAILABLE - final check failed due to agent unavailability")
    elif isinstance(agent_check_result, dict) and agent_check_result.get("result") == "OK":
        print("Agent verification: Финальная проверка успешна — OK")
    elif isinstance(agent_check_result, dict) and agent_check_result.get("result") == "ERROR":
        message = agent_check_result.get("message", "Unknown error")
        pytest.fail(f"Agent verification: ERROR - Финальная проверка провалена: {message}")
    else:
        pytest.fail(f"Agent verification: UNEXPECTED RESULT для финальной проверки: {agent_check_result}")

    # Финальная проверка статуса генерации
    final_check_response = api_client.post(check_url, headers=headers)
    final_check_data = final_check_response.json()
    assert final_check_data.get("status") == "GENERATED", f"Expected status GENERATED, got {final_check_data.get('status')}"

    # Если агент вернул размер в предыдущей проверке, сравниваем с размером из final_check
    # agent_check_result может быть строкой "unavailable" или dict
    agent_report_size = None
    if isinstance(agent_check_result, dict) and agent_check_result.get("result") == "OK":
        # агент может вернуть размер в теле ответа
        agent_report_size = agent_check_result.get("size")

    # Если агент предоставил размер, сравниваем с данными final_check
    if agent_report_size is not None:
        check_report_size = final_check_data.get("size")
        assert check_report_size is not None, f"Expected size in final check response, got {final_check_data}"
        assert int(check_report_size) == int(agent_report_size), f"Size mismatch: agent={agent_report_size}, check={check_report_size}"


@pytest.mark.parametrize(
    "payload, headers, expected_status",
    [
        # 1) Без токена аутентификации
        pytest.param({"report_type": "system"}, {"Content-Type": "application/json"}, 401, id="no-auth-token"),
        # 2) Пустой токен
        pytest.param({"report_type": "system"}, {"x-access-token": "", "Content-Type": "application/json"}, 401, id="empty-token"),
        # 3) Некорректный токен
        pytest.param({"report_type": "system"}, {"x-access-token": "invalid_token", "Content-Type": "application/json"}, 401, id="invalid-token"),
        # 4) Тело как обычный текст без авторизации -> 400
        pytest.param("just text", {"Content-Type": "application/json"}, 400, id="plain-text-no-auth"),
        # 5) Тело-массив без авторизации -> 401
        pytest.param(["not", "an", "object"], {"Content-Type": "application/json"}, 401, id="array-body-no-auth"),
    ],
)
def test_system_report_generate_negative_cases(
    api_client,
    api_base_url,
    attach_curl_on_fail,
    payload,
    headers,
    expected_status,
):
    url = f"{api_base_url}{ENDPOINT}"

    with attach_curl_on_fail(ENDPOINT, payload, headers, "POST"):
        if isinstance(payload, str) or isinstance(payload, list):
            body = payload if isinstance(payload, str) else json.dumps(payload)
            response = api_client.post(url, headers=headers, data=body)
        else:
            response = api_client.post(url, headers=headers, json=payload)

    assert response.status_code == expected_status, \
        f"Expected {expected_status}, got {response.status_code}"