# file: /services/csi-server/service_integrity.py
import json
import pytest
from qa_constants import SERVICES

ENDPOINT = "/service/integrity"

# ----- СХЕМА ОТВЕТА (получена из API_EXAMPLE_RESPONSE_200_OK) -----
IMAGE_ITEM_SCHEMA = {
    "status": {"type": "string", "required": True},
    # Поле 'original' может отсутствовать для некоторых статусов (modified/new)
    "original": {"type": "string", "required": False},
    # В ряде окружений поле 'actual' может отсутствовать
    "actual": {"type": "string", "required": False}
}

FILE_ITEM_SCHEMA = {
    "status": {"type": "string", "required": True},
    # Поле 'original' может отсутствовать для некоторых статусов (modified/new)
    "original": {"type": "string", "required": False},
    # В ряде окружений поле 'actual' может отсутствовать
    "actual": {"type": "string", "required": False}
}

RESPONSE_SCHEMA = {
    "images": {"type": "object", "required": True, "properties": IMAGE_ITEM_SCHEMA},
    "files": {"type": "object", "required": True, "properties": FILE_ITEM_SCHEMA}
}

# ----- ФИКСТУРЫ (в проекте уже существуют) -----
# api_client(base_url), auth_token() — ИСПОЛЬЗОВАТЬ, НЕ МЕНЯТЬ.

def _url(base_path: str) -> str:
    return f"{base_path}{ENDPOINT}"

def _check_type(name, value, spec):
    t = spec.get("type")
    if t == "string":
        assert isinstance(value, str), f"{name}: ожидается string; curl: curl --location 'http://127.0.0.1:2999/api/service/integrity' --header 'x-access-token: 9wO53O0bTModkbS3Vhc50kOR2bXafRHg3IA2CBcIt84j'"
    elif t == "number":
        assert isinstance(value, (int, float)) and not isinstance(value, bool), f"{name}: ожидается number; curl: curl --location 'http://127.0.0.1:2999/api/service/integrity' --header 'x-access-token: 9wO53O0bTModkbS3Vhc50kOR2bXafRHg3IA2CBcIt84j'"
    elif t == "boolean":
        assert isinstance(value, bool), f"{name}: ожидается boolean; curl: curl --location 'http://127.0.0.1:2999/api/service/integrity' --header 'x-access-token: 9wO53O0bTModkbS3Vhc50kOR2bXafRHg3IA2CBcIt84j'"
    elif t == "object":
        assert isinstance(value, dict), f"{name}: ожидается object; curl: curl --location 'http://127.0.0.1:2999/api/service/integrity' --header 'x-access-token: 9wO53O0bTModkbS3Vhc50kOR2bXafRHg3IA2CBcIt84j'"
        _validate_object(value, spec.get("properties", {}), name)
    elif t == "list":
        assert isinstance(value, list), f"{name}: ожидается list; curl: curl --location 'http://127.0.0.1:2999/api/service/integrity' --header 'x-access-token: 9wO53O0bTModkbS3Vhc50kOR2bXafRHg3IA2CBcIt84j'"
        item_spec = spec.get("item_type")
        if item_spec:
            for i, v in enumerate(value):
                _check_type(f"{name}[{i}]", v, item_spec)
    else:
        assert False, f"{name}: неизвестный тип '{t}'; curl: curl --location 'http://127.0.0.1:2999/api/service/integrity' --header 'x-access-token: 9wO53O0bTModkbS3Vhc50kOR2bXafRHg3IA2CBcIt84j'"

def _validate_object(obj, properties: dict, prefix: str = "root"):
    for key, prop in properties.items():
        required = prop.get("required", False)
        if required:
            assert key in obj, f"{prefix}.{key}: обязательное поле; curl: curl --location 'http://127.0.0.1:2999/api/service/integrity' --header 'x-access-token: 9wO53O0bTModkbS3Vhc50kOR2bXafRHg3IA2CBcIt84j'"
        if key in obj:
            _check_type(f"{prefix}.{key}", obj[key], prop)

