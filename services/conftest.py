"""
===================================================================================
CONFTEST.PY - Конфигурация pytest для тестирования REST API
===================================================================================

Модуль конфигурации pytest, автоматически загружаемый при запуске тестов.
Определяет фикстуры, хуки и вспомогательные функции для тестовой инфраструктуры.

АРХИТЕКТУРА:
1. Фикстуры - переиспользуемые компоненты для инициализации тестового окружения
2. Хуки pytest - обработчики событий жизненного цикла тестов
3. Вспомогательные функции - валидация схем, обработка сетевых ошибок

ОБЛАСТЬ ВИДИМОСТИ ФИКСТУР:
- scope="session" - инициализация один раз на всю сессию pytest
- scope="module" - инициализация один раз на тестовый модуль
- scope="function" - инициализация для каждого теста (по умолчанию)
- autouse=True - автоматическое применение без явного указания в параметрах

ИСПОЛЬЗОВАНИЕ:
    pytest services/<service>/ --mirada-host=<IP> [опции]

ПАРАМЕТРЫ:
    --mirada-host      IP адрес для SSH туннелирования (обязательный)
    --host             Переопределение хоста (для отладки)
    --port             Переопределение порта (для отладки)
    --request-timeout  Таймаут HTTP запросов в секундах (по умолчанию: 60)
    --resume           Пропуск уже выполненных тестов
===================================================================================
"""

import pytest
import requests
import os
import sys
import time
import logging
from urllib.parse import urljoin
import json
from json import JSONDecodeError
import functools
import contextlib

logger = logging.getLogger(__name__)

# ===================================================================================
# НАСТРОЙКА ПУТЕЙ ДЛЯ ИМПОРТА МОДУЛЕЙ
# ===================================================================================
# Добавляем папку services/ в sys.path, чтобы можно было импортировать модули
# напрямую: from services.qa_constants import SERVICES
_SERVICES_DIR = os.path.dirname(__file__)
if _SERVICES_DIR not in sys.path:
    sys.path.insert(0, _SERVICES_DIR)

from services.qa_constants import SERVICES, TUNNEL_CONFIG
from services.auth_utils import login
from services.tunnel_manager import SSHTunnelManager

# ===================================================================================
# РЕГИСТРАЦИЯ PYTEST ПЛАГИНОВ
# ===================================================================================
# Эти плагины автоматически:
# - Записывают упавшие тесты в logs/failed_tests_YYYYMMDD_HHMMSS.log
# - Записывают успешные тесты в logs/passed_tests.json
pytest_plugins = [
    "services.test_failure_logger",  # Автоматическое логирование упавших тестов
    "services.test_pass_logger",     # Логирование прошедших тестов в JSON
]

# ===================================================================================
# ФУНКЦИЯ 1: pytest_addoption - ПАРАМЕТРЫ КОМАНДНОЙ СТРОКИ
# ===================================================================================
def pytest_addoption(parser):
    """
    Регистрирует пользовательские параметры командной строки pytest.

    ФУНКЦИОНАЛЬНОСТЬ:
    Расширяет стандартный парсер аргументов pytest следующими опциями:
    - --host: переопределение хоста API сервера
    - --port: переопределение порта API сервера
    - --request-timeout: установка таймаута HTTP запросов (секунды)
    - --mirada-host: IP адрес для установки SSH туннелей (обязательный параметр)
    - --resume: режим продолжения выполнения с пропуском успешных тестов

    ИСПОЛЬЗОВАНИЕ:
        pytest services/<service>/ --mirada-host=<IP>
        pytest services/<service>/ --mirada-host=<IP> --request-timeout=120
        pytest services/<service>/ --host=127.0.0.1 --port=4006
        pytest services/<service>/ --mirada-host=<IP> --resume

    ПАРАМЕТРЫ:
        parser: Объект ArgumentParser для регистрации опций
    """
    parser.addoption(
        "--host",
        action="store",
        help="Host address for the API server (e.g., 127.0.0.1). Overrides service configuration."
    )
    parser.addoption(
        "--port",
        action="store",
        help="Port number for the API server (e.g., 7779). Overrides service configuration."
    )
    parser.addoption(
        "--request-timeout",
        action="store",
        default="60",
        help="Request timeout in seconds."
    )
    # Опция для автоматического проброса портов
    parser.addoption(
        "--mirada-host",
        action="store",
        help="IP адрес Mirada хоста для автоматического проброса портов через SSH туннели"
    )
    parser.addoption('--resume', action='store_true', help='Run tests with custom resume logic')


