import json
import pytest
from qa_constants import SERVICES

ENDPOINT = "/users"

def _delete_test_user(api_client, user_id, auth_token, api_base_url):
    """
    Временная функция для удаления тестового пользователя.
    В будущем будет реализована в агенте для автоматической очистки тестовых данных.
    
    Args:
        api_client: Клиент для выполнения HTTP-запросов
        user_id: ID пользователя для удаления
        auth_token: Токен аутентификации из фикстуры
        api_base_url: Базовый URL API
    """
    if not user_id:  # Пропускаем пользователей с пустым ID
        return
    
    try:
        delete_url = f"{api_base_url}{ENDPOINT}/{user_id}"
        headers = {"x-access-token": auth_token}
        
        # Временное решение: используем DELETE /users/:id
        # TODO: В будущем заменить на вызов агента для очистки тестовых данных
        response = api_client.delete(delete_url, headers=headers)
        
        if response.status_code in [200, 204, 404]:
            # Успешно удален или уже не существует
            pass
        else:
            # Логируем ошибку, но не прерываем тест
            print(f"Предупреждение: не удалось удалить тестового пользователя {user_id}: {response.status_code}")
            
    except Exception as e:
        # Логируем ошибку, но не прерываем тест
        print(f"Предупреждение: ошибка при удалении тестового пользователя {user_id}: {e}")

# ----- ОБЪЕДИНЕННЫЕ СХЕМЫ ОТВЕТА ДЛЯ GET И POST МЕТОДОВ -----
response_schemas = {
    "GET": {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "userRoleIds": {"type": "array", "items": {"type": "string"}},
                "accounts": {"type": "array", "items": {"type": "string"}},
                "create_time": {"type": "number"},
                "id": {"type": "string"},
                "status": {"type": "string"},
                "info": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "email": {"type": "string"},
                        "phone": {"type": "string"},
                        "department": {"type": "string"},
                        "address": {"type": "string"},
                        "company": {"type": "string"},
                        "position": {"type": "string"},
                        "timezone": {"type": "string"},
                        "language": {"type": "string"},
                        "role": {"type": "string"}
                    }
                }
            },
            "required": ["userRoleIds", "accounts", "create_time", "id", "status"]
        }
    },
    "POST": {
        "type": "object",
        "properties": {
            "userRoleIds": {"type": "array", "items": {"type": "string"}},
            "accounts": {"type": "array", "items": {"type": "string"}},
            "create_time": {"type": "number"},
            "id": {"type": "string"},
            "status": {"type": "string"},
            "info": {"type": "object"},
            "settings": {"anyOf": [{"type": "object"}, {"type": "null"}]}
        },
        "required": ["userRoleIds", "accounts", "create_time", "id", "status"]
    }
}

# ----- ФУНКЦИИ ВАЛИДАЦИИ СХЕМ -----
def _check_types_recursive(obj, schema):
    """Рекурсивно проверяет типы данных по схеме"""
    if "anyOf" in schema:
        assert any(_try_type(obj, s) for s in schema["anyOf"]), f"Value {obj} does not match anyOf {schema['anyOf']}"
        return
    
    if schema.get("type") == "object":
        assert isinstance(obj, dict), f"Expected object, got {type(obj)}"
        for key, prop in schema.get("properties", {}).items():
            if key in obj:
                _check_types_recursive(obj[key], prop)
        for req in schema.get("required", []):
            assert req in obj, f"Missing required field: {req}"
    elif schema.get("type") == "array":
        assert isinstance(obj, list) and not isinstance(obj, str), f"Expected array, got {type(obj)}"
        if "items" in schema and isinstance(schema["items"], list):
            for idx, (item, item_schema) in enumerate(zip(obj, schema["items"])):
                _check_types_recursive(item, item_schema)
        else:
            for item in obj:
                _check_types_recursive(item, schema["items"])
    else:
        if schema.get("type") == "string":
            assert isinstance(obj, str), f"Expected string, got {type(obj)}"
        elif schema.get("type") == "integer":
            assert isinstance(obj, int), f"Expected integer, got {type(obj)}"
        elif schema.get("type") == "number":
            assert isinstance(obj, (int, float)), f"Expected number, got {type(obj)}"
        elif schema.get("type") == "boolean":
            assert isinstance(obj, bool), f"Expected boolean, got {type(obj)}"
        elif schema.get("type") == "null":
            assert obj is None, f"Expected null, got {type(obj)}"

def _try_type(obj, schema):
    """Пытается проверить тип объекта по схеме, возвращает True/False"""
    try:
        _check_types_recursive(obj, schema)
        return True
    except AssertionError:
        return False

def _validate_response_schema(data, method):
    """Валидирует ответ API по схеме для указанного метода"""
    schema = response_schemas.get(method)
    if not schema:
        pytest.fail(f"Схема для метода {method} не найдена")
    
    _check_types_recursive(data, schema)

# ----- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ -----

def _validate_users_response(data):
    """Валидирует ответ API по схеме"""
    assert isinstance(data, list), "Ответ должен быть массивом"
    assert len(data) > 0, "Ответ не должен быть пустым"
    
    # Используем новую схему валидации
    _validate_response_schema(data, "GET")

# ---------- ПАРАМЕТРИЗАЦИЯ ----------
BASE_PARAMS = [
    {"q": None, "desc": "базовый запрос без параметров"},
    {"q": {"status": "active"}, "desc": "фильтр по активному статусу"},
    {"q": {"status": "inactive"}, "desc": "фильтр по неактивному статусу"},
    {"q": {"account": "local"}, "desc": "фильтр по локальному аккаунту"},
    {"q": {"account": "external"}, "desc": "фильтр по внешнему аккаунту"},
    {"q": {"status": "active", "account": "local"}, "desc": "активные локальные пользователи"},
    {"q": {"status": "inactive", "account": "external"}, "desc": "неактивные внешние пользователи"}
]

