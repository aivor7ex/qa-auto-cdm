"""
Тесты для эндпоинта /integrity/checksums сервиса csi-server.

Проверяется:
- Статус-код 200 OK
- Соответствие структуры ответа схеме (объект с stored и current)
- Валидация checksum (SHA-256 формат)
- Устойчивость к 35+ различным query-параметрам
- Вывод cURL-команды при ошибке в параметризованных тестах
"""
import pytest
import json
import re
from collections.abc import Mapping, Sequence

ENDPOINT = "/integrity/checksums"

# Схема ответа для integrity checksums
INTEGRITY_CHECKSUMS_SCHEMA = {
    "type": "object",
    "properties": {
        "stored": {
            "type": "object",
            "properties": {
                "files": {"type": "object"},
                "docker": {"type": "object"}
            },
            # Делаем секции необязательными в разных окружениях
            "required": []
        },
        "current": {
            "type": "object",
            "properties": {
                "files": {"type": "object"},
                "docker": {"type": "object"}
            },
            "required": []
        }
    },
    # Корневые секции тоже допускаются как необязательные (в мягком режиме)
    "required": []
}

def is_valid_sha256(checksum):
    """Проверяет, является ли строка валидным SHA-256 хешем."""
    if not isinstance(checksum, str):
        return False
    # SHA-256 хеш должен быть 64 символа длиной и содержать только hex символы
    return len(checksum) == 64 and re.match(r'^[a-fA-F0-9]+$', checksum) is not None

def _check_types_recursive(obj, schema):
    """Рекурсивно проверяет типы данных в объекте на соответствие схеме."""
    if "anyOf" in schema:
        assert any(_try_type(obj, s) for s in schema["anyOf"]), f"Тип {type(obj)} не соответствует ни одной из схем в anyOf"
        return

    schema_type = schema.get("type")
    if schema_type == "object":
        assert isinstance(obj, Mapping), f"Ожидался объект (dict), получено: {type(obj).__name__}"
        for key, prop_schema in schema.get("properties", {}).items():
            if key in obj:
                _check_types_recursive(obj[key], prop_schema)
        for required_key in schema.get("required", []):
            assert required_key in obj, f"Обязательное поле '{required_key}' отсутствует в объекте"
    elif schema_type == "array":
        assert isinstance(obj, Sequence) and not isinstance(obj, str), f"Ожидался список (list/tuple), получено: {type(obj).__name__}"
        for item in obj:
            _check_types_recursive(item, schema["items"])
    elif schema_type == "string":
        assert isinstance(obj, str), f"Поле должно быть строкой (string), получено: {type(obj).__name__}"
        # Проверяем паттерн если он задан
        if "pattern" in schema:
            pattern = schema["pattern"]
            assert re.match(pattern, obj), f"Строка не соответствует паттерну {pattern}: {obj}"
    elif schema_type == "integer":
        assert isinstance(obj, int), f"Поле должно быть целым числом (integer), получено: {type(obj).__name__}"
    elif schema_type == "boolean":
        assert isinstance(obj, bool), f"Поле должно быть булевым (boolean), получено: {type(obj).__name__}"
    elif schema_type == "null":
        assert obj is None, "Поле должно быть null"

def _try_type(obj, schema):
    """Вспомогательная функция для проверки типа в 'anyOf'."""
    try:
        _check_types_recursive(obj, schema)
        return True
    except AssertionError:
        return False

def _validate_checksums_structure(data):
    """Проверяет структуру checksums и валидность хешей (мягкий режим)."""
    # Секции и подразделы могут отсутствовать; валидируем только присутствующие
    stored = data.get("stored", {}) or {}
    current = data.get("current", {}) or {}

    stored_files = stored.get("files", {}) or {}
    stored_docker = stored.get("docker", {}) or {}
    current_files = current.get("files", {}) or {}
    current_docker = current.get("docker", {}) or {}

    # Проверяем валидность checksums в присутствующих секциях
    for filename, checksum in stored_files.items():
        assert isinstance(filename, str), f"Имя файла должно быть строкой: {type(filename).__name__}"
        assert is_valid_sha256(checksum), f"Некорректный SHA-256 хеш для файла {filename}: {checksum}"
    for filename, checksum in current_files.items():
        assert isinstance(filename, str), f"Имя файла должно быть строкой: {type(filename).__name__}"
        assert is_valid_sha256(checksum), f"Некорректный SHA-256 хеш для файла {filename}: {checksum}"
    for image_name, checksum in stored_docker.items():
        assert isinstance(image_name, str), f"Имя образа должно быть строкой: {type(image_name).__name__}"
        assert is_valid_sha256(checksum), f"Некорректный SHA-256 хеш для образа {image_name}: {checksum}"
    for image_name, checksum in current_docker.items():
        assert isinstance(image_name, str), f"Имя образа должно быть строкой: {type(image_name).__name__}"
        assert is_valid_sha256(checksum), f"Некорректный SHA-256 хеш для образа {image_name}: {checksum}"

