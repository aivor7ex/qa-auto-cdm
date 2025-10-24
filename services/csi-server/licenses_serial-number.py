"""
Тесты для эндпоинта /licenses/serial-number сервиса csi-server.

Проверяется:
- Статус-код 200 OK
- Соответствие структуры ответа схеме (UUID серийный номер)
- Валидация формата UUID серийного номера
- Устойчивость к различным сценариям
- Вывод cURL-команды при ошибке в параметризованных тестах
"""
import pytest
import json
import re
import uuid
from collections.abc import Mapping, Sequence

ENDPOINT = "/licenses/serial-number"

# Схема ответа для серийного номера лицензии
SERIAL_NUMBER_SCHEMA = {
    "type": "string",
    "pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
}

def is_valid_uuid(serial_number):
    """Проверяет, является ли строка валидным UUID."""
    if not isinstance(serial_number, str):
        return False
    try:
        uuid.UUID(serial_number)
        return True
    except ValueError:
        return False

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


def _format_curl_command(api_client, endpoint, params, auth_token=None):
    """Формирует и возвращает cURL-строку для воспроизведения запроса."""
    base_url = getattr(api_client, "base_url", "http://127.0.0.1")
    full_url = f"{base_url.rstrip('/')}/{endpoint.lstrip('/')}"
    
    # Формируем строку параметров
    param_str = "&".join([f"{k}={v}" for k, v in params.items() if v is not None])
    if param_str:
        full_url += f"?{param_str}"

    # Базовые заголовки
    headers = getattr(api_client, 'headers', {}).copy()
    
    # Добавляем заголовки авторизации если токен предоставлен
    if auth_token:
        headers['x-access-token'] = auth_token
        headers['token'] = auth_token
    
    headers_str = " \\\n  ".join([f"-H '{k}: {v}'" for k, v in headers.items()])
    
    curl_command = f"curl -X GET '{full_url}'"
    if headers_str:
        curl_command += f" \\\n  {headers_str}"
        
    return curl_command





# Осмысленная параметризация для тестирования эндпоинта /licenses/serial-number
PARAMS = [
    # --- Базовые позитивные сценарии ---
    pytest.param({}, 200, id="P01: no_params"),
    pytest.param({"format": "uuid"}, 200, id="P02: format_uuid"),
    pytest.param({"type": "license"}, 200, id="P03: type_license"),
    pytest.param({"type": "serial"}, 200, id="P04: type_serial"),
    
    # --- Фильтрация по типу лицензии ---
    pytest.param({"license_type": "standard"}, 200, id="P05: license_type_standard"),
    pytest.param({"license_type": "premium"}, 200, id="P06: license_type_premium"),
    pytest.param({"license_type": "enterprise"}, 200, id="P07: license_type_enterprise"),
    pytest.param({"license_type": "trial"}, 200, id="P08: license_type_trial"),
    
    # --- Фильтрация по статусу ---
    pytest.param({"status": "active"}, 200, id="P09: status_active"),
    pytest.param({"status": "inactive"}, 200, id="P10: status_inactive"),
    pytest.param({"status": "expired"}, 200, id="P11: status_expired"),
    pytest.param({"status": "pending"}, 200, id="P12: status_pending"),
    
    # --- Фильтрация по датам ---
    pytest.param({"created_after": "2023-01-01"}, 200, id="P13: created_after_2023"),
    pytest.param({"created_before": "2024-12-31"}, 200, id="P14: created_before_2024"),
    pytest.param({"expires_after": "2024-01-01"}, 200, id="P15: expires_after_2024"),
    
    # --- Комбинированные фильтры ---
    pytest.param({"license_type": "standard", "status": "active"}, 200, id="P16: standard_active"),
    pytest.param({"license_type": "premium", "status": "active"}, 200, id="P17: premium_active"),
    pytest.param({"format": "uuid", "type": "license"}, 200, id="P18: uuid_license"),
    pytest.param({"status": "active", "created_after": "2023-01-01"}, 200, id="P19: active_after_2023"),
    
    # --- Поиск и фильтрация ---
    pytest.param({"search": "license"}, 200, id="P20: search_license"),
    pytest.param({"search": "serial"}, 200, id="P21: search_serial"),
    pytest.param({"q": "number"}, 200, id="P22: query_number"),
    pytest.param({"filter": '{"status": "active"}'}, 200, id="P23: filter_active"),
    pytest.param({"filter": '{"license_type": "standard"}'}, 200, id="P24: filter_standard"),
    
    # --- Сортировка ---
    pytest.param({"sort": "created"}, 200, id="P25: sort_by_created"),
    pytest.param({"sort": "-created"}, 200, id="P26: sort_by_created_desc"),
    pytest.param({"sort": "expires"}, 200, id="P27: sort_by_expires"),
    pytest.param({"sort": "status"}, 200, id="P28: sort_by_status"),
    
    # --- Постраничная навигация ---
    pytest.param({"limit": "10"}, 200, id="P29: pagination_limit_10"),
    pytest.param({"limit": "1"}, 200, id="P30: pagination_limit_1"),
    pytest.param({"offset": "5"}, 200, id="P31: pagination_offset_5"),
    pytest.param({"limit": "5", "offset": "2"}, 200, id="P32: pagination_limit_offset"),
    
    # --- Комбинации параметров ---
    pytest.param({"sort": "created", "limit": "3"}, 200, id="P33: sort_and_limit"),
    pytest.param({"filter": '{"status": "active"}', "sort": "created"}, 200, id="P34: filter_and_sort"),
    pytest.param({"search": "license", "limit": "5"}, 200, id="P35: search_and_limit"),
]


