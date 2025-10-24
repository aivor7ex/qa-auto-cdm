# This file is intentionally left blank.
# It prevents pytest from using the root conftest.py for tests in this directory. 

import pytest
import json
from pathlib import Path
from playwright.sync_api import expect
import os
from playwright.sync_api import expect, Page, Browser, BrowserContext
from typing import Dict, Any

# Глобальный set для учёта уже сделанных скриншотов
_screenshots_taken = set()

def get_safe_test_name(request_or_item):
    # nodeid всегда уникален для параметризованных тестов
    nodeid = getattr(request_or_item, 'nodeid', None)
    if nodeid is None and hasattr(request_or_item, 'node'):
        nodeid = request_or_item.node.nodeid
    if nodeid is None:
        return None
    return nodeid.replace('/', '_').replace('\\', '_').replace(':', '_')

# Универсальная функция для создания скриншота перед вызовом pytest.fail
# Теперь принимает request и использует nodeid для имени файла

def fail_with_screenshot(message, page=None, request=None):
    import pytest
    if page and request:
        safe_test_name = get_safe_test_name(request)
        if safe_test_name and safe_test_name not in _screenshots_taken:
            screenshots_dir = os.path.join(os.path.dirname(__file__), "error_screenshots")
            os.makedirs(screenshots_dir, exist_ok=True)
            screenshot_path = os.path.join(screenshots_dir, f"{safe_test_name}.png")
            page.screenshot(path=screenshot_path)
            _screenshots_taken.add(safe_test_name)
    pytest.fail(message)

# Загружаем данные из creds.json один раз для использования в тестах
try:
    _creds_path = Path(__file__).parent / "creds.json"
    with open(_creds_path, 'r', encoding='utf-8') as f:
        _creds_data = json.load(f)
    CURRENT_CLUSTER_STATE = _creds_data.get('admin', {}).get('cluster_state')
    print(f"CURRENT_CLUSTER_STATE во время сбора тестов: {CURRENT_CLUSTER_STATE}")
except FileNotFoundError:
    CURRENT_CLUSTER_STATE = None
    print("Предупреждение: файл creds.json не найден. Тесты состояния кластера могут быть пропущены.")
except json.JSONDecodeError:
    CURRENT_CLUSTER_STATE = None
    print("Предупреждение: ошибка декодирования JSON в creds.json. Тесты состояния кластера могут быть пропущены.")

@pytest.fixture(scope="module")
def credentials(request):
    import json
    with open("UI/creds.json", encoding="utf-8") as f:
        all_creds = json.load(f)
    param = getattr(request, "param", "admin")
    if isinstance(param, (tuple, list)):
        user_type = param[0]
    else:
        user_type = param
    return all_creds[user_type]


@pytest.fixture(scope="module")
def authenticated_page(browser, credentials):
    """
    Выполняет авторизацию и предоставляет тестам уже аутентифицированную страницу.
    Фикстура выполняется один раз для каждого тестового модуля (файла),
    что экономит время на повторных логинах.
    """
    # Шаг 1: Инициализация браузера и страницы.
    context = browser.new_context(ignore_https_errors=True)
    page = context.new_page()
    try:
        # Шаг 2: Переход на страницу авторизации.
        page.goto(f"https://{credentials['ip']}/", timeout=50000)

        # Дополнительный шаг: обход страниц ошибок сертификата в режиме --headed
        try:
            # Кликаем на ссылку, которая вызывает диалог.
            page.get_by_text("Я понимаю риск, но хочу продолжить").click(timeout=1000)
            # Ждем, чтобы окно успело появиться и получить фокус.
            # page.wait_for_timeout(1000)
            # # Нажимаем Enter, чтобы подтвердить диалог.
            # page.keyboard.press('Enter')
            page.get_by_text("Подтвердить").click(timeout=1000)
        except Exception:
            # Если ни одна из страниц-заглушек не найдена, значит, мы на странице входа.
            pass
        
        # Шаг 3: Ввод учетных данных и вход.
        page.locator(".cdm-input-text:not(.cdm-input-password) input").fill(credentials['login'])
        page.locator(".cdm-input-password input").fill(credentials['password'])

        # Шаг 4: Ожидание ответа от API для подтверждения входа.
        with page.expect_response(f"**/api/users/login"):
            page.get_by_role("button", name="Вход").click()

        # Шаг 5: Переход на главную страницу после входа.
        # Это гарантирует, что тесты начнутся с ожидаемого экрана.
        page.goto(f"https://{credentials['ip']}/#/dashboard")

        # Убеждаемся, что мы на нужной странице, проверив заголовок.
        # Используем expect для более надежных и информативных проверок Playwright.
        expect(page.locator("span.cdm-layout__app-bar__title__label")).to_have_text("Инфографика")
        
        # Шаг 6: Предоставление авторизованной страницы тестам.
        # `yield` передает управление тестам, использующим эту фикстуру.
        yield page

    finally:
        # Шаг 7: Завершение сессии.
        # Этот блок выполнится после того, как все тесты в модуле завершатся.
        # Закрываем контекст, чтобы освободить ресурсы браузера.
        context.close()


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """
    Кастомизирует отчет о падении теста, добавляя в него cURL-команду.
    Этот хук перехватывает результат выполнения теста. Если тест упал
    на этапе вызова API через Playwright, хук извлекает данные запроса
    и формирует cURL-команду для легкого воспроизведения и отладки.
    """
    # yield позволяет выполнить основную логику теста и получить результат.
    outcome = yield
    rep = outcome.get_result()

    # Проверяем, что тест упал именно на этапе выполнения ('call')
    # и что он действительно провалился.
    if rep.when == "call" and rep.failed:
        # --- Вывод cURL-команды ---
        if hasattr(item, 'playwright_request'):
            pw_request = item.playwright_request
            try:
                # Извлекаем тело запроса, если оно есть.
                post_data = pw_request.post_data or ""

                # Формируем полную cURL-команду.
                curl_command = (
                    f"curl -X {pw_request.method} "
                    f"-H 'Content-Type: application/json' "
                    f"-d '{post_data}' "
                    f"--insecure {pw_request.url}"
                )
                # Добавляем cURL-команду в отчет об ошибке pytest.
                if rep.longrepr:
                    rep.longrepr.addsection('Failing Request cURL', curl_command)
            except Exception as e:
                # Если при генерации cURL произошла ошибка, сообщаем об этом.
                if rep.longrepr:
                    rep.longrepr.addsection('cURL Generation Error', str(e))

        # --- Создание скриншота при падении теста ---
        safe_test_name = get_safe_test_name(item)
        if safe_test_name and safe_test_name not in _screenshots_taken:
            page = item.funcargs.get("authenticated_page", None)
            if page:
                screenshots_dir = os.path.join(os.path.dirname(__file__), "error_screenshots")
                os.makedirs(screenshots_dir, exist_ok=True)
                screenshot_path = os.path.join(screenshots_dir, f"{safe_test_name}.png")
                page.screenshot(path=screenshot_path)
                _screenshots_taken.add(safe_test_name)


@pytest.fixture(autouse=True)
def clear_screenshots_taken():
    """
    Фикстура для очистки глобальной переменной _screenshots_taken в начале каждого теста
    """
    global _screenshots_taken
    _screenshots_taken.clear()
    yield

@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    """
    Фикстура для настройки аргументов контекста браузера.
    Устанавливает игнорирование ошибок сертификатов HTTPS.
    """
    return {
        **browser_context_args,
        "ignore_https_errors": True,
    }