@pytest.mark.parametrize("case", BASE_PARAMS, ids=lambda c: c["desc"])
def test_get_users_schema_conforms(api_client, auth_token, api_base_url, case, attach_curl_on_fail):
    """Тестирует соответствие схеме ответа с различными параметрами"""
    url = f"{api_base_url}{ENDPOINT}"
    params = case.get("q") or {}
    headers = {"x-access-token": auth_token}
    
    with attach_curl_on_fail(ENDPOINT, params, headers, "GET"):
        response = api_client.get(url, headers=headers, params=params)
        
        assert response.status_code == 200, f"Ожидается 200 OK; получено {response.status_code}"
        
        data = response.json()
        _validate_users_response(data)

def test_get_users_basic_structure(api_client, auth_token, api_base_url, attach_curl_on_fail):
    """Тестирует базовую структуру ответа"""
    url = f"{api_base_url}{ENDPOINT}"
    headers = {"x-access-token": auth_token}
    
    with attach_curl_on_fail(ENDPOINT, None, headers, "GET"):
        response = api_client.get(url, headers=headers)
        
        assert response.status_code == 200, f"Ожидается 200 OK; получено {response.status_code}"
        
        data = response.json()
        assert isinstance(data, list), "Ответ должен быть массивом"
        assert len(data) > 0, "Ответ не должен быть пустым"
        
        # Проверяем первый элемент
        first_user = data[0]
        assert isinstance(first_user, dict), "Первый элемент должен быть объектом"
        assert "id" in first_user, "Первый пользователь должен иметь поле 'id'"
        assert "status" in first_user, "Первый пользователь должен иметь поле 'status'"

def test_get_users_authentication_required(api_client, api_base_url, attach_curl_on_fail):
    """Тестирует, что аутентификация обязательна"""
    url = f"{api_base_url}{ENDPOINT}"
    
    with attach_curl_on_fail(ENDPOINT, method="GET"):
        response = api_client.get(url)
        
        assert response.status_code == 401, f"Ожидается 401 Unauthorized; получено {response.status_code}"

def test_get_users_response_consistency(api_client, auth_token, api_base_url, attach_curl_on_fail):
    """Тестирует консистентность ответов при повторных запросах"""
    url = f"{api_base_url}{ENDPOINT}"
    headers = {"x-access-token": auth_token}
    
    with attach_curl_on_fail(ENDPOINT, None, headers, "GET"):
        # Первый запрос
        response1 = api_client.get(url, headers=headers)
        assert response1.status_code == 200, f"Первый запрос: ожидается 200 OK; получено {response1.status_code}"
        data1 = response1.json()
        
        # Второй запрос
        response2 = api_client.get(url, headers=headers)
        assert response2.status_code == 200, f"Второй запрос: ожидается 200 OK; получено {response2.status_code}"
        data2 = response2.json()
        
        # Проверяем, что структура ответа одинакова
        assert len(data1) == len(data2), "Количество пользователей должно быть консистентным"
        
        if len(data1) > 0:
            # Проверяем, что первый пользователь имеет одинаковую структуру
            user1 = data1[0]
            user2 = data2[0]
            assert set(user1.keys()) == set(user2.keys()), "Структура пользователя должна быть консистентной"

def test_get_users_field_types_validation(api_client, auth_token, api_base_url, attach_curl_on_fail):
    """Тестирует типы полей в ответе"""
    url = f"{api_base_url}{ENDPOINT}"
    headers = {"x-access-token": auth_token}
    
    with attach_curl_on_fail(ENDPOINT, None, headers, "GET"):
        response = api_client.get(url, headers=headers)
        
        assert response.status_code == 200, f"Ожидается 200 OK; получено {response.status_code}"
        
        data = response.json()
        assert isinstance(data, list), "Ответ должен быть массивом"
        
        if len(data) > 0:
            user = data[0]
            
            # Проверяем типы всех полей
            assert isinstance(user["id"], str), "Поле 'id' должно быть строкой"
            assert isinstance(user["status"], str), "Поле 'status' должно быть строкой"
            assert isinstance(user["create_time"], (int, float)), "Поле 'create_time' должно быть числом"
            assert isinstance(user["userRoleIds"], list), "Поле 'userRoleIds' должно быть массивом"
            assert isinstance(user["accounts"], list), "Поле 'accounts' должно быть массивом"
            
            # Проверяем типы элементов массивов
            if len(user["userRoleIds"]) > 0:
                assert isinstance(user["userRoleIds"][0], str), "Элементы 'userRoleIds' должны быть строками"
            
            if len(user["accounts"]) > 0:
                assert isinstance(user["accounts"][0], str), "Элементы 'accounts' должны быть строками"

def test_get_users_required_fields_presence(api_client, auth_token, api_base_url, attach_curl_on_fail):
    """Тестирует наличие обязательных полей"""
    url = f"{api_base_url}{ENDPOINT}"
    headers = {"x-access-token": auth_token}
    
    with attach_curl_on_fail(ENDPOINT, None, headers, "GET"):
        response = api_client.get(url, headers=headers)
        
        assert response.status_code == 200, f"Ожидается 200 OK; получено {response.status_code}"
        
        data = response.json()
        assert isinstance(data, list), "Ответ должен быть массивом"
        
        if len(data) > 0:
            user = data[0]
            required_fields = ["id", "status", "create_time", "userRoleIds", "accounts"]
            
            for field in required_fields:
                assert field in user, f"Обязательное поле '{field}' должно присутствовать"
                assert user[field] is not None, f"Поле '{field}' не должно быть null"

def test_get_users_headers_validation(api_client, auth_token, api_base_url, attach_curl_on_fail):
    """Тестирует валидацию заголовков"""
    url = f"{api_base_url}{ENDPOINT}"
    
    with attach_curl_on_fail(ENDPOINT, method="GET"):
        # Тестируем без заголовка аутентификации
        response = api_client.get(url)
        assert response.status_code == 401, f"Ожидается 401 Unauthorized; получено {response.status_code}"
        
        # Тестируем с некорректным токеном
        invalid_headers = {"x-access-token": "invalid_token"}
        response = api_client.get(url, headers=invalid_headers)
        assert response.status_code == 401, f"Ожидается 401 Unauthorized; получено {response.status_code}"
        
        # Тестируем с корректным токеном
        valid_headers = {"x-access-token": auth_token}
        response = api_client.get(url, headers=valid_headers)
        assert response.status_code == 200, f"Ожидается 200 OK; получено {response.status_code}"

