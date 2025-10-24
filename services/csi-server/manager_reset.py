import json
import os
import pytest
from qa_constants import SERVICES
try:
    from services.auth_utils import login
except Exception:
    login = None

ENDPOINT = "/manager/reset"

# Схема ответа для успешного выполнения
SUCCESS_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "status": {"type": "string"},
        "message": {"type": "string"}
    },
    "required": ["status", "message"]
}

def _print_validation(step: str, success: bool, details: str = ""):
    """
    Краткий вывод результата шага проверки.
    """
    status = "\u2713 PASSED" if success else "\u2717 FAILED"
    msg = f"[validation-{step}] {status}"
    if details:
        msg += f" — {details}"
    print(msg)

def _perform_agent_verification_reset(agent_verification, auth_token: str):
    """
    Выполняет проверку через агента для сброса менеджера.

    Контракт ответа агента:
      - {"result": "OK"} — успех
      - {"result": "ERROR", "message": "..."} — ошибка проверки
      - "unavailable" — агент недоступен (тест должен упасть)
    """
    payload = {
        "x-access-token": auth_token,
    }

    _print_validation("agent-prepare", True, "payload=token_only")

    agent_result = agent_verification(ENDPOINT, payload)

    if agent_result == "unavailable":
        _print_validation("agent-availability", False, "agent=unavailable")
        pytest.fail("Agent verification unavailable: агент недоступен")

    if isinstance(agent_result, dict):
        res = agent_result.get("result")
        if res == "OK":
            _print_validation("agent-verification", True, "result=OK")
            return
        if res == "ERROR":
            message = agent_result.get("message", "Unknown error")
            print(f"WARNING: Агент \"доступ\" — {message}")
            _print_validation("agent-verification", False, f"error={message}")
            pytest.fail(f"Agent verification failed: {message}")

        _print_validation("agent-verification", False, f"unexpected_result={res}")
        pytest.fail(f"Agent verification returned unexpected result: {res}")

    _print_validation("agent-verification", False, f"invalid_response_type={type(agent_result)}")
    pytest.fail(f"Agent verification returned invalid response type: {type(agent_result)}")


def _get_auth_token_for_agent() -> str:
    """
    Получает токен для запроса к агенту из ENV или через login().

    Порядок:
      1) ENV: X_ACCESS_TOKEN или AUTH_TOKEN
      2) services.auth_utils.login (admin/admin, agent=local)
    """
    token = os.environ.get("X_ACCESS_TOKEN") or os.environ.get("AUTH_TOKEN")
    if token:
        return token
    if login is None:
        pytest.fail("Не удалось получить токен: нет ENV X_ACCESS_TOKEN/AUTH_TOKEN и недоступен login()")
    try:
        return login(username="admin", password="admin", agent="local")
    except Exception as e:
        pytest.fail(f"Не удалось получить токен: {e}")

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

def test_manager_reset_unauthorized(api_client, api_base_url, attach_curl_on_fail):
    """
    Тест попытки сброса системы без токена аутентификации.
    """
    url = f"{api_base_url}{ENDPOINT}"
    headers = {"Content-Type": "application/json"}
    
    response = api_client.post(url, headers=headers)
    
    # Проверяем, что запрос отклонен из-за отсутствия токена
    assert response.status_code in [401, 403], f"Expected status code 401 or 403, got {response.status_code}"

def test_manager_reset_invalid_token(api_client, api_base_url, attach_curl_on_fail):
    """
    Тест попытки сброса системы с недействительным токеном.
    """
    url = f"{api_base_url}{ENDPOINT}"
    headers = {"x-access-token": "invalid_token", "Content-Type": "application/json"}
    
    response = api_client.post(url, headers=headers)
    
    # Проверяем, что запрос отклонен из-за недействительного токена
    assert response.status_code in [401, 403], f"Expected status code 401 or 403, got {response.status_code}"

def test_manager_reset_wrong_method(api_client, api_base_url, auth_token, attach_curl_on_fail):
    """
    Тест попытки доступа к эндпоинту с неправильным HTTP-методом.
    """
    url = f"{api_base_url}{ENDPOINT}"
    headers = {"x-access-token": auth_token, "Content-Type": "application/json"}
    
    # Пробуем GET вместо POST
    response = api_client.get(url, headers=headers)
    
    # Проверяем, что метод не поддерживается
    assert response.status_code == 404, f"Expected status code 404, got {response.status_code}"

