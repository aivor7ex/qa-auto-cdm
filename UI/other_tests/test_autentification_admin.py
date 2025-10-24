import random
import string
from playwright.sync_api import Browser, expect, Page


def generate_random_string(length=10):
    """
    Генерирует случайную строку заданной длины из букв и цифр.
    Используется для создания невалидных данных в негативных тестах.
    """
    letters_and_digits = string.ascii_letters + string.digits
    return ''.join(random.choice(letters_and_digits) for i in range(length))


def _perform_login(page: Page, username, password, base_url, request):
    """
    Вспомогательная функция для выполнения авторизации.
    Шаг № 1: Выполняет переход на страницу авторизации.
    Шаг № 2: Обходит страницы ошибок SSL-сертификата (если применимо).
    Шаг № 3: Вводит учетные данные.
    Шаг № 4: Отправляет форму и ожидает ответа от API.
    Шаг № 5: Проверяет статус ответа API и наличие ошибок.
    Шаг № 6: Убеждается, что пользователь перенаправлен на страницу дашборда.
    """
    # Шаг № 1: Переход на страницу авторизации.
    page.goto(base_url, wait_until="networkidle")

    # Шаг № 2: Обход страниц ошибок сертификата в режиме --headed.
    try:
        # Пробуем обойти стандартную страницу ошибки Chrome.
        page.locator("#details-button").click(timeout=1000)
        page.locator("#proceed-link").click()
    except Exception:
        try:
            # Пробуем обойти кастомную страницу-заглушку.
            page.get_by_text("Я понимаю риск, но хочу продолжить").click(timeout=1000)
            # page.wait_for_timeout(1000)
            page.keyboard.press('enter') # НЕ РАБОТАЕТ С КАСПЕРОМ, ОН НАТИВНО ВЫЗЫВАЕТ ОКНО
        except Exception:
            # Если ни одна из страниц-заглушек не найдена, значит, мы на странице входа.
            pass

    # Шаг № 3: Ввод учетных данных.
    page.locator(".cdm-input-text:not(.cdm-input-password) input").fill(username)
    page.locator(".cdm-input-password input").fill(password)

    # Шаг № 4: Отправка формы и ожидание ответа от API.
    with page.expect_response("**/api/users/login") as response_info:
        page.get_by_role("button", name="Вход").click()

    # Шаг № 5: Проверка ответа от сервера.
    response = response_info.value
    request.node.playwright_request = response.request

    assert response.status == 200, f"Ожидался статус 200, но получен {response.status}"
    response_json = response.json()
    assert "error" not in response_json, f"Вход не удался с ошибкой: {response_json.get('error')}"

    # Шаг № 6: Убеждаемся, что мы перешли на главную страницу после авторизации.
    page.wait_for_url(f"{base_url}/dashboard")
    # Шаг № 7: Ожидаем полной загрузки DOM-контента страницы.
    page.wait_for_load_state('domcontentloaded')
    page.wait_for_selector('span.cdm-layout__app-bar__title__label')
    assert page.locator('span.cdm-layout__app-bar__title__label').text_content() == "Инфографика", "Заголовок страницы не соответствует 'Инфографика'"
    return page


def test_autentification_positive(browser: Browser, request, credentials):
    """
    Проверяет успешную авторизацию с валидными учетными данными.
    Тест вводит правильный логин и пароль, нажимает кнопку "Вход"
    и ожидает успешного ответа от сервера (статус 200).
    """
    # Шаг № 1: Инициализация браузера и страницы.
    # Создаем новый контекст с игнорированием ошибок HTTPS для работы с самоподписанным сертификатом.
    context = browser.new_context(ignore_https_errors=True)
    page = context.new_page()

    try:
        # Шаг № 2: Выполняем авторизацию с использованием вспомогательной функции.
        _perform_login(page, credentials['login'], credentials['password'], f"https://{credentials['ip']}", request)


    except Exception as e:
        # В случае сбоя делаем скриншот для анализа проблемы.
        page.screenshot(path="UI/error_screenshots/autentification_positive_error.png")
        raise e

    finally:
        # Закрываем контекст.
        context.close()


