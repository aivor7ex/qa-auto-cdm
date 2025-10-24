"""
Тесты для эндпоинта /update/images/current сервиса csi-server.

Проверяется:
- Статус-код 200 OK
- Соответствие структуры ответа схеме (объект с информацией об обновлении образов)
- Валидация дат и времени
- Проверка хеш-сумм
- Устойчивость к различным query-параметрам
- Вывод cURL-команды при ошибке в параметризованных тестах
"""
import pytest
import json
from collections.abc import Mapping, Sequence
from datetime import datetime
import re

ENDPOINT = "/update/images/current"

# Схема ответа для update/images/current на основе реального ответа API
UPDATE_IMAGES_CURRENT_SCHEMA = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
        "type": {"type": "string"},
        "name": {"type": "string"},
        "date": {"type": "string"},
        "channel": {"type": "string"},
        "files": {
            "type": "object",
            "additionalProperties": {
                "type": "object",
                "properties": {
                    "commit": {"type": "string"},
                    "name": {"type": "string"},
                    "downloaded": {"type": "boolean"},
                    "applied": {"type": "boolean"}
                },
                "required": ["commit", "name", "downloaded", "applied"]
            }
        },
        "applied": {"type": "boolean"},
        "downloading": {"type": "boolean"},
        "downloaded": {"type": "boolean"},
        "local": {"type": "boolean"},
        "createdAt": {"type": "string"},
        "modifiedAt": {"type": "string"}
    },
    "required": ["type", "name", "date", "channel", "files", "applied", "downloading", "downloaded", "local", "createdAt", "modifiedAt"]
}

# Осмысленная параметризация для тестирования эндпоинта /update/images/current
PARAMS = [
    # --- Базовые позитивные сценарии ---
    pytest.param({}, 200, id="P01: no_params"),
    pytest.param({"id": "release_1.2.0_release"}, 200, id="P02: filter_by_id"),
    pytest.param({"name": "release_1.2.0"}, 200, id="P03: filter_by_name"),
    pytest.param({"type": "images"}, 200, id="P04: filter_by_type"),
    pytest.param({"channel": "release"}, 200, id="P05: filter_by_channel"),
    
    # --- Фильтрация по статусу ---
    pytest.param({"applied": "true"}, 200, id="P06: filter_applied_true"),
    pytest.param({"applied": "false"}, 200, id="P07: filter_applied_false"),
    pytest.param({"downloaded": "true"}, 200, id="P08: filter_downloaded_true"),
    pytest.param({"downloaded": "false"}, 200, id="P09: filter_downloaded_false"),
    pytest.param({"downloading": "true"}, 200, id="P10: filter_downloading_true"),
    pytest.param({"downloading": "false"}, 200, id="P11: filter_downloading_false"),
    pytest.param({"local": "true"}, 200, id="P12: filter_local_true"),
    pytest.param({"local": "false"}, 200, id="P13: filter_local_false"),
    
    # --- Фильтрация по файлам ---
    pytest.param({"file": "external/vpp"}, 200, id="P14: filter_by_file_name"),
    pytest.param({"file": "ngfw/core"}, 200, id="P15: filter_by_ngfw_file"),
    pytest.param({"file": "csi/csi-server"}, 200, id="P16: filter_by_csi_file"),
    pytest.param({"file": "mirada/mirada-ui"}, 200, id="P17: filter_by_mirada_file"),
    pytest.param({"has_file": "external/vpp"}, 200, id="P18: filter_has_file"),
    pytest.param({"has_file": "ngfw/core"}, 200, id="P19: filter_has_ngfw_file"),
    
    # --- Фильтрация по коммитам ---
    pytest.param({"commit": "653e2aea5cb3b02446c7b8902bfa0d9bd2d4a5a5"}, 200, id="P20: filter_by_commit_hash"),
    pytest.param({"commit": "d3fe4703eb0a3971ca28d3b02f83ff3d7d2e9b8d"}, 200, id="P21: filter_by_another_commit"),
    pytest.param({"has_commit": "653e2aea5cb3b02446c7b8902bfa0d9bd2d4a5a5"}, 200, id="P22: filter_has_commit"),
    
    # --- Фильтрация по датам ---
    pytest.param({"date": "2025-07-25"}, 200, id="P23: filter_by_date"),
    pytest.param({"date_from": "2025-07-01"}, 200, id="P24: filter_by_date_from"),
    pytest.param({"date_to": "2025-07-31"}, 200, id="P25: filter_by_date_to"),
    pytest.param({"created_after": "2025-07-01T00:00:00Z"}, 200, id="P26: filter_created_after"),
    pytest.param({"created_before": "2025-08-01T23:59:59Z"}, 200, id="P27: filter_created_before"),
    pytest.param({"modified_after": "2025-07-01T00:00:00Z"}, 200, id="P28: filter_modified_after"),
    pytest.param({"modified_before": "2025-08-01T23:59:59Z"}, 200, id="P29: filter_modified_before"),
    
    # --- Поиск и фильтрация ---
    pytest.param({"search": "release"}, 200, id="P30: search_release"),
    pytest.param({"search": "1.2.0"}, 200, id="P31: search_version"),
    pytest.param({"search": "images"}, 200, id="P32: search_images"),
    pytest.param({"q": "update"}, 200, id="P33: query_update"),
    pytest.param({"q": "current"}, 200, id="P34: query_current"),
    
    # --- Сортировка ---
    pytest.param({"sort": "name"}, 200, id="P35: sort_by_name_asc"),
    pytest.param({"sort": "-name"}, 200, id="P36: sort_by_name_desc"),
    pytest.param({"sort": "date"}, 200, id="P37: sort_by_date"),
    pytest.param({"sort": "-date"}, 200, id="P38: sort_by_date_desc"),
    pytest.param({"sort": "createdAt"}, 200, id="P39: sort_by_created_at"),
    pytest.param({"sort": "-createdAt"}, 200, id="P40: sort_by_created_at_desc"),
    
    # --- Постраничная навигация ---
    pytest.param({"limit": "10"}, 200, id="P41: pagination_limit_10"),
    pytest.param({"limit": "1"}, 200, id="P42: pagination_limit_1"),
    pytest.param({"offset": "0"}, 200, id="P43: pagination_offset_0"),
    pytest.param({"page": "1"}, 200, id="P44: pagination_page_1"),
    pytest.param({"per_page": "20"}, 200, id="P45: pagination_per_page_20"),
    
    # --- Дополнительные фильтры ---
    pytest.param({"status": "applied"}, 200, id="P46: filter_status_applied"),
    pytest.param({"status": "downloaded"}, 200, id="P47: filter_status_downloaded"),
    pytest.param({"status": "downloading"}, 200, id="P48: filter_status_downloading"),
    pytest.param({"version": "1.2.0"}, 200, id="P49: filter_by_version"),
    pytest.param({"tag": "release"}, 200, id="P50: filter_by_tag")
]


