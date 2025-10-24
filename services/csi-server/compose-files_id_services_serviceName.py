"""
Тесты для эндпоинта /compose-files/{id}/services/{serviceName} сервиса csi-server.

Проверяется:
- Статус-код 200 OK
- Соответствие структуры ответа схеме (объект сервиса)
- Устойчивость к 35+ различным query-параметрам
- Вывод cURL-команды при ошибке в параметризованных тестах
"""
import pytest
import json
from collections.abc import Mapping, Sequence

ENDPOINT = "/compose-files"

# Схема ответа для compose-files/{id}/services/{serviceName} на основе реального ответа API
SERVICE_DETAIL_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "properties": {"type": "null"},
        "swagger": {"type": "null"}
    },
    "required": ["name"]
}

# Осмысленная параметризация для тестирования эндпоинта
PARAMS = [
    # --- Базовые позитивные сценарии ---
    pytest.param({}, 200, id="P01: no_params"),
    pytest.param({"fields": "name"}, 200, id="P02: fields_name"),
    pytest.param({"fields": "properties"}, 200, id="P03: fields_properties"),
    pytest.param({"fields": "swagger"}, 200, id="P04: fields_swagger"),
    pytest.param({"fields": "name,properties"}, 200, id="P05: fields_multiple"),
    
    # --- Форматирование ответа ---
    pytest.param({"format": "json"}, 200, id="P06: format_json"),
    pytest.param({"pretty": "true"}, 200, id="P07: pretty_true"),
    pytest.param({"pretty": "false"}, 200, id="P08: pretty_false"),
    pytest.param({"indent": "2"}, 200, id="P09: indent_2"),
    pytest.param({"indent": "4"}, 200, id="P10: indent_4"),
    
    # --- Детализация ответа ---
    pytest.param({"verbose": "true"}, 200, id="P11: verbose_true"),
    pytest.param({"verbose": "false"}, 200, id="P12: verbose_false"),
    pytest.param({"details": "true"}, 200, id="P13: details_true"),
    pytest.param({"details": "false"}, 200, id="P14: details_false"),
    pytest.param({"expand": "true"}, 200, id="P15: expand_true"),
    
    # --- Исключение полей ---
    pytest.param({"exclude": "properties"}, 200, id="P16: exclude_properties"),
    pytest.param({"exclude": "swagger"}, 200, id="P17: exclude_swagger"),
    pytest.param({"exclude": "name"}, 200, id="P18: exclude_name"),
    pytest.param({"exclude": "properties,swagger"}, 200, id="P19: exclude_multiple"),
    
    # --- Версионирование ---
    pytest.param({"version": "latest"}, 200, id="P20: version_latest"),
    pytest.param({"version": "1.0"}, 200, id="P21: version_1_0"),
    pytest.param({"api_version": "v1"}, 200, id="P22: api_version_v1"),
    pytest.param({"schema_version": "1"}, 200, id="P23: schema_version_1"),
    pytest.param({"service_version": "1.0"}, 200, id="P24: service_version_1_0"),
    
    # --- Локализация ---
    pytest.param({"locale": "en"}, 200, id="P25: locale_en"),
    pytest.param({"locale": "ru"}, 200, id="P26: locale_ru"),
    pytest.param({"timezone": "UTC"}, 200, id="P27: timezone_utc"),
    pytest.param({"timezone": "Europe/Moscow"}, 200, id="P28: timezone_moscow"),
    pytest.param({"date_format": "ISO"}, 200, id="P29: date_format_iso"),
    
    # --- Безопасность ---
    pytest.param({"mask_secrets": "true"}, 200, id="P30: mask_secrets_true"),
    pytest.param({"mask_secrets": "false"}, 200, id="P31: mask_secrets_false"),
    pytest.param({"hide_passwords": "true"}, 200, id="P32: hide_passwords_true"),
    pytest.param({"sanitize": "true"}, 200, id="P33: sanitize_true"),
    pytest.param({"encrypt": "false"}, 200, id="P34: encrypt_false"),
    
    # --- Комбинированные параметры ---
    pytest.param({"fields": "name", "pretty": "true"}, 200, id="P40: fields_name_pretty"),
    pytest.param({"exclude": "properties", "verbose": "true"}, 200, id="P41: exclude_properties_verbose"),
    pytest.param({"mask_secrets": "true", "details": "true"}, 200, id="P42: mask_secrets_details"),
    pytest.param({"format": "json", "indent": "2"}, 200, id="P43: format_json_indent"),
    pytest.param({"locale": "en", "timezone": "UTC"}, 200, id="P44: locale_timezone"),
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


def _format_curl_command(api_client, endpoint, id_param, service_name, params, auth_token):
    """Формирует и возвращает cURL-строку для воспроизведения запроса."""
    base_url = getattr(api_client, "base_url", "http://127.0.0.1:2999")
    full_url = f"{base_url.rstrip('/')}/{endpoint.lstrip('/')}/{id_param}/services/{service_name}"
    
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


def _get_compose_files_data(api_client, auth_token):
    """Получает данные о compose files для извлечения id и service names."""
    headers = {
        'x-access-token': auth_token,
        'token': auth_token
    }
    
    response = api_client.get(ENDPOINT, headers=headers)
    if response.status_code != 200:
        pytest.skip(f"Не удалось получить данные compose files. Статус: {response.status_code}")
    
    data = response.json()
    if not data:
        pytest.skip("Список compose files пуст")
    
    # Берем первый доступный compose file
    compose_file = data[0]
    compose_id = compose_file.get('id')
    
    if not compose_id:
        pytest.skip("ID compose file не найден")
    
    # Извлекаем service names из compose file
    services = compose_file.get('composeFile', {}).get('services', {})
    service_names = list(services.keys())
    
    if not service_names:
        pytest.skip("Сервисы не найдены в compose file")
    
    return compose_id, service_names[0]  # Возвращаем первый сервис


@pytest.mark.parametrize("params, expected_status", PARAMS)
def test_compose_files_id_services_serviceName_parametrized(api_client, auth_token, params, expected_status):
    """
    Основной параметризованный тест для эндпоинта /compose-files/{id}/services/{serviceName}.
    1. Получает актуальные данные о compose files для извлечения id и service name.
    2. Отправляет GET-запрос с указанными параметрами.
    3. Проверяет соответствие статус-кода ожидаемому.
    4. Для успешных ответов (200) валидирует схему JSON.
    5. В случае падения теста выводит полную cURL-команду для воспроизведения.
    """
    try:
        # Получаем актуальные данные
        compose_id, service_name = _get_compose_files_data(api_client, auth_token)
        
        # Добавляем заголовки авторизации
        headers = {
            'x-access-token': auth_token,
            'token': auth_token
        }
        
        # Формируем endpoint с параметрами
        endpoint = f"{ENDPOINT}/{compose_id}/services/{service_name}"
        
        response = api_client.get(endpoint, params=params, headers=headers)
        
        # 1. Проверка статус-кода
        assert response.status_code == expected_status, \
            f"Ожидался статус-код {expected_status}, получен {response.status_code}. Ответ: {response.text}"

        # 2. Валидация схемы ответа
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, dict), f"Тело ответа не является объектом JSON, получено: {type(data).__name__}"
            _check_types_recursive(data, SERVICE_DETAIL_SCHEMA)

    except (AssertionError, json.JSONDecodeError) as e:
        # 3. Формирование и вывод детального отчета об ошибке
        compose_id, service_name = _get_compose_files_data(api_client, auth_token)
        curl_command = _format_curl_command(api_client, ENDPOINT, compose_id, service_name, params, auth_token)
        
        error_message = (
            f"\nТест с параметрами {params} упал.\n"
            f"Ошибка: {e}\n\n"
            "================= Failed Test Request (cURL) =================\n"
            f"{curl_command}\n"
            "============================================================="
        )
        pytest.fail(error_message, pytrace=False)


