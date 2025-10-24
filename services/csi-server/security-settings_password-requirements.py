"""
Тесты для эндпоинта /security-settings/password-requirements сервиса csi-server.

Проверяется:
- Статус-код 200 OK
- Соответствие структуры ответа схеме (объект password requirements)
- Вывод cURL-команды при ошибке в параметризованных тестах
"""
import pytest
import json
from collections.abc import Mapping, Sequence

ENDPOINT = "/security-settings/password-requirements"

PASSWORD_REQUIREMENTS_SCHEMA = {
    "type": "object",
    "properties": {
        "agent": {"type": "string"},
        "settings": {
            "type": "object",
            "properties": {
                "different_case_required": {"type": "boolean"},
                "min_password_length": {"type": "integer"},
                "numbers_required": {"type": "boolean"},
                "special_characters_required": {"type": "boolean"}
            },
            "required": ["different_case_required", "min_password_length", "numbers_required", "special_characters_required"]
        }
    },
    "required": ["agent", "settings"],
}

# Осмысленная параметризация для тестирования эндпоинта /security-settings/password-requirements
PARAMS = [
    # --- Базовые позитивные сценарии ---
    pytest.param({}, 200, id="P01: no_params"),
    pytest.param({"format": "json"}, 200, id="P02: format_json"),
    pytest.param({"pretty": "true"}, 200, id="P03: pretty_true"),
    pytest.param({"pretty": "false"}, 200, id="P04: pretty_false"),
    pytest.param({"indent": "2"}, 200, id="P05: indent_2"),
    pytest.param({"indent": "4"}, 200, id="P06: indent_4"),
    pytest.param({"info": "true"}, 200, id="P07: info_true"),
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


def _format_curl_command(api_client, endpoint, params, auth_token=None):
    """Формирует и возвращает cURL-строку для воспроизведения запроса."""
    base_url = getattr(api_client, "base_url", "http://127.0.0.1")
    full_url = f"{base_url.rstrip('/')}/{endpoint.lstrip('/')}"
    
    param_str = "&".join([f"{k}={v}" for k, v in params.items() if v is not None])
    if param_str:
        full_url += f"?{param_str}"

    headers = getattr(api_client, 'headers', {}).copy()
    
    if auth_token:
        headers['x-access-token'] = auth_token
        headers['token'] = auth_token
    
    headers_str = " \\\n  ".join([f"-H '{k}: {v}'" for k, v in headers.items()])
    
    curl_command = f"curl -X GET '{full_url}'"
    if headers_str:
        curl_command += f" \\\n  {headers_str}"
        
    return curl_command





@pytest.mark.parametrize("params, expected_status", PARAMS)
def test_security_settings_password_requirements_parametrized(api_client, auth_token, params, expected_status):
    """
    Основной параметризованный тест для эндпоинта /security-settings/password-requirements.
    """
    try:
        headers = {
            'x-access-token': auth_token,
            'token': auth_token
        }
        
        response = api_client.get(ENDPOINT, params=params, headers=headers, timeout=10)
        
        assert response.status_code == expected_status, \
            f"Ожидался статус-код {expected_status}, получен {response.status_code}. Ответ: {response.text}"

        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, dict), f"Тело ответа не является объектом JSON, получено: {type(data).__name__}"
            _check_types_recursive(data, PASSWORD_REQUIREMENTS_SCHEMA)

    except (AssertionError, json.JSONDecodeError, Exception) as e:
        curl_command = _format_curl_command(api_client, ENDPOINT, params, auth_token)
        
        error_message = (
            f"\nТест с параметрами {params} упал.\n"
            f"Ошибка: {e}\n\n"
            "================= Failed Test Request (cURL) ================\n"
            f"{curl_command}\n"
            "============================================================="
        )
        pytest.fail(error_message, pytrace=False)


def test_security_settings_password_requirements_basic(api_client, auth_token):
    """
    Базовый тест для проверки основного функционала эндпоинта.
    """
    try:
        headers = {
            'x-access-token': auth_token,
            'token': auth_token
        }
        
        response = api_client.get(ENDPOINT, headers=headers, timeout=10)
        
        assert response.status_code == 200, \
            f"Ожидался статус-код 200, получен {response.status_code}. Ответ: {response.text}"

        data = response.json()
        assert isinstance(data, dict), f"Тело ответа не является объектом JSON, получено: {type(data).__name__}"
        _check_types_recursive(data, PASSWORD_REQUIREMENTS_SCHEMA)

    except (AssertionError, json.JSONDecodeError, Exception) as e:
        curl_command = _format_curl_command(api_client, ENDPOINT, {}, auth_token)
        
        error_message = (
            f"\nБазовый тест упал.\n"
            f"Ошибка: {e}\n\n"
            "================= Failed Test Request (cURL) ================\n"
            f"{curl_command}\n"
            "============================================================="
        )
        pytest.fail(error_message, pytrace=False)