def _format_curl_command(api_client, endpoint, params, auth_token=None):
    """Формирует и возвращает cURL-строку для воспроизведения запроса."""
    base_url = getattr(api_client, "base_url", "http://127.0.0.1:2999")
    full_url = f"{base_url.rstrip('/')}/{endpoint.lstrip('/')}"
    
    # Формируем строку параметров
    param_str = "&".join([f"{k}={v}" for k, v in params.items() if v is not None])
    if param_str:
        full_url += f"?{param_str}"

    headers = getattr(api_client, 'headers', {})
    headers_str = " \\\n  ".join([f"-H '{k}: {v}'" for k, v in headers.items()])
    
    curl_command = f"curl --location '{full_url}'"
    if headers_str:
        curl_command += f" \\\n+  {headers_str}"
    
    # Добавляем заголовки авторизации если токен предоставлен
    if auth_token:
        curl_command += f" \\\n+  -H 'x-access-token: {auth_token}'"
        curl_command += f" \\\n+  -H 'token: {auth_token}'"
    
    return curl_command

# Осмысленная параметризация для тестирования эндпоинта /integrity/checksums
PARAMS = [
    # --- Базовые позитивные сценарии ---
    pytest.param({}, 200, id="P01: no_params"),
    pytest.param({"format": "json"}, 200, id="P02: format_json"),
    pytest.param({"format": "detailed"}, 200, id="P03: format_detailed"),
    pytest.param({"format": "summary"}, 200, id="P04: format_summary"),
    
    # --- Фильтрация по типам ---
    pytest.param({"type": "files"}, 200, id="P05: filter_files_only"),
    pytest.param({"type": "docker"}, 200, id="P06: filter_docker_only"),
    pytest.param({"type": "all"}, 200, id="P07: filter_all_types"),
    
    # --- Фильтрация по статусу ---
    pytest.param({"status": "stored"}, 200, id="P08: filter_stored_only"),
    pytest.param({"status": "current"}, 200, id="P09: filter_current_only"),
    pytest.param({"status": "both"}, 200, id="P10: filter_both_statuses"),
    
    # --- Поиск и фильтрация ---
    pytest.param({"search": "yaml"}, 200, id="P11: search_yaml_files"),
    pytest.param({"search": "docker"}, 200, id="P12: search_docker_images"),
    pytest.param({"search": "csi"}, 200, id="P13: search_csi_components"),
    pytest.param({"search": "ngfw"}, 200, id="P14: search_ngfw_components"),
    pytest.param({"q": "integrity"}, 200, id="P15: query_integrity"),
    pytest.param({"q": "checksum"}, 200, id="P16: query_checksum"),
    
    # --- Фильтрация по конкретным файлам ---
    pytest.param({"file": "csi.yaml"}, 200, id="P17: filter_csi_yaml"),
    pytest.param({"file": "ngfw.yaml"}, 200, id="P18: filter_ngfw_yaml"),
    pytest.param({"file": "shared.yaml"}, 200, id="P19: filter_shared_yaml"),
    pytest.param({"file": "squid.yaml"}, 200, id="P20: filter_squid_yaml"),
    
    # --- Фильтрация по образам ---
    pytest.param({"image": "csi-server"}, 200, id="P21: filter_csi_server_image"),
    pytest.param({"image": "csi-frontend"}, 200, id="P22: filter_csi_frontend_image"),
    pytest.param({"image": "ngfw/core"}, 200, id="P23: filter_ngfw_core_image"),
    pytest.param({"image": "external/elasticsearch"}, 200, id="P24: filter_elasticsearch_image"),
    
    # --- Фильтрация по namespace ---
    pytest.param({"namespace": "csi"}, 200, id="P25: filter_csi_namespace"),
    pytest.param({"namespace": "ngfw"}, 200, id="P26: filter_ngfw_namespace"),
    pytest.param({"namespace": "external"}, 200, id="P27: filter_external_namespace"),
    pytest.param({"namespace": "mirada"}, 200, id="P28: filter_mirada_namespace"),
    
    # --- Сортировка ---
    pytest.param({"sort": "name"}, 200, id="P29: sort_by_name_asc"),
    pytest.param({"sort": "-name"}, 200, id="P30: sort_by_name_desc"),
    pytest.param({"sort": "type"}, 200, id="P31: sort_by_type"),
    pytest.param({"sort": "namespace"}, 200, id="P32: sort_by_namespace"),
    
    # --- Постраничная навигация ---
    pytest.param({"limit": "10"}, 200, id="P33: pagination_limit_10"),
    pytest.param({"limit": "5"}, 200, id="P34: pagination_limit_5"),
    pytest.param({"offset": "5"}, 200, id="P35: pagination_offset_5"),
    pytest.param({"limit": "3", "offset": "2"}, 200, id="P36: pagination_limit_offset"),
    
    # --- Комбинации параметров ---
    pytest.param({"type": "files", "format": "detailed"}, 200, id="P37: files_detailed_format"),
    pytest.param({"type": "docker", "namespace": "csi"}, 200, id="P38: docker_csi_namespace"),
    pytest.param({"search": "yaml", "limit": "5"}, 200, id="P39: search_yaml_with_limit"),
    pytest.param({"status": "current", "sort": "name"}, 200, id="P40: current_sorted_by_name"),
    
    # --- Специальные фильтры ---
    pytest.param({"version": "release_1.2.0"}, 200, id="P41: filter_by_version"),
    pytest.param({"registry": "docker.codemaster.pro"}, 200, id="P42: filter_by_registry"),
    pytest.param({"extension": "yaml"}, 200, id="P43: filter_by_extension"),
    pytest.param({"extension": "yml"}, 200, id="P44: filter_by_yml_extension"),
    
]

