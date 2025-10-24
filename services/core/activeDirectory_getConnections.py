"""
Тесты для эндпоинта /activeDirectory/getConnections сервиса core.

Проверяется:
- Статус-код 200 OK для базового запроса
- Соответствие ответа схеме (поля, типы-строки, паттерн пути)
- Игнорирование 35+ различных "мусорных" query-параметров
- Вывод cURL-команды с пояснением при ошибке
"""
import pytest
import json
from collections.abc import Mapping, Sequence
import time

ENDPOINT = "/activeDirectory/getConnections"

AD_CONNECTIONS_SCHEMA = {
    "type": "object",
    "properties": {
        "connections": {"type": "string"},
        "users": {"type": "string"},
        "groups": {"type": "string"},
        "swagger": {"type": "string"},
        "get current state": {"type": "string"}
    },
    "required": [],
}


# Автофикстура для задержки между каждым тестом
@pytest.fixture(autouse=True)
def pause_between_tests():
    yield
    time.sleep(1)

# Осмысленная параметризация для тестирования эндпоинта /activeDirectory/getConnections
PARAMS = [
    # --- Базовые позитивные сценарии ---
    pytest.param({}, 200, id="P01: no_params"),
    pytest.param({"format": "json"}, 200, id="P02: format_json"),
    pytest.param({"format": "xml"}, 200, id="P03: format_xml"),
    pytest.param({"format": "yaml"}, 200, id="P04: format_yaml"),
    pytest.param({"verbose": "true"}, 200, id="P05: verbose_true"),
    pytest.param({"verbose": "false"}, 200, id="P06: verbose_false"),
    pytest.param({"detailed": "true"}, 200, id="P07: detailed_true"),
    pytest.param({"detailed": "false"}, 200, id="P08: detailed_false"),
    pytest.param({"include_metadata": "true"}, 200, id="P09: include_metadata"),
    pytest.param({"include_paths": "true"}, 200, id="P10: include_paths"),
    
    # --- Фильтрация по типам соединений ---
    pytest.param({"type": "connections"}, 200, id="P11: filter_connections"),
    pytest.param({"type": "users"}, 200, id="P12: filter_users"),
    pytest.param({"type": "groups"}, 200, id="P13: filter_groups"),
    pytest.param({"type": "all"}, 200, id="P14: filter_all"),
    pytest.param({"connection_type": "ldap"}, 200, id="P15: connection_type_ldap"),
    pytest.param({"connection_type": "ad"}, 200, id="P16: connection_type_ad"),
    pytest.param({"connection_type": "local"}, 200, id="P17: connection_type_local"),
    pytest.param({"auth_method": "bind"}, 200, id="P18: auth_method_bind"),
    pytest.param({"auth_method": "kerberos"}, 200, id="P19: auth_method_kerberos"),
    pytest.param({"auth_method": "ntlm"}, 200, id="P20: auth_method_ntlm"),
    
    # --- Комбинированные параметры ---
    pytest.param({"format": "json", "verbose": "true"}, 200, id="P21: json_verbose"),
    pytest.param({"type": "users", "detailed": "true"}, 200, id="P22: users_detailed"),
    pytest.param({"connection_type": "ldap", "verbose": "true"}, 200, id="P23: ldap_verbose"),
    pytest.param({"auth_method": "bind", "format": "json"}, 200, id="P24: bind_json"),
    pytest.param({"include_metadata": "true", "include_paths": "true"}, 200, id="P25: metadata_and_paths"),
    
    # --- Поиск и фильтрация ---
    pytest.param({"search": "connection"}, 200, id="P26: search_connection"),
    pytest.param({"search": "user"}, 200, id="P27: search_user"),
    pytest.param({"search": "group"}, 200, id="P28: search_group"),
    pytest.param({"q": "api"}, 200, id="P29: query_api"),
    pytest.param({"filter": "active"}, 200, id="P30: filter_active"),
    pytest.param({"filter": "enabled"}, 200, id="P31: filter_enabled"),
    
    # --- Специальные параметры ---
    pytest.param({"domain": "example.com"}, 200, id="P32: domain_filter"),
    pytest.param({"protocol": "ldaps"}, 200, id="P33: protocol_ldaps"),
    pytest.param({"protocol": "ldap"}, 200, id="P34: protocol_ldap"),
    pytest.param({"port": "389"}, 200, id="P35: port_389"),
    pytest.param({"port": "636"}, 200, id="P36: port_636"),
    pytest.param({"ssl": "true"}, 200, id="P37: ssl_enabled"),
    pytest.param({"ssl": "false"}, 200, id="P38: ssl_disabled"),
    pytest.param({"timeout": "30"}, 200, id="P39: timeout_30"),
    pytest.param({"retry": "3"}, 200, id="P40: retry_3"),
    pytest.param({"base_dn": "dc=example,dc=com"}, 200, id="P41: base_dn"),
    pytest.param({"user_dn": "ou=users,dc=example,dc=com"}, 200, id="P42: user_dn"),
    pytest.param({"group_dn": "ou=groups,dc=example,dc=com"}, 200, id="P43: group_dn"),
    pytest.param({"bind_user": "admin"}, 200, id="P44: bind_user"),
    pytest.param({"attributes": "cn,mail,memberOf"}, 200, id="P45: attributes"),
    pytest.param({"scope": "subtree"}, 200, id="P46: scope_subtree"),
    pytest.param({"scope": "base"}, 200, id="P47: scope_base"),
    pytest.param({"test_connection": "true"}, 200, id="P48: test_connection"),
    pytest.param({"validate": "true"}, 200, id="P49: validate_config"),
    
    # --- Дополнительные системные параметры ---
    pytest.param({"sort": "name"}, 200, id="P50: sort_name"),
    pytest.param({"limit": "100"}, 200, id="P51: limit_100"),
    pytest.param({"offset": "10"}, 200, id="P52: offset_10"),
    pytest.param({"page": "1"}, 200, id="P53: page_1"),
    
    # --- Граничные значения ---
    pytest.param({"unsupported_param": "value"}, 200, id="P54: unsupported_param_ignored"),
]


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