def test_autentification_negative(browser: Browser, request, credentials):
    """
    Проверяет невозможность авторизации с неверными (случайными) учетными данными.
    Тест вводит сгенерированные логин и пароль и ожидает от сервера
    ошибку авторизации (статус 401).
    """
    # Шаг № 1: Инициализация браузера и страницы.
    context = browser.new_context(ignore_https_errors=True)
    page = context.new_page()

    try:
        # Шаг № 2: Генерируем случайные неверные логин и пароль.
        wrong_username = generate_random_string()
        wrong_password = generate_random_string()

        # Шаг № 3: Пытаемся авторизоваться с неверными учетными данными и ожидаем ошибку 401.
        page.goto(f"https://{credentials['ip']}/", wait_until="networkidle")
        try:
            page.locator("#details-button").click(timeout=1500)
            page.locator("#proceed-link").click()
        except Exception:
            try:
                page.get_by_text("Я понимаю риск, но хочу продолжить").click(timeout=1500)
                page.wait_for_timeout(1000)
                page.keyboard.press('Enter')
            except Exception:
                pass
        
        page.locator(".cdm-input-text:not(.cdm-input-password) input").fill(wrong_username)
        page.locator(".cdm-input-password input").fill(wrong_password)
        
        with page.expect_response(f"**/api/users/login") as response_info:
            page.get_by_role("button", name="Вход").click()

        # Шаг № 4: Проверка ответа от сервера.
        response = response_info.value
        request.node.playwright_request = response.request

        expected_json = {
            "error": {
                "statusCode": 401,
                "name": "UnauthorizedError",
                "message": "Unauthorized",
                "code": "LOGIN_FAILED"
            }
        }
        assert response.status == 401
        assert response.json() == expected_json

    except Exception as e:
        # В случае сбоя делаем скриншот.
        page.screenshot(path="UI/error_screenshots/autentification_negative_error.png")
        raise e
    finally:
        # Закрываем контекст.
        context.close()


def test_autentification_correct_login_wrong_password(browser: Browser, request, credentials):
    """
    Проверяет невозможность авторизации с верным логином, но неверным паролем.
    Тест вводит правильный логин и случайный неверный пароль,
    ожидая в ответ ошибку 401.
    """
    # Шаг № 1: Инициализация браузера и страницы.
    context = browser.new_context(ignore_https_errors=True)
    page = context.new_page()
    try:
        # Шаг № 2: Переход на страницу авторизации.
        page.goto(f"https://{credentials['ip']}/", wait_until="networkidle")

        # Дополнительный шаг: обход страниц ошибок сертификата в режиме --headed
        try:
            # Сначала пробуем обойти стандартную страницу ошибки Chrome.
            page.locator("#details-button").click(timeout=1500)
            page.locator("#proceed-link").click()
        except Exception:
            # Если не получилось, пробуем обойти кастомную страницу-заглушку.
            try:
                # Кликаем на ссылку, которая вызывает диалог.
                page.get_by_text("Я понимаю риск, но хочу продолжить").click(timeout=1500)
                # Ждем, чтобы окно успело появиться и получить фокус.
                page.wait_for_timeout(1000)
                # Нажимаем Enter, чтобы подтвердить диалог.
                page.keyboard.press('Enter')
            except Exception:
                # Если ни одна из страниц-заглушек не найдена, значит, мы на странице входа.
                pass

        # Шаг № 3: Генерация неверного пароля.
        # Убеждаемся, что сгенерированный пароль не совпадает с верным.
        wrong_password = generate_random_string()
        while wrong_password == credentials['password']:
            wrong_password = generate_random_string()

        # Шаг № 4: Ввод учетных данных.
        page.locator(".cdm-input-text:not(.cdm-input-password) input").fill(credentials['login']) # Использовать 'login'
        page.locator(".cdm-input-password input").fill(wrong_password)
        
        # Шаг № 5: Отправка формы и ожидание ответа от API.
        with page.expect_response(f"**/api/users/login") as response_info:
            page.get_by_role("button", name="Вход").click()
        
        # Шаг № 6: Проверка ответа от сервера.
        response = response_info.value
        request.node.playwright_request = response.request
        expected_json = {
            "error": {"statusCode": 401, "name": "UnauthorizedError", "message": "Unauthorized", "code": "LOGIN_FAILED"}
        }
        assert response.status == 401
        assert response.json() == expected_json

    except Exception as e:
        page.screenshot(path="UI/error_screenshots/correct_login_wrong_password_error.png")
        raise e
    finally:
        context.close()