def test_compose_files_id_services_serviceName_negative(api_client, auth_token):
    """
    Негативные тесты для эндпоинта /compose-files/{id}/services/{serviceName}.
    Проверяет обработку некорректных параметров и ошибок.
    """
    # Получаем актуальные данные
    compose_id, service_name = _get_compose_files_data(api_client, auth_token)
    
    headers = {
        'x-access-token': auth_token,
        'token': auth_token
    }
    
    # Тест с несуществующим ID
    endpoint = f"{ENDPOINT}/non-existent-id/services/{service_name}"
    response = api_client.get(endpoint, headers=headers)
    assert response.status_code in [404, 400], f"Ожидался статус 404 или 400 для несуществующего ID, получен {response.status_code}"
    
    # Тест с несуществующим service name
    endpoint = f"{ENDPOINT}/{compose_id}/services/non-existent-service"
    response = api_client.get(endpoint, headers=headers)
    assert response.status_code in [404, 400], f"Ожидался статус 404 или 400 для несуществующего service, получен {response.status_code}"
    
    # Тест с некорректными параметрами
    endpoint = f"{ENDPOINT}/{compose_id}/services/{service_name}"
    response = api_client.get(endpoint, params={"invalid_param": "value"}, headers=headers)
    # API может игнорировать неизвестные параметры или возвращать ошибку
    assert response.status_code in [200, 400, 422], f"Неожиданный статус для некорректных параметров: {response.status_code}"