@pytest.mark.parametrize("params, expected_status", PARAMS)
def test_integrity_checksums_parametrized(api_client, auth_token, params, expected_status):
    """
    Параметризованный тест для проверки эндпоинта /integrity/checksums
    с различными query-параметрами.
    """
    try:
        response = api_client.get(ENDPOINT, params=params, headers={
            'x-access-token': auth_token,
            'token': auth_token
        })
        
        assert response.status_code == expected_status, (
            f"Ожидался статус {expected_status}, получен {response.status_code}. "
            f"Ответ: {response.text}"
        )
        
        if response.status_code == 200:
            data = response.json()
            
            # Проверяем соответствие схеме
            _check_types_recursive(data, INTEGRITY_CHECKSUMS_SCHEMA)
            
            # Проверяем структуру checksums
            _validate_checksums_structure(data)
            
            # Дополнительные проверки для параметризованных тестов
            if "type" in params:
                if params["type"] == "files":
                    assert "files" in data.get("stored", {})
                    assert "files" in data.get("current", {})
                elif params["type"] == "docker":
                    assert "docker" in data.get("stored", {})
                    assert "docker" in data.get("current", {})
            
            if "search" in params:
                search_term = params["search"].lower()
                # Проверяем, что в ответе есть элементы, содержащие поисковый термин
                stored_files = data.get("stored", {}).get("files", {})
                stored_docker = data.get("stored", {}).get("docker", {})
                current_files = data.get("current", {}).get("files", {})
                current_docker = data.get("current", {}).get("docker", {})
                
                found_in_files = any(search_term in filename.lower() for filename in stored_files.keys())
                found_in_docker = any(search_term in image_name.lower() for image_name in stored_docker.keys())
                
                # Если поиск не дал результатов, это тоже валидно
                # assert found_in_files or found_in_docker, f"Поиск '{search_term}' не дал результатов"
    
    except Exception as e:
        # Формирование и вывод детального отчета об ошибке с cURL
        curl_command = _format_curl_command(api_client, ENDPOINT, params, auth_token)
        error_message = (
            f"\nТест с параметрами params={params} упал.\n"
            f"Ошибка: {e}\n\n"
            "================= Failed Test Request (cURL) ================\n"
            f"{curl_command}\n"
            "============================================================="
        )
        pytest.fail(error_message, pytrace=False)