@pytest.mark.parametrize("params, expected_status", PARAMS)
def test_licenses_serial_number_parametrized(api_client, auth_token, params, expected_status):
    """
    Основной параметризованный тест для эндпоинта /licenses/serial-number.
    1. Отправляет GET-запрос с указанными параметрами.
    2. Проверяет соответствие статус-кода ожидаемому.
    3. Для успешных ответов (200) валидирует схему JSON и формат UUID.
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
            assert isinstance(data, str), f"Тело ответа не является строкой JSON, получено: {type(data).__name__}"
            
            # Проверяем структуру и формат серийного номера
            _check_types_recursive(data, SERIAL_NUMBER_SCHEMA)
            
            # Дополнительная проверка валидности UUID
            assert is_valid_uuid(data), f"Серийный номер не является валидным UUID: {data}"

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





def test_licenses_serial_number_basic(api_client, auth_token):
    """
    Базовый тест для эндпоинта /licenses/serial-number без параметров.
    Проверяет основную функциональность получения серийного номера лицензии.
    """
    try:
        # Добавляем заголовки авторизации
        headers = {
            'x-access-token': auth_token,
            'token': auth_token
        }
        
        response = api_client.get(ENDPOINT, headers=headers)
        
        # Проверка статус-кода
        assert response.status_code == 200, \
            f"Ожидался статус-код 200, получен {response.status_code}. Ответ: {response.text}"

        # Валидация схемы ответа
        data = response.json()
        assert isinstance(data, str), f"Тело ответа не является строкой JSON, получено: {type(data).__name__}"
        
        # Проверяем структуру и формат серийного номера
        _check_types_recursive(data, SERIAL_NUMBER_SCHEMA)
        
        # Дополнительная проверка валидности UUID
        assert is_valid_uuid(data), f"Серийный номер не является валидным UUID: {data}"
        
        # Проверяем, что UUID не пустой
        assert len(data.strip()) > 0, "Серийный номер не может быть пустым"

    except (AssertionError, json.JSONDecodeError) as e:
        # Формирование и вывод детального отчета об ошибке
        curl_command = _format_curl_command(api_client, ENDPOINT, {}, auth_token)
        
        error_message = (
            f"\nБазовый тест упал.\n"
            f"Ошибка: {e}\n\n"
            "================= Failed Test Request (cURL) ================\n"
            f"{curl_command}\n"
            "============================================================="
        )
        pytest.fail(error_message, pytrace=False)