def test_manager_reset_success_no_payload(api_client, api_base_url, auth_token, attach_curl_on_fail):
    """
    Тест успешного сброса системы без дополнительных параметров.
    КРИТИЧНО: Этот тест запускается только вручную!
    Система будет перезагружена после выполнения теста.
    """
    # Запрашиваем подтверждение у пользователя
    print("\n" + "="*80)
    print("  ВНИМАНИЕ: Этот тест перезагрузит систему!")
    print("="*80)
    print("Тест test_manager_reset_success_no_payload требует ручного запуска.")
    print("Система будет перезагружена после выполнения теста.")
    print("="*80)
    print("\n КОМАНДЫ ДЛЯ ЗАПУСКА:")
    print("="*80)
    print("1. Запуск только этого теста:")
    print("   MANUAL_TEST_CONFIRMATION=1 pytest services/csi-server/manager_reset.py::test_manager_reset_success_no_payload -v")
    print("\n2. Запуск всех тестов в файле:")
    print("   MANUAL_TEST_CONFIRMATION=1 pytest services/csi-server/manager_reset.py -v")
    print("\n3. Запуск с подробным выводом:")
    print("   MANUAL_TEST_CONFIRMATION=1 pytest services/csi-server/manager_reset.py::test_manager_reset_success_no_payload -v -s")
    print("\n4. Отмена запуска (просто не устанавливайте переменную):")
    print("   pytest services/csi-server/manager_reset.py::test_manager_reset_success_no_payload -v")
    print("="*80)
    
    # Проверяем, что тест запущен вручную
    import os
    if not os.environ.get('MANUAL_TEST_CONFIRMATION'):
        pytest.skip("Тест требует ручного подтверждения. Установите MANUAL_TEST_CONFIRMATION=1 для запуска")
    
    # Выполняем POST-запрос без payload
    url = f"{api_base_url}{ENDPOINT}"
    headers = {"x-access-token": auth_token, "Content-Type": "application/json"}
    
    response = api_client.post(url, headers=headers)
    
    # Проверяем статус код (204 - успешное выполнение без содержимого)
    assert response.status_code == 204, f"Expected status code 204, got {response.status_code}"
    
    # Если ответ содержит JSON, валидируем схему
    if response.content:
        try:
            response_data = response.json()
            _check_types_recursive(response_data, SUCCESS_RESPONSE_SCHEMA)
        except json.JSONDecodeError:
            # Если ответ не JSON, это нормально для статуса 204
            pass

def test_manager_reset_success_skip_homedir_true(api_client, api_base_url, auth_token, attach_curl_on_fail):
    """
    Тест успешного сброса системы с параметром skip-homedir=true.
    КРИТИЧНО: Этот тест запускается только вручную!
    Система будет перезагружена после выполнения теста.
    """
    # Запрашиваем подтверждение у пользователя
    print("\n" + "="*80)
    print("  ВНИМАНИЕ: Этот тест перезагрузит систему!")
    print("="*80)
    print("Тест test_manager_reset_success_skip_homedir_true требует ручного запуска.")
    print("Система будет перезагружена после выполнения теста.")
    print("="*80)
    print("\n КОМАНДЫ ДЛЯ ЗАПУСКА:")
    print("="*80)
    print("1. Запуск только этого теста:")
    print("   MANUAL_TEST_CONFIRMATION=1 pytest services/csi-server/manager_reset.py::test_manager_reset_success_skip_homedir_true -v")
    print("\n2. Запуск всех тестов в файле:")
    print("   MANUAL_TEST_CONFIRMATION=1 pytest services/csi-server/manager_reset.py -v")
    print("\n3. Запуск с подробным выводом:")
    print("   MANUAL_TEST_CONFIRMATION=1 pytest services/csi-server/manager_reset.py::test_manager_reset_success_skip_homedir_true -v -s")
    print("\n4. Отмена запуска (просто не устанавливайте переменную):")
    print("   pytest services/csi-server/manager_reset.py::test_manager_reset_success_skip_homedir_true -v")
    print("="*80)
    
    # Проверяем, что тест запущен вручную
    import os
    if not os.environ.get('MANUAL_TEST_CONFIRMATION'):
        pytest.skip("Тест требует ручного подтверждения. Установите MANUAL_TEST_CONFIRMATION=1 для запуска")
    
    # Выполняем POST-запрос с параметром skip-homedir=true
    url = f"{api_base_url}{ENDPOINT}"
    headers = {"x-access-token": auth_token, "Content-Type": "application/json"}
    payload = {"skip-homedir": True}
    
    response = api_client.post(url, headers=headers, json=payload)
    
    # Проверяем статус код (204 - успешное выполнение без содержимого)
    assert response.status_code == 204, f"Expected status code 204, got {response.status_code}"
    
    # Если ответ содержит JSON, валидируем схему
    if response.content:
        try:
            response_data = response.json()
            _check_types_recursive(response_data, SUCCESS_RESPONSE_SCHEMA)
        except json.JSONDecodeError:
            # Если ответ не JSON, это нормально для статуса 204
            pass