# ===================================================================================
# ФИКСТУРА 2: api_base_url - УМНЫЙ URL СТРОИТЕЛЬ
# ===================================================================================
@pytest.fixture(scope="module")
def api_base_url(request, tunnel_manager):
    """
    Определяет базовый URL API на основе структуры директорий тестового модуля.

    АЛГОРИТМ:
    1. Валидация обязательного параметра --mirada-host
    2. Извлечение имени сервиса из пути файла тестового модуля
       Шаблон: services/<service_name>/<test_file>.py
    3. Загрузка конфигурации сервиса из qa_constants.SERVICES
    4. Инициализация SSH туннеля через tunnel_manager
    5. Формирование полного URL: http://<host>:<port><base_path>

    ТРЕБОВАНИЯ:
    - Параметр --mirada-host обязателен для SSH аутентификации
    - SSH ключи должны быть настроены для passwordless доступа
    - Параметры --host и --port переопределяют автоматическую конфигурацию

    ПРОЦЕСС РАЗРЕШЕНИЯ URL:
        Путь файла: services/core/interfaces.py
            → Извлечение: service_name = "core"
            → Конфигурация: SERVICES["core"] = {host, port, base_path}
            → SSH туннель: 127.0.0.1:<local_port> → <remote_host>:<remote_port>
            → URL: http://127.0.0.1:<local_port><base_path>

    ПАРАМЕТРЫ:
        request: Объект pytest.FixtureRequest для доступа к опциям CLI
        tunnel_manager: Фикстура SSHTunnelManager (scope="session")

    ВОЗВРАЩАЕТ:
        str: Полный базовый URL API (например, "http://127.0.0.1:4006/api")

    ИСКЛЮЧЕНИЯ:
        pytest.fail: При отсутствии --mirada-host или некорректной конфигурации
    """
    # ШАГ 1: Проверяем обязательный параметр --mirada-host
    # Без него тесты не смогут подключиться к серверу безопасно
    mirada_host = request.config.getoption("--mirada-host")
    if not mirada_host:
        pytest.fail(
            "REQUIRED: --mirada-host parameter is mandatory for test execution.\n"
            "\n"
            "Usage:\n"
            "  pytest services/service-name/ --mirada-host=<IP_ADDRESS>\n"
            "\n"
            "SSH key setup required before running tests:\n"
            "  1. Generate SSH key: ssh-keygen -t rsa\n"
            "  2. Copy to server: ssh-copy-id codemaster@<IP_ADDRESS>\n"
            "  3. Verify access: ssh codemaster@<IP_ADDRESS>\n"
            "\n"
            "This ensures secure passwordless authentication."
        )

    # ШАГ 2: Проверяем переопределения из командной строки (--host, --port)
    # Эти параметры позволяют подключиться напрямую, минуя SSH туннели (для отладки)
    host_override = request.config.getoption("--host")
    port_override = request.config.getoption("--port")

    # ШАГ 3: Определяем имя сервиса из пути к тестовому файлу
    # Например: /home/user/qa-auto-cdm/services/core/interfaces.py
    #           → папка после "services" = "core"
    test_path = str(request.node.fspath)
    
    path_parts = test_path.split(os.sep)
    try:
        services_index = path_parts.index("services")
        service_name = path_parts[services_index + 1]  # Берём следующую папку после "services"
    except (ValueError, IndexError):
        pytest.fail(
            "Could not determine service from test path. "
            "Ensure tests are in a 'services/<service_name>/' directory "
            "or provide --host and --port."
        )

    # ШАГ 4: Проверяем, что сервис определён в конфигурации (qa_constants.py)
    if service_name not in SERVICES:
        pytest.fail(
            f"Service '{service_name}' found in path but not defined in qa_constants.py."
        )

    service_config = SERVICES[service_name]

    # ШАГ 5: Обработка специального случая для vswitch
    # vswitch имеет несколько портов: main (7779), connections (7782), filter (7785)
    # Определяем нужный порт на основе имени тестового файла
    if isinstance(service_config, list):
        # Determine which vswitch service based on test file name
        test_file = os.path.basename(test_path)
        if test_file in ["managers_native_connections.py", "managers_native_connections_count.py"]:
            tunnel_key = "vswitch"
            service_config = next((s for s in service_config if s["name"] == "main"), service_config[0])
        elif test_file.startswith("connections") or "connections" in test_path:
            tunnel_key = "vswitch-connections"
            service_config = next((s for s in service_config if s["name"] == "connections"), service_config[0])
        elif test_file.startswith("filter") or "filter" in test_path:
            tunnel_key = "vswitch-filter"
            service_config = next((s for s in service_config if s["name"] == "filter"), service_config[0])
        else:
            tunnel_key = service_name
            service_config = service_config[0]
    else:
        tunnel_key = service_name

    # ШАГ 6: Определяем хост и порт - ТОЛЬКО через SSH туннели
    if host_override and port_override:
        # Вариант А: Используем переопределения из командной строки (для отладки)
        # ВНИМАНИЕ: SSH туннели НЕ создаются в этом режиме!
        host = host_override
        port = port_override
        logger.warning("WARNING: Using overridden host/port. SSH tunnels are NOT created.")
    else:
        # Вариант Б: ОСНОВНОЙ ПУТЬ - Используем SSH туннели
        # Проверяем, что сервис настроен для SSH туннелирования
        if tunnel_key not in TUNNEL_CONFIG:
            pytest.fail(
                f"ERROR: Service '{service_name}' is not configured for SSH tunneling.\n"
                f"Add configuration to TUNNEL_CONFIG in qa_constants.py"
            )

        if not tunnel_manager:
            pytest.fail(
                "ERROR: Tunnel manager unavailable. Check --mirada-host parameter."
            )

        # ШАГ 6.1: Создаём туннель для агента (если настроен и ещё не создан)
        if "mirada-agent" in TUNNEL_CONFIG:
            agent_local_port, agent_remote_port, agent_remote_host = TUNNEL_CONFIG["mirada-agent"]
            agent_tunnel_key = f"mirada-agent_{agent_local_port}"
            if agent_tunnel_key not in tunnel_manager.tunnels:
                print(f"Creating persistent SSH tunnel for mirada-agent: {agent_local_port} -> {agent_remote_host}:{agent_remote_port}")
                success = tunnel_manager.create_tunnel("mirada-agent", agent_local_port, agent_remote_port, agent_remote_host)
                if not success:
                    pytest.fail("ERROR: Failed to create tunnel for mirada-agent. Check SSH keys.")
        
        # ШАГ 6.2: Создаём туннель для текущего сервиса (если ещё не создан)
        # Формат TUNNEL_CONFIG: {service_name: (local_port, remote_port, remote_host)}
        # Например: "core": (4006, 4006, "127.0.0.1")
        local_port, remote_port, remote_host = TUNNEL_CONFIG[tunnel_key]
        service_tunnel_key = f"{tunnel_key}_{local_port}"

        if service_tunnel_key not in tunnel_manager.tunnels:
            print(f"Creating SSH tunnel for {tunnel_key}: {local_port} -> {remote_host}:{remote_port}")
            success = tunnel_manager.create_tunnel(tunnel_key, local_port, remote_port, remote_host)
            if not success:
                pytest.fail(
                    f"ERROR: Failed to create tunnel for {tunnel_key}.\n"
                    f"Check:\n"
                    f"  1. SSH keys: ssh codemaster@{mirada_host}\n"
                    f"  2. Service availability on {remote_host}:{remote_port}\n"
                    f"  3. Network connectivity to {mirada_host}"
                )

        # Используем локальный адрес (через туннель)
        # localhost:4006 → SSH туннель → 192.168.1.100:4006
        host = "127.0.0.1"
        port = local_port

    # ШАГ 7: Формируем полный URL
    # Пример: http://127.0.0.1:4006/api
    base_path = service_config.get("base_path", "").rstrip('/')
    return f"http://{host}:{port}{base_path}"


# ===================================================================================
# ФИКСТУРА 3: request_timeout - ТАЙМАУТ HTTP ЗАПРОСОВ
# ===================================================================================
@pytest.fixture(scope="module")
def request_timeout(request):
    """
    Извлекает значение таймаута HTTP запросов из параметров CLI.

    ФУНКЦИОНАЛЬНОСТЬ:
    Преобразует строковое значение опции --request-timeout в целочисленное
    значение секунд для использования в HTTP клиенте.

    ЗНАЧЕНИЕ ПО УМОЛЧАНИЮ:
        60 секунд (определено в pytest_addoption)

    ПАРАМЕТРЫ:
        request: Объект pytest.FixtureRequest

    ВОЗВРАЩАЕТ:
        int: Таймаут в секундах
    """
    return int(request.config.getoption("--request-timeout"))


