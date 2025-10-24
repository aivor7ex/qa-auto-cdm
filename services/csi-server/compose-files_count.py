"""
Тесты для эндпоинта /compose-files/count сервиса csi-server.

Проверяется:
- Статус-код 200 OK
- Соответствие структуры ответа схеме (число)
- Устойчивость к 35+ различным query-параметрам
- Вывод cURL-команды при ошибке в параметризованных тестах
"""
import pytest
import json
from collections.abc import Mapping, Sequence

ENDPOINT = "/compose-files/count"

# Схема ответа для compose-files/count на основе реального ответа API
COUNT_SCHEMA = {
    "type": "integer"
}

# Осмысленная параметризация для тестирования эндпоинта /compose-files/count
PARAMS = [
    # --- Базовые позитивные сценарии ---
    pytest.param({}, 200, id="P01: no_params"),
    pytest.param({"filter": '{"name": "test-stack"}'}, 200, id="P02: filter_by_name"),
    pytest.param({"filter": '{"id": "test-stack-123"}'}, 200, id="P03: filter_by_id"),
    pytest.param({"filter": '{"stack_id": "test-stack-123"}'}, 200, id="P04: filter_by_stack_id"),
    pytest.param({"filter": '{"stack_name": "test-stack"}'}, 200, id="P05: filter_by_stack_name"),
    
    # --- Фильтрация по версии compose ---
    pytest.param({"filter": '{"version": "3.8"}'}, 200, id="P06: filter_by_version_3_8"),
    pytest.param({"filter": '{"version": "3.7"}'}, 200, id="P07: filter_by_version_3_7"),
    pytest.param({"filter": '{"version": "3.9"}'}, 200, id="P08: filter_by_version_3_9"),
    pytest.param({"filter": '{"compose_version": "3.8"}'}, 200, id="P09: filter_by_compose_version"),
    
    # --- Фильтрация по сервисам ---
    pytest.param({"filter": '{"service": "web"}'}, 200, id="P10: filter_by_web_service"),
    pytest.param({"filter": '{"service": "db"}'}, 200, id="P11: filter_by_db_service"),
    pytest.param({"filter": '{"services": "web,db"}'}, 200, id="P12: filter_by_multiple_services"),
    pytest.param({"filter": '{"has_service": "web"}'}, 200, id="P13: filter_has_web_service"),
    pytest.param({"filter": '{"has_service": "db"}'}, 200, id="P14: filter_has_db_service"),
    
    # --- Фильтрация по образам ---
    pytest.param({"filter": '{"image": "nginx"}'}, 200, id="P15: filter_by_nginx_image"),
    pytest.param({"filter": '{"image": "postgres"}'}, 200, id="P16: filter_by_postgres_image"),
    pytest.param({"filter": '{"image": "nginx:latest"}'}, 200, id="P17: filter_by_nginx_latest"),
    pytest.param({"filter": '{"image": "postgres:13"}'}, 200, id="P18: filter_by_postgres_13"),
    
    # --- Фильтрация по портам ---
    pytest.param({"filter": '{"port": "80"}'}, 200, id="P19: filter_by_port_80"),
    pytest.param({"filter": '{"port": "80:80"}'}, 200, id="P20: filter_by_port_mapping"),
    pytest.param({"filter": '{"has_port": "80"}'}, 200, id="P21: filter_has_port_80"),
    pytest.param({"filter": '{"external_port": "80"}'}, 200, id="P22: filter_by_external_port"),
    
    # --- Фильтрация по переменным окружения ---
    pytest.param({"filter": '{"env": "POSTGRES_DB"}'}, 200, id="P23: filter_by_env_postgres_db"),
    pytest.param({"filter": '{"env": "POSTGRES_PASSWORD"}'}, 200, id="P24: filter_by_env_postgres_password"),
    pytest.param({"filter": '{"env": "POSTGRES_USER"}'}, 200, id="P25: filter_by_env_postgres_user"),
    pytest.param({"filter": '{"environment": "POSTGRES_DB=testdb"}'}, 200, id="P26: filter_by_environment_var"),
    
    # --- Фильтрация по volumes ---
    pytest.param({"filter": '{"volume": "postgres_data"}'}, 200, id="P27: filter_by_volume_name"),
    pytest.param({"filter": '{"volume": "postgres_data:/var/lib/postgresql/data"}'}, 200, id="P28: filter_by_volume_mapping"),
    pytest.param({"filter": '{"has_volume": "postgres_data"}'}, 200, id="P29: filter_has_volume"),
    
    # --- Поиск и фильтрация ---
    pytest.param({"search": "test"}, 200, id="P30: search_test"),
    pytest.param({"search": "stack"}, 200, id="P31: search_stack"),
    pytest.param({"search": "nginx"}, 200, id="P32: search_nginx"),
    pytest.param({"search": "postgres"}, 200, id="P33: search_postgres"),
    pytest.param({"q": "compose"}, 200, id="P34: query_compose"),
    pytest.param({"q": "docker"}, 200, id="P35: query_docker"),
    
    # --- Сортировка ---
    pytest.param({"sort": "name"}, 200, id="P36: sort_by_name_asc"),
    pytest.param({"sort": "-name"}, 200, id="P37: sort_by_name_desc"),
    pytest.param({"sort": "id"}, 200, id="P38: sort_by_id"),
    pytest.param({"sort": "-id"}, 200, id="P39: sort_by_id_desc"),
    pytest.param({"sort": "version"}, 200, id="P40: sort_by_version"),
    
    # --- Постраничная навигация ---
    pytest.param({"limit": "10"}, 200, id="P41: pagination_limit_10"),
    pytest.param({"limit": "1"}, 200, id="P42: pagination_limit_1"),
    pytest.param({"offset": "0"}, 200, id="P43: pagination_offset_0"),
    pytest.param({"limit": "5", "offset": "0"}, 200, id="P44: pagination_limit_offset"),
    
    # --- Комбинации параметров ---
    pytest.param({"sort": "name", "limit": "3"}, 200, id="P45: sort_and_limit"),
    pytest.param({"search": "test", "limit": "5"}, 200, id="P46: search_and_limit"),
    pytest.param({"filter": '{"service": "web"}', "sort": "name"}, 200, id="P47: service_and_sort"),
    
    # --- Специальные фильтры ---
    pytest.param({"filter": '{"status": "active"}'}, 200, id="P48: filter_by_active_status"),
    pytest.param({"filter": '{"status": "inactive"}'}, 200, id="P49: filter_by_inactive_status"),
    pytest.param({"filter": '{"type": "stack"}'}, 200, id="P50: filter_by_stack_type"),
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


@pytest.mark.parametrize("params, expected_status", PARAMS)
def test_compose_files_count_parametrized(api_client, auth_token, params, expected_status):
    """
    Основной параметризованный тест для эндпоинта /compose-files/count.
    1. Отправляет GET-запрос с указанными параметрами.
    2. Проверяет соответствие статус-кода ожидаемому.
    3. Для успешных ответов (200) валидирует схему JSON.
    4. В случае падения теста выводит полную cURL-команду для воспроизведения.
    """
    try:
        # Добавляем заголовки авторизации
        headers = {
            'x-access-token': auth_token,
            'token': auth_token
        }
        
        response = api_client.get(ENDPOINT, params=params, headers=headers)
        
        # 1. Проверка статус-кода
        assert response.status_code == expected_status, \
            f"Ожидался статус-код {expected_status}, получен {response.status_code}. Ответ: {response.text}"

        # 2. Валидация схемы ответа
        if response.status_code == 200:
            data = response.json()
            # Проверяем что ответ является числом
            _check_types_recursive(data, COUNT_SCHEMA)
            # Дополнительная проверка что count является неотрицательным числом
            assert data >= 0, f"Count должен быть неотрицательным, получено: {data}"

    except (AssertionError, json.JSONDecodeError) as e:
        # 3. Формирование и вывод детального отчета об ошибке
        curl_command = _format_curl_command(api_client, ENDPOINT, params, auth_token)
        
        error_message = (
            f"\nТест с параметрами {params} упал.\n"
            f"Ошибка: {e}\n\n"
            "================= Failed Test Request (cURL) ================\n"
            f"{curl_command}\n"
            "============================================================="
        )
        pytest.fail(error_message, pytrace=False) 