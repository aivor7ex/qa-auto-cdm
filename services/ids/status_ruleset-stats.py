import pytest
import random
import string

# Ожидаемая схема ответа для /status/ruleset-stats
SCHEMA = {
    "loaded": int,
    "failed": int,
}

def validate_schema(data, schema):
    """
    Рекурсивно валидирует структуру и типы данных ответа по заданной схеме.
    """
    assert isinstance(data, dict)
    # Проверяем, что все обязательные ключи из схемы присутствуют в ответе
    for key, expected_type in schema.items():
        assert key in data, f"Обязательный ключ '{key}' отсутствует в ответе."
        
        value = data[key]
        assert isinstance(value, expected_type), \
            f"Ключ '{key}' имеет неверный тип. Ожидался {expected_type}, получен {type(value)}."

@pytest.fixture
def ruleset_stats_data(api_client, attach_curl_on_fail):
    """
    Выполняет один GET-запрос и возвращает JSON-тело ответа.
    Фикстура используется всеми тестами для минимизации количества запросов.
    """
    with attach_curl_on_fail("/status/ruleset-stats", payload=None, method="GET"):
        response = api_client.get("/status/ruleset-stats")
        assert response.status_code == 200
        return response.json()

def test_ruleset_stats_schema(ruleset_stats_data):
    """
    Проверяет, что структура и типы данных ответа соответствуют схеме.
    """
    validate_schema(ruleset_stats_data, SCHEMA)

def test_values_are_non_negative(ruleset_stats_data):
    """
    Проверяет, что числовые значения в ответе являются неотрицательными.
    """
    for key, value in ruleset_stats_data.items():
        if isinstance(value, (int, float)):
            assert value >= 0, f"Значение для ключа '{key}' должно быть неотрицательным."

# --- Параметризация для проверки устойчивости ---

def generate_random_string(length=10):
    """Генерирует случайную строку."""
    letters = string.ascii_letters + string.digits
    return ''.join(random.choice(letters) for _ in range(length))

# Создаем 30 наборов случайных query-параметров для проверки устойчивости
robustness_params = [
    {generate_random_string(5): generate_random_string(10)} for _ in range(30)
]
robustness_params.extend([
    {"page": 1, "limit": 100},
    {"sort": "asc", "filter": "all"},
    {"_": 123456789},
    {"debug_mode": "true"},
])

@pytest.mark.parametrize("query_params", robustness_params)
def test_endpoint_robustness_with_query_params(api_client, query_params, attach_curl_on_fail):
    """
    Проверяет, что эндпоинт устойчив к различным и неожиданным query-параметрам,
    возвращая корректный код ответа и валидную схему.
    """
    with attach_curl_on_fail("/status/ruleset-stats", payload=query_params, method="GET"):
        response = api_client.get("/status/ruleset-stats", params=query_params)
        assert response.status_code == 200
        
        data = response.json()
        validate_schema(data, SCHEMA)

# Создаем 25 наборов случайных заголовков для проверки устойчивости
robustness_headers = [
    {f"X-{generate_random_string(10)}": generate_random_string(20)} for _ in range(25)
]
robustness_headers.extend([
    {"Accept-Language": "en-US,en;q=0.5"},
    {"X-Request-ID": "abc-123-def-456"},
    {"Pragma": "no-cache"},
])

@pytest.mark.parametrize("headers", robustness_headers)
def test_endpoint_robustness_with_headers(api_client, headers, attach_curl_on_fail):
    """
    Проверяет, что эндпоинт устойчив к различным и неожиданным заголовкам,
    возвращая корректный код ответа и валидную схему.
    """
    with attach_curl_on_fail("/status/ruleset-stats", headers=headers, method="GET"):
        response = api_client.get("/status/ruleset-stats", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        validate_schema(data, SCHEMA) 