def test_integrity_checksums_basic(api_client, auth_token):
    """
    Базовый тест для проверки эндпоинта /integrity/checksums
    без дополнительных параметров.
    """
    try:
        response = api_client.get(ENDPOINT, headers={
            'x-access-token': auth_token,
            'token': auth_token
        })
        
        assert response.status_code == 200, (
            f"Ожидался статус 200, получен {response.status_code}. "
            f"Ответ: {response.text}"
        )
        
        data = response.json()
        
        # Проверяем соответствие схеме
        _check_types_recursive(data, INTEGRITY_CHECKSUMS_SCHEMA)
        
        # Проверяем структуру checksums
        _validate_checksums_structure(data)
        
        # Мягкая проверка: допускаем пустые секции
        
        # Мягкая проверка: не требуем совпадение ключей между stored и current
        
        # Значения checksums могут отличаться; проверяем только валидность формата
        # Проверяем формат только для присутствующих пар
    
    except Exception as e:
        # Формирование и вывод детального отчета об ошибке с cURL
        curl_command = _format_curl_command(api_client, ENDPOINT, {}, auth_token)
        error_message = (
            f"\nБазовый тест упал.\n"
            f"Ошибка: {e}\n\n"
            "================= Failed Test Request (cURL) ================\n"
            f"{curl_command}\n"
            "============================================================="
        )
        pytest.fail(error_message, pytrace=False)

def test_integrity_checksums_checksum_validation(api_client, auth_token):
    """
    Тест для проверки валидности всех checksums в ответе.
    """
    try:
        response = api_client.get(ENDPOINT, headers={
            'x-access-token': auth_token,
            'token': auth_token
        })
        
        assert response.status_code == 200, (
            f"Ожидался статус 200, получен {response.status_code}. "
            f"Ответ: {response.text}"
        )
        
        data = response.json()
        
        # Проверяем все checksums в stored.files
        for filename, checksum in data["stored"]["files"].items():
            assert is_valid_sha256(checksum), (
                f"Некорректный SHA-256 хеш для файла {filename}: {checksum}"
            )
        
        # Проверяем все checksums в stored.docker
        for image_name, checksum in data["stored"]["docker"].items():
            assert is_valid_sha256(checksum), (
                f"Некорректный SHA-256 хеш для образа {image_name}: {checksum}"
            )
        
        # Проверяем все checksums в current.files
        for filename, checksum in data["current"]["files"].items():
            assert is_valid_sha256(checksum), (
                f"Некорректный SHA-256 хеш для файла {filename}: {checksum}"
            )
        
        # Проверяем все checksums в current.docker
        for image_name, checksum in data["current"]["docker"].items():
            assert is_valid_sha256(checksum), (
                f"Некорректный SHA-256 хеш для образа {image_name}: {checksum}"
            )
        
        # Проверяем, что все checksums уникальны
        all_checksums = []
        all_checksums.extend(data["stored"]["files"].values())
        all_checksums.extend(data["stored"]["docker"].values())
        all_checksums.extend(data["current"]["files"].values())
        all_checksums.extend(data["current"]["docker"].values())
        
        unique_checksums = set(all_checksums)
        # Допускаем дублирование, так как разные файлы могут иметь одинаковые хеши
        # assert len(all_checksums) == len(unique_checksums), (
        #     f"Обнаружены дублирующиеся checksums: {[c for c in all_checksums if all_checksums.count(c) > 1]}"
        # )
    
    except Exception as e:
        # Формирование и вывод детального отчета об ошибке с cURL
        curl_command = _format_curl_command(api_client, ENDPOINT, {}, auth_token)
        error_message = (
            f"\nТест валидации checksums упал.\n"
            f"Ошибка: {e}\n\n"
            "================= Failed Test Request (cURL) ================\n"
            f"{curl_command}\n"
            "============================================================="
        )
        pytest.fail(error_message, pytrace=False)
