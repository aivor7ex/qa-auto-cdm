import pytest
from playwright.sync_api import expect, Page, Browser
from UI.other_tests.test_autentification_admin import _perform_login
import json
import re
import time
import zipfile
from UI.conftest import fail_with_screenshot
from UI.universal_functions.navigation import (
    navigate_and_check_url_with_tab,
    check_tabs_selected_state
)
from UI.universal_functions.click_on_body import wait_for_api_response
from UI.universal_functions.click_on_body import wait_for_api_response_with_response

# Глобальная переменная для передачи информации о том, был ли уже сгенерирован системный отчёт
system_report_generated: bool | None = None


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_system_report_navigate_and_check_url(authenticated_page: Page, credentials):
    """
    Проверяет переход на вкладку "Отчетность" в разделе "Аудит безопасности" и корректность URL для "Системный отчет".
    """
    tab_button_1 = "Аудит безопасности"
    tab_button_2 = "Отчетность"
    tab_target = "Системный отчет"
    url = "security-audit/reports/system-report"
    navigate_and_check_url_with_tab(authenticated_page, tab_button_1, tab_button_2, tab_target, url, credentials)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_system_report_check_tabs_selected_state(authenticated_page: Page, credentials):
    """
    Проверяет, что после перехода на вкладку "Системный отчет" остальные вкладки
    ("Создание отчетов", "Рассылка отчетов") не активны (не выбраны).
    """
    tab_names = ["Создание отчетов", "Рассылка отчетов", "Системный отчет"]
    tab_target = "Системный отчет"
    url = "security-audit/reports/system-report"
    check_tabs_selected_state(authenticated_page, tab_names, tab_target, url, credentials)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_system_report_generate_modal_visible(authenticated_page: Page, credentials):
    """
    Проверяет, что на странице отображается карточка генерации системного отчёта
    с заголовком, подзаголовком и кнопкой "Сгенерировать новый отчёт".
    """

    # Шаг №1: Проверяем карточку генерации отчёта (страница уже открыта предыдущим тестом перехода)
    try:
        card = authenticated_page.locator('div.cdm-card', has_text="Генерация системного отчета")
        card.wait_for(state="visible", timeout=3000)
    except Exception:
        fail_with_screenshot("Карточка генерации системного отчёта не отображается", authenticated_page)

    # Шаг №2: Заголовок
    title = card.locator('span.MuiCardHeader-title', has_text="Генерация системного отчета")
    if not title.is_visible():
        fail_with_screenshot('Заголовок "Генерация системного отчета" не отображается', authenticated_page)

    # Шаг №3: Подзаголовок
    subtitle_text = "Сбор и выгрузка журналов и информации о системе"
    subtitle = card.locator('span.MuiCardHeader-subheader', has_text=subtitle_text)
    if not subtitle.is_visible():
        fail_with_screenshot(f'Подзаголовок "{subtitle_text}" не отображается', authenticated_page)

    # Шаг №4: Кнопка "Сгенерировать новый отчет" (ждём до 20 секунд)
    generate_btn = card.locator('button span.MuiButton-label', has_text="Сгенерировать новый отчет")
    try:
        generate_btn.wait_for(state="visible", timeout=20000)
    except Exception:
        fail_with_screenshot('Кнопка "Сгенерировать новый отчет" не отображается', authenticated_page)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_system_report_download_card_visible(authenticated_page: Page, credentials):
    """
    Проверяет, отображается ли карточка уже сгенерированного системного отчёта
    (заголовок "Системный отчет" и кнопка "Скачать"). Если карточки нет — тест пропускается.
    """

    global system_report_generated

    # Шаг №1: Ищем карточку готового отчёта (остались на той же странице после предыдущего теста)
    card = authenticated_page.locator('div.cdm-card', has_text="Системный отчет")

    if not card.is_visible(timeout=3000):
        system_report_generated = False
        pytest.skip("Системный отчёт ещё не сгенерирован – карта скачивания отсутствует")

    # Карточка видна → отчёт есть
    system_report_generated = True

    # Шаг №2: Проверяем заголовок
    title = card.locator('span.MuiCardHeader-title', has_text="Системный отчет")
    if not title.is_visible():
        fail_with_screenshot('Заголовок "Системный отчет" не отображается', authenticated_page)

    # Шаг №3: Проверяем подзаголовок (дата/время создания)
    subtitle = card.locator('span.MuiCardHeader-subheader')
    if not (subtitle.is_visible() and 'Дата и время создания' in subtitle.inner_text()):
        fail_with_screenshot('Подзаголовок с датой и временем создания не отображается', authenticated_page)

    # Шаг №4: Проверяем кнопку "Скачать"
    download_btn = card.locator('button span.MuiButton-label', has_text="Скачать")
    if not download_btn.is_visible() or not download_btn.is_enabled():
        fail_with_screenshot('Кнопка "Скачать" не кликабельна или не видна', authenticated_page)


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_system_report_generate_click_shows_confirm(authenticated_page: Page, credentials):
    """
    Нажимает на кнопку "Сгенерировать новый отчёт" и, если ранее существовал отчёт,
    ожидает появление диалога подтверждения.
    """

    global system_report_generated

    # Шаг №1: Находим кнопку "Сгенерировать новый отчет"
    generate_btn = authenticated_page.locator('button span.MuiButton-label', has_text="Сгенерировать новый отчет")

    # Шаг №2: Дожидаемся появления кнопки и кликаем
    if not generate_btn.is_visible(timeout=3000):
        fail_with_screenshot('Кнопка "Сгенерировать новый отчет" не найдена перед кликом', authenticated_page)

    # Шаг №3: Логика в зависимости от наличия предыдущего отчёта
    if system_report_generated:
        generate_btn.click()
        # Должно появиться окно подтверждения
        # Шаг №4: Ожидаем появление диалога подтверждения
        confirm_dialog = authenticated_page.locator('div[role="dialog"]', has_text="Текущий отчет будет удален")
        if not confirm_dialog.is_visible(timeout=5000):
            fail_with_screenshot('Окно подтверждения не появилось', authenticated_page)
    else:
        # Отчёта не было – запрос уйдёт сразу, подтверждения нет
        with wait_for_api_response(authenticated_page, "/api/system-report/generate", expected_status=200, method="POST"):
            generate_btn.click()


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_system_report_generate_click_cancel(authenticated_page: Page, credentials):
    """
    При открытом диалоге подтверждения нажимает "Отмена" и убеждается, что окно закрылось.
    Выполняется только если отчёт существовал ранее.
    """

    global system_report_generated

    if not system_report_generated:
        pytest.skip("Отчёт ранее не существовал – подтверждающего окна нет, пропуск")

    # Шаг №1: Находим открытый диалог подтверждения
    confirm_dialog = authenticated_page.locator('div[role="dialog"]', has_text="Текущий отчет будет удален")
    if not confirm_dialog.is_visible(timeout=2000):
        fail_with_screenshot('Окно подтверждения не найдено перед нажатием Отмена', authenticated_page)

    # Шаг №2: Нажимаем кнопку "Отмена"
    cancel_btn = authenticated_page.locator('button span.MuiButton-label', has_text="Отмена")
    cancel_btn.click()

    # Шаг №3: Убеждаемся, что диалог закрылся
    confirm_dialog.wait_for(state="hidden", timeout=5000)


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_system_report_generate_confirm_yes(authenticated_page: Page, credentials):
    """
    Нажимает "Сгенерировать новый отчёт" и подтверждает действие (кнопка "Да").
    Ожидает POST /api/system-report/generate с успешным статусом.
    """
    global system_report_generated

    if not system_report_generated:
        pytest.skip("Отчёт ранее не существовал – подтверждения 'Да' нет, пропуск теста")

    # Шаг №1: Нажимаем на кнопку "Сгенерировать новый отчет"
    generate_btn = authenticated_page.locator('button span.MuiButton-label', has_text="Сгенерировать новый отчет")
    if not generate_btn.is_visible(timeout=3000):
        fail_with_screenshot('Кнопка "Сгенерировать новый отчет" не найдена перед кликом', authenticated_page)
    generate_btn.click()
    # Уже знаем, что отчёт существовал ⇒ появится диалог
    # Шаг №4: Ожидаем появление диалога подтверждения
    confirm_dialog = authenticated_page.locator('div[role="dialog"]', has_text="Текущий отчет будет удален")
    if not confirm_dialog.is_visible(timeout=5000):
        fail_with_screenshot('Окно подтверждения не появилось', authenticated_page)

    # Шаг №3: Нажимаем кнопку "Да" и ждём POST запрос
    yes_btn = authenticated_page.locator('button span.MuiButton-label', has_text="Да")
    with wait_for_api_response(authenticated_page, "/api/system-report/generate", expected_status=200, method="POST"):
        yes_btn.click()
    # Шаг №4: Убеждаемся что диалог закрылся
    try:
        confirm_dialog.wait_for(state="hidden", timeout=3000)
    except Exception:
        fail_with_screenshot('Окно подтверждения не закрылось', authenticated_page)


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_system_report_generation_in_progress(authenticated_page: Page, credentials):
    """
    Проверяет, что после запуска генерации отчета отображается карточка
    с текстом "Идет генерация отчета..." и неактивной кнопкой.
    """
    # Шаг №1: Находим карточку генерации по тексту "Идет генерация отчета..."
    card = authenticated_page.locator('div.cdm-card', has_text="Идет генерация отчета...")
    try:
        # Генерация может занять время, поэтому ждём появления этого состояния
        card.wait_for(state="visible", timeout=10000)
    except Exception:
        fail_with_screenshot("Карточка 'Идет генерация отчета...' не отображается", authenticated_page)

    # Шаг №2: Проверяем заголовок
    title = card.locator('span.MuiCardHeader-title', has_text="Генерация системного отчета")
    if not title.is_visible():
        fail_with_screenshot('Заголовок "Генерация системного отчета" не отображается', authenticated_page)

    # Шаг №3: Проверяем текст о том, что идет генерация
    progress_text = card.locator('p', has_text="Идет генерация отчета...")
    if not progress_text.is_visible():
        fail_with_screenshot('Текст "Идет генерация отчета..." не отображается', authenticated_page)

    # Шаг №4: Проверяем, что кнопка "Сгенерировать новый отчет" неактивна
    generate_btn = card.locator('button:has-text("Сгенерировать новый отчет")')
    if not generate_btn.is_disabled():
        fail_with_screenshot('Кнопка "Сгенерировать новый отчет" активна, хотя должна быть неактивна', authenticated_page)


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_system_report_check_polling(authenticated_page: Page, credentials):
    """
    Проверяет, что во время генерации отчета отправляются
    периодические POST-запросы на /api/system-report/check для проверки статуса.
    """
    # Шаг №1: Ожидаем хотя бы один POST-запрос на эндпоинт /api/system-report/check
    # Используем универсальный контекст-менеджер. Так как поллинг запускается автоматически
    # после предыдущего теста, мы не выполняем никаких действий внутри блока, а просто ждем.
    try:
        with wait_for_api_response(
            authenticated_page,
            "/api/system-report/check",
            expected_status=200,
            method="POST",
            timeout=10000
        ):
            # Действие, инициирующее запрос, произошло в предыдущем тесте,
            # поэтому здесь мы просто ждём фоновый запрос.
            pass
    except Exception:
        fail_with_screenshot("Не был зафиксирован POST-запрос на /api/system-report/check в течение 10 секунд", authenticated_page)


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_system_report_wait_for_generated_status(authenticated_page: Page, credentials):
    """
    Ожидает POST-запрос на /api/system-report/check до получения ответа со статусом "GENERATED" в течение 30 минут.
    Если ответ не получен, тест проваливается и последующие тесты пропускаются.
    """
    global system_report_generated
    # Шаг №1: Устанавливаем таймаут в 10 минут (600 секунд)
    timeout = 1800
    start_time = time.time()

    # Шаг №2: Ожидаем ответ со статусом "GENERATED"
    while time.time() - start_time < timeout:
        try:
            with wait_for_api_response_with_response(
                authenticated_page,
                "/api/system-report/check",
                expected_status=200,
                method="POST",
                timeout=30000
            ) as resp_info:
                response = resp_info.value
                if response is None:
                    print("Received no response")
                    continue
                print(f"type(response.text) = {type(response.text)}")
                text = response.text()
                print(f"Full response: {text}")
                try:
                    data = json.loads(text)
                except Exception as e:
                    print(f"Could not parse JSON: {e}")
                    continue
                status = data.get("status")
                print(f"data.get('status') = {status!r}, type = {type(status)}")
                if isinstance(status, str) and status.strip().upper() == "GENERATED":
                    print("Status 'GENERATED' received, exiting loop and test")
                    system_report_generated = True
                    return  # Успешно получили нужный статус
        except Exception as e:
            print(f"Exception occurred: {e}")
            pass
        time.sleep(1)
    system_report_generated = False
    fail_with_screenshot("Не был получен ответ со статусом 'GENERATED' в течение 30 минут", authenticated_page)


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_system_report_download_button_clickable(authenticated_page: Page, credentials):
    """
    Ищет окно с заголовком "Системный отчет" и проверяет, что кнопка "Скачать" кликабельна.
    """
    # Шаг №1: Находим карточку с заголовком "Системный отчет"
    card = authenticated_page.locator('div.MuiCard-root', has_text="Системный отчет")
    if not card.is_visible(timeout=3000):
        fail_with_screenshot('Карточка "Системный отчет" не отображается', authenticated_page)

    # Шаг №2: Проверяем, что кнопка "Скачать" кликабельна
    download_btn = card.locator('button span.MuiButton-label', has_text="Скачать")
    if not download_btn.is_enabled():
        fail_with_screenshot('Кнопка "Скачать" не кликабельна', authenticated_page)