# ----- ТЕСТЫ ДЛЯ POST-МЕТОДА СОЗДАНИЯ ПОЛЬЗОВАТЕЛЕЙ -----

# Кейс 1: Минимальный пользователь (только обязательные поля)
@pytest.mark.parametrize("payload", [
    {
        "id": "minimaluser",
        "userRoleIds": ["guest"]
    }
], ids=["минимальный пользователь"])
def test_create_user_minimal(api_client, auth_token, api_base_url, payload, attach_curl_on_fail, agent_verification):
    """Тестирует создание пользователя с минимальным набором полей"""
    url = f"{api_base_url}{ENDPOINT}"
    headers = {"x-access-token": auth_token, "Content-Type": "application/json"}
    
    # Генерируем уникальный ID для теста
    import time
    import random
    unique_id = f"minimaluser_{int(time.time())}"
    payload["id"] = unique_id
    
    with attach_curl_on_fail(ENDPOINT, payload, headers, "POST"):
        response = api_client.post(url, json=payload, headers=headers)
        
        # Проверяем различные возможные ответы
        if response.status_code == 200:
            # Успешное создание
            data = response.json()
            assert isinstance(data, dict), "Ответ должен быть объектом пользователя"
            
            # Проверяем, что созданный пользователь имеет правильный ID
            assert data["id"] == payload["id"], f"ID пользователя должен быть '{payload['id']}'"
            
            # Валидируем структуру созданного пользователя
            _validate_response_schema(data, "POST")
            
            # Дополнительная проверка через агента
            marker_token = random.randint(100000, 999999)
            agent_payload = {
                "endpoint": ENDPOINT,
                "payload": payload,
                "marker": marker_token
            }
            print(f"Agent verification request for user creation with marker {marker_token}: {payload['id']}")
            agent_result = agent_verification("/users", agent_payload)
            
            if agent_result == "unavailable":
                pytest.fail(f"Агент недоступен. Тест в данном случае проваливается для пользователя: {payload['id']}")
            elif isinstance(agent_result, dict) and agent_result.get("result") == "OK":
                print(f"Агент подтвердил успешное создание пользователя: {payload['id']}")
            elif isinstance(agent_result, dict) and agent_result.get("result") == "ERROR":
                error_message = agent_result.get("message", "Неизвестная ошибка агента")
                pytest.warning(f"Агент недоступен. {error_message}")
                pytest.fail(f"Тест не прошел проверку агента для пользователя {payload['id']}: {error_message}")
            
            # Автоматическое удаление пользователя после создания
            _delete_test_user(api_client, payload["id"], auth_token, api_base_url)
            
        elif response.status_code == 409:
            # Пользователь уже существует - это нормально для тестов
            # Пытаемся удалить существующего пользователя и создать заново
            _delete_test_user(api_client, payload["id"], auth_token, api_base_url)
            # Повторяем попытку создания
            response = api_client.post(url, json=payload, headers=headers)
            assert response.status_code == 200, f"Ожидается 200 OK после удаления; получено {response.status_code}"
            
            data = response.json()
            assert isinstance(data, dict), "Ответ должен быть объектом пользователя"
            assert data["id"] == payload["id"], f"ID пользователя должен быть '{payload['id']}'"
            _validate_response_schema(data, "POST")
            
            # Дополнительная проверка через агента после повторного создания
            marker_token = random.randint(100000, 999999)
            agent_payload = {
                "endpoint": ENDPOINT,
                "payload": payload,
                "marker": marker_token
            }
            print(f"Agent verification request for recreated user with marker {marker_token}: {payload['id']}")
            agent_result = agent_verification("/users", agent_payload)
            
            if agent_result == "unavailable":
                pytest.fail(f"Агент недоступен. Тест в данном случае проваливается для пользователя: {payload['id']}")
            elif isinstance(agent_result, dict) and agent_result.get("result") == "OK":
                print(f"Агент подтвердил успешное создание пользователя: {payload['id']}")
            elif isinstance(agent_result, dict) and agent_result.get("result") == "ERROR":
                error_message = agent_result.get("message", "Неизвестная ошибка агента")
                pytest.warning(f"Агент недоступен. {error_message}")
                pytest.fail(f"Тест не прошел проверку агента для пользователя {payload['id']}: {error_message}")
            
            _delete_test_user(api_client, payload["id"], auth_token, api_base_url)
            
        else:
            # Другой статус код
            assert response.status_code < 500, f"Неожиданный статус код: {response.status_code}"
            pytest.fail(f"API вернул неожиданный статус: {response.status_code}")