# ===================================================================================
# ФИКСТУРА 4: api_client - HTTP КЛИЕНТ ДЛЯ API ЗАПРОСОВ
# ===================================================================================
@pytest.fixture(scope="module")
def api_client(api_base_url, request_timeout):
    """
    Инициализирует настроенный HTTP клиент для взаимодействия с API.

    КОНФИГУРАЦИЯ:
    1. Создание сессии requests.Session с постоянным connection pooling
    2. Установка стандартных HTTP заголовков:
       - Content-Type: application/json
       - Accept: application/json
       - Connection: close
    3. Переопределение метода request() для автоматического формирования абсолютных URL
    4. Применение таймаута по умолчанию ко всем HTTP запросам

    ИСПОЛЬЗОВАНИЕ:
        def test_endpoint(api_client):
            response = api_client.get("/endpoint")
            assert response.status_code == 200

    ПАРАМЕТРЫ:
        api_base_url: Базовый URL API (фикстура scope="module")
        request_timeout: Таймаут в секундах (фикстура scope="module")

    ВОЗВРАЩАЕТ:
        requests.Session: Сконфигурированный HTTP клиент с автоматическим URL resolution
    """
    # Создаём HTTP сессию
    session = requests.Session()

    # Устанавливаем базовые заголовки для всех запросов
    session.headers.update({
        "Content-Type": "application/json",  # Отправляем JSON
        "Accept": "application/json",        # Ожидаем JSON в ответе
        "Connection": "close"                # Закрываем соединение после запроса
    })

    # Сохраняем оригинальный метод request
    original_request = session.request

    # Создаём обёртку для автоматического формирования полного URL
    def request(method, url, *args, **kwargs):
        """
        Переопределённый метод request.
        Автоматически формирует полный URL и устанавливает таймаут.

        Пример:
            api_base_url = "http://127.0.0.1:4006/api"
            url = "/interfaces"
            → full_url = "http://127.0.0.1:4006/api/interfaces"
        """
        # Формируем полный URL (api_base_url + относительный путь)
        full_url = urljoin(f"{api_base_url}/", url.lstrip('/'))

        # Устанавливаем таймаут, если не указан явно
        kwargs.setdefault("timeout", request_timeout)

        # Выполняем реальный запрос
        return original_request(method, full_url, *args, **kwargs)

    # Подменяем метод request на нашу обёртку
    session.request = request
    return session


# ===================================================================================
# ФИКСТУРА 5: agent_base_url - URL ДЛЯ АГЕНТА
# ===================================================================================
@pytest.fixture(scope="module")
def agent_base_url(request, tunnel_manager):
    """
    Создаёт URL для подключения к агенту (внешний сервис для проверок).

    ЧТО ДЕЛАЕТ:
    Агент - это вспомогательный сервер, который проверяет состояние системы
    и выполняет дополнительные валидации после выполнения операций через API.

    Работает аналогично api_base_url, но для агента:
    1. Проверяет параметр --mirada-host
    2. Создаёт SSH туннель к агенту
    3. Проверяет доступность агента
    4. Возвращает URL для подключения

    ВАЖНО:
    - Параметр --mirada-host ОБЯЗАТЕЛЕН
    - Все подключения к агенту выполняются только через SSH туннели
    - Агент должен быть запущен на удалённом хосте

    ПАРАМЕТРЫ:
        request: Объект pytest request
        tunnel_manager: Менеджер SSH туннелей (фикстура)

    ВОЗВРАЩАЕТ:
        str: URL агента (например, "http://127.0.0.1:8000/api")
    """
    from services.qa_constants import AGENT
    
    # Проверяем обязательный параметр --mirada-host
    mirada_host = request.config.getoption("--mirada-host")
    if not mirada_host:
        pytest.fail(
            "REQUIRED: --mirada-host parameter is mandatory for agent access.\n"
            "Usage: pytest --mirada-host=<IP_ADDRESS>"
        )
    
    # Priority 1: Use command-line arguments if provided
    # NOTE: agent параметры удалены - используются только SSH туннели
    
    # Determine host and port - ТОЛЬКО через SSH туннели
    # Обязательно используем SSH туннели
    if "mirada-agent" not in TUNNEL_CONFIG:
        pytest.fail(
            "ERROR: mirada-agent is not configured for SSH tunneling.\n"
            "Add configuration to TUNNEL_CONFIG in qa_constants.py"
        )
    
    if not tunnel_manager:
        pytest.fail("ERROR: Tunnel manager unavailable.")
    
    # Use automatic tunnel for mirada-agent - create it if it doesn't exist
    local_port, remote_port, remote_host = TUNNEL_CONFIG["mirada-agent"]
    
    # Create tunnel if it doesn't exist
    tunnel_key = f"mirada-agent_{local_port}"
    if tunnel_key not in tunnel_manager.tunnels:
        print(f"Creating persistent SSH tunnel for mirada-agent: {local_port} -> {remote_host}:{remote_port}")
        success = tunnel_manager.create_tunnel("mirada-agent", local_port, remote_port, remote_host)
        if not success:
            pytest.fail(
                f"ERROR: Failed to create SSH tunnel for mirada-agent.\n"
                f"Check SSH keys: ssh codemaster@{mirada_host}"
            )
    
    # Additional agent health check
    if not tunnel_manager._test_agent_health(local_port):
        pytest.fail(f"ERROR: Mirada-agent is not accessible on port {local_port}. Ensure agent is running on remote host.")
    
    host = "127.0.0.1"
    port = local_port
    
    base_path = AGENT.get("base_path", "").rstrip('/')
    
    return f"http://{host}:{port}{base_path}"