def test_autentification_wrong_login_correct_password(browser: Browser, request, credentials):
    """
    Проверяет невозможность авторизации с неверным логином, но верным паролем.
    Тест вводит случайный неверный логин и правильный пароль,
    ожидая в ответ ошибку 401.
    """
    # Шаг № 1: Инициализация браузера и страницы.
    context = browser.new_context(ignore_https_errors=True)
    page = context.new_page()
    try:
        # Шаг № 2: Переход на страницу авторизации.
        page.goto(f"https://{credentials['ip']}/", wait_until="networkidle")

        # Дополнительный шаг: обход страниц ошибок сертификата в режиме --headed
        try:
            # Сначала пробуем обойти стандартную страницу ошибки Chrome.
            page.locator("#details-button").click(timeout=1500)
            page.locator("#proceed-link").click()
        except Exception:
            # Если не получилось, пробуем обойти кастомную страницу-заглушку.
            try:
                # Кликаем на ссылку, которая вызывает диалог.
                page.get_by_text("Я понимаю риск, но хочу продолжить").click(timeout=1500)
                # Ждем, чтобы окно успело появиться и получить фокус.
                page.wait_for_timeout(1000)
                # Нажимаем Enter, чтобы подтвердить диалог.
                page.keyboard.press('Enter')
            except Exception:
                # Если ни одна из страниц-заглушек не найдена, значит, мы на странице входа.
                pass

        # Шаг № 3: Генерация неверного логина.
        # Убеждаемся, что сгенерированный логин не совпадает с верным.
        wrong_login = generate_random_string()
        while wrong_login == credentials['login']: # Использовать 'login'
            wrong_login = generate_random_string()

        # Шаг № 4: Ввод учетных данных.
        page.locator(".cdm-input-text:not(.cdm-input-password) input").fill(wrong_login)
        page.locator(".cdm-input-password input").fill(credentials['password'])
        
        # Шаг № 5: Отправка формы и ожидание ответа от API.
        with page.expect_response(f"**/api/users/login") as response_info:
            page.get_by_role("button", name="Вход").click()
        
        # Шаг № 6: Проверка ответа от сервера.
        response = response_info.value
        request.node.playwright_request = response.request
        expected_json = {
            "error": {"statusCode": 401, "name": "UnauthorizedError", "message": "Unauthorized", "code": "LOGIN_FAILED"}
        }
        assert response.status == 401
        assert response.json() == expected_json

    except Exception as e:
        page.screenshot(path="UI/error_screenshots/wrong_login_correct_password_error.png")
        raise e
    finally:
        context.close()