def _validate_integrity_response(data):
    """Валидирует структуру ответа с проверкой целостности"""
    assert isinstance(data, dict), f"Корень: ожидается object; curl: curl --location 'http://127.0.0.1:2999/api/service/integrity' --header 'x-access-token: 9wO53O0bTModkbS3Vhc50kOR2bXafRHg3IA2CBcIt84j'"
    
    # Проверяем обязательные поля
    assert "images" in data, "Отсутствует поле 'images'; curl: curl --location 'http://127.0.0.1:2999/api/service/integrity' --header 'x-access-token: 9wO53O0bTModkbS3Vhc50kOR2bXafRHg3IA2CBcIt84j'"
    assert "files" in data, "Отсутствует поле 'files'; curl: curl --location 'http://127.0.0.1:2999/api/service/integrity' --header 'x-access-token: 9wO53O0bTModkbS3Vhc50kOR2bXafRHg3IA2CBcIt84j'"
    
    # Проверяем структуру images
    images = data["images"]
    assert isinstance(images, dict), "Поле 'images' должно быть объектом; curl: curl --location 'http://127.0.0.1:2999/api/service/integrity' --header 'x-access-token: 9wO53O0bTModkbS3Vhc50kOR2bXafRHg3IA2CBcIt84j'"
    
    for image_key, image_data in images.items():
        assert isinstance(image_key, str), f"Ключ образа должен быть строкой; curl: curl --location 'http://127.0.0.1:2999/api/service/integrity' --header 'x-access-token: 9wO53O0bTModkbS3Vhc50kOR2bXafRHg3IA2CBcIt84j'"
        _validate_object(image_data, IMAGE_ITEM_SCHEMA, f"images.{image_key}")
    
    # Проверяем структуру files
    files = data["files"]
    assert isinstance(files, dict), "Поле 'files' должно быть объектом; curl: curl --location 'http://127.0.0.1:2999/api/service/integrity' --header 'x-access-token: 9wO53O0bTModkbS3Vhc50kOR2bXafRHg3IA2CBcIt84j'"
    
    for file_key, file_data in files.items():
        assert isinstance(file_key, str), f"Ключ файла должен быть строкой; curl: curl --location 'http://127.0.0.1:2999/api/service/integrity' --header 'x-access-token: 9wO53O0bTModkbS3Vhc50kOR2bXafRHg3IA2CBcIt84j'"
        _validate_object(file_data, FILE_ITEM_SCHEMA, f"files.{file_key}")

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
    curl_command = f"curl --location '{full_url}'"
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
    {"q": {"offset": 1}, "desc": "смещение 1"},
    {"q": {"page": 1}, "desc": "первая страница"},
    {"q": {"page": 2}, "desc": "вторая страница"},
    {"q": {"sort": "name"}, "desc": "сортировка по имени"},
    {"q": {"sort": "asc"}, "desc": "сортировка по возрастанию"},
    {"q": {"sort": "desc"}, "desc": "сортировка по убыванию"},
    {"q": {"filter": "csi"}, "desc": "фильтр по csi"},
    {"q": {"filter": "ngfw"}, "desc": "фильтр по ngfw"},
    {"q": {"filter": "vpp"}, "desc": "фильтр по vpp"},
    {"q": {"filter": "squid"}, "desc": "фильтр по squid"},
    {"q": {"filter": "snmp"}, "desc": "фильтр по snmp"},
    {"q": {"filter": "logger"}, "desc": "фильтр по logger"},
    {"q": {"filter": "shared"}, "desc": "фильтр по shared"},
    {"q": {"filter": "tls-bridge"}, "desc": "фильтр по tls-bridge"}
]

@pytest.mark.parametrize("case", BASE_PARAMS, ids=lambda c: c["desc"])
def test_get_integrity_schema_conforms(api_client, auth_token, case):
    """Тест соответствия схеме ответа с различными параметрами"""
    base = f"http://127.0.0.1:{SERVICES['csi-server']['port']}{SERVICES['csi-server']['base_path']}"
    url = _url(base)
    params = case.get("q") or {}
    headers = {"x-access-token": auth_token}
    
    r = api_client.get(url, headers=headers, params=params)
    assert r.status_code == 200, f"Ожидается 200 OK; получено {r.status_code}; curl: {_format_curl_command(api_client, ENDPOINT, params, headers)}"
    
    data = r.json()
    _validate_integrity_response(data)