def test_compose_files_id_services_serviceName_schema_validation(api_client, auth_token):
    """
    Детальная валидация схемы ответа для эндпоинта /compose-files/{id}/services/{serviceName}.
    Проверяет все обязательные и необязательные поля.
    """
    compose_id, service_name = _get_compose_files_data(api_client, auth_token)
    
    headers = {
        'x-access-token': auth_token,
        'token': auth_token
    }
    
    endpoint = f"{ENDPOINT}/{compose_id}/services/{service_name}"
    response = api_client.get(endpoint, headers=headers)
    
    assert response.status_code == 200, f"Ожидался статус 200, получен {response.status_code}"
    
    data = response.json()
    
    # Проверка обязательных полей
    assert "name" in data, "Обязательное поле 'name' отсутствует в ответе"
    assert isinstance(data["name"], str), "Поле 'name' должно быть строкой"
    
    # Проверка необязательных полей (если присутствуют)
    if "properties" in data:
        # properties может быть null или объектом
        assert data["properties"] is None or isinstance(data["properties"], dict), \
            "Поле 'properties' должно быть null или объектом"
    
    if "swagger" in data:
        # swagger может быть null или объектом
        assert data["swagger"] is None or isinstance(data["swagger"], dict), \
            "Поле 'swagger' должно быть null или объектом"


def test_compose_files_id_services_serviceName_different_services(api_client, auth_token):
    """
    Тест для проверки работы с разными сервисами в одном compose file.
    """
    compose_id, _ = _get_compose_files_data(api_client, auth_token)
    
    headers = {
        'x-access-token': auth_token,
        'token': auth_token
    }
    
    # Получаем список всех сервисов в compose file
    response = api_client.get(f"{ENDPOINT}/{compose_id}", headers=headers)
    if response.status_code == 200:
        data = response.json()
        services = data.get('composeFile', {}).get('services', {})
        
        # Тестируем каждый сервис
        for service_name in services.keys():
            endpoint = f"{ENDPOINT}/{compose_id}/services/{service_name}"
            response = api_client.get(endpoint, headers=headers)
            
            assert response.status_code == 200, f"Ошибка для сервиса {service_name}: статус {response.status_code}"
            
            service_data = response.json()
            assert "name" in service_data, f"Поле 'name' отсутствует для сервиса {service_name}"
            assert service_data["name"] == service_name, f"Имя сервиса не совпадает: ожидалось {service_name}, получено {service_data['name']}"


def test_compose_files_id_services_serviceName_response_consistency(api_client, auth_token):
    """
    Тест для проверки консистентности ответов API.
    """
    compose_id, service_name = _get_compose_files_data(api_client, auth_token)
    
    headers = {
        'x-access-token': auth_token,
        'token': auth_token
    }
    
    endpoint = f"{ENDPOINT}/{compose_id}/services/{service_name}"
    
    # Выполняем несколько запросов и сравниваем ответы
    responses = []
    for _ in range(3):
        response = api_client.get(endpoint, headers=headers)
        assert response.status_code == 200, f"Ожидался статус 200, получен {response.status_code}"
        responses.append(response.json())
    
    # Проверяем, что все ответы идентичны
    for i in range(1, len(responses)):
        assert responses[i] == responses[0], f"Ответы не консистентны между запросами {i} и 0"