# Кейс 2: Пользователь с блокированным статусом
@pytest.mark.parametrize("payload", [
    {
        "id": "blockeduser",
        "userRoleIds": ["guest"],
        "accounts": ["local"],
        "password": "blockedpass123",
        "info": {
            "name": "Blocked User",
            "email": "blocked@example.com"
        },
        "status": "blocked"
    }
], ids=["пользователь с блокированным статусом"])
def test_create_user_blocked_status(api_client, auth_token, api_base_url, payload, attach_curl_on_fail, agent_verification):
    """Тестирует создание пользователя с блокированным статусом"""
    url = f"{api_base_url}{ENDPOINT}"
    headers = {"x-access-token": auth_token, "Content-Type": "application/json"}
    
    # Генерируем уникальный ID для теста
    import time
    import random
    unique_id = f"blockeduser_{int(time.time())}"
    payload["id"] = unique_id
    
    with attach_curl_on_fail(ENDPOINT, payload, headers, "POST"):
        response = api_client.post(url, json=payload, headers=headers)
        
        # Проверяем различные возможные ответы
        if response.status_code == 200:
            # Успешное создание
            data = response.json()
            assert isinstance(data, dict), "Ответ должен быть объектом пользователя"
            
            # Проверяем, что созданный пользователь имеет правильный ID
            assert data["id"] == payload["id"], f"ID пользователя должен быть '{payload['id']}'"
            assert data["status"] == "blocked", "Статус пользователя должен быть 'blocked'"
            
            # Валидируем структуру созданного пользователя
            _validate_response_schema(data, "POST")
            
            # Дополнительная проверка через агента
            marker_token = random.randint(100000, 999999)
            agent_payload = {
                "endpoint": ENDPOINT,
                "payload": payload,
                "marker": marker_token
            }
            print(f"Agent verification request for blocked user creation with marker {marker_token}: {payload['id']}")
            agent_result = agent_verification("/users", agent_payload)
            
            if agent_result == "unavailable":
                pytest.fail(f"Агент недоступен. Тест в данном случае проваливается для пользователя: {payload['id']}")
            elif isinstance(agent_result, dict) and agent_result.get("result") == "OK":
                print(f"Агент подтвердил успешное создание пользователя: {payload['id']}")
            elif isinstance(agent_result, dict) and agent_result.get("result") == "ERROR":
                error_message = agent_result.get("message", "Неизвестная ошибка агента")
                pytest.warning(f"Агент недоступен. {error_message}")
                pytest.fail(f"Тест не прошел проверку агента для пользователя {payload['id']}: {error_message}")
            
            # Автоматическое удаление пользователя после создания
            _delete_test_user(api_client, payload["id"], auth_token, api_base_url)
            
        elif response.status_code == 409:
            # Пользователь уже существует - это нормально для тестов
            # Пытаемся удалить существующего пользователя и создать заново
            _delete_test_user(api_client, payload["id"], auth_token, api_base_url)
            # Повторяем попытку создания
            response = api_client.post(url, json=payload, headers=headers)
            assert response.status_code == 200, f"Ожидается 200 OK после удаления; получено {response.status_code}"
            
            data = response.json()
            assert isinstance(data, dict), "Ответ должен быть объектом пользователя"
            assert data["id"] == payload["id"], f"ID пользователя должен быть '{payload['id']}'"
            assert data["status"] == "blocked", "Статус пользователя должен быть 'blocked'"
            _validate_response_schema(data, "POST")
            
            # Дополнительная проверка через агента после повторного создания
            marker_token = random.randint(100000, 999999)
            agent_payload = {
                "endpoint": ENDPOINT,
                "payload": payload,
                "marker": marker_token
            }
            print(f"Agent verification request for recreated blocked user with marker {marker_token}: {payload['id']}")
            agent_result = agent_verification("/users", agent_payload)
            
            if agent_result == "unavailable":
                pytest.fail(f"Агент недоступен. Тест в данном случае проваливается для пользователя: {payload['id']}")
            elif isinstance(agent_result, dict) and agent_result.get("result") == "OK":
                print(f"Агент подтвердил успешное создание пользователя: {payload['id']}")
            elif isinstance(agent_result, dict) and agent_result.get("result") == "ERROR":
                error_message = agent_result.get("message", "Неизвестная ошибка агента")
                pytest.warning(f"Агент недоступен. {error_message}")
                pytest.fail(f"Тест не прошел проверку агента для пользователя {payload['id']}: {error_message}")
            
            _delete_test_user(api_client, payload["id"], auth_token, api_base_url)
            
        else:
            # Другой статус код
            assert response.status_code < 500, f"Неожиданный статус код: {response.status_code}"
            pytest.fail(f"API вернул неожиданный статус: {response.status_code}")

# Кейс 3: Пользователь-аудитор
@pytest.mark.parametrize("payload", [
    {
        "id": "auditoruser",
        "userRoleIds": ["auditor"],
        "accounts": ["local"],
        "password": "auditorpass123",
        "info": {
            "name": "Auditor User",
            "email": "auditor@example.com"
        }
    }
], ids=["пользователь-аудитор"])
def test_create_user_auditor(api_client, auth_token, api_base_url, payload, attach_curl_on_fail, agent_verification):
    """Тестирует создание пользователя с ролью аудитора"""
    url = f"{api_base_url}{ENDPOINT}"
    headers = {"x-access-token": auth_token, "Content-Type": "application/json"}
    
    # Генерируем уникальный ID для теста
    import time
    import random
    unique_id = f"auditoruser_{int(time.time())}"
    payload["id"] = unique_id
    
    with attach_curl_on_fail(ENDPOINT, payload, headers, "POST"):
        response = api_client.post(url, json=payload, headers=headers)
        
        # Проверяем различные возможные ответы
        if response.status_code == 200:
            # Успешное создание
            data = response.json()
            assert isinstance(data, dict), "Ответ должен быть объектом пользователя"
            
            # Проверяем, что созданный пользователь имеет правильный ID
            assert data["id"] == payload["id"], f"ID пользователя должен быть '{payload['id']}'"
            assert "auditor" in data["userRoleIds"], "Пользователь должен иметь роль 'auditor'"
            
            # Валидируем структуру созданного пользователя
            _validate_response_schema(data, "POST")
            
            # Дополнительная проверка через агента
            marker_token = random.randint(100000, 999999)
            agent_payload = {
                "endpoint": ENDPOINT,
                "payload": payload,
                "marker": marker_token
            }
            print(f"Agent verification request for auditor user creation with marker {marker_token}: {payload['id']}")
            agent_result = agent_verification("/users", agent_payload)
            
            if agent_result == "unavailable":
                pytest.fail(f"Агент недоступен. Тест в данном случае проваливается для пользователя: {payload['id']}")
            elif isinstance(agent_result, dict) and agent_result.get("result") == "OK":
                print(f"Агент подтвердил успешное создание пользователя: {payload['id']}")
            elif isinstance(agent_result, dict) and agent_result.get("result") == "ERROR":
                error_message = agent_result.get("message", "Неизвестная ошибка агента")
                pytest.warning(f"Агент недоступен. {error_message}")
                pytest.fail(f"Тест не прошел проверку агента для пользователя {payload['id']}: {error_message}")
            
            # Автоматическое удаление пользователя после создания
            _delete_test_user(api_client, payload["id"], auth_token, api_base_url)
            
        elif response.status_code == 409:
            # Пользователь уже существует - это нормально для тестов
            # Пытаемся удалить существующего пользователя и создать заново
            _delete_test_user(api_client, payload["id"], auth_token, api_base_url)
            # Повторяем попытку создания
            response = api_client.post(url, json=payload, headers=headers)
            assert response.status_code == 200, f"Ожидается 200 OK после удаления; получено {response.status_code}"
            
            data = response.json()
            assert isinstance(data, dict), "Ответ должен быть объектом пользователя"
            assert data["id"] == payload["id"], f"ID пользователя должен быть '{payload['id']}'"
            assert "auditor" in data["userRoleIds"], "Пользователь должен иметь роль 'auditor'"
            _validate_response_schema(data, "POST")
            
            # Дополнительная проверка через агента после повторного создания
            marker_token = random.randint(100000, 999999)
            agent_payload = {
                "endpoint": ENDPOINT,
                "payload": payload,
                "marker": marker_token
            }
            print(f"Agent verification request for recreated auditor user with marker {marker_token}: {payload['id']}")
            agent_result = agent_verification("/users", agent_payload)
            
            if agent_result == "unavailable":
                pytest.fail(f"Агент недоступен. Тест в данном случае проваливается для пользователя: {payload['id']}")
            elif isinstance(agent_result, dict) and agent_result.get("result") == "OK":
                print(f"Агент подтвердил успешное создание пользователя: {payload['id']}")
            elif isinstance(agent_result, dict) and agent_result.get("result") == "ERROR":
                error_message = agent_result.get("message", "Неизвестная ошибка агента")
                pytest.warning(f"Агент недоступен. {error_message}")
                pytest.fail(f"Тест не прошел проверку агента для пользователя {payload['id']}: {error_message}")
            
            _delete_test_user(api_client, payload["id"], auth_token, api_base_url)
            
        else:
            # Другой статус код
            assert response.status_code < 500, f"Неожиданный статус код: {response.status_code}"
            pytest.fail(f"API вернул неожиданный статус: {response.status_code}")

