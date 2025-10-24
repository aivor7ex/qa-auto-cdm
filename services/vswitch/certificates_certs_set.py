import json
import pytest
import base64
import requests
from services.qa_constants import SERVICES
import os

# =====================================================================================================================
# Constants
# =====================================================================================================================

ENDPOINT = "/certificates/certs/set"
SERVICE = SERVICES["vswitch"][0]
PORT = SERVICE["port"]
BASE_PATH = SERVICE["base_path"]

# --- Response Schemas for POST (и для других методов, если появятся) ---
response_schemas = {
    "POST": {
        "type": "object",
        "properties": {
            "result": {"type": "string"},
            "error": {
                "type": "object",
                "properties": {
                    "statusCode": {"type": "integer"},
                    "name": {"type": "string"},
                    "message": {"type": "string"},
                    "status": {"type": "integer"},
                    "stack": {"type": "string"}
                },
                "required": ["statusCode", "name", "message"]
            }
        },
        "required": [],  # Проверяем ниже по статусу
    }
}

# =====================================================================================================================
# Helpers for schema validation and curl logging
# =====================================================================================================================

def _check_types_recursive(obj, schema):
    if "anyOf" in schema:
        assert any(_try_type(obj, s) for s in schema["anyOf"]), f"Value {obj} does not match anyOf {schema['anyOf']}"
        return
    if schema.get("type") == "object":
        assert isinstance(obj, dict), f"Expected object, got {type(obj)}"
        for key, prop in schema.get("properties", {}).items():
            if key in obj:
                _check_types_recursive(obj[key], prop)
        for req in schema.get("required", []):
            assert req in obj, f"Missing required field: {req}"
    elif schema.get("type") == "array":
        assert isinstance(obj, list), f"Expected array, got {type(obj)}"
        for item in obj:
            _check_types_recursive(item, schema["items"])
    elif schema.get("type") == "string":
        assert isinstance(obj, str), f"Expected string, got {type(obj)}"
    elif schema.get("type") == "integer":
        assert isinstance(obj, int), f"Expected integer, got {type(obj)}"
    elif schema.get("type") == "boolean":
        assert isinstance(obj, bool), f"Expected boolean, got {type(obj)}"
    elif schema.get("type") == "null":
        assert obj is None, f"Expected null, got {type(obj)}"
    # Не проверяем unknown type

def _try_type(obj, schema):
    try:
        _check_types_recursive(obj, schema)
        return True
    except AssertionError:
        return False





# =====================================================================================================================
# Фикстуры для валидных/текущих сертификатов и ключей
# =====================================================================================================================

@pytest.fixture(scope="function")
def valid_cert_and_key(tmp_path):
    """Скачивает и возвращает base64-строки валидного сертификата и ключа перед тестом."""
    import requests
    cert_url = f"http://{SERVICE['host']}:{PORT}{BASE_PATH}/certificates/ca/download/cert.crt"
    key_url = f"http://{SERVICE['host']}:{PORT}{BASE_PATH}/certificates/ca/download/cert.key"
    cert_path = tmp_path / "valid_cert.crt"
    key_path = tmp_path / "valid_cert.key"
    cert_b64_path = tmp_path / "valid_cert.b64"
    key_b64_path = tmp_path / "valid_cert.key.b64"
    with requests.get(cert_url, timeout=5) as r:
        r.raise_for_status()
        cert_path.write_bytes(r.content)
    with requests.get(key_url, timeout=5) as r:
        r.raise_for_status()
        key_path.write_bytes(r.content)
    cert_b64 = base64.b64encode(cert_path.read_bytes()).decode()
    key_b64 = base64.b64encode(key_path.read_bytes()).decode()
    return cert_b64, key_b64

@pytest.fixture(scope="function")
def restore_valid_cert_key(api_client, valid_cert_and_key):
    """Восстанавливает валидные ключи после теста."""
    cert_b64, key_b64 = valid_cert_and_key
    headers = {"Content-Type": "application/json"}
    payload = {"type": "tls", "cert": cert_b64, "key": key_b64}
    yield
    # Всегда восстанавливаем
    api_client.post(ENDPOINT, json=payload, headers=headers)

@pytest.fixture(scope="function")
def post_headers():
    return {"Content-Type": "application/json"}

# =====================================================================================================================
# Параметры для тестов (20+ осмысленных кейсов)
# =====================================================================================================================

from uuid import uuid4