def test_manager_reset_success_skip_homedir_false(api_client, api_base_url, auth_token, attach_curl_on_fail):
    """
    Тест успешного сброса системы с параметром skip-homedir=false.
    КРИТИЧНО: Этот тест запускается только вручную!
    Система будет перезагружена после выполнения теста.
    """
    # Запрашиваем подтверждение у пользователя
    print("\n" + "="*80)
    print("  ВНИМАНИЕ: Этот тест перезагрузит систему!")
    print("="*80)
    print("Тест test_manager_reset_success_skip_homedir_false требует ручного запуска.")
    print("Система будет перезагружена после выполнения теста.")
    print("="*80)
    print("\n КОМАНДЫ ДЛЯ ЗАПУСКА:")
    print("="*80)
    print("1. Запуск только этого теста:")
    print("   MANUAL_TEST_CONFIRMATION=1 pytest services/csi-server/manager_reset.py::test_manager_reset_success_skip_homedir_false -v")
    print("\n2. Запуск всех тестов в файле:")
    print("   MANUAL_TEST_CONFIRMATION=1 pytest services/csi-server/manager_reset.py -v")
    print("\n3. Запуск с подробным выводом:")
    print("   MANUAL_TEST_CONFIRMATION=1 pytest services/csi-server/manager_reset.py::test_manager_reset_success_skip_homedir_false -v -s")
    print("\n4. Отмена запуска (просто не устанавливайте переменную):")
    print("   pytest services/csi-server/manager_reset.py::test_manager_reset_success_skip_homedir_false -v")
    print("="*80)
    
    # Проверяем, что тест запущен вручную
    import os
    if not os.environ.get('MANUAL_TEST_CONFIRMATION'):
        pytest.skip("Тест требует ручного подтверждения. Установите MANUAL_TEST_CONFIRMATION=1 для запуска")
    
    # Выполняем POST-запрос с параметром skip-homedir=false
    url = f"{api_base_url}{ENDPOINT}"
    headers = {"x-access-token": auth_token, "Content-Type": "application/json"}
    payload = {"skip-homedir": False}
    
    response = api_client.post(url, headers=headers, json=payload)
    
    # Проверяем статус код (204 - успешное выполнение без содержимого)
    assert response.status_code == 204, f"Expected status code 204, got {response.status_code}"
    
    # Если ответ содержит JSON, валидируем схему
    if response.content:
        try:
            response_data = response.json()
            _check_types_recursive(response_data, SUCCESS_RESPONSE_SCHEMA)
        except json.JSONDecodeError:
            # Если ответ не JSON, это нормально для статуса 204
            pass


def test_manager_reset_agent_verification(agent_verification):
    """
    Дополнительная проверка через агента для POST /manager/reset.

    В тело запроса к агенту передаём токен доступа вида:
        { "x-access-token": "[token]" }

    Выполняется без ручного подтверждения.
    """
    # Тест выполняет только запрос к агенту, без вызова основного API
    token = _get_auth_token_for_agent()
    _print_validation("agent-request", True, "POST agent /manager/reset")
    _perform_agent_verification_reset(agent_verification, token)
    _print_validation("agent-check-complete", True)