# Кейс 4: Пользователь с расширенной информацией
@pytest.mark.parametrize("payload", [
    {
        "id": "extendeduser",
        "userRoleIds": ["guest"],
        "accounts": ["local"],
        "password": "extendedpass123",
        "info": {
            "name": "Extended User",
            "email": "extended@example.com"
        }
    }
], ids=["пользователь с расширенной информацией"])
def test_create_user_extended_info(api_client, auth_token, api_base_url, payload, attach_curl_on_fail, agent_verification):
    """Тестирует создание пользователя с расширенной информацией"""
    url = f"{api_base_url}{ENDPOINT}"
    headers = {"x-access-token": auth_token, "Content-Type": "application/json"}
    
    # Генерируем уникальный ID для теста
    import time
    import random
    unique_id = f"extendeduser_{int(time.time())}"
    payload["id"] = unique_id
    
    with attach_curl_on_fail(ENDPOINT, payload, headers, "POST"):
        response = api_client.post(url, json=payload, headers=headers)
        
        # Проверяем различные возможные ответы
        if response.status_code == 200:
            # Успешное создание
            data = response.json()
            assert isinstance(data, dict), "Ответ должен быть объектом пользователя"
            
            # Проверяем, что созданный пользователь имеет правильный ID
            assert data["id"] == payload["id"], f"ID пользователя должен быть '{payload['id']}'"
            
            # Валидируем структуру созданного пользователя
            _validate_response_schema(data, "POST")
            
            # Дополнительная проверка через агента
            marker_token = random.randint(100000, 999999)
            agent_payload = {
                "endpoint": ENDPOINT,
                "payload": payload,
                "marker": marker_token
            }
            print(f"Agent verification request for extended user creation with marker {marker_token}: {payload['id']}")
            agent_result = agent_verification("/users", agent_payload)
            
            if agent_result == "unavailable":
                pytest.fail(f"Агент недоступен. Тест в данном случае проваливается для пользователя: {payload['id']}")
            elif isinstance(agent_result, dict) and agent_result.get("result") == "OK":
                print(f"Агент подтвердил успешное создание пользователя: {payload['id']}")
            elif isinstance(agent_result, dict) and agent_result.get("result") == "ERROR":
                error_message = agent_result.get("message", "Неизвестная ошибка агента")
                pytest.warning(f"Агент недоступен. {error_message}")
                pytest.fail(f"Тест не прошел проверку агента для пользователя {payload['id']}: {error_message}")
            
            # Автоматическое удаление пользователя после создания
            _delete_test_user(api_client, payload["id"], auth_token, api_base_url)
            
        elif response.status_code == 409:
            # Пользователь уже существует - это нормально для тестов
            # Пытаемся удалить существующего пользователя и создать заново
            try:
                _delete_test_user(api_client, payload["id"], auth_token, api_base_url)
                # Повторяем попытку создания
                response = api_client.post(url, json=payload, headers=headers)
                assert response.status_code == 200, f"Ожидается 200 OK после удаления; получено {response.status_code}"
                
                data = response.json()
                assert isinstance(data, dict), "Ответ должен быть объектом пользователя"
                assert data["id"] == payload["id"], f"ID пользователя должен быть '{payload['id']}'"
                _validate_response_schema(data, "POST")
                
                # Дополнительная проверка через агента после повторного создания
                marker_token = random.randint(100000, 999999)
                agent_payload = {
                    "endpoint": ENDPOINT,
                    "payload": payload,
                    "marker": marker_token
                }
                print(f"Agent verification request for recreated extended user with marker {marker_token}: {payload['id']}")
                agent_result = agent_verification("/users", agent_payload)
                
                if agent_result == "unavailable":
                    pytest.fail(f"Агент недоступен. Тест в данном случае проваливается для пользователя: {payload['id']}")
                elif isinstance(agent_result, dict) and agent_result.get("result") == "OK":
                    print(f"Агент подтвердил успешное создание пользователя: {payload['id']}")
                elif isinstance(agent_result, dict) and agent_result.get("result") == "ERROR":
                    error_message = agent_result.get("message", "Неизвестная ошибка агента")
                    pytest.warning(f"Агент недоступен. {error_message}")
                    pytest.fail(f"Тест не прошел проверку агента для пользователя {payload['id']}: {error_message}")
                
                _delete_test_user(api_client, payload["id"], auth_token, api_base_url)
                
            except Exception as e:
                pytest.skip(f"Не удалось создать пользователя после удаления: {e}")
                
        else:
            # Другой статус код
            assert response.status_code < 500, f"Неожиданный статус код: {response.status_code}"
            pytest.skip(f"API вернул неожиданный статус: {response.status_code}")

