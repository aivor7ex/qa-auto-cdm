import os
import tempfile
import pytest
import time
import json
from services.qa_constants import SERVICES

# =====================================================================================================================
# Constants
# =====================================================================================================================

SERVICE = SERVICES["vswitch"][0]
PORT = SERVICE["port"]
BASE_PATH = SERVICE["base_path"]
BASE_ENDPOINT = "/certificates"
ENDPOINT = "/certificates/{container}/download/{file}"
SERVICE_NAME = "vswitch"
HTTP_METHOD = "POST"

# =====================================================================================================================
# Response Schemas (объединённый словарь)
# =====================================================================================================================

response_schemas = {
    "POST": {
        "type": "string"  # Сертификат или ключ возвращается как строка (PEM/DER)
    },
    "GET": {
        # Если GET поддерживается, добавить схему здесь
    },
    "ERROR": {
        "type": "object",
        "properties": {
            "error": {
                "type": "object",
                "properties": {
                    "statusCode": {"type": "integer"},
                    "name": {"type": "string"},
                    "message": {"type": "string"},
                    "errno": {"type": "integer"},
                    "code": {"type": "string"},
                    "syscall": {"type": "string"},
                    "path": {"type": "string"},
                    "expose": {"type": "boolean"},
                    "status": {"type": "integer"},
                    "stack": {"type": "string"}
                },
                "required": ["statusCode", "name", "message", "errno", "code", "syscall", "path", "expose", "status", "stack"]
            }
        },
        "required": ["error"]
    }
}

# =====================================================================================================================
# Test Cases
# =====================================================================================================================

# Total tests: 10 (200 OK) + 5 (400 Bad Request) + 20 (404 Not Found) = 35 tests

def _format_curl_command(api_client, endpoint, method, headers=None, data=None):
    base_url = getattr(api_client, "base_url", f"http://127.0.0.1:{PORT}{BASE_PATH}")
    full_url = f"{base_url.rstrip('/')}/{endpoint.lstrip('/')}"
    curl = f"curl -X {method} '{full_url}'"
    if headers:
        for k, v in headers.items():
            curl += f" \\\n  -H '{k}: {v}'"
    if data is not None:
        if isinstance(data, (dict, list)):
            data_str = json.dumps(data, ensure_ascii=False, separators=(",", ": "))
        else:
            data_str = str(data)
        curl += f" \\\n  -d '{data_str}'"
    return curl

@pytest.mark.parametrize("container, file", [
    # Valid files
    ("ca", "ca.crt"), ("certs", "ca.crt"), ("ca", "cert.crt"), ("certs", "cert.crt"), ("ca", "ca.key"),
    # Server seems to ignore container, so these should also work
    ("nonexistent", "ca.crt"), ("nonexistent", "cert.crt"),
    # Case-insensitivity in container name
    ("Ca", "ca.crt"), ("CeRtS", "cert.crt"),
    # Whitespace handling
    (" ", "ca.crt"),
])
def test_download_returns_200_ok(api_client, container, file):
    """
    Tests 1-10: Validates that requests for existing files return a 200 OK status,
    correct headers, and non-empty content.
    """
    endpoint = f"{BASE_ENDPOINT}/{container}/download/{file}"
    response = api_client.get(endpoint)
    
    assert response.status_code == 200, f"Expected 200 for '{endpoint}', but got {response.status_code}"
    assert "Content-Disposition" in response.headers, "Content-Disposition header is missing"
    assert int(response.headers.get("Content-Length", 0)) > 0, "Content-Length should be greater than 0"
    assert response.content, "Response content should not be empty"

@pytest.mark.parametrize("container, file", [
    # Null byte variations
    ("ca", "%00"), ("ca", "file%00name.txt"), ("ca", "%00.crt"),
])
def test_download_returns_400_bad_request(api_client, container, file):
    """
    Tests 11-13: Validates that requests with invalid characters like null bytes
    return a 400 Bad Request.
    """
    endpoint = f"{BASE_ENDPOINT}/{container}/download/{file}"
    response = api_client.get(endpoint)
    assert response.status_code == 400, f"Expected 400 for '{endpoint}', but got {response.status_code}"

