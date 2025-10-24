"""
Тесты для эндпоинта /manager/stacks сервиса csi-server.

Проверяется:
- Статус-код 200 OK
- Валидация структуры JSON ответа (массив строк)
- Проверка типов данных
- Вывод cURL-команды при ошибке
"""
import pytest
import json
from typing import List

ENDPOINT = "/manager/stacks"

# Схема ответа API на основе реального ответа
RESPONSE_SCHEMA = {
    "type": "array",
    "items": {
        "type": "string"
    },
    "minItems": 1,
    "uniqueItems": True
}

# 35 параметров для тестирования API (соответствует R1: 35-50 параметров)
PARAMS = [
    pytest.param({}, 200, id="no_params"),
    pytest.param({"format": "json"}, 200, id="format_json"),
    pytest.param({"pretty": "true"}, 200, id="pretty_true"),
    pytest.param({"fields": "name"}, 200, id="fields_name"),
    pytest.param({"fields": "id,name"}, 200, id="fields_id_name"),
    pytest.param({"exclude": "metadata"}, 200, id="exclude_metadata"),
    pytest.param({"include": "active"}, 200, id="include_active"),
    pytest.param({"filter": "status:active"}, 200, id="filter_status_active"),
    pytest.param({"filter": "type:core"}, 200, id="filter_type_core"),
    pytest.param({"filter": "name:csi"}, 200, id="filter_name_csi"),
    pytest.param({"sort": "name"}, 200, id="sort_name"),
    pytest.param({"sort": "name:asc"}, 200, id="sort_name_asc"),
    pytest.param({"sort": "name:desc"}, 200, id="sort_name_desc"),
    pytest.param({"order": "asc"}, 200, id="order_asc"),
    pytest.param({"order": "desc"}, 200, id="order_desc"),
    pytest.param({"limit": "10"}, 200, id="limit_10"),
    pytest.param({"limit": "50"}, 200, id="limit_50"),
    pytest.param({"offset": "0"}, 200, id="offset_0"),
    pytest.param({"offset": "5"}, 200, id="offset_5"),
    pytest.param({"page": "1"}, 200, id="page_1"),
    pytest.param({"page": "2"}, 200, id="page_2"),
    pytest.param({"per_page": "20"}, 200, id="per_page_20"),
    pytest.param({"per_page": "100"}, 200, id="per_page_100"),
    pytest.param({"version": "v1"}, 200, id="version_v1"),
    pytest.param({"version": "latest"}, 200, id="version_latest"),
    pytest.param({"cache": "true"}, 200, id="cache_true"),
    pytest.param({"cache": "false"}, 200, id="cache_false"),
    pytest.param({"timeout": "30"}, 200, id="timeout_30"),
    pytest.param({"timeout": "60"}, 200, id="timeout_60"),
    pytest.param({"locale": "en"}, 200, id="locale_en"),
    pytest.param({"locale": "ru"}, 200, id="locale_ru"),
    pytest.param({"timezone": "UTC"}, 200, id="timezone_utc"),
    pytest.param({"timezone": "Europe/Moscow"}, 200, id="timezone_moscow"),
    pytest.param({"debug": "true"}, 200, id="debug_true"),
    pytest.param({"debug": "false"}, 200, id="debug_false"),
]


def validate_response_structure(response_data: List[str]) -> None:
    """
    Валидирует структуру ответа API согласно схеме.
    
    Args:
        response_data: Данные ответа для валидации
        
    Raises:
        AssertionError: Если структура не соответствует схеме
    """
    # Проверяем, что ответ является списком
    assert isinstance(response_data, list), f"Ответ должен быть списком, получено: {type(response_data)}"
    
    # Проверяем минимальное количество элементов
    assert len(response_data) >= RESPONSE_SCHEMA["minItems"], \
        f"Ответ должен содержать минимум {RESPONSE_SCHEMA['minItems']} элементов, получено: {len(response_data)}"
    
    # Проверяем уникальность элементов
    assert len(response_data) == len(set(response_data)), "Все элементы списка должны быть уникальными"
    
    # Проверяем тип каждого элемента
    for i, item in enumerate(response_data):
        assert isinstance(item, str), f"Элемент {i} должен быть строкой, получено: {type(item)} (значение: {item})"
        assert len(item) > 0, f"Элемент {i} не может быть пустой строкой"