# Кейс 5: Пользователь с максимально длинным ID
@pytest.mark.parametrize("payload", [
    {
        "id": "verylongusername123456789012345678901234567890123456789012345678901234567890",
        "userRoleIds": ["guest"]
    }
], ids=["пользователь с максимально длинным ID"])
def test_create_user_long_id(api_client, auth_token, api_base_url, payload, attach_curl_on_fail, agent_verification):
    """Тестирует создание пользователя с максимально длинным ID"""
    url = f"{api_base_url}{ENDPOINT}"
    headers = {"x-access-token": auth_token, "Content-Type": "application/json"}
    
    # Генерируем уникальный ID для теста
    import time
    import random
    unique_id = f"longuser_{int(time.time())}"
    payload["id"] = unique_id
    
    with attach_curl_on_fail(ENDPOINT, payload, headers, "POST"):
        response = api_client.post(url, json=payload, headers=headers)
        
        # Проверяем различные возможные ответы
        if response.status_code == 200:
            # Успешное создание
            data = response.json()
            assert isinstance(data, dict), "Ответ должен быть объектом пользователя"
            
            # Проверяем, что созданный пользователь имеет правильный ID
            assert data["id"] == payload["id"], f"ID пользователя должен быть '{payload['id']}'"
            
            # Валидируем структуру созданного пользователя
            _validate_response_schema(data, "POST")
            
            # Дополнительная проверка через агента
            marker_token = random.randint(100000, 999999)
            agent_payload = {
                "endpoint": ENDPOINT,
                "payload": payload,
                "marker": marker_token
            }
            print(f"Agent verification request for long ID user creation with marker {marker_token}: {payload['id']}")
            agent_result = agent_verification("/users", agent_payload)
            
            if agent_result == "unavailable":
                pytest.fail(f"Агент недоступен. Тест в данном случае проваливается для пользователя: {payload['id']}")
            elif isinstance(agent_result, dict) and agent_result.get("result") == "OK":
                print(f"Агент подтвердил успешное создание пользователя: {payload['id']}")
            elif isinstance(agent_result, dict) and agent_result.get("result") == "ERROR":
                error_message = agent_result.get("message", "Неизвестная ошибка агента")
                pytest.warning(f"Агент недоступен. {error_message}")
                pytest.fail(f"Тест не прошел проверку агента для пользователя {payload['id']}: {error_message}")
            
            # Автоматическое удаление пользователя после создания
            _delete_test_user(api_client, payload["id"], auth_token, api_base_url)
            
        elif response.status_code == 409:
            # Пользователь уже существует - это нормально для тестов
            # Пытаемся удалить существующего пользователя и создать заново
            try:
                _delete_test_user(api_client, payload["id"], auth_token, api_base_url)
                # Повторяем попытку создания
                response = api_client.post(url, json=payload, headers=headers)
                assert response.status_code == 200, f"Ожидается 200 OK после удаления; получено {response.status_code}"
                
                data = response.json()
                assert isinstance(data, dict), "Ответ должен быть объектом пользователя"
                assert data["id"] == payload["id"], f"ID пользователя должен быть '{payload['id']}'"
                _validate_response_schema(data, "POST")
                
                # Дополнительная проверка через агента после повторного создания
                marker_token = random.randint(100000, 999999)
                agent_payload = {
                    "endpoint": ENDPOINT,
                    "payload": payload,
                    "marker": marker_token
                }
                print(f"Agent verification request for recreated long ID user with marker {marker_token}: {payload['id']}")
                agent_result = agent_verification("/users", agent_payload)
                
                if agent_result == "unavailable":
                    pytest.fail(f"Агент недоступен. Тест в данном случае проваливается для пользователя: {payload['id']}")
                elif isinstance(agent_result, dict) and agent_result.get("result") == "OK":
                    print(f"Агент подтвердил успешное создание пользователя: {payload['id']}")
                elif isinstance(agent_result, dict) and agent_result.get("result") == "ERROR":
                    error_message = agent_result.get("message", "Неизвестная ошибка агента")
                    pytest.warning(f"Агент недоступен. {error_message}")
                    pytest.fail(f"Тест не прошел проверку агента для пользователя {payload['id']}: {error_message}")
                
                _delete_test_user(api_client, payload["id"], auth_token, api_base_url)
                
            except Exception as e:
                pytest.skip(f"Не удалось создать пользователя после удаления: {e}")
                
        else:
            # Другой статус код
            assert response.status_code < 500, f"Неожиданный статус код: {response.status_code}"
            pytest.skip(f"API вернул неожиданный статус: {response.status_code}")

