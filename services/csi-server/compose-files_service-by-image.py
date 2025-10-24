"""
Тесты для эндпоинта /compose-files/service-by-image сервиса csi-server.

Проверяется:
- Статус-код 200 OK
- Соответствие структуры ответа схеме (массив объектов сервисов)
- Устойчивость к 35+ различным query-параметрам
- Вывод cURL-команды при ошибке в параметризованных тестах
"""
import pytest
import json
from collections.abc import Mapping, Sequence

ENDPOINT = "/compose-files/service-by-image"

# Схема ответа для compose-files/service-by-image на основе реального ответа API
SERVICE_BY_IMAGE_SCHEMA = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "serviceName": {"type": "string"},
            "stackId": {"type": "string"}
        },
        "required": ["serviceName", "stackId"]
    }
}

# Осмысленная параметризация для тестирования эндпоинта
PARAMS = [
    # --- Базовые позитивные сценарии ---
    pytest.param({"image": "nginx:latest"}, 200, id="P01: nginx_latest"),
    pytest.param({"image": "nginx:1.21-alpine"}, 200, id="P02: nginx_alpine"),
    pytest.param({"image": "postgres:13-alpine"}, 200, id="P03: postgres_alpine"),
    pytest.param({"image": "postgres:13"}, 200, id="P04: postgres_13"),
    pytest.param({"image": "redis:6-alpine"}, 200, id="P05: redis_alpine"),
    
    # --- Негативные сценарии ---
    pytest.param({}, 400, id="P06: no_image_parameter"),
    
    # --- Различные образы nginx ---
    pytest.param({"image": "nginx"}, 200, id="P07: nginx_no_tag"),
    pytest.param({"image": "nginx:1.21"}, 200, id="P08: nginx_1_21"),
    pytest.param({"image": "nginx:alpine"}, 200, id="P09: nginx_alpine_no_version"),
    
    # --- Различные образы postgres ---
    pytest.param({"image": "postgres"}, 200, id="P10: postgres_no_tag"),
    pytest.param({"image": "postgres:13.0"}, 200, id="P11: postgres_13_0"),
    pytest.param({"image": "postgres:alpine"}, 200, id="P12: postgres_alpine"),
    
    # --- Различные образы redis ---
    pytest.param({"image": "redis"}, 200, id="P13: redis_no_tag"),
    pytest.param({"image": "redis:6"}, 200, id="P14: redis_6"),
    pytest.param({"image": "redis:alpine"}, 200, id="P15: redis_alpine"),
    
    # --- Различные образы node ---
    pytest.param({"image": "node:16-alpine"}, 200, id="P16: node_16_alpine"),
    pytest.param({"image": "node:16"}, 200, id="P17: node_16"),
    pytest.param({"image": "node:alpine"}, 200, id="P18: node_alpine"),
    
    # --- Фильтрация и поиск ---
    pytest.param({"image": "nginx", "exact": "true"}, 200, id="P19: nginx_exact_match"),
    pytest.param({"image": "nginx", "exact": "false"}, 200, id="P20: nginx_partial_match"),
    pytest.param({"image": "nginx", "case_sensitive": "true"}, 200, id="P21: nginx_case_sensitive"),
    pytest.param({"image": "nginx", "case_sensitive": "false"}, 200, id="P22: nginx_case_insensitive"),
    pytest.param({"image": "nginx", "regex": "true"}, 200, id="P23: nginx_regex"),
    
    # --- Дополнительные параметры ---
    pytest.param({"image": "nginx:latest", "limit": "10"}, 200, id="P24: nginx_limit_10"),
    pytest.param({"image": "nginx:latest", "offset": "0"}, 200, id="P25: nginx_offset_0"),
    pytest.param({"image": "nginx:latest", "sort": "serviceName"}, 200, id="P26: nginx_sort_service"),
    pytest.param({"image": "nginx:latest", "sort": "stackId"}, 200, id="P27: nginx_sort_stack"),
    pytest.param({"image": "nginx:latest", "order": "asc"}, 200, id="P28: nginx_order_asc"),
    
    # --- Форматирование ответа ---
    pytest.param({"image": "nginx:latest", "format": "json"}, 200, id="P29: nginx_format_json"),
    pytest.param({"image": "nginx:latest", "pretty": "true"}, 200, id="P30: nginx_pretty_true"),
    pytest.param({"image": "nginx:latest", "pretty": "false"}, 200, id="P31: nginx_pretty_false"),
    pytest.param({"image": "nginx:latest", "indent": "2"}, 200, id="P32: nginx_indent_2"),
    pytest.param({"image": "nginx:latest", "indent": "4"}, 200, id="P33: nginx_indent_4"),
    
    # --- Детализация ответа ---
    pytest.param({"image": "nginx:latest", "verbose": "true"}, 200, id="P34: nginx_verbose_true"),
    pytest.param({"image": "nginx:latest", "verbose": "false"}, 200, id="P35: nginx_verbose_false"),
    pytest.param({"image": "nginx:latest", "details": "true"}, 200, id="P36: nginx_details_true"),
    pytest.param({"image": "nginx:latest", "details": "false"}, 200, id="P37: nginx_details_false"),
    pytest.param({"image": "nginx:latest", "expand": "true"}, 200, id="P38: nginx_expand_true"),
    
    # --- Комбинированные параметры ---
    pytest.param({"image": "nginx:latest", "limit": "5", "sort": "serviceName"}, 200, id="P39: nginx_limit_sort"),
    pytest.param({"image": "nginx:latest", "pretty": "true", "indent": "2"}, 200, id="P40: nginx_pretty_indent"),
    pytest.param({"image": "nginx:latest", "verbose": "true", "details": "true"}, 200, id="P41: nginx_verbose_details"),
    pytest.param({"image": "nginx:latest", "exact": "true", "case_sensitive": "true"}, 200, id="P42: nginx_exact_case"),
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


def _get_available_images(api_client, auth_token):
    """Получает список доступных образов из compose files."""
    headers = {
        'x-access-token': auth_token,
        'token': auth_token
    }
    
    response = api_client.get("/compose-files", headers=headers)
    if response.status_code != 200:
        pytest.skip(f"Не удалось получить данные compose files. Статус: {response.status_code}")
    
    data = response.json()
    if not data:
        pytest.skip("Список compose files пуст")
    
    # Извлекаем все уникальные образы
    images = set()
    for compose_file in data:
        services = compose_file.get('composeFile', {}).get('services', {})
        for service in services.values():
            if 'image' in service:
                images.add(service['image'])
    
    if not images:
        pytest.skip("Образы не найдены в compose files")
    
    return list(images)


@pytest.mark.parametrize("params, expected_status", PARAMS)
def test_compose_files_service_by_image_parametrized(api_client, auth_token, params, expected_status):
    """
    Основной параметризованный тест для эндпоинта /compose-files/service-by-image.
    1. Получает актуальные данные о доступных образах.
    2. Отправляет GET-запрос с указанными параметрами.
    3. Проверяет соответствие статус-кода ожидаемому.
    4. Для успешных ответов (200) валидирует схему JSON.
    5. В случае падения теста выводит полную cURL-команду для воспроизведения.
    """
    try:
        # Добавляем заголовки авторизации
        headers = {
            'x-access-token': auth_token,
            'token': auth_token
        }
        
        # Если это тест без параметра image (негативный сценарий)
        if not params:
            response = api_client.get(ENDPOINT, headers=headers)
        else:
            # Получаем актуальные образы для позитивных тестов
            available_images = _get_available_images(api_client, auth_token)
            
            # Если в параметрах указан конкретный образ, проверяем его наличие
            if 'image' in params:
                image_param = params['image']
                # Если образ не найден в доступных, пропускаем тест
                if image_param not in available_images and not any(img.startswith(image_param.split(':')[0]) for img in available_images):
                    pytest.skip(f"Образ {image_param} не найден в доступных образах: {available_images}")
            
            response = api_client.get(ENDPOINT, params=params, headers=headers)
        
        # 1. Проверка статус-кода
        assert response.status_code == expected_status, \
            f"Ожидался статус-код {expected_status}, получен {response.status_code}. Ответ: {response.text}"

        # 2. Валидация схемы ответа
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list), f"Тело ответа не является массивом JSON, получено: {type(data).__name__}"
            _check_types_recursive(data, SERVICE_BY_IMAGE_SCHEMA)
        elif response.status_code == 400:
            # Для негативных тестов проверяем структуру ошибки
            data = response.json()
            assert "error" in data, "Ожидалось поле 'error' в ответе с ошибкой"
            assert "statusCode" in data["error"], "Ожидалось поле 'statusCode' в ошибке"
            assert "message" in data["error"], "Ожидалось поле 'message' в ошибке"

    except (AssertionError, json.JSONDecodeError) as e:
        # 3. Формирование и вывод детального отчета об ошибке
        curl_command = _format_curl_command(api_client, ENDPOINT, params, auth_token)
        
        error_message = (
            f"\nТест с параметрами {params} упал.\n"
            f"Ошибка: {e}\n\n"
            "================= Failed Test Request (cURL) =================\n"
            f"{curl_command}\n"
            "============================================================="
        )
        pytest.fail(error_message, pytrace=False)