"""------------------------------Проверка архива системного отчета--------------------------------------- """

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_click_download_button(authenticated_page: Page, credentials):
    """
    Нажимает на кнопку "Скачать" и проверяет загрузку файла system-report.log.zip.
    """
    global system_report_generated

    if not system_report_generated:
        pytest.skip("Отчёт не был сгенерирован, пропуск теста загрузки")

    # Шаг №1: Находим и нажимаем кнопку "Скачать"
    download_btn = authenticated_page.locator('button span.MuiButton-label', has_text="Скачать")
    if not download_btn.is_visible() or not download_btn.is_enabled():
        fail_with_screenshot('Кнопка "Скачать" не кликабельна или не видна', authenticated_page)

    with authenticated_page.expect_download() as download_info:
        download_btn.click()
    download = download_info.value
    filename = download.suggested_filename

    # Шаг №2: Проверяем имя скачанного файла
    if filename != "system-report.log.zip":
        fail_with_screenshot(f'Имя скачанного файла некорректно: {filename}', authenticated_page)

    # Шаг №3: Сохраняем путь для следующих тестов
    global _last_download_path
    _last_download_path = download.path()


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_verify_docker_directory(authenticated_page: Page, credentials):
    """
    Проверяет наличие директории /docker/ в загруженном архиве system-report.log.zip.
    """
    global _last_download_path

    if not _last_download_path:
        pytest.skip("Файл не был загружен, пропуск теста проверки директории /docker/")

    # Шаг №1: Открываем архив и проверяем наличие директории /docker/
    with zipfile.ZipFile(_last_download_path, 'r') as zip_ref:
        if 'system-report.log/docker/' not in zip_ref.namelist():
            fail_with_screenshot('Директория /docker/ отсутствует в архиве', authenticated_page)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_verify_docker_directory(authenticated_page: Page, credentials):
    """
    Проверяет наличие директории /docker/ в загруженном архиве system-report.log.zip.
    """
    global _last_download_path

    if not _last_download_path:
        pytest.skip("Файл не был загружен, пропуск теста проверки директории /docker/")

    # Шаг №1: Открываем архив и проверяем наличие директории /docker/
    with zipfile.ZipFile(_last_download_path, 'r') as zip_ref:
        if 'system-report.log/docker/' not in zip_ref.namelist():
            fail_with_screenshot('Директория /docker/ отсутствует в архиве', authenticated_page)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_verify_files_directory(authenticated_page: Page, credentials):
    """
    Проверяет наличие директории /files/ в загруженном архиве system-report.log.zip.
    """
    global _last_download_path

    if not _last_download_path:
        pytest.skip("Файл не был загружен, пропуск теста проверки директории /files/")

    # Шаг №1: Открываем архив и проверяем наличие директории /files/
    with zipfile.ZipFile(_last_download_path, 'r') as zip_ref:
        if 'system-report.log/files/' not in zip_ref.namelist():
            fail_with_screenshot('Директория /files/ отсутствует в архиве', authenticated_page)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_verify_services_directory(authenticated_page: Page, credentials):
    """
    Проверяет наличие директории /services/ в загруженном архиве system-report.log.zip.
    """
    global _last_download_path

    if not _last_download_path:
        pytest.skip("Файл не был загружен, пропуск теста проверки директории /services/")

    # Шаг №1: Открываем архив и проверяем наличие директории /files/
    with zipfile.ZipFile(_last_download_path, 'r') as zip_ref:
        if 'system-report.log/services/' not in zip_ref.namelist():
            fail_with_screenshot('Директория /services/ отсутствует в архиве', authenticated_page)


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_verify_system_directory(authenticated_page: Page, credentials):
    """
    Проверяет наличие директории /system/ в загруженном архиве system-report.log.zip.
    """
    global _last_download_path

    if not _last_download_path:
        pytest.skip("Файл не был загружен, пропуск теста проверки директории /system/")

    # Шаг №1: Открываем архив и проверяем наличие директории /files/
    with zipfile.ZipFile(_last_download_path, 'r') as zip_ref:
        if 'system-report.log/system/' not in zip_ref.namelist():
            fail_with_screenshot('Директория /system/ отсутствует в архиве', authenticated_page)