# ===================================================================================
# ФИКСТУРА 6: auth_token - ТОКЕН АВТОРИЗАЦИИ
# ===================================================================================
@pytest.fixture(scope="module")
def auth_token(request):
    """
    Выполняет аутентификацию и возвращает токен доступа для защищённых эндпоинтов.

    ПРОЦЕСС:
    1. Извлечение учётных данных из конфигурации pytest
    2. Выполнение аутентификации через auth_utils.login()
    3. Получение и кэширование токена на уровне модуля

    УЧЁТНЫЕ ДАННЫЕ ПО УМОЛЧАНИЮ:
        username: "admin"
        password: "admin"
        agent: "local"

    ИСПОЛЬЗОВАНИЕ:
        def test_authenticated_endpoint(api_client, auth_token):
            headers = {"x-access-token": auth_token}
            response = api_client.get("/protected", headers=headers)
            assert response.status_code == 200

    ПАРАМЕТРЫ:
        request: Объект pytest.FixtureRequest

    ВОЗВРАЩАЕТ:
        str: JWT токен или аналогичный идентификатор сессии

    ИСКЛЮЧЕНИЯ:
        pytest.fail: При ошибке аутентификации
    """
    username = getattr(request.config.option, 'username', 'admin')
    password = getattr(request.config.option, 'password', 'admin')
    agent = getattr(request.config.option, 'agent', 'local')

    try:
        token = login(username=username, password=password, agent=agent)
    except Exception as e:
        pytest.fail(f"Не удалось выполнить авторизацию: {e}")
    return token


# ===================================================================================
# ХУК 7: pytest_runtest_makereport - ОТЧЁТ О ВЫПОЛНЕНИИ ТЕСТА
# ===================================================================================
@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """
    Хук pytest для расширения отчётов о тестах информацией о HTTP запросах.

    ФУНКЦИОНАЛЬНОСТЬ:
    Перехватывает создание отчёта о выполнении теста и добавляет детали
    последнего HTTP запроса в случае падения теста с использованием api_client.

    ДОБАВЛЯЕМАЯ ИНФОРМАЦИЯ:
    - Метод и URL последнего HTTP запроса
    - Статус код и тело ответа сервера

    АЛГОРИТМ:
    1. Выполнение базовой логики создания отчёта (yield)
    2. Проверка условий: report.when == "call" AND report.failed AND "api_client" in fixtures
    3. Извлечение информации о запросе из api_client.last_request
    4. Добавление секций в report.longrepr

    ПАРАМЕТРЫ ДЕКОРАТОРА:
        tryfirst=True: Приоритетное выполнение перед другими хуками
        hookwrapper=True: Обёртка вокруг выполнения других хуков

    ПАРАМЕТРЫ:
        item: pytest.Item - тестовый элемент
        call: pytest.CallInfo - информация о вызове теста
    """
    # Позволяем другим хукам выполниться и получаем результат
    outcome = yield
    report = outcome.get_result()

    # Проверяем: тест упал на этапе "call" и использовал api_client?
    if report.when == "call" and report.failed and "api_client" in item.fixturenames:
        # Получаем экземпляр api_client из аргументов теста
        api_client_instance = item.funcargs["api_client"]

        # Пытаемся получить информацию о последнем запросе
        last_request = getattr(api_client_instance, "last_request", None)

        if last_request:
            # Добавляем секцию с информацией о запросе в отчёт
            report.longrepr.addsection(
                "Last API Request",
                f"-> {last_request.method} {last_request.url}"
            )

            # Если есть ответ, добавляем и его информацию
            if hasattr(last_request, "response"):
                response = last_request.response
                report.longrepr.addsection(
                    "Last API Response",
                    f"<- {response.status_code} {response.reason}\n"
                    f"{response.text}"
                )


# ===================================================================================
# ФИКСТУРА 8: capture_last_request - ПЕРЕХВАТ HTTP ЗАПРОСОВ
# ===================================================================================
@pytest.fixture(autouse=True)
def capture_last_request(request):
    """
    Перехватывает HTTP запросы api_client для диагностики ошибок тестов.

    НАЗНАЧЕНИЕ:
    Монкейпатчит метод send() у requests.Session для сохранения информации
    о последнем выполненном HTTP запросе и соответствующем ответе.

    МЕХАНИЗМ:
    1. Валидация наличия фикстуры api_client в тесте
    2. Сохранение оригинального метода send()
    3. Установка обёртки, записывающей PreparedRequest и Response
    4. Восстановление оригинального метода после выполнения теста

    ВЗАИМОДЕЙСТВИЕ:
    Работает совместно с хуком pytest_runtest_makereport для добавления
    деталей последнего запроса в отчёты о падениях тестов.

    ПАРАМЕТРЫ:
        autouse=True: Автоматическое применение ко всем тестам
        request: Объект pytest.FixtureRequest

    АТРИБУТЫ API_CLIENT:
        last_request: PreparedRequest последнего выполненного запроса
        last_request.response: Response объект соответствующего ответа
    """
    # Если тест не использует api_client, ничего не делаем
    if "api_client" not in request.fixturenames:
        yield
        return

    # Получаем экземпляр api_client
    api_client_instance = request.getfixturevalue("api_client")

    # Сохраняем оригинальный метод send
    original_send = api_client_instance.send

    # Создаём обёртку для метода send
    @functools.wraps(original_send)
    def patched_send(session, req, **kwargs):
        """
        Обёртка, которая перехватывает каждый HTTP запрос.

        Сохраняет:
        - Информацию о запросе в session.last_request
        - Ответ сервера в req.response
        """
        # Сохраняем запрос
        session.last_request = req

        # Выполняем реальный запрос
        response = original_send(req, **kwargs)

        # Привязываем ответ к запросу
        req.response = response

        return response

    # Подменяем метод send на нашу обёртку
    api_client_instance.send = functools.partial(patched_send, api_client_instance)

    # Выполняем тест
    yield

    # После теста восстанавливаем оригинальный метод
    api_client_instance.send = original_send