def validate_response_types(response_data: List[str]) -> None:
    """
    Валидирует типы данных в ответе.
    
    Args:
        response_data: Данные ответа для валидации типов
        
    Raises:
        AssertionError: Если типы данных не соответствуют ожидаемым
    """
    # Проверяем, что все элементы являются строками
    for i, item in enumerate(response_data):
        assert isinstance(item, str), f"Элемент {i} должен быть строкой, получено: {type(item)}"
        
        # Проверяем, что строка не содержит только пробелы
        assert item.strip() != "", f"Элемент {i} не может состоять только из пробелов"
        
        # Проверяем, что строка не содержит специальные символы управления
        assert all(ord(char) >= 32 for char in item), f"Элемент {i} содержит недопустимые символы управления"


def validate_response_content(response_data: List[str]) -> None:
    """
    Валидирует содержимое ответа.
    Делает мягкую проверку: не требует обязательного наличия фиксированного набора стеков,
    а лишь проверяет корректность имен.
    
    Args:
        response_data: Данные ответа для валидации содержимого
        
    Raises:
        AssertionError: Если имена стеков не соответствуют требованиям
    """
    # Проверяем, что все элементы являются валидными именами стеков
    for item in response_data:
        # Имя стека должно содержать только буквы, цифры, дефисы и подчеркивания
        assert all(c.isalnum() or c in '-_' for c in item), \
            f"Имя стека '{item}' содержит недопустимые символы"
        
        # Имя стека не должно начинаться или заканчиваться дефисом
        assert not item.startswith('-') and not item.endswith('-'), \
            f"Имя стека '{item}' не должно начинаться или заканчиваться дефисом"


@pytest.mark.parametrize("params,expected_status", PARAMS)
def test_manager_stacks_api(api_client, auth_token, params, expected_status):
    """
    Комплексный тест для endpoint /manager/stacks.
    
    Проверяет:
    - Статус-код ответа
    - Структуру JSON ответа
    - Типы данных
    - Содержимое ответа
    - Консистентность структуры
    - Формат JSON
    - Заголовки ответа
    """
    headers = {
        'x-access-token': auth_token,
        'token': auth_token
    }
    
    response = api_client.get(ENDPOINT, params=params, headers=headers)
    
    # Проверяем статус-код
    assert response.status_code == expected_status, \
        f"Ожидался статус {expected_status}, получен {response.status_code}. " \
        f"cURL: curl --location '{api_client.base_url}{ENDPOINT}' " \
        f"--header 'x-access-token: {auth_token}'"
    
    # Проверяем заголовки ответа
    assert 'application/json' in response.headers.get('content-type', ''), \
        f"Ответ должен содержать JSON, получен content-type: {response.headers.get('content-type')}"
    
    # Проверяем обязательные заголовки
    assert 'content-type' in response.headers, "Ответ должен содержать заголовок content-type"
    assert 'content-length' in response.headers, "Ответ должен содержать заголовок content-length"
    
    # Проверяем content-length
    content_length = response.headers.get('content-length', '')
    assert content_length.isdigit(), "Content-Length должен быть числом"
    assert int(content_length) > 0, "Content-Length должен быть больше 0"
    
    # Проверяем, что ответ не пустой
    assert response.content, "Ответ не должен быть пустым"
    
    # Проверяем, что ответ начинается с '[' и заканчивается на ']'
    content_str = response.content.decode('utf-8').strip()
    assert content_str.startswith('['), "JSON ответ должен начинаться с '['"
    assert content_str.endswith(']'), "JSON ответ должен заканчиваться на ']'"
    
    # Парсим JSON ответ
    try:
        response_data = response.json()
    except json.JSONDecodeError as e:
        pytest.fail(f"Не удалось распарсить JSON ответ: {e}. " \
                   f"cURL: curl --location '{api_client.base_url}{ENDPOINT}' " \
                   f"--header 'x-access-token: {auth_token}'")
    
    # Валидируем структуру ответа
    validate_response_structure(response_data)
    
    # Валидируем типы данных
    validate_response_types(response_data)
    
    # Валидируем содержимое ответа
    validate_response_content(response_data)
    
    # Проверяем, что ответ всегда является списком
    assert isinstance(response_data, list), \
        f"Ответ должен всегда быть списком, получено: {type(response_data)}"
    
    # Проверяем, что базовые стеки присутствуют независимо от параметров
    core_stacks = ["csi", "shared"]
    for core_stack in core_stacks:
        assert core_stack in response_data, \
            f"Базовый стек '{core_stack}' должен присутствовать в ответе независимо от параметров"
    
    # Проверяем размер ответа (должен быть разумным)
    assert len(response_data) > 0, "Размер ответа должен быть больше 0"
    assert len(response_data) < 1000, f"Размер ответа слишком большой: {len(response_data)} элементов"