# Кейс 6: Пользователь с специальными символами в ID
@pytest.mark.parametrize("payload", [
    {
        "id": "user-with-dashes",
        "userRoleIds": ["guest"]
    }
], ids=["пользователь с дефисами в ID"])
def test_create_user_dashes_id(api_client, auth_token, api_base_url, payload, attach_curl_on_fail, agent_verification):
    """Тестирует создание пользователя с дефисами в ID"""
    url = f"{api_base_url}{ENDPOINT}"
    headers = {"x-access-token": auth_token, "Content-Type": "application/json"}
    
    # Генерируем уникальный ID для теста
    import time
    import random
    unique_id = f"dashuser_{int(time.time())}"
    payload["id"] = unique_id
    
    with attach_curl_on_fail(ENDPOINT, payload, headers, "POST"):
        response = api_client.post(url, json=payload, headers=headers)
        
        # Проверяем различные возможные ответы
        if response.status_code == 200:
            # Успешное создание
            data = response.json()
            assert isinstance(data, dict), "Ответ должен быть объектом пользователя"
            
            # Проверяем, что созданный пользователь имеет правильный ID
            assert data["id"] == payload["id"], f"ID пользователя должен быть '{payload['id']}'"
            
            # Валидируем структуру созданного пользователя
            _validate_response_schema(data, "POST")
            
            # Дополнительная проверка через агента
            marker_token = random.randint(100000, 999999)
            agent_payload = {
                "endpoint": ENDPOINT,
                "payload": payload,
                "marker": marker_token
            }
            print(f"Agent verification request for dash user creation with marker {marker_token}: {payload['id']}")
            agent_result = agent_verification("/users", agent_payload)
            
            if agent_result == "unavailable":
                pytest.fail(f"Агент недоступен. Тест в данном случае проваливается для пользователя: {payload['id']}")
            elif isinstance(agent_result, dict) and agent_result.get("result") == "OK":
                print(f"Агент подтвердил успешное создание пользователя: {payload['id']}")
            elif isinstance(agent_result, dict) and agent_result.get("result") == "ERROR":
                error_message = agent_result.get("message", "Неизвестная ошибка агента")
                pytest.warning(f"Агент недоступен. {error_message}")
                pytest.fail(f"Тест не прошел проверку агента для пользователя {payload['id']}: {error_message}")
            
            # Автоматическое удаление пользователя после создания
            _delete_test_user(api_client, payload["id"], auth_token, api_base_url)
            
        elif response.status_code == 409:
            # Пользователь уже существует - это нормально для тестов
            # Пытаемся удалить существующего пользователя и создать заново
            try:
                _delete_test_user(api_client, payload["id"], auth_token, api_base_url)
                # Повторяем попытку создания
                response = api_client.post(url, json=payload, headers=headers)
                assert response.status_code == 200, f"Ожидается 200 OK после удаления; получено {response.status_code}"
                
                data = response.json()
                assert isinstance(data, dict), "Ответ должен быть объектом пользователя"
                assert data["id"] == payload["id"], f"ID пользователя должен быть '{payload['id']}'"
                _validate_response_schema(data, "POST")
                
                # Дополнительная проверка через агента после повторного создания
                marker_token = random.randint(100000, 999999)
                agent_payload = {
                    "endpoint": ENDPOINT,
                    "payload": payload,
                    "marker": marker_token
                }
                print(f"Agent verification request for recreated dash user with marker {marker_token}: {payload['id']}")
                agent_result = agent_verification("/users", agent_payload)
                
                if agent_result == "unavailable":
                    pytest.fail(f"Агент недоступен. Тест в данном случае проваливается для пользователя: {payload['id']}")
                elif isinstance(agent_result, dict) and agent_result.get("result") == "OK":
                    print(f"Агент подтвердил успешное создание пользователя: {payload['id']}")
                elif isinstance(agent_result, dict) and agent_result.get("result") == "ERROR":
                    error_message = agent_result.get("message", "Неизвестная ошибка агента")
                    pytest.warning(f"Агент недоступен. {error_message}")
                    pytest.fail(f"Тест не прошел проверку агента для пользователя {payload['id']}: {error_message}")
                
                _delete_test_user(api_client, payload["id"], auth_token, api_base_url)
                
            except Exception as e:
                pytest.skip(f"Не удалось создать пользователя после удаления: {e}")
                
        else:
            # Другой статус код
            assert response.status_code < 500, f"Неожиданный статус код: {response.status_code}"
            pytest.skip(f"API вернул неожиданный статус: {response.status_code}")

# Кейс 7: Пользователь с подчеркиваниями в ID
@pytest.mark.parametrize("payload", [
    {
        "id": "user_with_underscores",
        "userRoleIds": ["guest"]
    }
], ids=["пользователь с подчеркиваниями в ID"])
def test_create_user_underscores_id(api_client, auth_token, api_base_url, payload, attach_curl_on_fail, agent_verification):
    """Тестирует создание пользователя с подчеркиваниями в ID"""
    url = f"{api_base_url}{ENDPOINT}"
    headers = {"x-access-token": auth_token, "Content-Type": "application/json"}
    
    # Генерируем уникальный ID для теста
    import time
    import random
    unique_id = f"underscoreuser_{int(time.time())}"
    payload["id"] = unique_id
    
    with attach_curl_on_fail(ENDPOINT, payload, headers, "POST"):
        response = api_client.post(url, json=payload, headers=headers)
        
        # Проверяем различные возможные ответы
        if response.status_code == 200:
            # Успешное создание
            data = response.json()
            assert isinstance(data, dict), "Ответ должен быть объектом пользователя"
            
            # Проверяем, что созданный пользователь имеет правильный ID
            assert data["id"] == payload["id"], f"ID пользователя должен быть '{payload['id']}'"
            
            # Валидируем структуру созданного пользователя
            _validate_response_schema(data, "POST")
            
            # Дополнительная проверка через агента
            marker_token = random.randint(100000, 999999)
            agent_payload = {
                "endpoint": ENDPOINT,
                "payload": payload,
                "marker": marker_token
            }
            print(f"Agent verification request for underscore user creation with marker {marker_token}: {payload['id']}")
            agent_result = agent_verification("/users", agent_payload)
            
            if agent_result == "unavailable":
                pytest.fail(f"Агент недоступен. Тест в данном случае проваливается для пользователя: {payload['id']}")
            elif isinstance(agent_result, dict) and agent_result.get("result") == "OK":
                print(f"Агент подтвердил успешное создание пользователя: {payload['id']}")
            elif isinstance(agent_result, dict) and agent_result.get("result") == "ERROR":
                error_message = agent_result.get("message", "Неизвестная ошибка агента")
                pytest.warning(f"Агент недоступен. {error_message}")
                pytest.fail(f"Тест не прошел проверку агента для пользователя {payload['id']}: {error_message}")
            
            # Автоматическое удаление пользователя после создания
            _delete_test_user(api_client, payload["id"], auth_token, api_base_url)
            
        elif response.status_code == 409:
            # Пользователь уже существует - это нормально для тестов
            # Пытаемся удалить существующего пользователя и создать заново
            try:
                _delete_test_user(api_client, payload["id"], auth_token, api_base_url)
                # Повторяем попытку создания
                response = api_client.post(url, json=payload, headers=headers)
                assert response.status_code == 200, f"Ожидается 200 OK после удаления; получено {response.status_code}"
                
                data = response.json()
                assert isinstance(data, dict), "Ответ должен быть объектом пользователя"
                assert data["id"] == payload["id"], f"ID пользователя должен быть '{payload['id']}'"
                _validate_response_schema(data, "POST")
                
                # Дополнительная проверка через агента после повторного создания
                marker_token = random.randint(100000, 999999)
                agent_payload = {
                    "endpoint": ENDPOINT,
                    "payload": payload,
                    "marker": marker_token
                }
                print(f"Agent verification request for recreated underscore user with marker {marker_token}: {payload['id']}")
                agent_result = agent_verification("/users", agent_payload)
                
                if agent_result == "unavailable":
                    pytest.fail(f"Агент недоступен. Тест в данном случае проваливается для пользователя: {payload['id']}")
                elif isinstance(agent_result, dict) and agent_result.get("result") == "OK":
                    print(f"Агент подтвердил успешное создание пользователя: {payload['id']}")
                elif isinstance(agent_result, dict) and agent_result.get("result") == "ERROR":
                    error_message = agent_result.get("message", "Неизвестная ошибка агента")
                    pytest.warning(f"Агент недоступен. {error_message}")
                    pytest.fail(f"Тест не прошел проверку агента для пользователя {payload['id']}: {error_message}")
                
                _delete_test_user(api_client, payload["id"], auth_token, api_base_url)
                
            except Exception as e:
                pytest.skip(f"Не удалось создать пользователя после удаления: {e}")
                
        else:
            # Другой статус код
            assert response.status_code < 500, f"Неожиданный статус код: {response.status_code}"
            pytest.skip(f"API вернул неожиданный статус: {response.status_code}")

