import pytest
import json
from collections.abc import Mapping, Sequence

ENDPOINT = "/nats"

NAT_SCHEMA = {
    "type": "object",
    "properties": {
        "natType": {"type": "string"},
        "sourceNet": {"type": "string"},
        "outInterface": {"type": "string"},
        "proto": {"type": "string"},
        "id": {"type": "string"},
        "objHash": {"type": "string"}
    },
    "required": ["id"],
}

# Функция для получения реальных NAT ID из системы
def get_real_nat_ids(api_client):
    """Получает список реальных NAT ID из системы."""
    try:
        response = api_client.get(ENDPOINT)
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list) and len(data) > 0:
                return [item.get("id") for item in data if item.get("id")]
        return []
    except Exception:
        return []

# Осмысленная параметризация для тестирования эндпоинта /nats/{id}
def get_test_params(api_client):
    """Генерирует параметры тестов на основе реальных данных из системы."""
    real_ids = get_real_nat_ids(api_client)
    
    params = [
        # --- Базовые позитивные сценарии с валидными ID ---
        pytest.param({"id": "6876106aaa5c6d0009376eb1"}, 404, id="P01: valid_mongodb_id_not_found"),
        pytest.param({"id": "507f1f77bcf86cd799439011"}, 404, id="P02: another_valid_id_not_found"),
        pytest.param({"id": "123456789012345678901234"}, 404, id="P03: valid_format_id_not_found"),
        pytest.param({"id": "abcdef1234567890abcdef12"}, 404, id="P04: hex_id_not_found"),
        
        # --- Тестовые ID (возвращают 404, так как в системе нет NAT записей) ---
        pytest.param({"id": "test_nat_001"}, 404, id="P23: test_nat_001_not_found"),
        pytest.param({"id": "test_nat_002"}, 404, id="P24: test_nat_002_not_found"),
        pytest.param({"id": "test_nat_003"}, 404, id="P25: test_nat_003_not_found"),
        pytest.param({"id": "test_nat_004"}, 404, id="P26: test_nat_004_not_found"),
        pytest.param({"id": "test_nat_005"}, 404, id="P27: test_nat_005_not_found"),
        
        # --- Дополнительные параметры с несуществующими ID ---
        pytest.param({"id": "6876106aaa5c6d0009376eb1", "format": "json"}, 404, id="P05: valid_id_with_format"),
        pytest.param({"id": "6876106aaa5c6d0009376eb1", "verbose": "true"}, 404, id="P06: valid_id_verbose"),
        pytest.param({"id": "6876106aaa5c6d0009376eb1", "detailed": "true"}, 404, id="P07: valid_id_detailed"),
        pytest.param({"id": "6876106aaa5c6d0009376eb1", "include_metadata": "true"}, 404, id="P08: valid_id_metadata"),
        pytest.param({"id": "6876106aaa5c6d0009376eb1", "expand": "true"}, 404, id="P09: valid_id_expand"),
        
        # --- Комбинированные параметры с несуществующими ID ---
        pytest.param({"id": "6876106aaa5c6d0009376eb1", "format": "json", "verbose": "true"}, 404, id="P10: valid_id_json_verbose"),
        pytest.param({"id": "6876106aaa5c6d0009376eb1", "detailed": "true", "expand": "true"}, 404, id="P11: valid_id_detailed_expand"),
        pytest.param({"id": "6876106aaa5c6d0009376eb1", "include_metadata": "true", "verbose": "true"}, 404, id="P12: valid_id_metadata_verbose"),
        
        # --- Специальные параметры с несуществующими ID ---
        pytest.param({"id": "6876106aaa5c6d0009376eb1", "include_rules": "true"}, 404, id="P13: valid_id_include_rules"),
        pytest.param({"id": "6876106aaa5c6d0009376eb1", "include_interfaces": "true"}, 404, id="P14: valid_id_include_interfaces"),
        pytest.param({"id": "6876106aaa5c6d0009376eb1", "include_stats": "true"}, 404, id="P15: valid_id_include_stats"),
        pytest.param({"id": "6876106aaa5c6d0009376eb1", "resolve_names": "true"}, 404, id="P16: valid_id_resolve_names"),
        pytest.param({"id": "6876106aaa5c6d0009376eb1", "show_config": "true"}, 404, id="P17: valid_id_show_config"),
        
        # --- Негативные сценарии с невалидными ID ---
        pytest.param({"id": "invalid"}, 404, id="N01: invalid_id_format"),
        pytest.param({"id": "123"}, 404, id="N02: short_id"),
        pytest.param({"id": "not-a-mongodb-id"}, 404, id="N03: non_hex_id"),
        pytest.param({"id": ""}, 200, id="N04: empty_id"),
        pytest.param({"id": " "}, 404, id="N05: space_id"),
        pytest.param({"id": "null"}, 400, id="N06: null_string_id"),
        pytest.param({"id": "undefined"}, 404, id="N07: undefined_string_id"),
        pytest.param({"id": "0"}, 404, id="N08: zero_id"),
        pytest.param({"id": "1"}, 404, id="N09: one_id"),
        pytest.param({"id": "-1"}, 404, id="N10: negative_id"),
        pytest.param({"id": "12345678901234567890123"}, 404, id="N11: too_short_hex"),
        pytest.param({"id": "123456789012345678901234567890"}, 404, id="N12: too_long_hex"),
        pytest.param({"id": "special!@#$%^&*()"}, 404, id="N13: special_chars_id"),
        pytest.param({"id": "../../etc/passwd"}, 404, id="N14: path_traversal_id"),
        pytest.param({"id": "<script>alert(1)</script>"}, 404, id="N15: xss_id"),
        pytest.param({"id": "' OR 1=1 --"}, 404, id="N16: sql_injection_id"),
        
        # --- Дополнительные параметры с невалидными ID ---
        pytest.param({"id": "invalid", "format": "json"}, 404, id="N17: invalid_id_with_format"),
        pytest.param({"id": "123", "verbose": "true"}, 404, id="N18: short_id_verbose"),
        pytest.param({"id": "", "detailed": "true"}, 200, id="N19: empty_id_detailed"),
        
        # --- Граничные значения ---
        pytest.param({"id": "6876106aaa5c6d0009376eb1", "unsupported": "param"}, 404, id="P18: valid_id_unsupported_param"),
        pytest.param({"id": "6876106aaa5c6d0009376eb1", "limit": "10"}, 404, id="P19: valid_id_with_limit"),
        pytest.param({"id": "6876106aaa5c6d0009376eb1", "offset": "5"}, 404, id="P20: valid_id_with_offset"),
        pytest.param({"id": "6876106aaa5c6d0009376eb1", "sort": "name"}, 404, id="P21: valid_id_with_sort"),
        pytest.param({"id": "6876106aaa5c6d0009376eb1", "filter": "active"}, 400, id="P22: valid_id_with_filter"),
        
        # --- Тестовые ID с дополнительными параметрами ---
        pytest.param({"id": "test_nat_001", "format": "json"}, 404, id="P28: test_nat_001_with_format"),
        pytest.param({"id": "test_nat_002", "verbose": "true"}, 404, id="P29: test_nat_002_verbose"),
        pytest.param({"id": "test_nat_003", "detailed": "true"}, 404, id="P30: test_nat_003_detailed"),
        pytest.param({"id": "test_nat_004", "include_metadata": "true"}, 404, id="P31: test_nat_004_metadata"),
        pytest.param({"id": "test_nat_005", "expand": "true"}, 404, id="P32: test_nat_005_expand"),
        
        # --- Комбинированные тестовые ID ---
        pytest.param({"id": "test_nat_001", "format": "json", "verbose": "true"}, 404, id="P33: test_nat_001_json_verbose"),
        pytest.param({"id": "test_nat_002", "detailed": "true", "expand": "true"}, 404, id="P34: test_nat_002_detailed_expand"),
        pytest.param({"id": "test_nat_003", "include_metadata": "true", "verbose": "true"}, 404, id="P35: test_nat_003_metadata_verbose"),
        
        # --- Специальные тестовые ID ---
        pytest.param({"id": "test_nat_001", "include_rules": "true"}, 404, id="P36: test_nat_001_include_rules"),
        pytest.param({"id": "test_nat_002", "include_interfaces": "true"}, 404, id="P37: test_nat_002_include_interfaces"),
        pytest.param({"id": "test_nat_003", "include_stats": "true"}, 404, id="P38: test_nat_003_include_stats"),
        pytest.param({"id": "test_nat_004", "resolve_names": "true"}, 404, id="P39: test_nat_004_resolve_names"),
        pytest.param({"id": "test_nat_005", "show_config": "true"}, 404, id="P40: test_nat_005_show_config"),
        
        # --- Граничные тестовые ID ---
        pytest.param({"id": "test_nat_001", "unsupported": "param"}, 404, id="P41: test_nat_001_unsupported_param"),
        pytest.param({"id": "test_nat_002", "limit": "10"}, 404, id="P42: test_nat_002_with_limit"),
        pytest.param({"id": "test_nat_003", "offset": "5"}, 404, id="P43: test_nat_003_with_offset"),
        pytest.param({"id": "test_nat_004", "sort": "name"}, 404, id="P44: test_nat_004_with_sort"),
        pytest.param({"id": "test_nat_005", "filter": "active"}, 400, id="P45: test_nat_005_with_filter"),
        
        # --- Положительные тест-кейсы с пустым ID (возвращает список всех NAT) ---
        pytest.param({"id": ""}, 200, id="P46: empty_id_returns_all"),
        pytest.param({"id": "", "format": "json"}, 200, id="P47: empty_id_with_format"),
        pytest.param({"id": "", "verbose": "true"}, 200, id="P48: empty_id_verbose"),
        pytest.param({"id": "", "detailed": "true"}, 200, id="P49: empty_id_detailed"),
        pytest.param({"id": "", "include_metadata": "true"}, 200, id="P50: empty_id_metadata"),
        pytest.param({"id": "", "expand": "true"}, 200, id="P51: empty_id_expand"),
        
        # --- Комбинированные положительные тест-кейсы с пустым ID ---
        pytest.param({"id": "", "format": "json", "verbose": "true"}, 200, id="P52: empty_id_json_verbose"),
        pytest.param({"id": "", "detailed": "true", "expand": "true"}, 200, id="P53: empty_id_detailed_expand"),
        pytest.param({"id": "", "include_metadata": "true", "verbose": "true"}, 200, id="P54: empty_id_metadata_verbose"),
        
        # --- Специальные положительные тест-кейсы с пустым ID ---
        pytest.param({"id": "", "include_rules": "true"}, 200, id="P55: empty_id_include_rules"),
        pytest.param({"id": "", "include_interfaces": "true"}, 200, id="P56: empty_id_include_interfaces"),
        pytest.param({"id": "", "include_stats": "true"}, 200, id="P57: empty_id_include_stats"),
        pytest.param({"id": "", "resolve_names": "true"}, 200, id="P58: empty_id_resolve_names"),
        pytest.param({"id": "", "show_config": "true"}, 200, id="P59: empty_id_show_config"),
        
        # --- Граничные положительные тест-кейсы с пустым ID ---
        pytest.param({"id": "", "unsupported": "param"}, 200, id="P60: empty_id_unsupported_param"),
        pytest.param({"id": "", "limit": "10"}, 200, id="P61: empty_id_with_limit"),
        pytest.param({"id": "", "offset": "5"}, 200, id="P62: empty_id_with_offset"),
        pytest.param({"id": "", "sort": "name"}, 200, id="P63: empty_id_with_sort"),
        pytest.param({"id": "", "filter": "active"}, 400, id="P64: empty_id_with_filter"),
    ]
    
    # Добавляем положительные тест-кейсы с реальными ID, если они есть
    if real_ids:
        for i, nat_id in enumerate(real_ids[:3]):  # Берем первые 3 ID для тестов
            params.extend([
                pytest.param({"id": nat_id}, 200, id=f"REAL_P{i+1}: real_nat_id_{i+1}"),
                pytest.param({"id": nat_id, "format": "json"}, 200, id=f"REAL_P{i+4}: real_nat_id_{i+1}_with_format"),
                pytest.param({"id": nat_id, "verbose": "true"}, 200, id=f"REAL_P{i+7}: real_nat_id_{i+1}_verbose"),
                pytest.param({"id": nat_id, "detailed": "true"}, 200, id=f"REAL_P{i+10}: real_nat_id_{i+1}_detailed"),
                pytest.param({"id": nat_id, "expand": "true"}, 200, id=f"REAL_P{i+13}: real_nat_id_{i+1}_expand"),
            ])
    
    return params


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