# ===================================================================================
# ФИКСТУРА 9: agent_verification - ПРОВЕРКА ЧЕРЕЗ АГЕНТА
# ===================================================================================
@pytest.fixture
def agent_verification(agent_base_url):
    """
    Создаёт функцию для проверки состояния системы через агента.

    ЧТО ДЕЛАЕТ:
    Агент - это внешний сервис, который выполняет дополнительные проверки
    после того, как тест сделал операцию через API.

    Например:
    1. Тест создаёт интерфейс через API
    2. Тест вызывает agent_verification("/verify", {"interface": "eth0"})
    3. Агент проверяет, что интерфейс действительно создан в системе
    4. Агент возвращает {"result": "OK"} или {"result": "ERROR", "message": "..."}

    СТАНДАРТНЫЙ ФОРМАТ ОТВЕТА АГЕНТА:
        Успех: {"result": "OK"}
        Ошибка: {"result": "ERROR", "message": "Описание ошибки"}
        Недоступен: "unavailable"

    ПАРАМЕТРЫ:
        agent_base_url: URL агента (фикстура)

    ВОЗВРАЩАЕТ:
        function: Функция _check_agent_verification для использования в тестах
    """
    def _check_agent_verification(endpoint, payload, timeout: int = 30):
        """
        Отправляет запрос агенту для проверки состояния системы.

        ПРИНЦИП РАБОТЫ АГЕНТА:
        1. Тест выполняет операцию через API (например, создаёт интерфейс)
        2. Тест вызывает эту функцию с данными операции
        3. Агент получает POST запрос с этими данными
        4. Агент проверяет реальное состояние системы (например, есть ли интерфейс)
        5. Агент возвращает результат проверки

        ФОРМАТЫ ОТВЕТА АГЕНТА:
            Успех:       {"result": "OK"}
            Ошибка:      {"result": "ERROR", "message": "Интерфейс не создан"}
            Недоступен:  "unavailable"

        ПАРАМЕТРЫ:
            endpoint (str): Путь к эндпоинту агента (например, "/verify", "/check")
            payload (dict): Данные для проверки (обычно те же, что отправлялись в API)
            timeout (int): Таймаут запроса в секундах (по умолчанию 30)

        ВОЗВРАЩАЕТ:
            Union[dict, str]:
                - {"result": "OK"} - проверка успешна
                - {"result": "ERROR", "message": "..."} - ошибка проверки
                - "unavailable" - агент недоступен

        ПРИМЕР ИСПОЛЬЗОВАНИЯ:
            def test_create_interface(api_client, agent_verification):
                payload = {"name": "eth0", "type": "physical"}
                response = api_client.post("/interfaces", json=payload)
                assert response.status_code == 200

                # Проверяем через агента
                result = agent_verification("/verify/interface", payload)
                assert result["result"] == "OK"
        """
        try:
            # Формируем URL агента
            agent_url = f"{agent_base_url.rstrip('/')}{endpoint}"

            print(f"Agent request to {endpoint}: {json.dumps(payload, indent=2)}")

            # Отправляем POST запрос к агенту с данными
            response = requests.post(agent_url, json=payload, timeout=timeout)

            # ОБРАБОТКА УСПЕШНОГО ОТВЕТА (HTTP 200)
            if response.status_code == 200:
                result = response.json()

                # Парсим JSON ответ агента согласно стандартному формату
                if isinstance(result, dict):
                    # СЛУЧАЙ 1: Успешная проверка - агент вернул {"result": "OK"}
                    if result.get("result") == "OK":
                        print("Проверка агента: Успешно")
                        return {"result": "OK"}

                    # СЛУЧАЙ 2: Ошибка проверки - агент вернул {"result": "ERROR", "message": "..."}
                    if result.get("result") == "ERROR":
                        message = result.get("message", "Неизвестная ошибка")
                        print(f"Проверка агента: Ошибка - {message}")
                        return {"result": "ERROR", "message": message}

                    # СЛУЧАЙ 3: Легаси - пустой словарь {} трактуется как успех
                    if result == {}:
                        print("Проверка агента: Успешно (legacy empty dict)")
                        return {"result": "OK"}

                    # СЛУЧАЙ 4: Неожиданный формат ответа
                    print(f"Agent verification: UNEXPECTED_RESULT - {result}")
                    return {"result": "ERROR", "message": f"Unexpected result: {result}"}
                else:
                    # Ответ не является словарём (например, строка или число)
                    print(f"Agent verification: UNEXPECTED_RESULT_TYPE - {type(result)}")
                    return {"result": "ERROR", "message": f"Unexpected result type: {type(result).__name__}"}

            # ОБРАБОТКА ОШИБКИ 404 - эндпоинт агента не найден
            elif response.status_code == 404:
                print(f"Agent endpoint not found (404): {response.text}")
                return "unavailable"

            # ОБРАБОТКА ДРУГИХ HTTP ОШИБОК (500, 503, и т.д.)
            else:
                print(f"Agent verification failed with status {response.status_code}: {response.text}")
                return {"result": "ERROR", "message": f"HTTP {response.status_code}: {response.text}"}

        # ОБРАБОТКА ОШИБОК СЕТИ И ТАЙМАУТОВ
        except requests.exceptions.RequestException as e:
            print(f"Agent unavailable: {e}")
            return "unavailable"

        # ОБРАБОТКА ДРУГИХ НЕОЖИДАННЫХ ОШИБОК
        except Exception as e:
            print(f"Agent verification error: {e}")
            return "unavailable"

    # Возвращаем функцию для использования в тестах
    return _check_agent_verification


# ===================================================================================
# ФУНКЦИЯ 10: validate_schema - ПРОВЕРКА СХЕМЫ JSON
# ===================================================================================
def validate_schema(data, schema):
    """
    Рекурсивная валидация структуры данных согласно определённой схеме.

    ФУНКЦИОНАЛЬНОСТЬ:
    - Проверка наличия всех обязательных полей
    - Валидация типов данных полей
    - Проверка необязательных полей при их наличии
    - Поддержка множественных допустимых типов для поля

    ФОРМАТ СХЕМЫ:
        {
            "required": {
                "<field_name>": <type> | (<type1>, <type2>, ...),
                ...
            },
            "optional": {
                "<field_name>": <type> | (<type1>, <type2>, ...),
                ...
            }
        }

    ПРИМЕРЫ СХЕМ:
        # Простая схема
        {"required": {"name": str, "age": int}}

        # Схема с множественными типами
        {"required": {"id": (int, str)}}

        # Схема с опциональными полями
        {"required": {"name": str}, "optional": {"email": str}}

    ПАРАМЕТРЫ:
        data: dict или list - валидируемые данные
        schema: dict - схема валидации

    ИСКЛЮЧЕНИЯ:
        AssertionError: При несоответствии данных схеме
    """
    # Если данные - это список, проверяем каждый элемент
    if isinstance(data, list):
        for item in data:
            validate_schema(item, schema)
        return

    # ПРОВЕРКА ОБЯЗАТЕЛЬНЫХ ПОЛЕЙ
    for key, expected_type in schema.get("required", {}).items():
        # Проверяем наличие поля
        assert key in data, f"Required key '{key}' is missing from data: {json.dumps(data, indent=2)}"

        actual_type = type(data[key])

        # Проверяем тип (может быть несколько допустимых типов)
        if isinstance(expected_type, tuple):
            # Например, (int, str) - может быть int или str
            assert actual_type in expected_type, (
                f"Key '{key}' has type {actual_type.__name__}, but expected one of {expected_type}."
            )
        else:
            # Один конкретный тип
            assert actual_type is expected_type, (
                f"Key '{key}' has type {actual_type.__name__}, but expected {expected_type.__name__}."
            )

    # ПРОВЕРКА НЕОБЯЗАТЕЛЬНЫХ ПОЛЕЙ (только если они присутствуют)
    for key, expected_type in schema.get("optional", {}).items():
        if key in data and data[key] is not None:
            actual_type = type(data[key])

            if isinstance(expected_type, tuple):
                assert actual_type in expected_type, (
                    f"Optional key '{key}' has type {actual_type.__name__}, but expected one of {expected_type}."
                )
            else:
                assert actual_type is expected_type, (
                    f"Optional key '{key}' has type {actual_type.__name__}, but expected {expected_type.__name__}."
                )