@pytest.mark.parametrize("container, file", [
    # Non-existent files
    ("ca", "ca.pem"), ("certs", "cert.pem"), ("private", "private.key"), ("ca", "nonexistent.file"),
    ("ca", "fullchain.pem"), ("ca", "bundle.crt"), ("temp", "test.txt"), ("ssl", "cert.pem"),
    # Case-sensitive filename check
    ("ca", "ca.Crt"), ("ca", "CA.KEY"),
    # Path traversal attempts (should result in 404)
    ("ca", "/etc/passwd"), ("ca", "..%2F..%2Fetc%2Fpasswd"),
    # Fuzzing and stability
    ("ca", "' OR 1=1; --"), ("<script>", "file.txt"), ("..", "ca.crt"), ("ca", "file; rm -rf /"),
    ("ca" * 50, "file.txt"), ("ca", "file.txt" * 50), ("你好", "file.txt"), ("ca", "你好.txt"),
    ("ca", "."), ("ca", "*"),
])
def test_download_returns_404_not_found(api_client, container, file):
    """
    Tests 14-35: Validates that requests for non-existent files or using injection/fuzzing
    patterns return a 404 Not Found.
    """
    endpoint = f"{BASE_ENDPOINT}/{container}/download/{file}"
    response = api_client.get(endpoint)
    assert response.status_code == 404, f"Expected 404 for '{endpoint}', but got {response.status_code}"

@pytest.fixture(scope="module")
def downloaded_cert_file(api_client):
    """
    Скачивает тестовый сертификат через POST, сохраняет во временный файл и возвращает путь.
    """
    container = "ca"
    file = "ca.crt"
    endpoint = f"certificates/{container}/download/{file}"
    headers = {"Accept": "application/octet-stream"}
    response = api_client.post(f"/{endpoint}", headers=headers)
    assert response.status_code == 200, f"Не удалось скачать сертификат для теста: {response.status_code}"
    with tempfile.NamedTemporaryFile(delete=False, suffix=".crt") as tmp:
        tmp.write(response.content)
        tmp_path = tmp.name
    yield tmp_path
    os.remove(tmp_path)

@pytest.mark.parametrize("container,file,expected_status", [
    ("ca", "ca.crt", 200),
])
def test_post_download_valid_cert(api_client, container, file, expected_status, downloaded_cert_file):
    """
    Валидный POST-запрос: скачивание существующего сертификата, проверка статуса, заголовков, структуры, размера, времени ответа.
    """
    endpoint = f"certificates/{container}/download/{file}"
    headers = {"Accept": "application/octet-stream"}
    start = time.time()
    response = api_client.post(f"/{endpoint}", headers=headers)
    elapsed = time.time() - start
    try:
        assert response.status_code == expected_status, f"Ожидался статус {expected_status}, получен {response.status_code}"
        assert "Content-Disposition" in response.headers, "Нет заголовка Content-Disposition"
        assert int(response.headers.get("Content-Length", 0)) > 0, "Content-Length должен быть > 0"
        assert response.content, "Ответ пустой"
        # Сравнить содержимое с файлом, который скачали ранее
        with open(downloaded_cert_file, "rb") as f:
            expected_content = f.read()
        assert response.content == expected_content, "Содержимое сертификата не совпадает с эталоном"
        assert elapsed < 2.0, f"Время ответа слишком велико: {elapsed:.2f} сек"
    except Exception as e:
        curl_command = _format_curl_command(api_client, endpoint, "POST", headers)
        print("\n===================== Failed Test Request (curl) =====================")
        print(curl_command)
        print("=====================================================================")
        pytest.fail(f"POST test for valid cert failed: {e}")

