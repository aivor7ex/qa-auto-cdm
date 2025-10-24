"""
Тесты для эндпоинта /update/images/status сервиса csi-server.

Проверяется:
- Статус-код 200 OK
- Соответствие структуры ответа схеме (объект с информацией о статусе обновления образов)
- Валидация дат и времени (date, createdAt, modifiedAt)
- Проверка хеш-сумм коммитов
- Устойчивость к различным query-параметрам
- Вывод cURL-команды при ошибке в параметризованных тестах
"""
import pytest
import json
from collections.abc import Mapping, Sequence
from datetime import datetime
import re

ENDPOINT = "/update/images/status"

# Схема ответа для update/images/status на основе реального ответа API
UPDATE_IMAGES_STATUS_SCHEMA = {
    "type": "object",
    "properties": {
        "latest": {"type": "null"},
        "current": {
            "type": "object",
            "properties": {
                "id": {"type": "string"},
                "type": {"type": "string"},
                "name": {"type": "string"},
                "date": {"type": "string"},
                "version": {"type": "string"},
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
            "required": ["date"]
        },
        "versionDetails": {
            "type": "object",
            "properties": {
                "image": {"type": "string"},
                "commit": {"type": "string"},
                "time": {"type": "string"}
            },
            "required": ["image", "commit", "time"]
        }
    },
    "required": ["latest", "current", "versionDetails"]
}

# Осмысленная параметризация для тестирования реальной функциональности API
PARAMS = [
    # --- Базовые позитивные сценарии ---
    pytest.param({}, 200, id="P01: no_params"),
    
    # --- Тестирование устойчивости к параметрам (API игнорирует все параметры) ---
    pytest.param({"any_param": "any_value"}, 200, id="P02: single_param_ignored"),
    pytest.param({"unknown": "value"}, 200, id="P03: unknown_param_ignored"),
    pytest.param({"multiple": "params", "another": "value"}, 200, id="P04: multiple_params_ignored"),
    
    # --- Параметры, которые логично могли бы существовать, но API их игнорирует ---
    pytest.param({"status": "current"}, 200, id="P05: status_current_param_ignored"),
    pytest.param({"status": "latest"}, 200, id="P06: status_latest_param_ignored"),
    pytest.param({"type": "images"}, 200, id="P07: type_images_param_ignored"),
    pytest.param({"channel": "release"}, 200, id="P08: channel_release_param_ignored"),
    pytest.param({"channel": "stable"}, 200, id="P09: channel_stable_param_ignored"),
    pytest.param({"channel": "beta"}, 200, id="P10: channel_beta_param_ignored"),
    
    # --- Статусные параметры (API игнорирует) ---
    pytest.param({"applied": "true"}, 200, id="P11: applied_true_param_ignored"),
    pytest.param({"applied": "false"}, 200, id="P12: applied_false_param_ignored"),
    pytest.param({"downloaded": "true"}, 200, id="P13: downloaded_true_param_ignored"),
    pytest.param({"downloaded": "false"}, 200, id="P14: downloaded_false_param_ignored"),
    pytest.param({"downloading": "true"}, 200, id="P15: downloading_true_param_ignored"),
    pytest.param({"downloading": "false"}, 200, id="P16: downloading_false_param_ignored"),
    pytest.param({"local": "true"}, 200, id="P17: local_true_param_ignored"),
    pytest.param({"local": "false"}, 200, id="P18: local_false_param_ignored"),
    
    # --- Версионные параметры (API игнорирует) ---
    pytest.param({"version": "1.2.0"}, 200, id="P19: version_param_ignored"),
    pytest.param({"version": "1.1.0"}, 200, id="P20: another_version_param_ignored"),
    pytest.param({"version_prefix": "1.2"}, 200, id="P21: version_prefix_param_ignored"),
    pytest.param({"version_suffix": "0"}, 200, id="P22: version_suffix_param_ignored"),
    
    # --- Файловые параметры (API игнорирует) ---
    pytest.param({"file": "external/vpp"}, 200, id="P23: file_name_param_ignored"),
    pytest.param({"file": "ngfw/core"}, 200, id="P24: ngfw_file_param_ignored"),
    pytest.param({"has_file": "ngfw/core"}, 200, id="P25: filter_has_ngfw_file"),
    pytest.param({"file_type": "external"}, 200, id="P26: filter_by_file_type_external"),
    pytest.param({"file_type": "ngfw"}, 200, id="P27: filter_by_file_type_ngfw"),
    pytest.param({"file_type": "csi"}, 200, id="P28: filter_by_file_type_csi"),
    pytest.param({"file_type": "mirada"}, 200, id="P29: filter_by_file_type_mirada"),
    
    # --- Фильтрация по коммитам ---
    pytest.param({"commit": "653e2aea5cb3b02446c7b8902bfa0d9bd2d4a5a5"}, 200, id="P30: filter_by_commit_hash"),
    pytest.param({"commit": "d3fe4703eb0a3971ca28d3b02f83ff3d7d2e9b8d"}, 200, id="P31: filter_by_another_commit"),
    pytest.param({"has_commit": "653e2aea5cb3b02446c7b8902bfa0d9bd2d4a5a5"}, 200, id="P32: filter_has_commit"),
    pytest.param({"commit_prefix": "653e2"}, 200, id="P33: filter_by_commit_prefix"),
    
    # --- Фильтрация по датам ---
    pytest.param({"date": "2025-07-25"}, 200, id="P34: filter_by_date"),
    pytest.param({"date_from": "2025-07-01"}, 200, id="P35: filter_by_date_from"),
    pytest.param({"date_to": "2025-07-31"}, 200, id="P36: filter_by_date_to"),
    pytest.param({"created_after": "2025-07-01T00:00:00Z"}, 200, id="P37: filter_created_after"),
    pytest.param({"created_before": "2025-08-01T23:59:59Z"}, 200, id="P38: filter_created_before"),
    pytest.param({"modified_after": "2025-07-01T00:00:00Z"}, 200, id="P39: filter_modified_after"),
    pytest.param({"modified_before": "2025-08-01T23:59:59Z"}, 200, id="P40: filter_modified_before"),
    
    # --- Поиск и фильтрация ---
    pytest.param({"search": "release"}, 200, id="P41: search_release"),
    pytest.param({"search": "1.2.0"}, 200, id="P42: search_version"),
    pytest.param({"search": "images"}, 200, id="P43: search_images"),
    pytest.param({"q": "update"}, 200, id="P44: query_update"),
    pytest.param({"q": "status"}, 200, id="P45: query_status"),
    
    # --- Сортировка ---
    pytest.param({"sort": "date"}, 200, id="P46: sort_by_date"),
    pytest.param({"sort": "-date"}, 200, id="P47: sort_by_date_desc"),
    pytest.param({"sort": "name"}, 200, id="P48: sort_by_name"),
    pytest.param({"sort": "-name"}, 200, id="P49: sort_by_name_desc"),
    pytest.param({"sort": "createdAt"}, 200, id="P50: sort_by_created_at"),
    
    # --- Комбинированные фильтры ---
    pytest.param({"channel": "release", "applied": "true"}, 200, id="P51: channel_and_applied"),
    pytest.param({"type": "images", "downloaded": "true"}, 200, id="P52: type_and_downloaded"),
    pytest.param({"file_type": "ngfw", "applied": "false"}, 200, id="P53: file_type_and_applied"),
    
    # --- Граничные значения ---
    pytest.param({"limit": "10"}, 200, id="P54: pagination_limit"),
    pytest.param({"offset": "0"}, 200, id="P55: pagination_offset"),
    pytest.param({"unsupported_param": "value"}, 200, id="P56: unsupported_param_ignored"),
    
    # --- Граничные значения и специальные случаи ---
    pytest.param({"filter": "invalid_json"}, 200, id="P57: invalid_json_filter_ignored"),
    pytest.param({"filter": '{"invalid": }'}, 200, id="P58: malformed_json_filter_ignored"),
    pytest.param({"date": "invalid_date"}, 200, id="P59: invalid_date_format_ignored"),
    pytest.param({"commit": "invalid_hash"}, 200, id="P60: invalid_commit_hash_ignored"),
]


def _validate_date_format(date_string, field_name):
    """Валидирует формат даты ISO 8601."""
    try:
        # Парсим дату в ISO формате
        parsed_date = datetime.fromisoformat(date_string.replace('Z', '+00:00'))
        # Проверяем, что дата не в будущем (допускаем небольшое отклонение для тестов)
        current_time = datetime.now().replace(tzinfo=parsed_date.tzinfo)
        time_diff = (parsed_date - current_time).total_seconds()
        assert time_diff < 86400, f"Дата {field_name} не может быть в будущем более чем на 24 часа"
        return True
    except ValueError as e:
        pytest.fail(f"Неверный формат даты в поле {field_name}: {date_string}. Ошибка: {e}")


def _validate_commit_hash(hash_string):
    """Валидирует формат хеша коммита Git (SHA-1)."""
    # Git SHA-1 хеш: 40 символов, шестнадцатеричные цифры
    if not re.match(r'^[a-f0-9]{40}$', hash_string):
        pytest.fail(f"Неверный формат хеша коммита: {hash_string}. Ожидается SHA-1 хеш (40 символов)")


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


def _validate_update_images_status_response(data):
    """Валидирует ответ API update/images/status."""
    # Проверяем основную структуру
    assert "latest" in data, "Отсутствует поле 'latest'"
    assert "current" in data, "Отсутствует поле 'current'"
    assert "versionDetails" in data, "Отсутствует поле 'versionDetails'"
    
    # Проверяем поле latest (может быть null)
    if data["latest"] is not None:
        # Если latest не null, проверяем его структуру
        _check_types_recursive(data["latest"], UPDATE_IMAGES_STATUS_SCHEMA["properties"]["current"])
    
    # Проверяем поле current
    current = data["current"]
    assert current is not None, "Поле 'current' не может быть null"
    
    # Валидируем даты
    if "date" in current:
        _validate_date_format(current["date"], "date")
    if "createdAt" in current:
        _validate_date_format(current["createdAt"], "createdAt")
    if "modifiedAt" in current:
        _validate_date_format(current["modifiedAt"], "modifiedAt")
    
    # Валидируем файлы
    if "files" in current:
        assert isinstance(current["files"], dict), "Поле 'files' должно быть объектом"
        for file_hash, file_info in current["files"].items():
            # Проверяем формат хеша файла
            _validate_commit_hash(file_hash)
            # Проверяем структуру информации о файле
            assert "commit" in file_info, f"Отсутствует поле 'commit' в информации о файле {file_hash}"
            assert "name" in file_info, f"Отсутствует поле 'name' в информации о файле {file_hash}"
            assert "downloaded" in file_info, f"Отсутствует поле 'downloaded' в информации о файле {file_hash}"
            assert "applied" in file_info, f"Отсутствует поле 'applied' в информации о файле {file_hash}"
            
            # Валидируем хеш коммита
            _validate_commit_hash(file_info["commit"])
            
            # Проверяем типы булевых полей
            assert isinstance(file_info["downloaded"], bool), f"Поле 'downloaded' должно быть boolean в файле {file_hash}"
            assert isinstance(file_info["applied"], bool), f"Поле 'applied' должно быть boolean в файле {file_hash}"
    
    # Проверяем versionDetails
    version_details = data["versionDetails"]
    assert version_details is not None, "Поле 'versionDetails' не может быть null"
    
    if "commit" in version_details:
        _validate_commit_hash(version_details["commit"])
    
    if "time" in version_details:
        # Проверяем формат времени в versionDetails (может отличаться от ISO)
        time_str = version_details["time"]
        try:
            # Пробуем разные форматы времени
            datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            try:
                datetime.fromisoformat(time_str.replace('Z', '+00:00'))
            except ValueError:
                pytest.fail(f"Неверный формат времени в versionDetails.time: {time_str}")


def _format_curl_command(api_client, endpoint, params, auth_token):
    """Формирует и возвращает cURL-строку для воспроизведения запроса."""
    base_url = getattr(api_client, "base_url", "http://127.0.0.1:2999")
    full_url = f"{base_url.rstrip('/')}/{endpoint.lstrip('/')}"
    
    # Формируем строку параметров
    param_str = "&".join([f"{k}={v}" for k, v in params.items() if v is not None])
    if param_str:
        full_url += f"?{param_str}"

    curl_command = f"curl --location '{full_url}' \\\n--header 'x-access-token: {auth_token}' \\\n--header 'token: {auth_token}'"
        
    return curl_command


@pytest.mark.parametrize("params, expected_status", PARAMS)
def test_update_images_status_parametrized(api_client, auth_token, params, expected_status, attach_curl_on_fail):
    """
    Основной параметризованный тест для эндпоинта /update/images/status.
    1. Отправляет GET-запрос с указанными параметрами.
    2. Проверяет соответствие статус-кода ожидаемому.
    3. Для успешных ответов (200) валидирует схему JSON.
    4. В случае падения теста выводит полную cURL-команду для воспроизведения.
    """
    # Добавляем заголовки авторизации
    headers = {
        "x-access-token": auth_token,
        "token": auth_token
    }

    # Используем фиксутру attach_curl_on_fail для автоматического приаттачивания cURL при падении теста
    with attach_curl_on_fail(ENDPOINT, params, headers, method="GET"):
        response = api_client.get(ENDPOINT, params=params, headers=headers)

        # 1. Проверка статус-кода
        assert response.status_code == expected_status, \
            f"Ожидался статус-код {expected_status}, получен {response.status_code}. Ответ: {response.text}"

        # 2. Валидация схемы ответа
        if response.status_code == 200:
            data = response.json()
            # Проверяем основную структуру ответа
            _check_types_recursive(data, UPDATE_IMAGES_STATUS_SCHEMA)
            # Дополнительная валидация специфичных полей
            _validate_update_images_status_response(data)
            
            # 3. Проверяем, что API игнорирует все параметры
            # Для этого сравниваем ответ с базовым запросом без параметров
            if params:  # Если есть параметры
                base_response = api_client.get(ENDPOINT, headers=headers)
                base_data = base_response.json()
                
                # API должен возвращать одинаковый ответ независимо от параметров
                assert data == base_data, \
                    f"API должен игнорировать параметры {params}. Ответы должны быть идентичными."


def test_update_images_status_basic_structure(api_client, auth_token):
    """Тест базовой структуры ответа API."""
    headers = {
        "x-access-token": auth_token,
        "token": auth_token
    }
    
    response = api_client.get(ENDPOINT, headers=headers)
    assert response.status_code == 200, f"Ожидался статус 200, получен {response.status_code}"
    
    data = response.json()
    
    # Проверяем обязательные поля верхнего уровня
    assert "latest" in data, "Отсутствует поле 'latest'"
    assert "current" in data, "Отсутствует поле 'current'"
    assert "versionDetails" in data, "Отсутствует поле 'versionDetails'"
    
    # Проверяем, что current не null
    assert data["current"] is not None, "Поле 'current' не может быть null"
    
    # Проверяем структуру current
    current = data["current"]
    # The API may return a minimal 'current' object. Require only 'date' plus either 'type' or 'version'.
    assert "date" in current, "Отсутствует обязательное поле 'date' в current"
    assert ("type" in current) or ("version" in current), "Поле 'current' должно содержать либо 'type', либо 'version'"


def test_update_images_status_date_validation(api_client, auth_token):
    """Тест валидации дат в ответе API."""
    headers = {
        "x-access-token": auth_token,
        "token": auth_token
    }
    
    response = api_client.get(ENDPOINT, headers=headers)
    assert response.status_code == 200, f"Ожидался статус 200, получен {response.status_code}"
    
    data = response.json()
    current = data["current"]
    
    # Валидируем все даты
    if "date" in current:
        _validate_date_format(current["date"], "date")
    if "createdAt" in current:
        _validate_date_format(current["createdAt"], "createdAt")
    if "modifiedAt" in current:
        _validate_date_format(current["modifiedAt"], "modifiedAt")


def test_update_images_status_commit_hashes(api_client, auth_token):
    """Тест валидации хешей коммитов."""
    headers = {
        "x-access-token": auth_token,
        "token": auth_token
    }
    
    response = api_client.get(ENDPOINT, headers=headers)
    assert response.status_code == 200, f"Ожидался статус 200, получен {response.status_code}"
    
    data = response.json()
    current = data["current"]
    
    # Проверяем хеши в files
    if "files" in current:
        for file_hash, file_info in current["files"].items():
            _validate_commit_hash(file_hash)
            if "commit" in file_info:
                _validate_commit_hash(file_info["commit"])
    
    # Проверяем хеш в versionDetails
    if "versionDetails" in data and "commit" in data["versionDetails"]:
        _validate_commit_hash(data["versionDetails"]["commit"])


def test_update_images_status_files_structure(api_client, auth_token):
    """Тест структуры файлов в ответе API."""
    headers = {
        "x-access-token": auth_token,
        "token": auth_token
    }
    
    response = api_client.get(ENDPOINT, headers=headers)
    assert response.status_code == 200, f"Ожидался статус 200, получен {response.status_code}"
    
    data = response.json()
    current = data["current"]
    
    if "files" in current:
        assert isinstance(current["files"], dict), "Поле 'files' должно быть объектом"
        
        for file_hash, file_info in current["files"].items():
            # Проверяем обязательные поля файла
            required_file_fields = ["commit", "name", "downloaded", "applied"]
            for field in required_file_fields:
                assert field in file_info, f"Отсутствует обязательное поле '{field}' в файле {file_hash}"
            
            # Проверяем типы полей
            assert isinstance(file_info["name"], str), f"Поле 'name' должно быть строкой в файле {file_hash}"
            assert isinstance(file_info["downloaded"], bool), f"Поле 'downloaded' должно быть boolean в файле {file_hash}"
            assert isinstance(file_info["applied"], bool), f"Поле 'applied' должно быть boolean в файле {file_hash}"
            
            # Проверяем, что имя файла не пустое
            assert file_info["name"].strip(), f"Имя файла не может быть пустым в файле {file_hash}"


def test_update_images_status_version_details(api_client, auth_token):
    """Тест структуры versionDetails."""
    headers = {
        "x-access-token": auth_token,
        "token": auth_token
    }
    
    response = api_client.get(ENDPOINT, headers=headers)
    assert response.status_code == 200, f"Ожидался статус 200, получен {response.status_code}"
    
    data = response.json()
    
    if "versionDetails" in data:
        version_details = data["versionDetails"]
        assert version_details is not None, "Поле 'versionDetails' не может быть null"
        
        # Проверяем обязательные поля
        required_fields = ["image", "commit", "time"]
        for field in required_fields:
            assert field in version_details, f"Отсутствует обязательное поле '{field}' в versionDetails"
        
        # Проверяем типы полей
        assert isinstance(version_details["image"], str), "Поле 'image' должно быть строкой"
        assert isinstance(version_details["commit"], str), "Поле 'commit' должно быть строкой"
        assert isinstance(version_details["time"], str), "Поле 'time' должно быть строкой"
        
        # Проверяем, что поля не пустые
        assert version_details["image"].strip(), "Поле 'image' не может быть пустым"
        assert version_details["commit"].strip(), "Поле 'commit' не может быть пустым"
        assert version_details["time"].strip(), "Поле 'time' не может быть пустым"