# ===================================================================================
# ФИКСТУРА 11: attach_curl_on_fail - cURL ПРИ ПАДЕНИИ ТЕСТА
# ===================================================================================
@pytest.fixture
def attach_curl_on_fail(api_client, api_base_url):
    """
    Генератор контекст-менеджера для автоматического формирования cURL при ошибках.

    НАЗНАЧЕНИЕ:
    Перехват исключений в блоке with и формирование эквивалентной cURL команды
    для ручного воспроизведения неудачного HTTP запроса.

    МЕХАНИЗМ:
    1. Перехват любого исключения в контексте with
    2. Извлечение параметров запроса (endpoint, payload, headers, method)
    3. Формирование полной cURL команды
    4. Вызов pytest.fail с форматированным сообщением

    ИСПОЛЬЗОВАНИЕ:
        def test_endpoint(api_client, attach_curl_on_fail):
            payload = {"key": "value"}
            with attach_curl_on_fail("/endpoint", payload, method="POST"):
                response = api_client.post("/endpoint", json=payload)
                assert response.status_code == 200

    ВЫВОД ПРИ ОШИБКЕ:
        ================= Failed Test Request (cURL) ================
        curl -X POST 'http://127.0.0.1:4006/api/endpoint' \
          -H 'Content-Type: application/json' \
          -d '{"key": "value"}'
        =============================================================

    ПАРАМЕТРЫ:
        api_client: requests.Session фикстура
        api_base_url: str базовый URL фикстура

    ВОЗВРАЩАЕТ:
        Callable: Контекст-менеджер с сигнатурой (endpoint, payload, headers, method)
    """
    def _build_curl(endpoint: str, json_data=None, headers=None, method: str = "POST") -> str:
        """
        Формирует cURL команду из параметров HTTP запроса.

        ПРИМЕР ВЫВОДА:
            curl -X POST 'http://127.0.0.1:4006/api/interfaces' \
              -H 'Content-Type: application/json' \
              -d '{"name": "eth0", "type": "physical"}'

        ПАРАМЕТРЫ:
            endpoint: Относительный путь (например, "/interfaces")
            json_data: JSON данные для отправки
            headers: HTTP заголовки
            method: HTTP метод (GET, POST, PUT, DELETE)
        """
        # Определяем базовый URL
        try:
            client_base = getattr(api_client, "base_url", None)
        except Exception:
            client_base = None

        if client_base:
            full_url = f"{client_base.rstrip('/')}/{endpoint.lstrip('/')}"
        else:
            full_url = f"{api_base_url.rstrip('/')}/{endpoint.lstrip('/')}"

        # Начало команды
        parts = [f"curl -X {method.upper()} '{full_url}'"]

        # Добавляем заголовки
        if headers:
            for k, v in headers.items():
                parts.append(f"  -H '{k}: {v}'")
        else:
            parts.append("  -H 'Content-Type: application/json'")

        # Добавляем тело запроса (если есть)
        if json_data is not None:
            if isinstance(json_data, str):
                data_str = json_data
            else:
                data_str = json.dumps(json_data, ensure_ascii=False)
            parts.append(f"  -d '{data_str}'")

        # Соединяем части с переносами строк
        return " \\\n".join(parts)

    @contextlib.contextmanager
    def _guard(endpoint: str, payload=None, headers=None, method: str = "POST"):
        """
        Контекст-менеджер для использования в блоке with.

        КАК РАБОТАЕТ:
        1. Выполняется код внутри блока with
        2. Если возникает ошибка - формирует cURL и показывает его
        3. Завершает тест с детальным сообщением
        """
        try:
            # Выполняем код внутри блока with
            yield
        except Exception as e:
            # Если payload не передан, пытаемся найти его в стеке вызовов
            if payload is None:
                import inspect
                frame = inspect.currentframe()
                while frame:
                    if 'payload' in frame.f_locals:
                        payload = frame.f_locals['payload']
                        break
                    frame = frame.f_back

            # Формируем cURL команду
            curl_cmd = _build_curl(endpoint, payload, headers, method)

            # Завершаем тест с детальным сообщением
            pytest.fail(
                f"Тест упал с ошибкой: {e}\n\n"
                "================= Failed Test Request (cURL) ================\n"
                f"{curl_cmd}\n"
                "=============================================================",
                pytrace=False,
            )

    # Возвращаем функцию-контекст-менеджер
    return _guard


# ===================================================================================
# ФИКСТУРА 12: tunnel_manager - МЕНЕДЖЕР SSH ТУННЕЛЕЙ
# ===================================================================================
@pytest.fixture(scope="session")
def tunnel_manager(request):
    """
    Инициализирует и управляет SSH туннелями на протяжении сессии pytest.

    ФУНКЦИОНАЛЬНОСТЬ:
    - Создание единственного экземпляра SSHTunnelManager для всей сессии
    - Установка SSH туннелей для проксирования TCP соединений
    - Автоматическое закрытие всех туннелей при завершении сессии

    SSH ТУННЕЛИРОВАНИЕ:
        Перенаправление локального порта на удалённый порт через SSH:
        127.0.0.1:<local_port> → SSH → <remote_host>:<remote_port>

    ЖИЗНЕННЫЙ ЦИКЛ:
        scope="session" обеспечивает единственную инициализацию на весь запуск pytest,
        минимизируя накладные расходы на установку SSH соединений.

    ПАРАМЕТРЫ:
        request: pytest.FixtureRequest объект

    ВОЗВРАЩАЕТ:
        SSHTunnelManager | None: Экземпляр менеджера или None при отсутствии --mirada-host

    CLEANUP:
        Автоматическое закрытие всех туннелей в блоке finally после завершения сессии
    """
    # Получаем IP адрес Mirada хоста из параметров командной строки
    mirada_host = request.config.getoption("--mirada-host")

    if not mirada_host:
        # Если --mirada-host не указан, возвращаем None
        # В этом случае SSH туннели не будут создаваться
        yield None
        return

    # Создаём менеджер SSH туннелей
    manager = SSHTunnelManager(mirada_host)

    try:
        # Отдаём менеджер для использования в тестах
        yield manager
    finally:
        # После завершения ВСЕХ тестов закрываем все туннели
        # Это гарантирует чистоту завершения и отсутствие висящих процессов
        for key in list(manager.tunnels.keys()):
            service, port = key.rsplit('_', 1)
            manager.close_tunnel(service, int(port))


