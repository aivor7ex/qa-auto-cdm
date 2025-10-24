"""
Тесты для эндпоинта /interfaceRuntimes/{id} сервиса core.

Проверяется:
- Корректное получение ID из зависимого эндпоинта
- Статус-код 200 OK для существующего ID
- Соответствие ответа схеме для существующего ID
- Корректная обработка несуществующих и некорректных ID (404, 400)
- Устойчивость к 35+ различным форматам ID
- Вывод cURL-команды с пояснением при ошибке
"""
import pytest
import requests
import json
from collections.abc import Mapping, Sequence

ENDPOINT = "/interfaceRuntimes"

INTERFACE_RUNTIME_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "rt_active": {"type": "boolean"}
    },
    "required": ["name", "rt_active"],
}

# Осмысленная параметризация для тестирования эндпоинта /interfaceRuntimes/{id}
# Примечание: позитивные кейсы с существующими ID формируются динамически в отдельном тесте,
# чтобы устранить зависимости от хардкода и среды.
PARAMS = [
    # --- Негативные сценарии с несуществующими ID ---
    pytest.param({"id": "nonexistent"}, 404, id="N01: nonexistent_id"),
    pytest.param({"id": "fake-interface"}, 404, id="N02: fake_interface_id"),
    pytest.param({"id": "test123"}, 404, id="N03: test_id"),
    pytest.param({"id": "invalid-name"}, 404, id="N04: invalid_name_id"),
    pytest.param({"id": "bond999"}, 404, id="N05: non_existing_bond"),
    pytest.param({"id": "eth-999-999"}, 404, id="N06: non_existing_eth"),
    pytest.param({"id": "unknown"}, 404, id="N07: unknown_id"),
    pytest.param({"id": "missing"}, 404, id="N08: missing_id"),
    pytest.param({"id": "notfound"}, 404, id="N09: notfound_id"),
    pytest.param({"id": "absent"}, 404, id="N10: absent_id"),

    # --- Специальные символы и граничные случаи ---
    pytest.param({"id": ""}, 200, id="N11: empty_id_returns_list"),
    pytest.param({"id": " "}, 404, id="N12: space_id"),
    pytest.param({"id": "null"}, 400, id="N13: null_string_id"),
    pytest.param({"id": "undefined"}, 404, id="N14: undefined_string_id"),
    pytest.param({"id": "0"}, 404, id="N15: zero_id"),
    pytest.param({"id": "1"}, 404, id="N16: one_id"),
    pytest.param({"id": "-1"}, 404, id="N17: negative_id"),
    pytest.param({"id": "special!@#$%^&*()"}, 404, id="N18: special_chars_id"),
    pytest.param({"id": "../../etc/passwd"}, 404, id="N19: path_traversal_id"),
    pytest.param({"id": "<script>alert(1)</script>"}, 404, id="N20: xss_id"),
    pytest.param({"id": "' OR 1=1 --"}, 404, id="N21: sql_injection_id"),
    pytest.param({"id": "very-long-interface-name-that-should-not-exist-in-system"}, 404, id="N22: very_long_id"),

    # --- Дополнительные параметры с пустым ID и несуществующими ID ---
    pytest.param({"id": "nonexistent", "format": "json"}, 404, id="N23: nonexistent_with_format"),
    pytest.param({"id": "fake", "verbose": "true"}, 404, id="N24: fake_verbose"),
    pytest.param({"id": "", "detailed": "true"}, 200, id="N25: empty_detailed"),
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


def _format_curl_command(api_client, endpoint, interface_id, params, api_base_url=None):
    """Формирует и возвращает cURL-строку для воспроизведения запроса."""
    # Пытаемся использовать корректный base_url из фикстуры, иначе берём из последнего запроса
    if api_base_url:
        base_url = api_base_url
    else:
        last_req = getattr(api_client, "last_request", None)
        if last_req is not None:
            # last_request.url уже содержит полный URL, воспользуемся им
            full_url = last_req.url
        else:
            base_url = "http://127.0.0.1"
            full_url = f"{base_url.rstrip('/')}/{endpoint.lstrip('/')}/{interface_id}"
            
    if not 'full_url' in locals():
        full_url = f"{base_url.rstrip('/')}/{endpoint.lstrip('/')}/{interface_id}"
    
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


@pytest.mark.parametrize("params, expected_status", PARAMS)
def test_interface_runtimes_id_parametrized(api_client, api_base_url, params, expected_status):
    """
    Основной параметризованный тест для эндпоинта /interfaceRuntimes/{id}.
    1. Отправляет GET-запрос с указанными параметрами и ID.
    2. Проверяет соответствие статус-кода ожидаемому.
    3. Для успешных ответов (200) валидирует схему JSON.
    4. В случае падения теста выводит полную cURL-команду для воспроизведения.
    """
    interface_id = params.pop("id")
    try:
        response = api_client.get(f"{ENDPOINT}/{interface_id}", params=params)
        
        # 1. Проверка статус-кода
        assert response.status_code == expected_status, \
            f"Ожидался статус-код {expected_status}, получен {response.status_code}. Ответ: {response.text}"

        # 2. Валидация схемы ответа
        if response.status_code == 200:
            data = response.json()
            # Для пустого ID возвращается список интерфейсов
            if interface_id == "":
                assert isinstance(data, list), f"Тело ответа не является массивом JSON, получено: {type(data).__name__}"
                for interface_data in data:
                    _check_types_recursive(interface_data, INTERFACE_RUNTIME_SCHEMA)
            else:
                assert isinstance(data, dict), f"Тело ответа не является объектом JSON, получено: {type(data).__name__}"
                _check_types_recursive(data, INTERFACE_RUNTIME_SCHEMA)
                # Дополнительная проверка что name соответствует запрошенному ID
                assert data["name"] == interface_id, f"Name в ответе {data['name']} не соответствует запрошенному ID {interface_id}"
        elif response.status_code in [400, 404]:
            # Для 400/404 статус-кода проверяем что есть error объект
            data = response.json()
            assert "error" in data, f"Ответ с {response.status_code} статусом должен содержать error объект"

    except requests.exceptions.ConnectionError as e:
        pytest.skip(f"Сервис core недоступен: {e}")
    except (AssertionError, json.JSONDecodeError) as e:
        # 3. Формирование и вывод детального отчета об ошибке
        curl_command = _format_curl_command(api_client, ENDPOINT, interface_id, params, api_base_url)
        
        error_message = (
            f"\nТест с ID '{interface_id}' и параметрами {params} упал.\n"
            f"Ошибка: {e}\n\n"
            "================= Failed Test Request (cURL) ================\n"
            f"{curl_command}\n"
            "============================================================="
        )
        pytest.fail(error_message, pytrace=False) 


@pytest.fixture(scope="module")
def existing_interface_ids(api_client):
    """Возвращает список доступных ID интерфейсов из /interfaceRuntimes."""
    try:
        resp = api_client.get(ENDPOINT)
    except requests.exceptions.ConnectionError as e:
        pytest.skip(f"Сервис core недоступен: {e}")
    assert resp.status_code == 200, f"Не удалось получить список интерфейсов, статус: {resp.status_code}, тело: {resp.text}"
    try:
        data = resp.json()
    except json.JSONDecodeError:
        pytest.fail("Ответ /interfaceRuntimes не является валидным JSON")
    assert isinstance(data, list), "Ожидался список интерфейсов"
    names = [item.get("name") for item in data if isinstance(item, dict) and item.get("name")]
    # Удаляем дубликаты, сохраняем порядок
    seen = set()
    unique_names = []
    for n in names:
        if n not in seen:
            seen.add(n)
            unique_names.append(n)
    return unique_names


def test_interface_runtimes_id_existing_dynamic(api_client, existing_interface_ids):
    """
    Динамический позитивный тест без хардкода:
    - Получаем доступные ID из списка /interfaceRuntimes
    - Проверяем что GET /interfaceRuntimes/{id} возвращает 200 и валидный JSON по схеме
    """
    # Покрываем до 10 интерфейсов для экономии времени выполнения
    for interface_id in existing_interface_ids[:10]:
        response = api_client.get(f"{ENDPOINT}/{interface_id}")
        assert response.status_code == 200, f"ID '{interface_id}' должен существовать. Ответ: {response.status_code} {response.text}"
        data = response.json()
        assert isinstance(data, dict), f"Ожидался объект JSON, получено: {type(data).__name__}"
        _check_types_recursive(data, INTERFACE_RUNTIME_SCHEMA)
        assert data["name"] == interface_id, f"Name в ответе {data['name']} не соответствует запрошенному ID {interface_id}"