def _format_curl_command(api_client, endpoint, nat_id, params):
    """Формирует и возвращает cURL-строку для воспроизведения запроса."""
    base_url = getattr(api_client, "base_url", "http://127.0.0.1")
    full_url = f"{base_url.rstrip('/')}/{endpoint.lstrip('/')}/{nat_id}"
    
    # Формируем строку параметров (исключая id)
    filtered_params = {k: v for k, v in params.items() if k != "id"}
    if filtered_params:
        param_str = "&".join([f"{k}={v}" for k, v in filtered_params.items() if v is not None])
        full_url += f"?{param_str}"

    headers = getattr(api_client, 'headers', {})
    headers_str = " \\\n  ".join([f"-H '{k}: {v}'" for k, v in headers.items()])
    
    curl_command = f"curl -X GET '{full_url}'"
    if headers_str:
        curl_command += f" \\\n  {headers_str}"
        
    return curl_command


def pytest_generate_tests(metafunc):
    """Генератор тестов для создания отдельных тестов для каждого кейса."""
    if "test_params" in metafunc.fixturenames and "expected_status" in metafunc.fixturenames:
        # Получаем api_client из фикстуры
        api_client = metafunc.config.cache.get("api_client", None)
        if api_client is None:
            # Если api_client недоступен, используем статические параметры
            test_params = [
                pytest.param({"id": "6876106aaa5c6d0009376eb1"}, 404, id="P01: valid_mongodb_id_not_found"),
                pytest.param({"id": "507f1f77bcf86cd799439011"}, 404, id="P02: another_valid_id_not_found"),
                pytest.param({"id": "123456789012345678901234"}, 404, id="P03: valid_format_id_not_found"),
                pytest.param({"id": "abcdef1234567890abcdef12"}, 404, id="P04: hex_id_not_found"),
                pytest.param({"id": ""}, 200, id="N04: empty_id"),
                pytest.param({"id": "invalid"}, 404, id="N01: invalid_id_format"),
                pytest.param({"id": "123"}, 404, id="N02: short_id"),
                pytest.param({"id": "null"}, 400, id="N06: null_string_id"),
            ]
        else:
            test_params = get_test_params(api_client)
        
        metafunc.parametrize("test_params,expected_status", test_params)