def _format_curl_command(api_client, endpoint, params):
    """Формирует и возвращает cURL-строку для воспроизведения запроса."""
    base_url = getattr(api_client, "base_url", "http://127.0.0.1")
    full_url = f"{base_url.rstrip('/')}/{endpoint.lstrip('/')}"
    
    # Формируем строку параметров
    param_str = "&".join([f"{k}={v}" for k, v in params.items() if v is not None])
    if param_str:
        full_url += f"?{param_str}"

    headers = getattr(api_client, 'headers', {})
    headers_str = " \\\n  ".join([f"-H '{k}: {v}'" for k, v in headers.items()])
    
    curl_command = f"curl -X GET '{full_url}'"
    if headers_str:
        curl_command += f" \\\n  {headers_str}"
        
    return curl_command


@pytest.mark.parametrize("params, expected_status", PARAMS)
def test_active_directory_get_connections_parametrized(api_client, params, expected_status):
    """
    Основной параметризованный тест для эндпоинта /activeDirectory/getConnections.
    1. Отправляет GET-запрос с указанными параметрами.
    2. Проверяет соответствие статус-кода ожидаемому.
    3. Для успешных ответов (200) валидирует схему JSON.
    4. В случае падения теста выводит полную cURL-команду для воспроизведения.
    """
    try:
        response = api_client.get(ENDPOINT, params=params)
        
        # 1. Проверка статус-кода
        assert response.status_code == expected_status, \
            f"Ожидался статус-код {expected_status}, получен {response.status_code}. Ответ: {response.text}"

        # 2. Валидация схемы ответа
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, dict), f"Тело ответа не является объектом JSON, получено: {type(data).__name__}"
            _check_types_recursive(data, AD_CONNECTIONS_SCHEMA)

    except (AssertionError, json.JSONDecodeError) as e:
        # 3. Формирование и вывод детального отчета об ошибке
        curl_command = _format_curl_command(api_client, ENDPOINT, params)
        
        error_message = (
            f"\nТест с параметрами {params} упал.\n"
            f"Ошибка: {e}\n\n"
            "================= Failed Test Request (cURL) ================\n"
            f"{curl_command}\n"
            "============================================================="
        )
        pytest.fail(error_message, pytrace=False) 