def test_get_integrity_basic_structure(api_client, auth_token):
    """Тест базовой структуры ответа"""
    base = f"http://127.0.0.1:{SERVICES['csi-server']['port']}{SERVICES['csi-server']['base_path']}"
    url = _url(base)
    headers = {"x-access-token": auth_token}
    
    r = api_client.get(url, headers=headers)
    assert r.status_code == 200, f"Ожидается 200 OK; получено {r.status_code}; curl: {_format_curl_command(api_client, ENDPOINT, {}, headers)}"
    
    data = r.json()
    _validate_integrity_response(data)
    
    # Проверяем, что поля не пустые
    assert len(data["images"]) > 0, "Поле 'images' не должно быть пустым"
    assert len(data["files"]) > 0, "Поле 'files' не должно быть пустым"

def test_get_integrity_image_structure(api_client, auth_token):
    """Тест структуры образов Docker"""
    base = f"http://127.0.0.1:{SERVICES['csi-server']['port']}{SERVICES['csi-server']['base_path']}"
    url = _url(base)
    headers = {"x-access-token": auth_token}
    
    r = api_client.get(url, headers=headers)
    assert r.status_code == 200, f"Ожидается 200 OK; получено {r.status_code}; curl: {_format_curl_command(api_client, ENDPOINT, {}, headers)}"
    
    data = r.json()
    _validate_integrity_response(data)
    
    # Проверяем структуру первого образа
    first_image_key = next(iter(data["images"]))
    first_image = data["images"][first_image_key]
    
    assert "status" in first_image, "Поле 'status' должно присутствовать в образе"
    # Поля original/actual могут отсутствовать в некоторых окружениях — проверяем только если присутствуют
    assert isinstance(first_image["status"], str), "Поле 'status' должно быть строкой"
    if "original" in first_image and first_image["original"] is not None:
        assert isinstance(first_image["original"], str), "Поле 'original' должно быть строкой"
    if "actual" in first_image and first_image["actual"] is not None:
        assert isinstance(first_image["actual"], str), "Поле 'actual' должно быть строкой"

def test_get_integrity_file_structure(api_client, auth_token):
    """Тест структуры файлов"""
    base = f"http://127.0.0.1:{SERVICES['csi-server']['port']}{SERVICES['csi-server']['base_path']}"
    url = _url(base)
    headers = {"x-access-token": auth_token}
    
    r = api_client.get(url, headers=headers)
    assert r.status_code == 200, f"Ожидается 200 OK; получено {r.status_code}; curl: {_format_curl_command(api_client, ENDPOINT, {}, headers)}"
    
    data = r.json()
    _validate_integrity_response(data)
    
    # Проверяем структуру первого файла
    first_file_key = next(iter(data["files"]))
    first_file = data["files"][first_file_key]
    
    assert "status" in first_file, "Поле 'status' должно присутствовать в файле"
    # Поля original/actual могут отсутствовать — проверяем только если присутствуют
    assert isinstance(first_file["status"], str), "Поле 'status' должно быть строкой"
    if "original" in first_file and first_file["original"] is not None:
        assert isinstance(first_file["original"], str), "Поле 'original' должно быть строкой"
    if "actual" in first_file and first_file["actual"] is not None:
        assert isinstance(first_file["actual"], str), "Поле 'actual' должно быть строкой"