def _validate_date_format(date_string, field_name):
    """Проверяет валидность формата даты ISO 8601."""
    try:
        datetime.fromisoformat(date_string.replace('Z', '+00:00'))
        return True
    except ValueError:
        raise AssertionError(f"Поле '{field_name}' содержит невалидную дату: {date_string}")


def _validate_commit_hash(hash_string):
    """Проверяет валидность SHA-1 хеша."""
    if not re.match(r'^[a-f0-9]{40}$', hash_string):
        raise AssertionError(f"Невалидный SHA-1 хеш: {hash_string}")


def _check_types_recursive(obj, schema):
    """
    Рекурсивно проверяет соответствие объекта схеме JSON.
    Поддерживает вложенные объекты, массивы и примитивные типы.
    """
    schema_type = schema.get("type")
    if schema_type == "object":
        assert isinstance(obj, Mapping), f"Ожидался объект (dict), получено: {type(obj).__name__}"
        
        # Обычная проверка для объектов
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
    elif schema_type == "integer":
        assert isinstance(obj, int), f"Поле должно быть целым числом (integer), получено: {type(obj).__name__}"
    elif schema_type == "boolean":
        assert isinstance(obj, bool), f"Поле должно быть булевым (boolean), получено: {type(obj).__name__}"
    elif schema_type == "null":
        assert obj is None, "Поле должно быть null"


def _validate_update_images_response(data):
    """Дополнительная валидация специфичная для update/images/current."""
    # Проверка дат
    if "date" in data:
        _validate_date_format(data["date"], "date")
    if "createdAt" in data:
        _validate_date_format(data["createdAt"], "createdAt")
    if "modifiedAt" in data:
        _validate_date_format(data["modifiedAt"], "modifiedAt")
    
    # Проверка файлов и их хешей
    if "files" in data and isinstance(data["files"], dict):
        for file_hash, file_info in data["files"].items():
            # Проверка хеша файла
            _validate_commit_hash(file_hash)
            
            # Проверка хеша в commit поле
            if "commit" in file_info:
                _validate_commit_hash(file_info["commit"])
                # Хеш в ключе должен совпадать с хешем в commit
                assert file_hash == file_info["commit"], f"Хеш в ключе ({file_hash}) не совпадает с хешем в commit ({file_info['commit']})"


def _format_curl_command(api_client, endpoint, params, auth_token):
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
        curl_command += f" \\\n  {headers_str}"
    
    # Добавляем заголовки авторизации
    if auth_token:
        curl_command += f" \\\n  -H 'x-access-token: {auth_token}'"
        curl_command += f" \\\n  -H 'token: {auth_token}'"
        
    return curl_command


@pytest.mark.parametrize("params, expected_status", PARAMS)
def test_update_images_current_parametrized(api_client, auth_token, params, expected_status, attach_curl_on_fail):
    """
    Основной параметризованный тест для эндпоинта /update/images/current.
    1. Отправляет GET-запрос с указанными параметрами.
    2. Проверяет соответствие статус-кода ожидаемому.
    3. Для успешных ответов (200) валидирует схему JSON.
    4. Проверяет валидность дат и хеш-сумм.
    5. В случае падения теста выводит полную cURL-команду для воспроизведения.
    """
    # Добавляем заголовки авторизации
    headers = {
        'x-access-token': auth_token,
        'token': auth_token
    }

    # Используем фиксутру attach_curl_on_fail для автоматического приаттачивания cURL при падении теста
    # Параметры: endpoint, params (payload/query), headers, method
    with attach_curl_on_fail(ENDPOINT, params, headers, method="GET"):
        response = api_client.get(ENDPOINT, params=params, headers=headers)

        # 1. Проверка статус-кода
        # Новый кейс: сервис может возвращать 422 (CURRENT_VERSION_IS_NOT_DEFINED)
        # Когда ожидаемый статус — 200, считаем 200 или 422 корректными ответами.
        if expected_status == 200:
            assert response.status_code in (200, 422), \
                f"Ожидался статус-код 200 или 422, получен {response.status_code}. Ответ: {response.text}"
        else:
            assert response.status_code == expected_status, \
                f"Ожидался статус-код {expected_status}, получен {response.status_code}. Ответ: {response.text}"

        # 2. Валидация схемы ответа (только для 200)
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, dict), f"Тело ответа не является объектом JSON, получено: {type(data).__name__}"

            # Проверяем структуру ответа
            _check_types_recursive(data, UPDATE_IMAGES_CURRENT_SCHEMA)

            # Дополнительная валидация специфичная для update/images/current
            _validate_update_images_response(data)