def test_compose_files_service_by_image_negative(api_client, auth_token):
    """
    Негативные тесты для эндпоинта /compose-files/service-by-image.
    Проверяет обработку некорректных параметров и ошибок.
    """
    headers = {
        'x-access-token': auth_token,
        'token': auth_token
    }
    
    # Тест с несуществующим образом
    response = api_client.get(ENDPOINT, params={"image": "non-existent-image:latest"}, headers=headers)
    # API может возвращать пустой массив или ошибку
    assert response.status_code in [200, 404, 400], f"Неожиданный статус для несуществующего образа: {response.status_code}"
    
    # Тест с некорректными параметрами
    response = api_client.get(ENDPOINT, params={"image": "nginx:latest", "invalid_param": "value"}, headers=headers)
    # API может игнорировать неизвестные параметры или возвращать ошибку
    assert response.status_code in [200, 400, 422], f"Неожиданный статус для некорректных параметров: {response.status_code}"
    
    # Тест с пустым значением image
    response = api_client.get(ENDPOINT, params={"image": ""}, headers=headers)
    assert response.status_code in [400, 422], f"Ожидался статус 400 или 422 для пустого image, получен {response.status_code}"
    
    # Тест с null значением image (API возвращает 200 с пустым массивом)
    response = api_client.get(ENDPOINT, params={"image": "null"}, headers=headers)
    assert response.status_code == 200, f"Ожидался статус 200 для null image, получен {response.status_code}"
    data = response.json()
    assert isinstance(data, list), "Ответ должен быть массивом"
    assert len(data) == 0, "Массив должен быть пустым для несуществующего образа"