@pytest.mark.parametrize("payload, expected_status, resp_schema, id", [
    # 1. Валидный сертификат и ключ
    pytest.param(lambda cert, key: {"type": "tls", "cert": cert, "key": key}, 200, "POST", "valid-cert-key"),
    # 2. Не совпадающие сертификат и ключ
    pytest.param(lambda cert, key: {"type": "tls", "cert": cert, "key": base64.b64encode(os.urandom(256)).decode()}, 404, "POST", "mismatched-key"),
    # 3. Некорректный base64
    pytest.param(lambda cert, key: {"type": "tls", "cert": "!!!notbase64!!!", "key": "!!!notbase64!!!"}, 404, "POST", "bad-base64"),
    # 4. Отсутствует ключ, cert содержит приватный ключ (валидный cert+key слитые)
    pytest.param(lambda cert, key: {"type": "tls", "cert": base64.b64encode(base64.b64decode(cert) + base64.b64decode(key)).decode()}, 200, "POST", "cert-with-key"),
    # 5. Отсутствует обязательное поле cert
    pytest.param(lambda cert, key: {"type": "tls", "key": key}, 404, "POST", "missing-cert"),
    # 6. Неизвестный type
    pytest.param(lambda cert, key: {"type": "unknown", "cert": cert, "key": key}, 200, "POST", "unknown-type"),
    # 7. Пустое тело
    pytest.param(lambda cert, key: {}, 404, "POST", "empty-body"),
    # 8. cert пустой
    pytest.param(lambda cert, key: {"type": "tls", "cert": "", "key": key}, 404, "POST", "empty-cert"),
    # 9. key пустой
    pytest.param(lambda cert, key: {"type": "tls", "cert": cert, "key": ""}, 404, "POST", "empty-key"),
    # 10. cert=None
    pytest.param(lambda cert, key: {"type": "tls", "cert": None, "key": key}, 400, "POST", "none-cert"),
    # 11. key=None
    pytest.param(lambda cert, key: {"type": "tls", "cert": cert, "key": None}, 400, "POST", "none-key"),
    # 12. type=None
    pytest.param(lambda cert, key: {"type": None, "cert": cert, "key": key}, 400, "POST", "none-type"),
    # 13. cert не строка
    pytest.param(lambda cert, key: {"type": "tls", "cert": 123, "key": key}, 400, "POST", "cert-not-str"),
    # 14. key не строка
    pytest.param(lambda cert, key: {"type": "tls", "cert": cert, "key": 123}, 400, "POST", "key-not-str"),
    # 15. type не строка
    pytest.param(lambda cert, key: {"type": 123, "cert": cert, "key": key}, 400, "POST", "type-not-str"),
    # 16. cert слишком длинный
    pytest.param(lambda cert, key: {"type": "tls", "cert": "a"*10000, "key": key}, 404, "POST", "cert-too-long"),
    # 17. key слишком длинный
    pytest.param(lambda cert, key: {"type": "tls", "cert": cert, "key": "a"*10000}, 404, "POST", "key-too-long"),
    # 18. type пустой
    pytest.param(lambda cert, key: {"type": "", "cert": cert, "key": key}, 200, "POST", "empty-type"),
    # 19. Все поля пустые строки
    pytest.param(lambda cert, key: {"type": "", "cert": "", "key": ""}, 404, "POST", "all-empty"),
    # 20. Все поля None
    pytest.param(lambda cert, key: {"type": None, "cert": None, "key": None}, 400, "POST", "all-none"),
    # 21. Неожиданный тип поля cert (list)
    pytest.param(lambda cert, key: {"type": "tls", "cert": [cert], "key": key}, 400, "POST", "cert-list"),
    # 22. Неожиданный тип поля key (list)
    pytest.param(lambda cert, key: {"type": "tls", "cert": cert, "key": [key]}, 400, "POST", "key-list"),
    # 23. Неожиданный тип поля type (list)
    pytest.param(lambda cert, key: {"type": ["tls"], "cert": cert, "key": key}, 400, "POST", "type-list"),
    # 24. cert и key перепутаны местами
    pytest.param(lambda cert, key: {"type": "tls", "cert": key, "key": cert}, 404, "POST", "swapped-cert-key"),
])
def test_certificates_certs_set(api_client, payload, expected_status, resp_schema, id, valid_cert_and_key, post_headers, restore_valid_cert_key, attach_curl_on_fail, agent_verification):
    cert, key = valid_cert_and_key
    # Формируем тело
    body = payload(cert, key)
    
    with attach_curl_on_fail(ENDPOINT, body, post_headers):
        response = api_client.post(ENDPOINT, json=body, headers=post_headers)
        assert response.status_code == expected_status, f"Expected status {expected_status}, got {response.status_code}"
        data = response.json()
        # Проверка схемы
        _check_types_recursive(data, response_schemas[resp_schema])
        # Дополнительные проверки по статусу
        if expected_status == 200:
            assert data.get("result") == "OK", f"Expected result OK, got {data}"
            
            # Дополнительная проверка через агента только для успешных случаев (статус 200)
            print(f"Checking agent verification for successful test: {id}")
            agent_result = agent_verification("/certificates/certs/set", body)
            if agent_result == "unavailable":
                print(f"Agent verification skipped - agent is unavailable for test: {id}")
            elif isinstance(agent_result, dict) and agent_result.get("result") == "OK":  # Проверка выполнилась успешно
                print(f"Agent verification: Certificate was successfully set for test: {id}")
            elif isinstance(agent_result, dict) and agent_result.get("result") == "ERROR":  # Проверка выполнилась, но неуспешно
                message = agent_result.get("message", "Неизвестная ошибка")
                raise AssertionError(f"Agent verification failed: {message} for test: {id}")
            else:
                raise AssertionError(f"Agent verification returned unexpected result: {agent_result} for test: {id}")
        elif expected_status == 404:
            assert "error" in data, f"Expected error in response, got {data}"
            assert "statusCode" in data["error"], f"Expected statusCode in error, got {data}"
        elif expected_status == 400:
            # Для других ошибок просто проверяем схему
            pass 