def test_autentification_empty_credentials(browser: Browser, credentials):
    """
    Проверяет валидацию на стороне клиента при отправке пустых полей.
    Тест оставляет поля логина и пароля пустыми и проверяет,
    что под каждым полем появляется текст ошибки "Заполните поле".
    """
    # Шаг № 1: Инициализация браузера и страницы.
    context = browser.new_context(ignore_https_errors=True)
    page = context.new_page()
    try:
        # Шаг № 2: Переход на страницу авторизации и обход ошибок сертификата.
        page.goto(f"https://{credentials['ip']}/")
        try:
            page.locator("#details-button").click(timeout=1500)
            page.locator("#proceed-link").click()
        except Exception:
            try:
                page.get_by_text("Я понимаю риск, но хочу продолжить").click(timeout=1500)
                page.wait_for_timeout(1000)
                page.keyboard.press('Enter')
            except Exception:
                pass
        
        # Шаг № 3: Очистка полей логина и пароля, затем попытка входа.
        page.locator(".cdm-input-text:not(.cdm-input-password) input").fill("")
        page.locator(".cdm-input-password input").fill("")
        page.get_by_role("button", name="Вход").click()

        # Шаг № 4: Проверка видимости и текста сообщений об ошибках валидации.
        login_error = page.locator(".cdm-input-text:not(.cdm-input-password) p.Mui-error")
        expect(login_error).to_be_visible()
        expect(login_error).to_have_text("Заполните поле")

        password_error = page.locator(".cdm-input-password p.Mui-error")
        expect(password_error).to_be_visible()
        expect(password_error).to_have_text("Заполните поле")

    except Exception as e:
        page.screenshot(path="UI/error_screenshots/empty_credentials_error.png")
        raise e
    finally:
        context.close()


def test_logout(browser: Browser, request, credentials):
    """
    Тест на выход пользователя из системы.
    """
    # Шаг № 1: Инициализация браузера и страницы.
    context = browser.new_context(ignore_https_errors=True)
    page = context.new_page()

    try:
        # Шаг № 2: Авторизуемся как администратор с дефолтными кредами.
        _perform_login(page, credentials['login'], credentials['password'], f"https://{credentials['ip']}", request)

        # Шаг № 3: Нажимаем кнопку "admin" в шапке страницы.
        page.locator('button.MuiButtonBase-root.MuiButton-root.cdm-button.MuiButton-text span.MuiButton-label:has-text("admin")').click()

        # Шаг № 4: Нажимаем "Выход" и ожидаем POST-запрос на /api/users/logout.
        with page.expect_response(f"**/api/users/logout") as response_info:
            page.locator('li.MuiButtonBase-root.MuiListItem-root.MuiMenuItem-root:has-text("Выход")').click()

        # Шаг № 5: Проверяем ответ от API.
        response = response_info.value
        assert response.status == 204, f"Ожидался статус 204, но получен {response.status}"
        assert response.status_text == "No Content", f"Ожидался статус текст 'No Content', но получен {response.status_text}"

    except Exception as e:
        page.screenshot(path="UI/error_screenshots/logout_error.png")
        raise e
    finally:
        page.close() # Закрываем страницу по завершении теста

def test_change_password(browser: Browser, request, credentials):
    """
    Тест на смену пароля пользователя.
    После успешной смены, пароль восстанавливается до исходного значения
    из creds.json, чтобы не влиять на другие тесты.
    """
    # Шаг № 1: Инициализация браузера и страницы.
    context = browser.new_context(ignore_https_errors=True)
    page = context.new_page()
    # Временный пароль для теста
    new_password = "new_password" 

    try:
        # Шаг № 2: Авторизуемся как администратор с дефолтными кредами.
        _perform_login(page, credentials['login'], credentials['password'], f"https://{credentials['ip']}", request)

        # Шаг № 3: Нажимаем кнопку "admin" в шапке страницы.
        page.locator('button.MuiButtonBase-root.MuiButton-root.cdm-button.MuiButton-text span.MuiButton-label:has-text("admin")').click()

        # Шаг № 4: Нажимаем "Пользовательские настройки".
        page.locator('li.MuiButtonBase-root.MuiListItem-root.MuiMenuItem-root:has-text("Пользовательские настройки")').click()
        page.wait_for_url(f"https://{credentials['ip']}/user-settings/profile")

        # Шаг № 5: Нажимаем вкладку "Сменить пароль".
        page.locator('button.MuiButtonBase-root.MuiTab-root.tabs-navigation__item:has-text("Сменить пароль")').click()
        page.wait_for_url(f"https://{credentials['ip']}/user-settings/change-password")

        # Шаг № 6: Вводим текущий пароль.
        current_password_input = page.locator('div.MuiInputBase-root.MuiInput-root.MuiInput-underline input#standard-adornment-password[type="password"]').first
        current_password_input.fill(credentials["password"]) # Используем creds.json для текущего пароля

        # Шаг № 7: Вводим новый пароль.
        new_password_input = page.locator('div.MuiInputBase-root.MuiInput-root.MuiInput-underline input#standard-adornment-password[type="password"]').nth(1)
        new_password_input.fill(new_password)

        # Шаг № 8: Нажимаем кнопку "Сменить пароль".
        page.locator('button.MuiButtonBase-root.MuiButton-root.cdm-button.cdm-button__primary.MuiButton-contained:has-text("Сменить пароль")').click()

        # Шаг № 9: Ожидаем сохранения изменений.
        page.wait_for_timeout(5000)

    except Exception as e:
        page.screenshot(path="UI/error_screenshots/change_password_error.png")
        raise e
    finally:
        page.close() # Закрываем страницу по завершении теста