def test_compose_files_service_by_image_schema_validation(api_client, auth_token):
    """
    Детальная валидация схемы ответа для эндпоинта /compose-files/service-by-image.
    Проверяет все обязательные и необязательные поля.
    """
    available_images = _get_available_images(api_client, auth_token)
    test_image = available_images[0] if available_images else "nginx:latest"
    
    headers = {
        'x-access-token': auth_token,
        'token': auth_token
    }
    
    response = api_client.get(ENDPOINT, params={"image": test_image}, headers=headers)
    
    assert response.status_code == 200, f"Ожидался статус 200, получен {response.status_code}"
    
    data = response.json()
    assert isinstance(data, list), "Ответ должен быть массивом"
    
    # Проверяем структуру каждого элемента в массиве
    for item in data:
        assert isinstance(item, dict), "Каждый элемент должен быть объектом"
        
        # Проверка обязательных полей
        assert "serviceName" in item, "Обязательное поле 'serviceName' отсутствует в ответе"
        assert isinstance(item["serviceName"], str), "Поле 'serviceName' должно быть строкой"
        
        assert "stackId" in item, "Обязательное поле 'stackId' отсутствует в ответе"
        assert isinstance(item["stackId"], str), "Поле 'stackId' должно быть строкой"


def test_compose_files_service_by_image_different_images(api_client, auth_token):
    """
    Тест для проверки работы с разными образами.
    """
    available_images = _get_available_images(api_client, auth_token)
    
    headers = {
        'x-access-token': auth_token,
        'token': auth_token
    }
    
    # Тестируем каждый доступный образ
    for image in available_images[:3]:  # Ограничиваем количество для производительности
        response = api_client.get(ENDPOINT, params={"image": image}, headers=headers)
        
        assert response.status_code == 200, f"Ошибка для образа {image}: статус {response.status_code}"
        
        data = response.json()
        assert isinstance(data, list), f"Ответ для образа {image} должен быть массивом"
        
        # Проверяем, что все элементы содержат корректные данные
        for item in data:
            assert "serviceName" in item, f"Поле 'serviceName' отсутствует для образа {image}"
            assert "stackId" in item, f"Поле 'stackId' отсутствует для образа {image}"