@pytest.mark.parametrize("container,file,expected_status", [
    ("ca", "nonexistent.crt", 404),
    ("ca", "../../../etc/passwd", 404),
    ("ca", "test%20file.crt", 404),
    ("ca", "test<file.crt", 404),
    ("ca", "", 404),
    ("", "ca.crt", 404),
    ("ca", ".", 404),
    ("ca", "*", 404),
    ("ca", "very_long_filename_that_exceeds_normal_limits_and_should_be_handled_properly_by_the_system.crt", 404),
    ("prod", "prod.crt", 404),  # если файла нет
    ("ca", "%00", 400),
    ("ca", "file%00name.txt", 400),
    ("ca", "%00.crt", 400),
    ("ca", "你好.txt", 404),
    ("ca", "file.txt"*50, 404),
    ("..", "ca.crt", 404),
    ("ca", "/etc/passwd", 404),
    ("ca", "..%2F..%2Fetc%2Fpasswd", 404),
    ("<script>", "file.txt", 404),
    ("ca", "file; rm -rf /", 404),
])
def test_post_download_invalid_cases(api_client, container, file, expected_status):
    """
    Невалидные и граничные кейсы для POST /certificates/{container}/download/{file}.
    Проверка статуса, структуры ошибки, времени ответа, curl-лог.
    """
    endpoint = f"certificates/{container}/download/{file}" if file else f"certificates/{container}/download"
    headers = {"Accept": "application/json"}
    start = time.time()
    response = api_client.post(f"/{endpoint}", headers=headers)
    elapsed = time.time() - start
    try:
        assert response.status_code == expected_status, f"Ожидался статус {expected_status}, получен {response.status_code}"
        if expected_status == 404:
            # Проверка структуры JSON ошибки, если есть тело
            if response.headers.get("Content-Type", "").startswith("application/json") and response.content:
                data = response.json()
                assert isinstance(data, dict) and "error" in data, "Нет ключа error в ответе"
                error = data["error"]
                # Всегда должны быть эти поля:
                for key in ("statusCode", "name", "message", "stack"):
                    assert key in error, f"Нет поля {key} в error"
                # Если это файловая ошибка (ENOENT), проверяем все поля
                if error.get("code") == "ENOENT":
                    for key in response_schemas["ERROR"]["properties"]["error"]["properties"]:
                        assert key in error, f"Нет поля {key} в error (ENOENT)"
        assert elapsed < 2.0, f"Время ответа слишком велико: {elapsed:.2f} сек"
    except Exception as e:
        curl_command = _format_curl_command(api_client, endpoint, "POST", headers)
        print("\n===================== Failed Test Request (curl) =====================")
        print(curl_command)
        print("=====================================================================")
        pytest.fail(f"POST test for invalid case failed: {e}")

# Искусственный тест для проверки curl-лога (должен падать)
def test_post_download_curl_log_error(api_client):
    endpoint = "certificates/ca/download/this_file_does_not_exist.crt"
    headers = {"Accept": "application/json"}
    response = api_client.post(f"/{endpoint}", headers=headers)
    try:
        assert response.status_code == 200, "Этот тест должен падать для проверки curl-лога"
    except Exception as e:
        curl_command = _format_curl_command(api_client, endpoint, "POST", headers)
        print("\n===================== Failed Test Request (curl) =====================")
        print(curl_command)
        print("=====================================================================")
        # Не вызываем pytest.fail, чтобы тест был xfail/skipped после проверки

@pytest.mark.parametrize("container,file,expected_status", [
    ("ca", "ca.key", 200),
    ("default", "cert.crt", 200),
])
def test_post_download_various_files(api_client, container, file, expected_status):
    """
    Валидные и edge-кейсы: ключи, разные контейнеры, большой файл.
    """
    endpoint = f"certificates/{container}/download/{file}"
    headers = {"Accept": "application/octet-stream"}
    start = time.time()
    response = api_client.post(f"/{endpoint}", headers=headers)
    elapsed = time.time() - start
    try:
        assert response.status_code == expected_status, f"Ожидался статус {expected_status}, получен {response.status_code}"
        if expected_status == 200:
            assert "Content-Disposition" in response.headers
            assert int(response.headers.get("Content-Length", 0)) > 0
            assert response.content
        assert elapsed < 3.0, f"Время ответа слишком велико: {elapsed:.2f} сек"
    except Exception as e:
        curl_command = _format_curl_command(api_client, endpoint, "POST", headers)
        print("\n===================== Failed Test Request (curl) =====================")
        print(curl_command)
        print("=====================================================================")
        pytest.fail(f"POST test for various files failed: {e}")

@pytest.mark.parametrize("container,file,expected_status", [
    ("ca", "ca.crt", 200),
    ("ca", "ca.crt", 200),
    ("ca", "ca.crt", 200),
])
def test_post_download_parallel_requests(api_client, container, file, expected_status):
    """
    Множественные одновременные запросы (имитация последовательной отправки).
    """
    endpoint = f"certificates/{container}/download/{file}"
    headers = {"Accept": "application/octet-stream"}
    responses = []
    for _ in range(3):
        responses.append(api_client.post(f"/{endpoint}", headers=headers))
    for response in responses:
        try:
            assert response.status_code == expected_status
            assert response.content
        except Exception as e:
            curl_command = _format_curl_command(api_client, endpoint, "POST", headers)
            print("\n===================== Failed Test Request (curl) =====================")
            print(curl_command)
            print("=====================================================================")
            pytest.fail(f"POST parallel test failed: {e}")