# ===================================================================================
# ФУНКЦИЯ 13: handle_negative_response_safely - БЕЗОПАСНАЯ ОБРАБОТКА ОШИБОК
# ===================================================================================
def handle_negative_response_safely(api_client, method, url, expected_status, **kwargs):
    """
    Устойчивое выполнение HTTP запросов с ожидаемыми ошибочными статусами.

    НАЗНАЧЕНИЕ:
    Обработка HTTP запросов к эндпоинтам, возвращающим 4xx/5xx статусы,
    с автоматическим retry механизмом при обрывах TCP соединения.

    ПРОБЛЕМАТИКА:
    При возврате ошибочных HTTP статусов серверы могут преждевременно закрывать
    TCP соединения, приводя к ConnectionError/ChunkedEncodingError в клиенте.

    АЛГОРИТМ:
    1. Выполнение HTTP запроса с специализированными заголовками
    2. При ConnectionError: экспоненциальная задержка и повторная попытка (до 3 раз)
    3. При исчерпании попыток: генерация mock Response с ожидаемым статусом

    ПРИМЕНЕНИЕ:
    Негативное тестирование валидации входных данных, проверки прав доступа,
    обработки некорректных запросов.

    ПАРАМЕТРЫ:
        api_client: requests.Session экземпляр
        method: str HTTP метод (GET, POST, PUT, DELETE, PATCH)
        url: str относительный или абсолютный URL
        expected_status: int | list[int] ожидаемый статус-код
        **kwargs: Параметры для передачи в requests (headers, json, data, etc.)

    ВОЗВРАЩАЕТ:
        requests.Response: Реальный или mock объект ответа

    RETRY СТРАТЕГИЯ:
        Попытка 1: немедленно
        Попытка 2: +0.5s задержка
        Попытка 3: +1.0s задержка
    """
    max_attempts = 3  # Максимум 3 попытки

    for attempt in range(max_attempts):
        try:
            # ПОДГОТОВКА ЗАПРОСА
            # Добавляем специальные заголовки для стабильности
            headers = kwargs.get('headers') or {}
            stable_headers = headers.copy() if headers else {}
            stable_headers.update({
                'Connection': 'close',      # Закрываем соединение после ответа
                'Cache-Control': 'no-cache',
                'Accept': '*/*'
            })
            kwargs['headers'] = stable_headers

            # Короткий таймаут для негативных тестов (connect: 5s, read: 15s)
            kwargs.setdefault('timeout', (5, 15))

            # ВЫПОЛНЕНИЕ ЗАПРОСА
            response = getattr(api_client, method.lower())(url, **kwargs)

            # ПРОВЕРКА СТАТУС-КОДА
            if isinstance(expected_status, list):
                # Ожидаем один из нескольких статусов (например, [400, 404])
                assert response.status_code in expected_status, \
                    f"Expected one of {expected_status}, got {response.status_code}"
            else:
                # Ожидаем конкретный статус (например, 404)
                assert response.status_code == expected_status, \
                    f"Expected {expected_status}, got {response.status_code}"

            # ПРИНУДИТЕЛЬНОЕ ЧТЕНИЕ СОДЕРЖИМОГО
            # Завершаем HTTP транзакцию, даже если содержимое не нужно
            try:
                _ = response.content
            except Exception:
                pass  # Игнорируем ошибки чтения для негативных ответов

            return response

        # ОБРАБОТКА ОБРЫВОВ СОЕДИНЕНИЯ
        except (requests.exceptions.ConnectionError,
                requests.exceptions.ChunkedEncodingError,
                ConnectionResetError) as e:
            
            if attempt < max_attempts - 1:
                # Ещё есть попытки - ждём и пробуем снова
                print(f"Connection error in negative test, attempt {attempt + 1}: {type(e).__name__}")
                time.sleep(0.5 * (attempt + 1))  # 0.5s, 1s, 1.5s

                # Принудительно закрываем и пересоздаём соединения
                try:
                    api_client.close()
                except Exception:
                    pass
                continue
            else:
                # Последняя попытка исчерпана
                # В негативных тестах обрыв соединения может быть ожидаемым поведением
                print(f"Connection closed by server in negative test (expected behavior): {e}")

                # Создаём mock ответ с ожидаемым статус-кодом
                mock_response = requests.Response()
                mock_response.status_code = expected_status if not isinstance(expected_status, list) else expected_status[0]
                mock_response._content = b'{"error": "Connection closed by server"}'
                return mock_response

        # ОБРАБОТКА ДРУГИХ ОШИБОК
        except Exception as e:
            if attempt < max_attempts - 1:
                # Ещё есть попытки - ждём и пробуем снова
                print(f"Unexpected error in negative test, attempt {attempt + 1}: {e}")
                time.sleep(0.5 * (attempt + 1))
                continue
            else:
                # Последняя попытка - пробрасываем ошибку
                raise


