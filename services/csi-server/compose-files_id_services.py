"""
Тесты для эндпоинта /compose-files/{id}/services сервиса csi-server.

Проверяется:
- Статус-код 200 OK
- Соответствие структуры ответа схеме (массив объектов сервисов)
- Устойчивость к 35+ различным query-параметрам
- Вывод cURL-команды при ошибке в параметризованных тестах
"""
import pytest
import json
from collections.abc import Mapping, Sequence

ENDPOINT = "/compose-files"

# Схема ответа для compose-files/{id}/services на основе реального ответа API
SERVICE_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "properties": {"type": "null"},
        "swagger": {"type": "null"}
    },
    "required": ["name"]
}

# Параметры для тестирования
TEST_PARAMS = [
    {},  # Без параметров
    {"fields": "name"},
    {"fields": "properties"},
    {"fields": "swagger"},
    {"fields": "name,properties"},
    {"include": "web"},
    {"format": "json"},
    {"pretty": "true"},
    {"pretty": "false"},
    {"indent": "2"},
    {"indent": "4"},
    {"verbose": "true"},
    {"verbose": "false"},
    {"details": "true"},
    {"details": "false"},
    {"expand": "true"},
    {"exclude": "properties"},
    {"exclude": "swagger"},
    {"include": "web"},
    {"include": "db"},
    {"include": "redis"},
    {"version": "latest"},
    {"version": "1.0"},
    {"api_version": "v1"},
    {"schema_version": "1"},
    {"service_version": "1.0"},
    {"locale": "en"},
    {"locale": "ru"},
    {"timezone": "UTC"},
    {"timezone": "Europe/Moscow"},
    {"date_format": "ISO"},
    {"mask_secrets": "true"},
    {"mask_secrets": "false"},
    {"hide_passwords": "true"},
    {"sanitize": "true"},
    {"encrypt": "false"},
    {"cache": "true"},
    {"cache": "false"},
    {"fields": "name", "pretty": "true"},
    {"include": "web", "exclude": "properties"},
    {"verbose": "true", "format": "json"},
    {"mask_secrets": "true", "details": "true"},
]


def _check_types_recursive(obj, schema):
    """Рекурсивно проверяет типы данных в объекте на соответствие схеме."""
    if "anyOf" in schema:
        assert any(_try_type(obj, s) for s in schema["anyOf"]), f"Тип {type(obj)} не соответствует ни одной из схем в anyOf"
        return

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


def _try_type(obj, schema):
    """Вспомогательная функция для проверки типа в 'anyOf'."""
    try:
        _check_types_recursive(obj, schema)
        return True
    except AssertionError:
        return False


def _format_curl_command(api_client, endpoint, id_param, params, auth_token):
    """Формирует и возвращает cURL-строку для воспроизведения запроса."""
    base_url = getattr(api_client, "base_url", "http://127.0.0.1:2999")
    full_url = f"{base_url.rstrip('/')}/{endpoint.lstrip('/')}/{id_param}/services"
    
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


@pytest.mark.parametrize("param_index", range(len(TEST_PARAMS)))
def test_compose_files_id_services_parametrized(api_client, auth_token, param_index):
    """
    Параметризованный тест для эндпоинта /compose-files/{id}/services.
    Получает реальные ID из API и тестирует с различными параметрами.
    """
    # 1. Получаем реальные ID из API
    headers = {
        'x-access-token': auth_token,
        'token': auth_token
    }
    
    compose_response = api_client.get(ENDPOINT, headers=headers)
    assert compose_response.status_code == 200, f"Не удалось получить список compose файлов: {compose_response.status_code}"
    
    compose_data = compose_response.json()
    assert isinstance(compose_data, list), "Ответ должен быть массивом"
    if len(compose_data) == 0:
        pytest.skip("Список compose файлов пуст; проверена структура ответа массива")
    
    # Получаем ID из первого элемента
    valid_id = compose_data[0].get('id')
    assert valid_id, "ID не найден в ответе"
    
    # 2. Тестируем эндпоинт services с полученным ID
    params = TEST_PARAMS[param_index]
    
    try:
        response = api_client.get(f"{ENDPOINT}/{valid_id}/services", params=params, headers=headers)
        
        # Проверка статус-кода
        assert response.status_code == 200, \
            f"Ожидался статус-код 200, получен {response.status_code}. Ответ: {response.text}"

        # Валидация схемы ответа
        data = response.json()
        assert isinstance(data, list), f"Тело ответа не является массивом JSON, получено: {type(data).__name__}"
        
        # Проверяем структуру каждого сервиса в ответе
        for service_data in data:
            _check_types_recursive(service_data, SERVICE_SCHEMA)

    except (AssertionError, json.JSONDecodeError) as e:
        # Формирование и вывод детального отчета об ошибке
        curl_command = _format_curl_command(api_client, ENDPOINT, valid_id, params, auth_token)
        
        error_message = (
            f"\nТест с параметрами params={params} упал.\n"
            f"Ошибка: {e}\n\n"
            "================= Failed Test Request (cURL) ================\n"
            f"{curl_command}\n"
            "============================================================="
        )
        pytest.fail(error_message, pytrace=False)


def test_compose_files_id_services_negative(api_client, auth_token):
    """
    Негативные тесты для эндпоинта /compose-files/{id}/services.
    Проверяет 404 ошибки для несуществующих ID.
    """
    invalid_ids = ["non-existent-id", "invalid-stack-123", "test-stack-123", "compose-test", "docker-app"]
    
    headers = {
        'x-access-token': auth_token,
        'token': auth_token
    }
    
    for invalid_id in invalid_ids:
        try:
            response = api_client.get(f"{ENDPOINT}/{invalid_id}/services", headers=headers)
            
            # Проверка статус-кода
            assert response.status_code == 404, \
                f"Для несуществующего ID '{invalid_id}' ожидался статус-код 404, получен {response.status_code}"

        except (AssertionError, json.JSONDecodeError) as e:
            # Формирование и вывод детального отчета об ошибке
            curl_command = _format_curl_command(api_client, ENDPOINT, invalid_id, {}, auth_token)
            
            error_message = (
                f"\nНегативный тест с ID '{invalid_id}' упал.\n"
                f"Ошибка: {e}\n\n"
                "================= Failed Test Request (cURL) ================\n"
                f"{curl_command}\n"
                "============================================================="
            )
            pytest.fail(error_message, pytrace=False)