def test_get_integrity_hash_format(api_client, auth_token):
    """Тест формата хэшей"""
    base = f"http://127.0.0.1:{SERVICES['csi-server']['port']}{SERVICES['csi-server']['base_path']}"
    url = _url(base)
    headers = {"x-access-token": auth_token, "token": auth_token}

    try:
        r = api_client.get(url, headers=headers)
        assert r.status_code == 200, (
            f"Ожидается 200 OK; получено {r.status_code}; curl: {_format_curl_command(api_client, ENDPOINT, {}, headers)}"
        )

        data = r.json()
        _validate_integrity_response(data)

        # Проверяем формат хэшей (64 символа hex), если поля присутствуют
        for image_key, image_data in data["images"].items():
            if "actual" in image_data and image_data["actual"] is not None:
                assert len(image_data["actual"]) == 64, (
                    f"Хэш 'actual' образа {image_key} должен быть длиной 64 символа"
                )
                assert all(c in "0123456789abcdef" for c in image_data["actual"]), (
                    f"Хэш 'actual' образа {image_key} должен содержать только hex символы"
                )
            # 'original' может отсутствовать (например, при статусе modified/new)
            if "original" in image_data and image_data["original"] is not None:
                assert len(image_data["original"]) == 64, (
                    f"Хэш 'original' образа {image_key} должен быть длиной 64 символа"
                )
                assert all(c in "0123456789abcdef" for c in image_data["original"]), (
                    f"Хэш 'original' образа {image_key} должен содержать только hex символы"
                )

        for file_key, file_data in data["files"].items():
            if "actual" in file_data and file_data["actual"] is not None:
                assert len(file_data["actual"]) == 64, (
                    f"Хэш 'actual' файла {file_key} должен быть длиной 64 символа"
                )
                assert all(c in "0123456789abcdef" for c in file_data["actual"]), (
                    f"Хэш 'actual' файла {file_key} должен содержать только hex символы"
                )
            if "original" in file_data and file_data["original"] is not None:
                assert len(file_data["original"]) == 64, (
                    f"Хэш 'original' файла {file_key} должен быть длиной 64 символа"
                )
                assert all(c in "0123456789abcdef" for c in file_data["original"]), (
                    f"Хэш 'original' файла {file_key} должен содержать только hex символы"
                )
    except (AssertionError, Exception) as e:
        curl_command = _format_curl_command(api_client, ENDPOINT, {}, headers)
        pytest.fail(
            "\nТест 'формата хэшей' упал.\n"
            f"Ошибка: {e}\n\n"
            "================= Failed Test Request (cURL) ================\n"
            f"{curl_command}\n"
            "============================================================="
        , pytrace=False)

def test_get_integrity_status_values(api_client, auth_token):
    """Тест значений поля status"""
    base = f"http://127.0.0.1:{SERVICES['csi-server']['port']}{SERVICES['csi-server']['base_path']}"
    url = _url(base)
    headers = {"x-access-token": auth_token}
    
    r = api_client.get(url, headers=headers)
    assert r.status_code == 200, f"Ожидается 200 OK; получено {r.status_code}; curl: {_format_curl_command(api_client, ENDPOINT, {}, headers)}"
    
    data = r.json()
    _validate_integrity_response(data)
    
    # Проверяем, что все статусы имеют валидное значение
    valid_statuses = {"original", "modified", "missing", "new"}
    
    for image_key, image_data in data["images"].items():
        assert image_data["status"] in valid_statuses, f"Невалидный статус образа {image_key}: {image_data['status']}"
    
    for file_key, file_data in data["files"].items():
        assert file_data["status"] in valid_statuses, f"Невалидный статус файла {file_key}: {file_data['status']}"

def test_get_integrity_image_names_format(api_client, auth_token):
    """Тест формата имен образов Docker"""
    base = f"http://127.0.0.1:{SERVICES['csi-server']['port']}{SERVICES['csi-server']['base_path']}"
    url = _url(base)
    headers = {"x-access-token": auth_token}
    
    r = api_client.get(url, headers=headers)
    assert r.status_code == 200, f"Ожидается 200 OK; получено {r.status_code}; curl: {_format_curl_command(api_client, ENDPOINT, {}, headers)}"
    
    data = r.json()
    _validate_integrity_response(data)
    
    # Проверяем формат имен образов (должны содержать двоеточие для версии)
    for image_key in data["images"].keys():
        assert ":" in image_key, f"Имя образа должно содержать двоеточие: {image_key}"
        assert "/" in image_key, f"Имя образа должно содержать слеш: {image_key}"