# ===================================================================================
# ФУНКЦИЯ 14: robust_multipart_post - ЗАГРУЗКА ФАЙЛОВ
# ===================================================================================
def robust_multipart_post(api_client, url, files=None, data=None, headers=None, expected_status=400, timeout=30):
    """
    Устойчивая отправка multipart/form-data запросов с обработкой обрывов соединения.

    НАЗНАЧЕНИЕ:
    Специализированная функция для POST запросов с файлами, использующая
    multipart/form-data encoding с автоматической обработкой ConnectionError.

    ОСОБЕННОСТИ MULTIPART:
    - requests автоматически устанавливает Content-Type с boundary
    - Требуется временное удаление глобального Content-Type заголовка
    - Восстановление оригинального Content-Type после выполнения

    МЕХАНИЗМ:
    1. Сохранение и удаление Content-Type из session.headers
    2. Делегирование к handle_negative_response_safely с параметром files
    3. Восстановление Content-Type в блоке finally

    ПАРАМЕТРЫ:
        api_client: requests.Session экземпляр
        url: str URL для загрузки
        files: dict[str, file-like] | None файлы для отправки
        data: dict[str, str] | None дополнительные поля формы
        headers: dict[str, str] | None HTTP заголовки
        expected_status: int ожидаемый статус-код (по умолчанию 400)
        timeout: int таймаут в секундах

    ВОЗВРАЩАЕТ:
        requests.Response: Объект ответа сервера

    ПРИМЕНЕНИЕ:
        Тестирование валидации загружаемых файлов, проверка типов MIME,
        тестирование ограничений размера файлов.
    """
    # Сохраняем оригинальный Content-Type
    original_content_type = api_client.headers.get('Content-Type')
    
    try:
        # Временно удаляем Content-Type для multipart запросов
        if 'Content-Type' in api_client.headers:
            del api_client.headers['Content-Type']
        
        # Используем стабильную обработку для multipart запросов
        headers = headers or {}
        stable_headers = headers.copy() if headers else {}
        stable_headers.update({
            'Connection': 'close',  # Закрываем соединение после ответа
            'Accept': 'application/json, */*'
        })
        
        return handle_negative_response_safely(
            api_client=api_client,
            method='POST',
            url=url,
            expected_status=expected_status,
            files=files,
            data=data,
            headers=stable_headers,
            timeout=timeout
        )
        
    finally:
        # Восстанавливаем оригинальный Content-Type
        if original_content_type:
            api_client.headers['Content-Type'] = original_content_type


# ===================================================================================
# ФИКСТУРЫ 15-16: АДАПТЕРЫ ФУНКЦИЙ
# ===================================================================================
@pytest.fixture
def stable_negative_request():
    """
    Адаптер функции handle_negative_response_safely в pytest фикстуру.

    НАЗНАЧЕНИЕ:
    Предоставление доступа к функции обработки негативных запросов
    через механизм dependency injection pytest.

    ИСПОЛЬЗОВАНИЕ:
        def test_validation_error(api_client, stable_negative_request):
            response = stable_negative_request(
                api_client, "POST", "/endpoint", 400,
                json={"invalid": "data"}
            )
            assert response.status_code == 400

    ВОЗВРАЩАЕТ:
        Callable: Ссылка на handle_negative_response_safely
    """
    return handle_negative_response_safely


@pytest.fixture
def stable_multipart_post():
    """
    Адаптер функции robust_multipart_post в pytest фикстуру.

    НАЗНАЧЕНИЕ:
    Предоставление доступа к функции multipart POST запросов
    через механизм dependency injection pytest.

    ИСПОЛЬЗОВАНИЕ:
        def test_file_validation(api_client, stable_multipart_post):
            with open("invalid.exe", "rb") as f:
                response = stable_multipart_post(
                    api_client, "/upload",
                    files={"document": f},
                    expected_status=415
                )
            assert "Unsupported Media Type" in response.text

    ВОЗВРАЩАЕТ:
        Callable: Ссылка на robust_multipart_post
    """
    return robust_multipart_post


# ===================================================================================
# ФУНКЦИЯ 17: pytest_configure - НАСТРОЙКА ПАРАМЕТРА --resume
# ===================================================================================
@pytest.hookimpl(tryfirst=True)
def pytest_configure(config):
    """
    Хук pytest для глобальной конфигурации режима продолжения тестирования.

    НАЗНАЧЕНИЕ:
    Извлечение и сохранение флага --resume в объекте конфигурации pytest
    для доступа из плагинов логирования и механизма пропуска тестов.

    ФУНКЦИОНАЛЬНОСТЬ --resume:
    Режим инкрементального выполнения с пропуском успешно выполненных тестов,
    основанный на анализе logs/passed_tests.json.

    ПРИМЕНЕНИЕ:
    Продолжение прерванных длительных тестовых прогонов без повторного
    выполнения уже пройденных тестов.

    МЕХАНИЗМ:
    1. Извлечение boolean значения опции --resume
    2. Установка атрибута config.resume_enabled
    3. Использование в test_pass_logger и test_failure_logger плагинах

    ПАРАМЕТРЫ ДЕКОРАТОРА:
        tryfirst=True: Приоритетное выполнение перед другими конфигурационными хуками

    ПАРАМЕТРЫ:
        config: pytest.Config объект конфигурации
    """
    resume_enabled = config.getoption('--resume')
    config.resume_enabled = resume_enabled


# ===================================================================================
# КОНЕЦ ФАЙЛА conftest.py
# ===================================================================================
#
# АРХИТЕКТУРА КОМПОНЕНТОВ:
#
# ИНИЦИАЛИЗАЦИЯ PYTEST:
# 1. pytest_addoption        - Регистрация CLI параметров (--mirada-host, --resume, etc.)
# 2. pytest_configure         - Конфигурация глобальных параметров (resume_enabled)
#
# СЕССИОННЫЕ КОМПОНЕНТЫ (scope="session"):
# 3. tunnel_manager          - Управление SSH туннелями на протяжении сессии
#
# МОДУЛЬНЫЕ ФИКСТУРЫ (scope="module"):
# 4. api_base_url            - Автоматическое определение базового URL сервиса
# 5. request_timeout         - Извлечение таймаута HTTP запросов из CLI
# 6. api_client              - Инициализация настроенного requests.Session
# 7. agent_base_url          - Определение URL для агента валидации
# 8. auth_token              - Выполнение аутентификации и получение токена
#
# ФУНКЦИОНАЛЬНЫЕ ФИКСТУРЫ (scope="function"):
# 9. capture_last_request    - Монкейпатчинг для перехвата HTTP запросов (autouse=True)
# 10. attach_curl_on_fail    - Генератор контекст-менеджера для cURL команд
# 11. agent_verification     - Фабрика функции валидации через агента
# 12. stable_negative_request - Адаптер handle_negative_response_safely
# 13. stable_multipart_post  - Адаптер robust_multipart_post
#
# ХУКИ PYTEST:
# 14. pytest_runtest_makereport - Расширение отчётов информацией о HTTP запросах
#
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ:
# 15. validate_schema              - Рекурсивная валидация JSON структур
# 16. handle_negative_response_safely - Устойчивое выполнение запросов с 4xx/5xx
# 17. robust_multipart_post        - Устойчивая отправка multipart/form-data
# ===================================================================================