def test_login_with_new_password(browser: Browser, request, credentials):
    """
    Тест на вход в систему с новым паролем.
    Этот тест предполагает, что пароль был изменен до 'new_password'
    предыдущим выполнением теста test_change_password.
    """
    # Шаг № 1: Инициализация браузера и страницы.
    context = browser.new_context(ignore_https_errors=True)
    page = context.new_page()

    try:
        # Шаг № 2: Вход с новым паролем.
        new_password = "new_password" # Ожидаемый новый пароль
        _perform_login(page, credentials['login'], new_password, f"https://{credentials['ip']}", request)

    except Exception as e:
        page.screenshot(path="UI/error_screenshots/login_with_new_password_error.png")
        raise e
    finally:
        page.close() # Закрываем страницу по завершении теста


def test_reset_password_to_default(browser: Browser, request, credentials):
    """
    Тест на сброс пароля до стандартных значений из creds.json.
    Предполагает, что текущий пароль 'new_password'.
    """
    # Шаг № 1: Инициализация браузера и страницы.
    context = browser.new_context(ignore_https_errors=True)
    page = context.new_page()

    try:
        # Шаг № 2: Авторизуемся с новым паролем.
        new_password = "new_password"
        _perform_login(page, credentials['login'], new_password, f"https://{credentials['ip']}", request)

        # Шаг № 3: Нажимаем кнопку "admin" в шапке страницы.
        page.locator('button.MuiButtonBase-root.MuiButton-root.cdm-button.MuiButton-text span.MuiButton-label:has-text("admin")').click()

        # Шаг № 4: Нажимаем "Пользовательские настройки".
        page.locator('li.MuiButtonBase-root.MuiListItem-root.MuiMenuItem-root:has-text("Пользовательские настройки")').click()
        page.wait_for_url(f"https://{credentials['ip']}/user-settings/profile")

        # Шаг № 5: Нажимаем вкладку "Сменить пароль".
        page.locator('button.MuiButtonBase-root.MuiTab-root.tabs-navigation__item:has-text("Сменить пароль")').click()
        page.wait_for_url(f"https://{credentials['ip']}/user-settings/change-password")

        # Шаг № 6: Вводим текущий пароль (который был 'new_password').
        current_password_input = page.locator('div.MuiInputBase-root.MuiInput-root.MuiInput-underline input#standard-adornment-password[type="password"]').first
        current_password_input.fill(new_password)

        # Шаг № 7: Вводим стандартный пароль из creds.json.
        default_password = credentials["password"]
        new_password_input = page.locator('div.MuiInputBase-root.MuiInput-root.MuiInput-underline input#standard-adornment-password[type="password"]').nth(1)
        new_password_input.fill(default_password)

        # Шаг № 8: Нажимаем кнопку "Сменить пароль".
        page.locator('button.MuiButtonBase-root.MuiButton-root.cdm-button.cdm-button__primary.MuiButton-contained:has-text("Сменить пароль")').click()

        # Шаг № 9: Ожидаем сохранения изменений.
        page.wait_for_timeout(5000)

    except Exception as e:
        page.screenshot(path="UI/error_screenshots/reset_password_to_default_error.png")
        raise e
    finally:
        page.close() # Закрываем страницу по завершении теста