def test_get_integrity_file_paths_format(api_client, auth_token):
    """Тест формата путей файлов"""
    base = f"http://127.0.0.1:{SERVICES['csi-server']['port']}{SERVICES['csi-server']['base_path']}"
    url = _url(base)
    headers = {"x-access-token": auth_token}
    
    r = api_client.get(url, headers=headers)
    assert r.status_code == 200, f"Ожидается 200 OK; получено {r.status_code}; curl: {_format_curl_command(api_client, ENDPOINT, {}, headers)}"
    
    data = r.json()
    _validate_integrity_response(data)
    
    # Проверяем формат путей файлов (должны начинаться с /)
    for file_key in data["files"].keys():
        assert file_key.startswith("/"), f"Путь файла должен начинаться с /: {file_key}"

def test_get_integrity_hash_consistency(api_client, auth_token):
    """Тест консистентности хэшей"""
    base = f"http://127.0.0.1:{SERVICES['csi-server']['port']}{SERVICES['csi-server']['base_path']}"
    url = _url(base)
    headers = {"x-access-token": auth_token, "token": auth_token}

    try:
        r = api_client.get(url, headers=headers)
        assert r.status_code == 200, (
            f"Ожидается 200 OK; получено {r.status_code}; curl: {_format_curl_command(api_client, ENDPOINT, {}, headers)}"
        )

        data = r.json()
        _validate_integrity_response(data)

        # Проверяем, что хэши не пустые и не null (если присутствуют)
        for image_key, image_data in data["images"].items():
            if "actual" in image_data:
                assert image_data.get("actual") not in (None, ""), f"Хэш 'actual' образа {image_key} не должен быть пустым или null"
            if "original" in image_data and image_data["original"] is not None:
                assert image_data["original"] != "", f"Хэш 'original' образа {image_key} не должен быть пустым"

        for file_key, file_data in data["files"].items():
            if "actual" in file_data:
                assert file_data.get("actual") not in (None, ""), f"Хэш 'actual' файла {file_key} не должен быть пустым или null"
            if "original" in file_data and file_data["original"] is not None:
                assert file_data["original"] != "", f"Хэш 'original' файла {file_key} не должен быть пустым"
    except (AssertionError, Exception) as e:
        curl_command = _format_curl_command(api_client, ENDPOINT, {}, headers)
        pytest.fail(
            "\nТест 'консистентности хэшей' упал.\n"
            f"Ошибка: {e}\n\n"
            "================= Failed Test Request (cURL) ================\n"
            f"{curl_command}\n"
            "============================================================="
        , pytrace=False)

def test_get_integrity_response_consistency(api_client, auth_token):
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
    
    _validate_integrity_response(data1)
    _validate_integrity_response(data2)
    
    # Проверяем, что количество образов и файлов одинаково
    assert len(data1["images"]) == len(data2["images"]), "Количество образов должно быть одинаковым в последовательных запросах"
    assert len(data1["files"]) == len(data2["files"]), "Количество файлов должно быть одинаковым в последовательных запросах"

def test_get_integrity_with_limit_param(api_client, auth_token):
    """Тест с параметром limit"""
    base = f"http://127.0.0.1:{SERVICES['csi-server']['port']}{SERVICES['csi-server']['base_path']}"
    url = _url(base)
    params = {"limit": "10"}
    headers = {"x-access-token": auth_token}
    
    r = api_client.get(url, headers=headers, params=params)
    assert r.status_code == 200, f"Ожидается 200 OK; получено {r.status_code}; curl: {_format_curl_command(api_client, ENDPOINT, params, headers)}"
    
    data = r.json()
    _validate_integrity_response(data)

def test_get_integrity_with_offset_param(api_client, auth_token):
    """Тест с параметром offset"""
    base = f"http://127.0.0.1:{SERVICES['csi-server']['port']}{SERVICES['csi-server']['base_path']}"
    url = _url(base)
    params = {"offset": "5"}
    headers = {"x-access-token": auth_token}
    
    r = api_client.get(url, headers=headers, params=params)
    assert r.status_code == 200, f"Ожидается 200 OK; получено {r.status_code}; curl: {_format_curl_command(api_client, ENDPOINT, params, headers)}"
    
    data = r.json()
    _validate_integrity_response(data)