def test_compose_files_service_by_image_response_consistency(api_client, auth_token):
    """
    Тест для проверки консистентности ответов API.
    """
    available_images = _get_available_images(api_client, auth_token)
    test_image = available_images[0] if available_images else "nginx:latest"
    
    headers = {
        'x-access-token': auth_token,
        'token': auth_token
    }
    
    # Выполняем несколько запросов и сравниваем ответы
    responses = []
    for _ in range(3):
        response = api_client.get(ENDPOINT, params={"image": test_image}, headers=headers)
        assert response.status_code == 200, f"Ожидался статус 200, получен {response.status_code}"
        responses.append(response.json())
    
    # Проверяем, что все ответы идентичны
    for i in range(1, len(responses)):
        assert responses[i] == responses[0], f"Ответы не консистентны между запросами {i} и 0"


def test_compose_files_service_by_image_empty_response(api_client, auth_token):
    """
    Тест для проверки обработки пустого ответа.
    """
    headers = {
        'x-access-token': auth_token,
        'token': auth_token
    }
    
    # Тест с образом, который точно не существует
    response = api_client.get(ENDPOINT, params={"image": "definitely-non-existent-image:999.999"}, headers=headers)
    
    # API может возвращать пустой массив или ошибку
    if response.status_code == 200:
        data = response.json()
        assert isinstance(data, list), "Ответ должен быть массивом"
        # Пустой массив - это валидный ответ
    else:
        assert response.status_code in [404, 400, 422], f"Неожиданный статус для несуществующего образа: {response.status_code}"


def test_compose_files_service_by_image_with_filters(api_client, auth_token):
    """
    Тест для проверки работы с дополнительными фильтрами.
    """
    available_images = _get_available_images(api_client, auth_token)
    test_image = available_images[0] if available_images else "nginx:latest"
    
    headers = {
        'x-access-token': auth_token,
        'token': auth_token
    }
    
    # Тест с различными комбинациями фильтров
    filter_combinations = [
        {"image": test_image, "limit": "5"},
        {"image": test_image, "sort": "serviceName"},
        {"image": test_image, "pretty": "true"},
        {"image": test_image, "verbose": "true"},
        {"image": test_image, "limit": "3", "sort": "stackId"}
    ]
    
    for filters in filter_combinations:
        response = api_client.get(ENDPOINT, params=filters, headers=headers)
        
        # API может поддерживать или игнорировать дополнительные параметры
        assert response.status_code in [200, 400, 422], f"Неожиданный статус для фильтров {filters}: {response.status_code}"
        
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list), f"Ответ для фильтров {filters} должен быть массивом"
            
            # Проверяем базовую структуру элементов
            for item in data:
                assert "serviceName" in item, f"Поле 'serviceName' отсутствует для фильтров {filters}"
                assert "stackId" in item, f"Поле 'stackId' отсутствует для фильтров {filters}"
