"""
===================================================================================
AUTH_UTILS - Модуль аутентификации и управления сессиями
===================================================================================

Предоставляет функциональность для выполнения аутентификации пользователей
через REST API csi-server и получения токенов доступа для авторизованных запросов.

ЗАВИСИМОСТИ:
    - qa_constants.SERVICES: Конфигурация эндпоинтов микросервисов
    - requests: HTTP клиент для взаимодействия с API

ИСПОЛЬЗОВАНИЕ:
    from auth_utils import login
    token = login(username="admin", password="admin")
===================================================================================
"""

import requests
import json
from qa_constants import SERVICES


def login(username: str, password: str, agent: str = "local") -> str:
    """
    Выполняет аутентификацию через csi-server API и возвращает токен сессии.

    ПРОЦЕСС АУТЕНТИФИКАЦИИ:
    1. Извлечение конфигурации csi-server из SERVICES
    2. Формирование POST запроса к /users/login эндпоинту
    3. Валидация ответа сервера (raise_for_status)
    4. Извлечение идентификатора сессии из поля 'id'

    ПАРАМЕТРЫ:
        username: str - Идентификатор пользователя
        password: str - Пароль в открытом виде (передаётся через HTTPS)
        agent: str - Идентификатор клиентского агента (по умолчанию "local")

    ВОЗВРАЩАЕТ:
        str: Токен сессии (JWT или session ID) из поля response['id']

    ИСКЛЮЧЕНИЯ:
        requests.exceptions.HTTPError: При ошибке аутентификации (401, 403)
        requests.exceptions.RequestException: При сетевых ошибках
        KeyError: При отсутствии поля 'id' в ответе сервера

    ПРИМЕР:
        token = login("admin", "SecureP@ss123", "pytest-agent")
        headers = {"x-access-token": token}
    """
    # Получаем конфигурацию csi-server из общего конфига
    csi_config = SERVICES["csi-server"]
    host = csi_config["host"]
    port = csi_config["port"]
    base_path = csi_config["base_path"]
    
    url = f"http://{host}:{port}{base_path}/users/login"
    
    payload = {
        "username": username,
        "password": password,
        "agent": agent
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    response = requests.post(url=url, headers=headers, data=json.dumps(payload))
    response.raise_for_status()
    
    response_data = response.json()
    return response_data['id'] 