def test_get_integrity_with_page_param(api_client, auth_token):
    """Тест с параметром page"""
    base = f"http://127.0.0.1:{SERVICES['csi-server']['port']}{SERVICES['csi-server']['base_path']}"
    url = _url(base)
    params = {"page": "1"}
    headers = {"x-access-token": auth_token}
    
    r = api_client.get(url, headers=headers, params=params)
    assert r.status_code == 200, f"Ожидается 200 OK; получено {r.status_code}; curl: {_format_curl_command(api_client, ENDPOINT, params, headers)}"
    
    data = r.json()
    _validate_integrity_response(data)

def test_get_integrity_with_sort_param(api_client, auth_token):
    """Тест с параметром sort"""
    base = f"http://127.0.0.1:{SERVICES['csi-server']['port']}{SERVICES['csi-server']['base_path']}"
    url = _url(base)
    params = {"sort": "name"}
    headers = {"x-access-token": auth_token}
    
    r = api_client.get(url, headers=headers, params=params)
    assert r.status_code == 200, f"Ожидается 200 OK; получено {r.status_code}; curl: {_format_curl_command(api_client, ENDPOINT, params, headers)}"
    
    data = r.json()
    _validate_integrity_response(data)

def test_get_integrity_with_filter_param(api_client, auth_token):
    """Тест с параметром filter"""
    base = f"http://127.0.0.1:{SERVICES['csi-server']['port']}{SERVICES['csi-server']['base_path']}"
    url = _url(base)
    params = {"filter": "csi"}
    headers = {"x-access-token": auth_token}
    
    r = api_client.get(url, headers=headers, params=params)
    assert r.status_code == 200, f"Ожидается 200 OK; получено {r.status_code}; curl: {_format_curl_command(api_client, ENDPOINT, params, headers)}"
    
    data = r.json()
    _validate_integrity_response(data)

def test_get_integrity_with_multiple_params(api_client, auth_token):
    """Тест с несколькими параметрами одновременно"""
    base = f"http://127.0.0.1:{SERVICES['csi-server']['port']}{SERVICES['csi-server']['base_path']}"
    url = _url(base)
    params = {"limit": "5", "offset": "0", "sort": "name"}
    headers = {"x-access-token": auth_token}
    
    r = api_client.get(url, headers=headers, params=params)
    assert r.status_code == 200, f"Ожидается 200 OK; получено {r.status_code}; curl: {_format_curl_command(api_client, ENDPOINT, params, headers)}"
    
    data = r.json()
    _validate_integrity_response(data)

def test_get_integrity_with_empty_params(api_client, auth_token):
    """Тест с пустыми параметрами"""
    base = f"http://127.0.0.1:{SERVICES['csi-server']['port']}{SERVICES['csi-server']['base_path']}"
    url = _url(base)
    params = {"limit": "", "offset": "", "filter": ""}
    headers = {"x-access-token": auth_token}
    
    r = api_client.get(url, headers=headers, params=params)
    assert r.status_code == 200, f"Ожидается 200 OK; получено {r.status_code}; curl: {_format_curl_command(api_client, ENDPOINT, params, headers)}"
    
    data = r.json()
    _validate_integrity_response(data)

def test_get_integrity_with_special_chars(api_client, auth_token):
    """Тест с специальными символами в параметрах"""
    base = f"http://127.0.0.1:{SERVICES['csi-server']['port']}{SERVICES['csi-server']['base_path']}"
    url = _url(base)
    params = {"filter": "test@example.com", "sort": "name-desc"}
    headers = {"x-access-token": auth_token}
    
    r = api_client.get(url, headers=headers, params=params)
    assert r.status_code == 200, f"Ожидается 200 OK; получено {r.status_code}; curl: {_format_curl_command(api_client, ENDPOINT, params, headers)}"
    
    data = r.json()
    _validate_integrity_response(data)