def test_nats_id_case(api_client, test_params, expected_status):
    """
    Отдельный тест для каждого кейса эндпоинта /nats/{id}.
    1. Отправляет GET-запрос с указанными параметрами и ID.
    2. Проверяет соответствие статус-кода ожидаемому.
    3. Для успешных ответов (200) валидирует схему JSON.
    4. В случае падения теста выводит полную cURL-команду для воспроизведения.
    """
    params = test_params.copy()  # Получаем копию параметров
    nat_id = params.pop("id")
    
    try:
        response = api_client.get(f"{ENDPOINT}/{nat_id}", params=params)
        
        # 1. Проверка статус-кода
        assert response.status_code == expected_status, \
            f"Ожидался статус-код {expected_status}, получен {response.status_code}. Ответ: {response.text}"

        # 2. Валидация схемы ответа
        if response.status_code == 200:
            data = response.json()
            
            # Для пустого ID возвращается список всех NAT
            if nat_id == "":
                assert isinstance(data, list), f"Тело ответа для пустого ID должно быть массивом JSON, получено: {type(data).__name__}"
                # Проверяем структуру каждого NAT в списке
                for nat_data in data:
                    _check_types_recursive(nat_data, NAT_SCHEMA)
            else:
                # Для конкретного ID возвращается один объект NAT
                assert isinstance(data, dict), f"Тело ответа не является объектом JSON, получено: {type(data).__name__}"
                _check_types_recursive(data, NAT_SCHEMA)
                # Дополнительная проверка что ID в ответе соответствует запрошенному
                assert data.get("id") == nat_id, f"ID в ответе {data.get('id')} не соответствует запрошенному {nat_id}"
        elif response.status_code == 404:
            # Для 404 статус-кода проверяем что есть error объект
            data = response.json()
            assert "error" in data, f"Ответ с 404 статусом должен содержать error объект"
        elif response.status_code == 400:
            # Для 400 статус-кода проверяем что есть error объект
            data = response.json()
            assert "error" in data, f"Ответ с 400 статусом должен содержать error объект"

    except (AssertionError, json.JSONDecodeError) as e:
        # 3. Формирование и вывод детального отчета об ошибке
        curl_command = _format_curl_command(api_client, ENDPOINT, nat_id, params)
        
        error_message = (
            f"\nТест с ID '{nat_id}' и параметрами {params} упал.\n"
            f"Ошибка: {e}\n\n"
            "================= Failed Test Request (cURL) ================\n"
            f"{curl_command}\n"
            "============================================================="
        )
        pytest.fail(error_message, pytrace=False) 