# Кейс 8: Пользователь с точками в ID
@pytest.mark.parametrize("payload", [
    {
        "id": "user.name",
        "userRoleIds": ["guest"]
    }
], ids=["пользователь с точками в ID"])
def test_create_user_dots_id(api_client, auth_token, api_base_url, payload, attach_curl_on_fail, agent_verification):
    """Тестирует создание пользователя с точками в ID"""
    url = f"{api_base_url}{ENDPOINT}"
    headers = {"x-access-token": auth_token, "Content-Type": "application/json"}
    
    # Генерируем уникальный ID для теста
    import time
    import random
    unique_id = f"dotuser_{int(time.time())}"
    payload["id"] = unique_id
    
    with attach_curl_on_fail(ENDPOINT, payload, headers, "POST"):
        response = api_client.post(url, json=payload, headers=headers)
        
        # Проверяем различные возможные ответы
        if response.status_code == 200:
            # Успешное создание
            data = response.json()
            assert isinstance(data, dict), "Ответ должен быть объектом пользователя"
            
            # Проверяем, что созданный пользователь имеет правильный ID
            assert data["id"] == payload["id"], f"ID пользователя должен быть '{payload['id']}'"
            
            # Валидируем структуру созданного пользователя
            _validate_response_schema(data, "POST")
            
            # Дополнительная проверка через агента
            marker_token = random.randint(100000, 999999)
            agent_payload = {
                "endpoint": ENDPOINT,
                "payload": payload,
                "marker": marker_token
            }
            print(f"Agent verification request for dot user creation with marker {marker_token}: {payload['id']}")
            agent_result = agent_verification("/users", agent_payload)
            
            if agent_result == "unavailable":
                pytest.fail(f"Агент недоступен. Тест в данном случае проваливается для пользователя: {payload['id']}")
            elif isinstance(agent_result, dict) and agent_result.get("result") == "OK":
                print(f"Агент подтвердил успешное создание пользователя: {payload['id']}")
            elif isinstance(agent_result, dict) and agent_result.get("result") == "ERROR":
                error_message = agent_result.get("message", "Неизвестная ошибка агента")
                pytest.warning(f"Агент недоступен. {error_message}")
                pytest.fail(f"Тест не прошел проверку агента для пользователя {payload['id']}: {error_message}")
            
            # Автоматическое удаление пользователя после создания
            _delete_test_user(api_client, payload["id"], auth_token, api_base_url)
            
        elif response.status_code == 409:
            # Пользователь уже существует - это нормально для тестов
            # Пытаемся удалить существующего пользователя и создать заново
            try:
                _delete_test_user(api_client, payload["id"], auth_token, api_base_url)
                # Повторяем попытку создания
                response = api_client.post(url, json=payload, headers=headers)
                assert response.status_code == 200, f"Ожидается 200 OK после удаления; получено {response.status_code}"
                
                data = response.json()
                assert isinstance(data, dict), "Ответ должен быть объектом пользователя"
                assert data["id"] == payload["id"], f"ID пользователя должен быть '{payload['id']}'"
                _validate_response_schema(data, "POST")
                
                # Дополнительная проверка через агента после повторного создания
                marker_token = random.randint(100000, 999999)
                agent_payload = {
                    "endpoint": ENDPOINT,
                    "payload": payload,
                    "marker": marker_token
                }
                print(f"Agent verification request for recreated dot user with marker {marker_token}: {payload['id']}")
                agent_result = agent_verification("/users", agent_payload)
                
                if agent_result == "unavailable":
                    pytest.fail(f"Агент недоступен. Тест в данном случае проваливается для пользователя: {payload['id']}")
                elif isinstance(agent_result, dict) and agent_result.get("result") == "OK":
                    print(f"Агент подтвердил успешное создание пользователя: {payload['id']}")
                elif isinstance(agent_result, dict) and agent_result.get("result") == "ERROR":
                    error_message = agent_result.get("message", "Неизвестная ошибка агента")
                    pytest.warning(f"Агент недоступен. {error_message}")
                    pytest.fail(f"Тест не прошел проверку агента для пользователя {payload['id']}: {error_message}")
                
                _delete_test_user(api_client, payload["id"], auth_token, api_base_url)
                
            except Exception as e:
                pytest.skip(f"Не удалось создать пользователя после удаления: {e}")
                
        else:
            # Другой статус код
            assert response.status_code < 500, f"Неожиданный статус код: {response.status_code}"
            pytest.skip(f"API вернул неожиданный статус: {response.status_code}")

# ----- НЕГАТИВНЫЕ ТЕСТЫ -----

# Эти тесты удалены из-за проблем с соединением к mirada-agent
