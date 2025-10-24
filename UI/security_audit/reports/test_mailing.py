import pytest
from playwright.sync_api import expect, Page, Browser
from UI.other_tests.test_autentification_admin import _perform_login
import json
import re
from UI.universal_functions.navigation import (
    navigate_and_check_url_with_tab,
    check_tabs_selected_state,
    find_input_by_label
)
from UI.universal_functions.filter import (
    check_filter_by_select,
    check_filter_by_select_negative_other_values,
    check_filter_by_input,
    check_filter_by_input_negative_other_values,
    check_filter_by_input_first_row_value
)
from UI.conftest import fail_with_screenshot
from UI.universal_functions.click_on_body import hover_column_help_icon_and_assert_title, delete_row_by_first_cell


def find_row_by_text(table, text):
    """
    Возвращает первую строку, где в любой ячейке есть div с нужным текстом.
    """
    rows = table.locator('tbody tr')
    for i in range(rows.count()):
        row = rows.nth(i)
        divs = row.locator(f'div:has-text("{text}")')
        if divs.count() > 0:
            return row
    return None

def find_row_with_input(table, value=None):
    """
    Возвращает первую строку, где есть input[type="text"] (если value=None)
    или input[type="text"][value=...] (если value задан).
    """
    rows = table.locator('tbody tr')
    for i in range(rows.count()):
        row = rows.nth(i)
        if value is not None:
            inputs = row.locator(f'input[type="text"][value="{value}"]')
            if inputs.count() > 0:
                return row
        else:
            inputs = row.locator('input[type="text"]')
            if inputs.count() > 0:
                return row
    return None

def find_editing_row(table):
    """
    Возвращает первую строку, в которой есть кнопка 'Сохранить' (редактируемая строка).
    """
    rows = table.locator('tbody tr')
    for i in range(rows.count()):
        row = rows.nth(i)
        save_btn = row.locator('button:has(span[title="Сохранить"])')
        if save_btn.count() > 0 and save_btn.is_visible():
            return row
    return None

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_mailing_navigate_and_check_url(authenticated_page: Page, credentials):
    """
    Проверяет переход на вкладку "Отчетность" в разделе "Аудит безопасности" и корректность URL для "Рассылка отчетов".
    """
    tab_button_1 = "Аудит безопасности"
    tab_button_2 = "Отчетность"
    tab_target = "Рассылка отчетов"
    url = "security-audit/reports/mailing"
    navigate_and_check_url_with_tab(authenticated_page, tab_button_1, tab_button_2, tab_target, url, credentials)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_mailing_check_tabs_selected_state(authenticated_page: Page, credentials):
    """
    Проверяет, что после перехода на вкладку "Рассылка отчетов" остальные вкладки
    ("Создание отчетов", "Системный отчет") не активны (не выбраны).
    """
    tab_names = ["Создание отчетов", "Рассылка отчетов", "Системный отчет"]
    tab_target = "Рассылка отчетов"
    url = "security-audit/reports/mailing"
    check_tabs_selected_state(authenticated_page, tab_names, tab_target, url, credentials)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_mailing_no_templates_hint_present(authenticated_page: Page, credentials):
    """
    Проверяет, что отображается надпись 'Для создания рассылки требуется создать шаблон' в нужном классе.
    """
    # Шаг №1: Находим элемент с нужным классом и текстом
    hint = authenticated_page.locator('div.MuiCardActions-root p', has_text="Для создания рассылки требуется создать шаблон")
    # Шаг №2: Проверяем, что надпись видима
    if not hint.is_visible():
        fail_with_screenshot('Надпись "Для создания рассылки требуется создать шаблон" не отображается на странице', authenticated_page)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_create_navigate_and_check_url_2(authenticated_page: Page, credentials):
    """
    Проверяет переход на вкладку "Отчетность" в разделе "Аудит безопасности" и корректность URL для "Создание отчетов".
    """
    tab_button_1 = "Аудит безопасности"
    tab_button_2 = "Отчетность"
    tab_target = "Создание отчетов"
    url = "security-audit/reports/create"
    navigate_and_check_url_with_tab(authenticated_page, tab_button_1, tab_button_2, tab_target, url, credentials)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_create_report_save_template_and_check_modal_and_template_radio(authenticated_page: Page, credentials):
    """
    Вводит название шаблона 'test', сохраняет шаблон, проверяет появление модального окна об успешном сохранении,
    закрывает окно по крестику, затем проверяет появление радиокнопки 'Создать по шаблону', что она выбрана,
    и что появился селект с шаблоном 'test'.
    """
    # Шаг №1: Проверяем, что все чекбоксы включены, если нет — включаем
    checkbox_labels = [
        "Сводный трафик по угрозам",
        "Дифференциальный трафик по угрозам",
        "Таблица \"Топ 10\""
    ]
    for label in checkbox_labels:
        checkbox = authenticated_page.get_by_label(label)
        if not checkbox.is_checked():
            checkbox.check()
        if not checkbox.is_checked():
            fail_with_screenshot(f'Чекбокс "{label}" должен быть включён для сохранения шаблона', authenticated_page)
    # Шаг №2: Вводим название шаблона 'test'
    input_field = find_input_by_label(authenticated_page, "Название шаблона", "test")
    if not input_field.is_visible():
        fail_with_screenshot("Поле 'Название шаблона' не найдено на странице", authenticated_page)
    # Шаг №3: Проверяем, что кнопка "Сохранить шаблон" кликабельна и нажимаем её
    save_btn = authenticated_page.get_by_role("button", name="Сохранить шаблон")
    if not save_btn.is_visible():
        fail_with_screenshot("Кнопка 'Сохранить шаблон' не найдена на странице", authenticated_page)
    if not save_btn.is_enabled():
        fail_with_screenshot("Кнопка 'Сохранить шаблон' должна быть кликабельна при включенных чекбоксах", authenticated_page)
    save_btn.click()
    # Шаг №4: Проверяем появление модального окна об успешном сохранении
    modal = authenticated_page.locator('div[role="dialog"] div.cdm-card._without-margin')
    modal.wait_for(state="visible", timeout=5000)
    if not modal.locator('div', has_text="Шаблон test успешно сохранен").nth(0).is_visible():
        fail_with_screenshot("Модальное окно с текстом 'Шаблон test успешно сохранен' не появилось", authenticated_page)
    # Шаг №5: Проверяем, что кнопки "Закрыть" и "OK" кликабельны
    close_btn = modal.locator('button span.cdm-icon-wrapper[title="Закрыть"]')
    ok_btn = authenticated_page.get_by_role("button", name="OK")
    if not close_btn.is_visible():
        fail_with_screenshot("Кнопка-крестик 'Закрыть' не найдена в модальном окне", authenticated_page)
    if not ok_btn.is_visible():
        fail_with_screenshot("Кнопка 'OK' не найдена в модальном окне", authenticated_page)
    # Шаг №6: Закрываем окно по крестику
    close_btn.click()
    modal.wait_for(state="hidden", timeout=5000)
    # Шаг №7: Проверяем, что появилась радиокнопка "Создать по шаблону" и она выбрана
    radio_template_based = authenticated_page.locator('input[name="mode"][value="template-based"]')
    if not radio_template_based.is_visible():
        fail_with_screenshot("Радиокнопка 'Создать по шаблону' не найдена", authenticated_page)
    if not radio_template_based.is_checked():
        fail_with_screenshot("Радиокнопка 'Создать по шаблону' должна быть выбрана после создания шаблона", authenticated_page)
    # Шаг №8: Проверяем, что появился селект с шаблоном 'test'
    select_template = authenticated_page.locator('div.MuiSelect-root[role="button"]#templateId')
    if not select_template.is_visible():
        fail_with_screenshot("Селект выбора шаблона не найден", authenticated_page)
    if "test" not in select_template.inner_text():
        fail_with_screenshot("В селекте не найден шаблон 'test'", authenticated_page)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_create_report_create_new_template_test2(authenticated_page: Page, credentials):
    """
    Переключает радиокнопку на "Создать новый шаблон", создаёт шаблон с названием 'new_template', проверяет появление модального окна и наличие шаблона в селекте.
    """
    # Шаг 0: Обновляем страницу для сброса состояния
    authenticated_page.context.clear_cookies()
    authenticated_page.reload()
    # Шаг 1: Переключаем радиокнопку на "Создать новый шаблон"
    radio_new_template = authenticated_page.locator('input[name="mode"][value="new-template"]')
    radio_new_template.wait_for(state='visible', timeout=5000)
    if not radio_new_template.is_visible():
        fail_with_screenshot("Радиокнопка 'Создать новый шаблон' не найдена", authenticated_page)
    radio_new_template.check()
    if not radio_new_template.is_checked():
        fail_with_screenshot("Радиокнопка 'Создать новый шаблон' не выбрана после переключения", authenticated_page)
    # Шаг 2: Включаем все чекбоксы
    checkbox_labels = [
        "Сводный трафик по угрозам",
        "Дифференциальный трафик по угрозам",
        "Таблица \"Топ 10\""
    ]
    for label in checkbox_labels:
        checkbox = authenticated_page.get_by_label(label)
        if not checkbox.is_checked():
            checkbox.check()
        if not checkbox.is_checked():
            fail_with_screenshot(f'Чекбокс "{label}" должен быть включён для сохранения шаблона', authenticated_page)
    # Шаг 3: Вводим название шаблона 'new_template'
    input_field = find_input_by_label(authenticated_page, "Название шаблона", "new_template")
    # Шаг 4: Нажимаем кнопку "Сохранить шаблон"
    save_btn = authenticated_page.get_by_role("button", name="Сохранить шаблон")
    save_btn.click()
    # Шаг 5: Проверяем появление модального окна
    modal = authenticated_page.locator('div[role="dialog"] div.cdm-card._without-margin')
    modal.wait_for(state="visible", timeout=5000)
    if not modal.locator('div[style*="font-weight: bold"]', has_text="Шаблон new_template успешно сохранен").nth(0).is_visible():
        fail_with_screenshot('В модальном окне не найден заголовок "Шаблон new_template успешно сохранен"', authenticated_page)
    if not modal.locator('.MuiCardContent-root', has_text="Данный шаблон теперь будет доступен в списке шаблонов").nth(0).is_visible():
        fail_with_screenshot('В модальном окне не найден текст "Данный шаблон теперь будет доступен в списке шаблонов"', authenticated_page)
    # Шаг 6: Проверяем наличие кнопок "Закрыть" и "OK"
    close_btn = authenticated_page.get_by_role("button", name="Закрыть")
    ok_btn = authenticated_page.get_by_role("button", name="OK")    
    if not close_btn.is_visible():
        fail_with_screenshot('Кнопка "Закрыть" не найдена в модальном окне', authenticated_page)
    if not ok_btn.is_visible():
        fail_with_screenshot('Кнопка "OK" не найдена в модальном окне', authenticated_page)
    # Шаг 7: Нажимаем "OK"
    ok_btn.click()
    modal.wait_for(state="hidden", timeout=5000)
    # Шаг 8: Проверяем, что шаблон 'new_template' появился в селекте
    radio_template_based = authenticated_page.locator('input[name="mode"][value="template-based"]')
    radio_template_based.check()
    select_template = authenticated_page.locator('div#templateId[role="button"]')
    if not select_template.is_visible():
        fail_with_screenshot("Селект выбора шаблона не найден после создания шаблона", authenticated_page)
    select_template.click(force=True)
    menu = authenticated_page.locator('ul.MuiMenu-list[role="listbox"]')
    if not menu.locator('li', has_text="new_template").is_visible():
        fail_with_screenshot('Шаблон "new_template" не найден в выпадающем списке', authenticated_page)
    size = authenticated_page.viewport_size or authenticated_page.context.viewport_size
    if size:
        authenticated_page.mouse.click(size['width'] / 4, size['height'] / 4)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_mailing_navigate_and_check_url_3(authenticated_page: Page, credentials):
    """
    Проверяет переход на вкладку "Отчетность" в разделе "Аудит безопасности" и корректность URL для "Рассылка отчетов".
    """
    tab_button_1 = "Аудит безопасности"
    tab_button_2 = "Отчетность"
    tab_target = "Рассылка отчетов"
    url = "security-audit/reports/mailing"
    navigate_and_check_url_with_tab(authenticated_page, tab_button_1, tab_button_2, tab_target, url, credentials)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_mailing_create_button_visible_and_hint_absent(authenticated_page: Page, credentials):
    """
    Проверяет, что надпись 'Для создания рассылки требуется создать шаблон' отсутствует, а кнопка 'Создать' отображается и кликабельна.
    """
    # Шаг №1: Проверяем, что надпись отсутствует (вариант 3)
    hint = authenticated_page.get_by_text("Для создания рассылки требуется создать шаблон")
    if hint.count() > 0:
        for i in range(hint.count()):
            if hint.nth(i).is_visible():
                fail_with_screenshot('Надпись "Для создания рассылки требуется создать шаблон" должна быть скрыта', authenticated_page)
    # Шаг №2: Находим контейнер с кнопкой 'Создать' и саму кнопку
    container = authenticated_page.locator('div.MuiCardActions-root', has=authenticated_page.get_by_role("button", name="Создать"))
    if not container.is_visible(timeout=5000):
        fail_with_screenshot("Элемент не видим", authenticated_page)
    create_btn = container.get_by_role("button", name="Создать")
    # Шаг №3: Проверяем, что кнопка видима и кликабельна
    if not create_btn.is_visible():
        fail_with_screenshot('Кнопка "Создать" не отображается на странице', authenticated_page)
    if not create_btn.is_enabled():
        fail_with_screenshot('Кнопка "Создать" неактивна (не кликабельна)', authenticated_page)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_mailing_empty_table_and_create_row_elements(authenticated_page: Page, credentials):
    """
    Проверяет, что в таблице нет строк и отображается надпись 'Нет данных', затем после клика по 'Создать' появляется таблица с нужными колонками и элементами для ввода.
    """
    # Шаг №1: Явно ждём появления контейнера таблицы (5 секунд)
    if not authenticated_page.locator('div.cdm-list__grid-box').is_visible(timeout=5000):
        fail_with_screenshot("Таблица не видна", authenticated_page)
    # Шаг №2: Проверяем, что отображается надпись 'Нет данных'
    empty_message = authenticated_page.locator('div.cdm-data-grid__empty-message', has_text="Нет данных")
    if not empty_message.is_visible():
        fail_with_screenshot('Надпись "Нет данных" не отображается при пустой таблице', authenticated_page)
    # Шаг №3: Кликаем по кнопке 'Создать'
    create_btn = authenticated_page.get_by_role("button", name="Создать")
    if not create_btn.is_visible() or not create_btn.is_enabled():
        fail_with_screenshot('Кнопка "Создать" не отображается или неактивна', authenticated_page)
    create_btn.click()
    # Шаг №4: Проверяем, что появилась таблица с нужными колонками
    table = authenticated_page.locator('table.cdm-data-grid')
    if not table.is_visible():
        fail_with_screenshot('Таблица не появилась после нажатия "Создать"', authenticated_page)
    headers = [
        "Рассылка",
        "Активна",
        "Шаблон",
        "Периодичность",
        "E-mail"
    ]
    for header in headers:
        th = table.locator('th', has_text=header)
        if not th.is_visible():
            fail_with_screenshot(f'Колонка "{header}" не отображается в таблице', authenticated_page)
    # Шаг №5: Проверяем элементы для ввода в первой строке
    row = table.locator('tbody tr').first
    # Рассылка: input
    mailing_input = row.locator('td').nth(0).locator('input[type="text"]')
    if not mailing_input.is_visible():
        fail_with_screenshot('В колонке "Рассылка" нет input для ввода', authenticated_page)
    # Активна: чекбокс
    active_checkbox = row.locator('td').nth(1).locator('input[type="checkbox"]')
    if not active_checkbox.is_visible():
        fail_with_screenshot('В колонке "Активна" нет чекбокса', authenticated_page)
    # Шаблон: селект (role="button")
    template_select = row.locator('td').nth(2).locator('[role="button"]')
    if not template_select.is_visible():
        fail_with_screenshot('В колонке "Шаблон" нет селекта', authenticated_page)
    # Периодичность: input
    period_input = row.locator('td').nth(3).locator('input[type="text"]')
    if not period_input.is_visible():
        fail_with_screenshot('В колонке "Периодичность" нет input для ввода', authenticated_page)
    # Адреса: input
    address_input = row.locator('td').nth(4).locator('input[type="text"]')
    if not address_input.is_visible():
        fail_with_screenshot('В колонке "Адреса" нет input для ввода', authenticated_page)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_mailing_create_row_fill_fields(authenticated_page: Page, credentials):
    """
    Заполняет строку рассылки: вводит имя, включает чекбокс, вводит периодичность и email, проверяет значения.
    Предполагает, что строка для заполнения уже создана предыдущим тестом.
    """
    # Шаг №1: Ждём появления таблицы
    expect(authenticated_page.locator('div.cdm-list__grid-box')).to_be_visible(timeout=5000)
    # Шаг №2: Находим первую строку для ввода
    table = authenticated_page.locator('table.cdm-data-grid')
    row = table.locator('tbody tr').first
    # Шаг №3: Заполняем поле "Рассылка"
    mailing_input = row.locator('td').nth(0).locator('input[type="text"]')
    mailing_input.fill('test_mail')
    if mailing_input.input_value() != 'test_mail':
        fail_with_screenshot('Поле "Рассылка" не заполнено значением test_mail', authenticated_page)
    # Шаг №4: Включаем чекбокс "Активна"
    active_checkbox = row.locator('td').nth(1).locator('input[type="checkbox"]')
    if not active_checkbox.is_checked():
        active_checkbox.check()
    if not active_checkbox.is_checked():
        fail_with_screenshot('Чекбокс "Активна" не включился', authenticated_page)
    # Шаг №5: Выбираем шаблон 'test' в селекте
    template_select = row.locator('td').nth(2).locator('[role="button"]')
    template_select.click()
    menu = authenticated_page.locator('ul[role="listbox"]')
    option = menu.locator('li', has_text="test")
    if not option.is_visible():
        fail_with_screenshot('Шаблон "test" не найден в выпадающем списке', authenticated_page)
    option.click()
    # Проверяем, что селект теперь отображает 'test'
    if "test" not in template_select.inner_text():
        fail_with_screenshot('Селект не отобразил выбранное значение "test"', authenticated_page)
    # Шаг №6: Вводим периодичность (cron)
    period_input = row.locator('td').nth(3).locator('input[type="text"]')
    period_input.fill('0 * * * *')
    if period_input.input_value() != '0 * * * *':
        fail_with_screenshot('Поле "Периодичность" не заполнено значением 0 * * * *', authenticated_page)
    # Шаг №7: Вводим email
    address_input = row.locator('td').nth(4).locator('input[type="text"]')
    address_input.fill(credentials["email"])
    if address_input.input_value() != credentials["email"]:
        fail_with_screenshot(f'Поле "Адреса" не заполнено email {credentials["email"]}', authenticated_page)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_mailing_save_row_and_check_display(authenticated_page: Page, credentials):
    """
    Нажимает на кнопку "Сохранить" в уже заполненной строке с рассылкой 'test_mail' и проверяет, что все значения отображаются корректно.
    """
    # Шаг №1: Находим редактируемую строку
    table = authenticated_page.locator('table.cdm-data-grid')
    row = find_row_with_input(table, "test_mail") or find_row_with_input(table)
    if row is None:
        fail_with_screenshot("Не найдена редактируемая строка с нужным input", authenticated_page)
    # Шаг №2: Нажимаем на кнопку "Сохранить"
    save_btn = row.locator('button:has(span[title="Сохранить"])')
    save_btn.wait_for(state='visible', timeout=5000)
    if not save_btn.is_visible() or not save_btn.is_enabled():
        fail_with_screenshot('Кнопка "Сохранить" не отображается или неактивна', authenticated_page)
    save_btn.click()
    # Шаг №3: Ждём исчезновения input (редактируемая строка)
    input_locator = table.locator('input[type="text"][value="test_mail"]')
    input_locator.wait_for(state='detached', timeout=5000)
    # Шаг №4: Явно ждём появления строки с текстом (уже сохранённая строка)
    row_locator = table.locator('tbody tr', has_text="test_mail")
    row_locator.wait_for(state='visible', timeout=5000)
    # Шаг №5: Теперь ищем строку по тексту
    row = find_row_by_text(table, "test_mail")
    if row is None:
        fail_with_screenshot('Не найдена строка с текстом "test_mail" после сохранения', authenticated_page)
    # Шаг №6: Проверяем значения в сохранённой строке
    mailing_cell = row.locator('td').nth(0)
    if 'test_mail' not in mailing_cell.inner_text():
        fail_with_screenshot('В ячейке "Рассылка" не отображается значение test_mail', authenticated_page)
    # Проверяем "Активна" (теперь это текст "Да")
    active_cell = row.locator('td').nth(1)
    if 'Да' not in active_cell.inner_text():
        fail_with_screenshot('В ячейке "Активна" не отображается значение "Да" после сохранения', authenticated_page)
    # Проверяем "Шаблон"
    template_cell = row.locator('td').nth(2)
    if 'test' not in template_cell.inner_text():
        fail_with_screenshot('В ячейке "Шаблон" не отображается значение test', authenticated_page)
    # Проверяем "Периодичность"
    period_cell = row.locator('td').nth(3)
    if '0 * * * *' not in period_cell.inner_text():
        fail_with_screenshot('В ячейке "Периодичность" не отображается значение 0 * * * *', authenticated_page)
    # Проверяем email
    address_cell = row.locator('td').nth(4)
    if credentials["email"] not in address_cell.inner_text():
        fail_with_screenshot(f'В ячейке "Адреса" не отображается email {credentials["email"]}', authenticated_page)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_mailing_create_row_elements(authenticated_page: Page, credentials):
    """
    Проверяет, что после клика по 'Создать' появляется таблица с нужными колонками и элементами для ввода.
    """
    # Шаг №1: Кликаем по кнопке 'Создать'
    create_btn = authenticated_page.get_by_role("button", name="Создать")
    if not create_btn.is_visible() or not create_btn.is_enabled():
        fail_with_screenshot('Кнопка "Создать" не отображается или неактивна', authenticated_page)
    create_btn.click()
    # Шаг №4: Проверяем, что появилась таблица с нужными колонками
    table = authenticated_page.locator('table.cdm-data-grid')
    if not table.is_visible():
        fail_with_screenshot('Таблица не появилась после нажатия "Создать"', authenticated_page)
    headers = [
        "Рассылка",
        "Активна",
        "Шаблон",
        "Периодичность",
        "E-mail"
    ]
    for header in headers:
        th = table.locator('th', has_text=header)
        if not th.is_visible():
            fail_with_screenshot(f'Колонка "{header}" не отображается в таблице', authenticated_page)
    # Шаг №5: Проверяем элементы для ввода в первой строке
    row = table.locator('tbody tr').first
    # Рассылка: input
    mailing_input = row.locator('td').nth(0).locator('input[type="text"]')
    if not mailing_input.is_visible():
        fail_with_screenshot('В колонке "Рассылка" нет input для ввода', authenticated_page)
    # Активна: чекбокс
    active_checkbox = row.locator('td').nth(1).locator('input[type="checkbox"]')
    if not active_checkbox.is_visible():
        fail_with_screenshot('В колонке "Активна" нет чекбокса', authenticated_page)
    # Шаблон: селект (role="button")
    template_select = row.locator('td').nth(2).locator('[role="button"]')
    if not template_select.is_visible():
        fail_with_screenshot('В колонке "Шаблон" нет селекта', authenticated_page)
    # Периодичность: input
    period_input = row.locator('td').nth(3).locator('input[type="text"]')
    if not period_input.is_visible():
        fail_with_screenshot('В колонке "Периодичность" нет input для ввода', authenticated_page)
    # Адреса: input
    address_input = row.locator('td').nth(4).locator('input[type="text"]')
    if not address_input.is_visible():
        fail_with_screenshot('В колонке "Адреса" нет input для ввода', authenticated_page)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_mailing_create_second_row_fill_fields(authenticated_page: Page, credentials):
    """
    Заполняет строку рассылки: вводит имя, включает чекбокс, вводит периодичность и email, проверяет значения.
    Предполагает, что строка для заполнения уже создана предыдущим тестом.
    """
    # Шаг №1: Ждём появления таблицы
    expect(authenticated_page.locator('div.cdm-list__grid-box')).to_be_visible(timeout=5000)
    # Шаг №2: Находим первую строку для ввода
    table = authenticated_page.locator('table.cdm-data-grid')
    row = table.locator('tbody tr').first
    # Шаг №3: Заполняем поле "Рассылка"
    mailing_input = row.locator('td').nth(0).locator('input[type="text"]')
    mailing_input.fill('new_mail_test')
    if mailing_input.input_value() != 'new_mail_test':
        fail_with_screenshot('Поле "Рассылка" не заполнено значением new_mail_test', authenticated_page)
    # Шаг №4: Включаем чекбокс "Активна"
    active_checkbox = row.locator('td').nth(1).locator('input[type="checkbox"]')
    if not active_checkbox.is_checked():
        active_checkbox.check()
    if not active_checkbox.is_checked():
        fail_with_screenshot('Чекбокс "Активна" не включился', authenticated_page)
    # Шаг №5: Выбираем шаблон 'test' в селекте
    template_select = row.locator('td').nth(2).locator('[role="button"]')
    template_select.click()
    menu = authenticated_page.locator('ul[role="listbox"]')
    option = menu.locator('li', has_text="new_template")
    if not option.is_visible():
        fail_with_screenshot('Шаблон "new_template" не найден в выпадающем списке', authenticated_page)
    option.click()
    # Проверяем, что селект теперь отображает 'test'
    if "new_template" not in template_select.inner_text():
        fail_with_screenshot('Селект не отобразил выбранное значение "new_template"', authenticated_page)
    # Шаг №6: Вводим периодичность (cron)
    period_input = row.locator('td').nth(3).locator('input[type="text"]')
    period_input.fill('0 * * * *')
    if period_input.input_value() != '0 * * * *':
        fail_with_screenshot('Поле "Периодичность" не заполнено значением 0 * * * *', authenticated_page)
    # Шаг №7: Вводим email
    address_input = row.locator('td').nth(4).locator('input[type="text"]')
    address_input.fill(credentials["email"])
    if address_input.input_value() != credentials["email"]:
        fail_with_screenshot(f'Поле "Адреса" не заполнено email {credentials["email"]}', authenticated_page)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_mailing_cancel_row_removes_row(authenticated_page: Page, credentials):
    """
    Проверяет, что после нажатия на крестик (Отмена) редактируемая строка с рассылкой 'test_mail' исчезает из таблицы.
    """
    # Шаг №1: Находим редактируемую строку
    table = authenticated_page.locator('table.cdm-data-grid')
    row = find_row_with_input(table, "test_mail") or find_row_with_input(table)
    if row is None:
        fail_with_screenshot("Не найдена редактируемая строка с нужным input", authenticated_page)
    # Шаг №2: Находим кнопку "Отмена" (крестик)
    cancel_btn = row.locator('button:has(span[title="Отмена"])')
    cancel_btn.wait_for(state='visible', timeout=5000)
    if not cancel_btn.is_visible():
        fail_with_screenshot('Кнопка "Отмена" (крестик) не найдена в строке', authenticated_page)
    # Шаг №3: Кликаем по крестику
    cancel_btn.click()
    # Шаг №4: Проверяем, что редактируемая строка исчезла
    if find_row_with_input(table, "test_mail") is not None:
        fail_with_screenshot('Редактируемая строка не исчезла после нажатия на крестик', authenticated_page)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_mailing_third_create_row_elements(authenticated_page: Page, credentials):
    """
    Проверяет, что после клика по 'Создать' появляется таблица с нужными колонками и элементами для ввода.
    """
    # Шаг №1: Кликаем по кнопке 'Создать'
    create_btn = authenticated_page.get_by_role("button", name="Создать")
    if not create_btn.is_visible() or not create_btn.is_enabled():
        fail_with_screenshot('Кнопка "Создать" не отображается или неактивна', authenticated_page)
    create_btn.click()
    # Шаг №4: Проверяем, что появилась таблица с нужными колонками
    table = authenticated_page.locator('table.cdm-data-grid')
    if not table.is_visible():
        fail_with_screenshot('Таблица не появилась после нажатия "Создать"', authenticated_page)
    headers = [
        "Рассылка",
        "Активна",
        "Шаблон",
        "Периодичность",
        "E-mail"
    ]
    for header in headers:
        th = table.locator('th', has_text=header)
        if not th.is_visible():
            fail_with_screenshot(f'Колонка "{header}" не отображается в таблице', authenticated_page)
    # Шаг №5: Проверяем элементы для ввода в первой строке
    row = table.locator('tbody tr').first
    # Рассылка: input
    mailing_input = row.locator('td').nth(0).locator('input[type="text"]')
    if not mailing_input.is_visible():
        fail_with_screenshot('В колонке "Рассылка" нет input для ввода', authenticated_page)
    # Активна: чекбокс
    active_checkbox = row.locator('td').nth(1).locator('input[type="checkbox"]')
    if not active_checkbox.is_visible():
        fail_with_screenshot('В колонке "Активна" нет чекбокса', authenticated_page)
    # Шаблон: селект (role="button")
    template_select = row.locator('td').nth(2).locator('[role="button"]')
    if not template_select.is_visible():
        fail_with_screenshot('В колонке "Шаблон" нет селекта', authenticated_page)
    # Периодичность: input
    period_input = row.locator('td').nth(3).locator('input[type="text"]')
    if not period_input.is_visible():
        fail_with_screenshot('В колонке "Периодичность" нет input для ввода', authenticated_page)
    # Адреса: input
    address_input = row.locator('td').nth(4).locator('input[type="text"]')
    if not address_input.is_visible():
        fail_with_screenshot('В колонке "Адреса" нет input для ввода', authenticated_page)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_mailing_empty_row_validation(authenticated_page: Page, credentials):
    """
    Нажимает на кнопку "Сохранить" в не заполненной строке проверяет, что отображается валидация "Заполните поле".
    """
    # Шаг №1: Находим редактируемую строку
    table = authenticated_page.locator('table.cdm-data-grid')
    row = find_row_with_input(table, "new_mail_test") or find_row_with_input(table)
    if row is None:
        fail_with_screenshot("Не найдена редактируемая строка с нужным input", authenticated_page)
    # Шаг №2: Нажимаем на кнопку "Сохранить" не заполняя поля
    save_btn = row.locator('button:has(span[title="Сохранить"])')
    save_btn.wait_for(state='visible', timeout=15000)
    save_btn.click()
    # Шаг №3: Проверяем наличие подсказок 'Заполните поле' под каждым обязательным полем
    # Рассылка
    mailing_hint = row.locator('td').nth(0).locator('p.MuiFormHelperText-root.Mui-error')
    if not (mailing_hint.is_visible() and 'Заполните поле' in mailing_hint.inner_text()):
        fail_with_screenshot('Нет подсказки "Заполните поле" под полем "Рассылка"', authenticated_page)
    # Шаблон
    template_hint = row.locator('td').nth(2).locator('p.MuiFormHelperText-root.Mui-error')
    if not (template_hint.is_visible() and 'Заполните поле' in template_hint.inner_text()):
        fail_with_screenshot('Нет подсказки "Заполните поле" под полем "Шаблон"', authenticated_page)
    # Периодичность
    period_hint = row.locator('td').nth(3).locator('p.MuiFormHelperText-root.Mui-error')
    if not (period_hint.is_visible() and 'Заполните поле' in period_hint.inner_text()):
        fail_with_screenshot('Нет подсказки "Заполните поле" под полем "Периодичность"', authenticated_page)
    # Адреса
    address_hint = row.locator('td').nth(4).locator('p.MuiFormHelperText-root.Mui-error')
    if not (address_hint.is_visible() and 'Заполните поле' in address_hint.inner_text()):
        fail_with_screenshot('Нет подсказки "Заполните поле" под полем "Адреса"', authenticated_page)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_mailing_create_third_row_fill_fields(authenticated_page: Page, credentials):
    """
    Заполняет строку рассылки: вводит имя, включает чекбокс, вводит периодичность и email, проверяет значения.
    Предполагает, что строка для заполнения уже создана предыдущим тестом.
    """
    # Шаг №1: Ждём появления таблицы
    expect(authenticated_page.locator('div.cdm-list__grid-box')).to_be_visible(timeout=5000)
    # Шаг №2: Находим первую строку для ввода
    table = authenticated_page.locator('table.cdm-data-grid')
    row = table.locator('tbody tr').first
    # Шаг №3: Заполняем поле "Рассылка"
    mailing_input = row.locator('td').nth(0).locator('input[type="text"]')
    mailing_input.fill('new_mail_test')
    if mailing_input.input_value() != 'new_mail_test':
        fail_with_screenshot('Поле "Рассылка" не заполнено значением new_mail_test', authenticated_page)
    # Шаг №4: Включаем чекбокс "Активна"
    active_checkbox = row.locator('td').nth(1).locator('input[type="checkbox"]')
    if not active_checkbox.is_checked():
        active_checkbox.check()
    if not active_checkbox.is_checked():
        fail_with_screenshot('Чекбокс "Активна" не включился', authenticated_page)
    # Шаг №5: Выбираем шаблон 'new_template' в селекте
    template_select = row.locator('td').nth(2).locator('[role="button"]')
    template_select.click()
    menu = authenticated_page.locator('ul[role="listbox"]')
    option = menu.locator('li', has_text="new_template")
    if not option.is_visible():
        fail_with_screenshot('Шаблон "new_template" не найден в выпадающем списке', authenticated_page)
    option.click()
    # Проверяем, что селект теперь отображает 'new_template'
    if "new_template" not in template_select.inner_text():
        fail_with_screenshot('Селект не отобразил выбранное значение "new_template"', authenticated_page)
    # Шаг №6: Вводим периодичность (cron)
    period_input = row.locator('td').nth(3).locator('input[type="text"]')
    period_input.fill('0 * * * *')
    if period_input.input_value() != '0 * * * *':
        fail_with_screenshot('Поле "Периодичность" не заполнено значением 0 * * * *', authenticated_page)
    # Шаг №7: Вводим email
    address_input = row.locator('td').nth(4).locator('input[type="text"]')
    address_input.fill(credentials["email"])
    if address_input.input_value() != credentials["email"]:
        fail_with_screenshot(f'Поле "Адреса" не заполнено email {credentials["email"]}', authenticated_page)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_mailing_save_row_and_check_display_2(authenticated_page: Page, credentials):
    """
    Нажимает на кнопку "Сохранить" в уже заполненной строке с рассылкой 'test_mail' и проверяет, что все значения отображаются корректно.
    """
    # Шаг №1: Находим редактируемую строку
    table = authenticated_page.locator('table.cdm-data-grid')
    row = find_row_with_input(table, "test_mail") or find_row_with_input(table)
    if row is None:
        fail_with_screenshot("Не найдена редактируемая строка с нужным input", authenticated_page)
    # Шаг №2: Нажимаем на кнопку "Сохранить"
    save_btn = row.locator('button:has(span[title="Сохранить"])')
    save_btn.wait_for(state='visible', timeout=5000)
    if not save_btn.is_visible() or not save_btn.is_enabled():
        fail_with_screenshot('Кнопка "Сохранить" не отображается или неактивна', authenticated_page)
    save_btn.click()
    # Шаг №3: Ждём появления строки с текстом "new_mail_test" (уже сохранённая строка)
    row_locator = table.locator('tbody tr', has_text="new_mail_test")
    row_locator.wait_for(state='visible', timeout=5000)
    # Шаг №4: Проверяем значения в сохранённой строке
    row = find_row_by_text(table, "new_mail_test")
    if row is None:
        fail_with_screenshot('Не найдена строка с текстом "new_mail_test" после сохранения', authenticated_page)
    mailing_cell = row.locator('td').nth(0)
    if 'new_mail_test' not in mailing_cell.inner_text():
        fail_with_screenshot('В ячейке "Рассылка" не отображается значение new_mail_test', authenticated_page)
    # Проверяем "Активна" (теперь это текст "Да")
    active_cell = row.locator('td').nth(1)
    if 'Да' not in active_cell.inner_text():
        fail_with_screenshot('В ячейке "Активна" не отображается значение "Да" после сохранения', authenticated_page)
    # Проверяем "Шаблон"
    template_cell = row.locator('td').nth(2)
    if 'new_template' not in template_cell.inner_text():
        fail_with_screenshot('В ячейке "Шаблон" не отображается значение new_template', authenticated_page)
    # Проверяем "Периодичность"
    period_cell = row.locator('td').nth(3)
    if '0 * * * *' not in period_cell.inner_text():
        fail_with_screenshot('В ячейке "Периодичность" не отображается значение 0 * * * *', authenticated_page)
    # Проверяем email
    address_cell = row.locator('td').nth(4)
    if credentials["email"] not in address_cell.inner_text():
        fail_with_screenshot(f'В ячейке "Адреса" не отображается email {credentials["email"]}', authenticated_page)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_mailing_edit_row_fields_enabled(authenticated_page: Page, credentials):
    """
    Проверяет, что после нажатия на кнопку "Изменить" в строке с рассылкой 'test_mail' все колонки становятся доступны для редактирования.
    """
    # Шаг №1: Находим строку с рассылкой 'test_mail'
    table = authenticated_page.locator('table.cdm-data-grid')
    row = find_row_by_text(table, "test_mail")
    if row is None:
        fail_with_screenshot('Не найдена строка с рассылкой "test_mail" для редактирования', authenticated_page)
    # Шаг №2: Находим и нажимаем кнопку "Изменить"
    edit_btn = row.locator('button:has(span[title="Изменить"])')
    edit_btn.wait_for(state='visible', timeout=5000)
    if not edit_btn.is_visible() or not edit_btn.is_enabled():
        fail_with_screenshot('Кнопка "Изменить" не отображается или неактивна', authenticated_page)
    edit_btn.click()
    # Шаг №3: Проверяем, что все колонки стали доступны для редактирования
    # Рассылка: input
    mailing_input = row.locator('td').nth(0).locator('input[type="text"]')
    if not (mailing_input.is_visible() and mailing_input.is_enabled()):
        fail_with_screenshot('Поле "Рассылка" не доступно для редактирования', authenticated_page)
    # Активна: чекбокс
    active_checkbox = row.locator('td').nth(1).locator('input[type="checkbox"]')
    if not (active_checkbox.is_visible() and not active_checkbox.is_disabled()):
        fail_with_screenshot('Чекбокс "Активна" не доступен для редактирования', authenticated_page)
    # Шаблон: селект (role="button")
    template_select = row.locator('td').nth(2).locator('[role="button"]')
    if not (template_select.is_visible() and template_select.is_enabled()):
        fail_with_screenshot('Селект "Шаблон" не доступен для редактирования', authenticated_page)
    # Периодичность: input
    period_input = row.locator('td').nth(3).locator('input[type="text"]')
    if not (period_input.is_visible() and period_input.is_enabled()):
        fail_with_screenshot('Поле "Периодичность" не доступно для редактирования', authenticated_page)
    # Адреса: input
    address_input = row.locator('td').nth(4).locator('input[type="text"]')
    if not (address_input.is_visible() and address_input.is_enabled()):
        fail_with_screenshot('Поле "Адреса" не доступно для редактирования', authenticated_page)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_mailing_invalid_cron_validation(authenticated_page: Page, credentials):
    """
    Проверяет, что при вводе некорректного значения в поле 'Периодичность' появляется ошибка 'Неверный формат cron-строки'.
    """
    # Шаг №1: Находим редактируемую строку
    table = authenticated_page.locator('table.cdm-data-grid')
    row = find_editing_row(table)
    if row is None:
        fail_with_screenshot('Не найдена редактируемая строка для проверки', authenticated_page)
    # Шаг №2: Очищаем поле 'Периодичность' и вводим некорректное значение
    period_input = row.locator('td').nth(3).locator('input[type="text"]')
    period_input.fill("")
    period_input.fill("not_a_cron")
    # Шаг №3: Нажимаем на кнопку 'Сохранить'
    save_btn = row.locator('button:has(span[title="Сохранить"])')
    save_btn.wait_for(state='visible', timeout=5000)
    save_btn.click()
    # Шаг №4: Проверяем наличие ошибки
    period_hint = row.locator('td').nth(3).locator('p.MuiFormHelperText-root.Mui-error')
    if not (period_hint.is_visible() and 'Неверный формат cron-строки' in period_hint.inner_text()):
        fail_with_screenshot('Нет ошибки "Неверный формат cron-строки" под полем "Периодичность"', authenticated_page)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_mailing_invalid_email_validation(authenticated_page: Page, credentials):
    """
    Проверяет, что при вводе некорректного значения в поле 'Адреса' появляется ошибка 'E-mail неверный'.
    """
    # Шаг №1: Находим редактируемую строку
    table = authenticated_page.locator('table.cdm-data-grid')
    row = find_editing_row(table)
    if row is None:
        fail_with_screenshot('Не найдена редактируемая строка для проверки', authenticated_page)
    # Шаг №2: Очищаем поле 'Адреса' и вводим некорректный e-mail
    address_input = row.locator('td').nth(4).locator('input[type="text"]')
    address_input.fill("")
    address_input.fill("not-an-email")
    # Шаг №3: Нажимаем на кнопку 'Сохранить'
    save_btn = row.locator('button:has(span[title="Сохранить"])')
    save_btn.wait_for(state='visible', timeout=5000)
    save_btn.click()
    # Шаг №4: Проверяем наличие ошибки
    address_hint = row.locator('td').nth(4).locator('p.MuiFormHelperText-root.Mui-error')
    if not (address_hint.is_visible() and 'E-mail неверный' in address_hint.inner_text()):
        fail_with_screenshot('Нет ошибки "E-mail неверный" под полем "Адреса"', authenticated_page)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_mailing_empty_cron_validation(authenticated_page: Page, credentials):
    """
    Проверяет, что при пустом значении в поле 'Периодичность' появляется ошибка 'Неверный формат cron-строки'.
    """
    # Шаг №1: Находим редактируемую строку
    table = authenticated_page.locator('table.cdm-data-grid')
    row = find_editing_row(table)
    if row is None:
        fail_with_screenshot('Не найдена редактируемая строка для проверки', authenticated_page)
    # Шаг №2: Очищаем поле 'Периодичность' и вводим некорректное значение
    period_input = row.locator('td').nth(3).locator('input[type="text"]')
    period_input.fill("")
    period_input.fill("not_a_cron")
    # Шаг №3: Нажимаем на кнопку 'Сохранить'
    save_btn = row.locator('button:has(span[title="Сохранить"])')
    save_btn.wait_for(state='visible', timeout=5000)
    save_btn.click()
    # Шаг №4: Проверяем наличие ошибки
    period_hint = row.locator('td').nth(3).locator('p.MuiFormHelperText-root.Mui-error')
    if not (period_hint.is_visible() and 'Неверный формат cron-строки' in period_hint.inner_text()):
        fail_with_screenshot('Нет ошибки "Неверный формат cron-строки" под полем "Периодичность"', authenticated_page)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_mailing_short_cron_validation(authenticated_page: Page, credentials):
    """
    Проверяет, что при слишком коротком значении в поле 'Периодичность' появляется ошибка 'Неверный формат cron-строки'.
    """
    # Шаг №1: Находим редактируемую строку
    table = authenticated_page.locator('table.cdm-data-grid')
    row = find_editing_row(table)
    if row is None:
        fail_with_screenshot('Не найдена редактируемая строка для проверки', authenticated_page)
    # Шаг №2: Очищаем поле 'Периодичность' и вводим некорректное значение
    period_input = row.locator('td').nth(3).locator('input[type="text"]')
    period_input.fill("")
    period_input.fill("*")
    # Шаг №3: Нажимаем на кнопку 'Сохранить'
    save_btn = row.locator('button:has(span[title="Сохранить"])')
    save_btn.wait_for(state='visible', timeout=5000)
    save_btn.click()
    # Шаг №4: Проверяем наличие ошибки
    period_hint = row.locator('td').nth(3).locator('p.MuiFormHelperText-root.Mui-error')
    if not (period_hint.is_visible() and 'Неверный формат cron-строки' in period_hint.inner_text()):
        fail_with_screenshot('Нет ошибки "Неверный формат cron-строки" под полем "Периодичность"', authenticated_page)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_mailing_empty_email_validation(authenticated_page: Page, credentials):
    """
    Проверяет, что при пустом значении в поле 'Адреса' появляется ошибка 'E-mail неверный'.
    """
    # Шаг №1: Находим редактируемую строку
    table = authenticated_page.locator('table.cdm-data-grid')
    row = find_editing_row(table)
    if row is None:
        fail_with_screenshot('Не найдена редактируемая строка для проверки', authenticated_page)
    # Шаг №2: Очищаем поле 'Адреса' и вводим некорректный e-mail
    address_input = row.locator('td').nth(4).locator('input[type="text"]')
    address_input.fill("")
    address_input.fill("not-an-email")
    # Шаг №3: Нажимаем на кнопку 'Сохранить'
    save_btn = row.locator('button:has(span[title="Сохранить"])')
    save_btn.wait_for(state='visible', timeout=5000)
    save_btn.click()
    # Шаг №4: Проверяем наличие ошибки
    address_hint = row.locator('td').nth(4).locator('p.MuiFormHelperText-root.Mui-error')
    if not (address_hint.is_visible() and 'E-mail неверный' in address_hint.inner_text()):
        fail_with_screenshot('Нет ошибки "E-mail неверный" под полем "Адреса"', authenticated_page)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_mailing_invalid_email_no_at_validation(authenticated_page: Page, credentials):
    """
    Проверяет, что при вводе строки без @ в поле 'Адреса' появляется ошибка 'E-mail неверный'.
    """
    # Шаг №1: Находим редактируемую строку
    table = authenticated_page.locator('table.cdm-data-grid')
    row = find_editing_row(table)
    if row is None:
        fail_with_screenshot('Не найдена редактируемая строка для проверки', authenticated_page)
    # Шаг №2: Очищаем поле 'Адреса' и вводим некорректный e-mail
    address_input = row.locator('td').nth(4).locator('input[type="text"]')
    address_input.fill("")
    address_input.fill("invalidemail.com")
    # Шаг №3: Нажимаем на кнопку 'Сохранить'
    save_btn = row.locator('button:has(span[title="Сохранить"])')
    save_btn.wait_for(state='visible', timeout=5000)
    save_btn.click()
    # Шаг №4: Проверяем наличие ошибки
    address_hint = row.locator('td').nth(4).locator('p.MuiFormHelperText-root.Mui-error')
    if not (address_hint.is_visible() and 'E-mail неверный' in address_hint.inner_text()):
        fail_with_screenshot('Нет ошибки "E-mail неверный" под полем "Адреса" (без @)', authenticated_page)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_mailing_cron_with_letters_validation(authenticated_page: Page, credentials):
    """
    Проверяет, что при вводе значения с буквами в поле 'Периодичность' появляется ошибка 'Неверный формат cron-строки'.
    """
    table = authenticated_page.locator('table.cdm-data-grid')
    row = find_editing_row(table)
    if row is None:
        fail_with_screenshot('Не найдена редактируемая строка для проверки', authenticated_page)
    period_input = row.locator('td').nth(3).locator('input[type="text"]')
    period_input.fill('0 * * * abc')
    save_btn = row.locator('button:has(span[title="Сохранить"])')
    save_btn.wait_for(state='visible', timeout=5000)
    save_btn.click()
    period_hint = row.locator('td').nth(3).locator('p.MuiFormHelperText-root.Mui-error')
    if not (period_hint.is_visible() and 'Неверный формат cron-строки' in period_hint.inner_text()):
        fail_with_screenshot('Нет ошибки "Неверный формат cron-строки" под полем "Периодичность" (буквы)', authenticated_page)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_mailing_cron_wrong_fields_count_validation(authenticated_page: Page, credentials):
    """
    Проверяет, что при вводе cron-строки с неправильным количеством полей появляется ошибка 'Неверный формат cron-строки'.
    """
    table = authenticated_page.locator('table.cdm-data-grid')
    row = find_editing_row(table)
    if row is None:
        fail_with_screenshot('Не найдена редактируемая строка для проверки', authenticated_page)
    period_input = row.locator('td').nth(3).locator('input[type="text"]')
    period_input.fill('* * *')
    save_btn = row.locator('button:has(span[title="Сохранить"])')
    save_btn.wait_for(state='visible', timeout=5000)
    save_btn.click()
    period_hint = row.locator('td').nth(3).locator('p.MuiFormHelperText-root.Mui-error')
    if not (period_hint.is_visible() and 'Неверный формат cron-строки' in period_hint.inner_text()):
        fail_with_screenshot('Нет ошибки "Неверный формат cron-строки" под полем "Периодичность" (неправильное количество полей)', authenticated_page)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_mailing_invalid_email_no_domain_validation(authenticated_page: Page, credentials):
    """
    Проверяет, что при вводе email без домена в поле 'Адреса' появляется ошибка 'E-mail неверный'.
    """
    table = authenticated_page.locator('table.cdm-data-grid')
    row = find_editing_row(table)
    if row is None:
        fail_with_screenshot('Не найдена редактируемая строка для проверки', authenticated_page)
    address_input = row.locator('td').nth(4).locator('input[type="text"]')
    address_input.fill('test@')
    save_btn = row.locator('button:has(span[title="Сохранить"])')
    save_btn.wait_for(state='visible', timeout=5000)
    save_btn.click()
    address_hint = row.locator('td').nth(4).locator('p.MuiFormHelperText-root.Mui-error')
    if not (address_hint.is_visible() and 'E-mail неверный' in address_hint.inner_text()):
        fail_with_screenshot('Нет ошибки "E-mail неверный" под полем "Адреса" (без домена)', authenticated_page)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_mailing_invalid_email_with_space_validation(authenticated_page: Page, credentials):
    """
    Проверяет, что при вводе email с пробелом в поле 'Адреса' появляется ошибка 'E-mail неверный'.
    """
    table = authenticated_page.locator('table.cdm-data-grid')
    row = find_editing_row(table)
    if row is None:
        fail_with_screenshot('Не найдена редактируемая строка для проверки', authenticated_page)
    address_input = row.locator('td').nth(4).locator('input[type="text"]')
    address_input.fill('test @mail.com')
    save_btn = row.locator('button:has(span[title="Сохранить"])')
    save_btn.wait_for(state='visible', timeout=5000)
    save_btn.click()
    address_hint = row.locator('td').nth(4).locator('p.MuiFormHelperText-root.Mui-error')
    if not (address_hint.is_visible() and 'E-mail неверный' in address_hint.inner_text()):
        fail_with_screenshot('Нет ошибки "E-mail неверный" под полем "Адреса" (с пробелом)', authenticated_page)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_mailing_invalid_email_multiple_at_validation(authenticated_page: Page, credentials):
    """
    Проверяет, что при вводе email с несколькими @ в поле 'Адреса' появляется ошибка 'E-mail неверный'.
    """
    table = authenticated_page.locator('table.cdm-data-grid')
    row = find_editing_row(table)
    if row is None:
        fail_with_screenshot('Не найдена редактируемая строка для проверки', authenticated_page)
    address_input = row.locator('td').nth(4).locator('input[type="text"]')
    address_input.fill('test@@mail.com')
    save_btn = row.locator('button:has(span[title="Сохранить"])')
    save_btn.wait_for(state='visible', timeout=5000)
    save_btn.click()
    address_hint = row.locator('td').nth(4).locator('p.MuiFormHelperText-root.Mui-error')
    if not (address_hint.is_visible() and 'E-mail неверный' in address_hint.inner_text()):
        fail_with_screenshot('Нет ошибки "E-mail неверный" под полем "Адреса" (несколько @)', authenticated_page)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_mailing_cron_out_of_range_minute(authenticated_page: Page, credentials):
    """
    Проверяет, что при вводе 60 минут в поле 'Периодичность' появляется ошибка 'Неверный формат cron-строки'.
    """
    # Шаг №1: Находим редактируемую строку
    table = authenticated_page.locator('table.cdm-data-grid')
    row = find_editing_row(table)
    if row is None:
        fail_with_screenshot('Не найдена редактируемая строка для проверки', authenticated_page)
    # Шаг №2: Вводим некорректное значение
    period_input = row.locator('td').nth(3).locator('input[type="text"]')
    period_input.fill('60 * * * *')
    # Шаг №3: Нажимаем на кнопку 'Сохранить'
    save_btn = row.locator('button:has(span[title="Сохранить"])')
    save_btn.wait_for(state='visible', timeout=5000)
    save_btn.click()
    # Шаг №4: Проверяем наличие ошибки
    period_hint = row.locator('td').nth(3).locator('p.MuiFormHelperText-root.Mui-error')
    if not (period_hint.is_visible() and 'Неверный формат cron-строки' in period_hint.inner_text()):
        fail_with_screenshot('Нет ошибки "Неверный формат cron-строки" под полем "Периодичность" (60 минут)', authenticated_page)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_mailing_cron_out_of_range_hour(authenticated_page: Page, credentials):
    """
    Проверяет, что при вводе 25 часов в поле 'Периодичность' появляется ошибка 'Неверный формат cron-строки'.
    """
    # Шаг №1: Находим редактируемую строку
    table = authenticated_page.locator('table.cdm-data-grid')
    row = find_editing_row(table)
    if row is None:
        fail_with_screenshot('Не найдена редактируемая строка для проверки', authenticated_page)
    # Шаг №2: Вводим некорректное значение
    period_input = row.locator('td').nth(3).locator('input[type="text"]')
    period_input.fill('* 25 * * *')
    # Шаг №3: Нажимаем на кнопку 'Сохранить'
    save_btn = row.locator('button:has(span[title="Сохранить"])')
    save_btn.wait_for(state='visible', timeout=5000)
    save_btn.click()
    # Шаг №4: Проверяем наличие ошибки
    period_hint = row.locator('td').nth(3).locator('p.MuiFormHelperText-root.Mui-error')
    if not (period_hint.is_visible() and 'Неверный формат cron-строки' in period_hint.inner_text()):
        fail_with_screenshot('Нет ошибки "Неверный формат cron-строки" под полем "Периодичность" (25 часов)', authenticated_page)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_mailing_cron_out_of_range_day(authenticated_page: Page, credentials):
    """
    Проверяет, что при вводе 32 дня в поле 'Периодичность' появляется ошибка 'Неверный формат cron-строки'.
    """
    # Шаг №1: Находим редактируемую строку
    table = authenticated_page.locator('table.cdm-data-grid')
    row = find_editing_row(table)
    if row is None:
        fail_with_screenshot('Не найдена редактируемая строка для проверки', authenticated_page)
    # Шаг №2: Вводим некорректное значение
    period_input = row.locator('td').nth(3).locator('input[type="text"]')
    period_input.fill('* * 32 * *')
    # Шаг №3: Нажимаем на кнопку 'Сохранить'
    save_btn = row.locator('button:has(span[title="Сохранить"])')
    save_btn.wait_for(state='visible', timeout=5000)
    save_btn.click()
    # Шаг №4: Проверяем наличие ошибки
    period_hint = row.locator('td').nth(3).locator('p.MuiFormHelperText-root.Mui-error')
    if not (period_hint.is_visible() and 'Неверный формат cron-строки' in period_hint.inner_text()):
        fail_with_screenshot('Нет ошибки "Неверный формат cron-строки" под полем "Периодичность" (32 дня)', authenticated_page)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_mailing_cron_out_of_range_month(authenticated_page: Page, credentials):
    """
    Проверяет, что при вводе 13 месяца в поле 'Периодичность' появляется ошибка 'Неверный формат cron-строки'.
    """
    # Шаг №1: Находим редактируемую строку
    table = authenticated_page.locator('table.cdm-data-grid')
    row = find_editing_row(table)
    if row is None:
        fail_with_screenshot('Не найдена редактируемая строка для проверки', authenticated_page)
    # Шаг №2: Вводим некорректное значение
    period_input = row.locator('td').nth(3).locator('input[type="text"]')
    period_input.fill('* * * 13 *')
    # Шаг №3: Нажимаем на кнопку 'Сохранить'
    save_btn = row.locator('button:has(span[title="Сохранить"])')
    save_btn.wait_for(state='visible', timeout=5000)
    save_btn.click()
    # Шаг №4: Проверяем наличие ошибки
    period_hint = row.locator('td').nth(3).locator('p.MuiFormHelperText-root.Mui-error')
    if not (period_hint.is_visible() and 'Неверный формат cron-строки' in period_hint.inner_text()):
        fail_with_screenshot('Нет ошибки "Неверный формат cron-строки" под полем "Периодичность" (13 месяцев)', authenticated_page)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_mailing_cron_out_of_range_weekday(authenticated_page: Page, credentials):
    """
    Проверяет, что при вводе 8 дня недели в поле 'Периодичность' появляется ошибка 'Неверный формат cron-строки'.
    """
    # Шаг №1: Находим редактируемую строку
    table = authenticated_page.locator('table.cdm-data-grid')
    row = find_editing_row(table)
    if row is None:
        fail_with_screenshot('Не найдена редактируемая строка для проверки', authenticated_page)
    # Шаг №2: Вводим некорректное значение
    period_input = row.locator('td').nth(3).locator('input[type="text"]')
    period_input.fill('* * * * 8')
    # Шаг №3: Нажимаем на кнопку 'Сохранить'
    save_btn = row.locator('button:has(span[title="Сохранить"])')
    save_btn.wait_for(state='visible', timeout=5000)
    save_btn.click()
    # Шаг №4: Проверяем наличие ошибки
    period_hint = row.locator('td').nth(3).locator('p.MuiFormHelperText-root.Mui-error')
    if not (period_hint.is_visible() and 'Неверный формат cron-строки' in period_hint.inner_text()):
        fail_with_screenshot('Нет ошибки "Неверный формат cron-строки" под полем "Периодичность" (8 день недели)', authenticated_page)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_mailing_invalid_email_multiple_addresses_one_invalid(authenticated_page: Page, credentials):
    """
    Проверяет, что при вводе нескольких адресов через запятую, где один некорректный, появляется ошибка 'E-mail неверный'.
    """
    # Шаг №1: Находим редактируемую строку
    table = authenticated_page.locator('table.cdm-data-grid')
    row = find_editing_row(table)
    if row is None:
        fail_with_screenshot('Не найдена редактируемая строка для проверки', authenticated_page)
    # Шаг №2: Вводим несколько адресов, один из которых некорректный
    address_input = row.locator('td').nth(4).locator('input[type="text"]')
    address_input.fill('test@mail.com,not-an-email')
    # Шаг №3: Нажимаем на кнопку 'Сохранить'
    save_btn = row.locator('button:has(span[title="Сохранить"])')
    save_btn.wait_for(state='visible', timeout=5000)
    save_btn.click()
    # Шаг №4: Проверяем наличие ошибки
    address_hint = row.locator('td').nth(4).locator('p.MuiFormHelperText-root.Mui-error')
    if not (address_hint.is_visible() and 'E-mail неверный' in address_hint.inner_text()):
        fail_with_screenshot('Нет ошибки "E-mail неверный" под полем "Адреса" (один некорректный email через запятую)', authenticated_page)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_mailing_invalid_email_multiple_addresses_semicolon(authenticated_page: Page, credentials):
    """
    Проверяет, что при вводе нескольких адресов через точку с запятой, где один некорректный, появляется ошибка 'E-mail неверный'.
    """
    # Шаг №1: Находим редактируемую строку
    table = authenticated_page.locator('table.cdm-data-grid')
    row = find_editing_row(table)
    if row is None:
        fail_with_screenshot('Не найдена редактируемая строка для проверки', authenticated_page)
    # Шаг №2: Вводим несколько адресов через ;, один из которых некорректный
    address_input = row.locator('td').nth(4).locator('input[type="text"]')
    address_input.fill('test@mail.com;invalid@')
    # Шаг №3: Нажимаем на кнопку 'Сохранить'
    save_btn = row.locator('button:has(span[title="Сохранить"])')
    save_btn.wait_for(state='visible', timeout=5000)
    save_btn.click()
    # Шаг №4: Проверяем наличие ошибки
    address_hint = row.locator('td').nth(4).locator('p.MuiFormHelperText-root.Mui-error')
    if not (address_hint.is_visible() and 'E-mail неверный' in address_hint.inner_text()):
        fail_with_screenshot('Нет ошибки "E-mail неверный" под полем "Адреса" (один некорректный email через ;)', authenticated_page)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_mailing_invalid_email_double_separator(authenticated_page: Page, credentials):
    """
    Проверяет, что при двойном разделителе (,, или ;;) появляется ошибка 'E-mail неверный'.
    """
    # Шаг №1: Находим редактируемую строку
    table = authenticated_page.locator('table.cdm-data-grid')
    row = find_editing_row(table)
    if row is None:
        fail_with_screenshot('Не найдена редактируемая строка для проверки', authenticated_page)
    # Шаг №2: Вводим адреса с двойным разделителем
    address_input = row.locator('td').nth(4).locator('input[type="text"]')
    address_input.fill('test@mail.com,,test2@mail.com')
    # Шаг №3: Нажимаем на кнопку 'Сохранить'
    save_btn = row.locator('button:has(span[title="Сохранить"])')
    save_btn.wait_for(state='visible', timeout=5000)
    save_btn.click()
    # Шаг №4: Проверяем наличие ошибки
    address_hint = row.locator('td').nth(4).locator('p.MuiFormHelperText-root.Mui-error')
    if not (address_hint.is_visible() and 'E-mail неверный' in address_hint.inner_text()):
        fail_with_screenshot('Нет ошибки "E-mail неверный" под полем "Адреса" (двойная запятая)', authenticated_page)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_mailing_invalid_email_separator_at_start_end(authenticated_page: Page, credentials):
    """
    Проверяет, что при разделителе в начале или конце строки появляется ошибка 'E-mail неверный'.
    """
    # Шаг №1: Находим редактируемую строку
    table = authenticated_page.locator('table.cdm-data-grid')
    row = find_editing_row(table)
    if row is None:
        fail_with_screenshot('Не найдена редактируемая строка для проверки', authenticated_page)
    # Шаг №2: Вводим адреса с разделителем в начале
    address_input = row.locator('td').nth(4).locator('input[type="text"]')
    address_input.fill(',test@mail.com')
    # Шаг №3: Нажимаем на кнопку 'Сохранить'
    save_btn = row.locator('button:has(span[title="Сохранить"])')
    save_btn.wait_for(state='visible', timeout=5000)
    save_btn.click()
    # Шаг №4: Проверяем наличие ошибки
    address_hint = row.locator('td').nth(4).locator('p.MuiFormHelperText-root.Mui-error')
    if not (address_hint.is_visible() and 'E-mail неверный' in address_hint.inner_text()):
        fail_with_screenshot('Нет ошибки "E-mail неверный" под полем "Адреса" (разделитель в начале)', authenticated_page)
    # Шаг №5: Вводим адреса с разделителем в конце
    address_input.fill('test@mail.com,')
    save_btn.click()
    if not (address_hint.is_visible() and 'E-mail неверный' in address_hint.inner_text()):
        fail_with_screenshot('Нет ошибки "E-mail неверный" под полем "Адреса" (разделитель в конце)', authenticated_page)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_mailing_invalid_email_with_spaces_in_list(authenticated_page: Page, credentials):
    """
    Проверяет, что при наличии пробелов внутри email в списке адресов появляется ошибка 'E-mail неверный'.
    """
    # Шаг №1: Находим редактируемую строку
    table = authenticated_page.locator('table.cdm-data-grid')
    row = find_editing_row(table)
    if row is None:
        fail_with_screenshot('Не найдена редактируемая строка для проверки', authenticated_page)
    # Шаг №2: Вводим адреса с пробелом внутри одного из email
    address_input = row.locator('td').nth(4).locator('input[type="text"]')
    address_input.fill('test@mail.com, test @mail.com')
    # Шаг №3: Нажимаем на кнопку 'Сохранить'
    save_btn = row.locator('button:has(span[title="Сохранить"])')
    save_btn.wait_for(state='visible', timeout=5000)
    save_btn.click()
    # Шаг №4: Проверяем наличие ошибки
    address_hint = row.locator('td').nth(4).locator('p.MuiFormHelperText-root.Mui-error')
    if not (address_hint.is_visible() and 'E-mail неверный' in address_hint.inner_text()):
        fail_with_screenshot('Нет ошибки "E-mail неверный" под полем "Адреса" (пробел внутри email)', authenticated_page)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_mailing_invalid_email_with_forbidden_symbols_in_list(authenticated_page: Page, credentials):
    """
    Проверяет, что при наличии запрещённых символов в одном из email в списке появляется ошибка 'E-mail неверный'.
    """
    # Шаг №1: Находим редактируемую строку
    table = authenticated_page.locator('table.cdm-data-grid')
    row = find_editing_row(table)
    if row is None:
        fail_with_screenshot('Не найдена редактируемая строка для проверки', authenticated_page)
    # Шаг №2: Вводим адреса с запрещённым символом
    address_input = row.locator('td').nth(4).locator('input[type="text"]')
    address_input.fill('test@mail.com, test@codemaster!.pro')
    # Шаг №3: Нажимаем на кнопку 'Сохранить'
    save_btn = row.locator('button:has(span[title="Сохранить"])')
    save_btn.wait_for(state='visible', timeout=5000)
    save_btn.click()
    # Шаг №4: Проверяем наличие ошибки
    address_hint = row.locator('td').nth(4).locator('p.MuiFormHelperText-root.Mui-error')
    if not (address_hint.is_visible() and 'E-mail неверный' in address_hint.inner_text()):
        fail_with_screenshot('Нет ошибки "E-mail неверный" под полем "Адреса" (запрещённый символ)', authenticated_page)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_mailing_invalid_email_with_double_dot_in_list(authenticated_page: Page, credentials):
    """
    Проверяет, что при наличии двойной точки в одном из email в списке появляется ошибка 'E-mail неверный'.
    """
    # Шаг №1: Находим редактируемую строку
    table = authenticated_page.locator('table.cdm-data-grid')
    row = find_editing_row(table)
    if row is None:
        fail_with_screenshot('Не найдена редактируемая строка для проверки', authenticated_page)
    # Шаг №2: Вводим адреса с двойной точкой
    address_input = row.locator('td').nth(4).locator('input[type="text"]')
    address_input.fill('test@mail.com, test..mail@codemaster.pro')
    # Шаг №3: Нажимаем на кнопку 'Сохранить'
    save_btn = row.locator('button:has(span[title="Сохранить"])')
    save_btn.wait_for(state='visible', timeout=5000)
    save_btn.click()
    # Шаг №4: Проверяем наличие ошибки
    address_hint = row.locator('td').nth(4).locator('p.MuiFormHelperText-root.Mui-error')
    if not (address_hint.is_visible() and 'E-mail неверный' in address_hint.inner_text()):
        fail_with_screenshot('Нет ошибки "E-mail неверный" под полем "Адреса" (двойная точка)', authenticated_page)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_mailing_invalid_email_dot_at_start_end_in_list(authenticated_page: Page, credentials):
    """
    Проверяет, что при наличии точки в начале или конце email в списке появляется ошибка 'E-mail неверный'.
    """
    # Шаг №1: Находим редактируемую строку
    table = authenticated_page.locator('table.cdm-data-grid')
    row = find_editing_row(table)
    if row is None:
        fail_with_screenshot('Не найдена редактируемая строка для проверки', authenticated_page)
    # Шаг №2: Вводим адреса с точкой в начале одного из email
    address_input = row.locator('td').nth(4).locator('input[type="text"]')
    address_input.fill('.test@mail.com, test2@mail.com')
    # Шаг №3: Нажимаем на кнопку 'Сохранить'
    save_btn = row.locator('button:has(span[title="Сохранить"])')
    save_btn.wait_for(state='visible', timeout=5000)
    save_btn.click()
    # Шаг №4: Проверяем наличие ошибки
    address_hint = row.locator('td').nth(4).locator('p.MuiFormHelperText-root.Mui-error')
    if not (address_hint.is_visible() and 'E-mail неверный' in address_hint.inner_text()):
        fail_with_screenshot('Нет ошибки "E-mail неверный" под полем "Адреса" (точка в начале)', authenticated_page)
    # Шаг №5: Вводим адреса с точкой в конце одного из email
    address_input.fill('test@mail.com, test2.@mail.com')
    save_btn.click()
    if not (address_hint.is_visible() and 'E-mail неверный' in address_hint.inner_text()):
        fail_with_screenshot('Нет ошибки "E-mail неверный" под полем "Адреса" (точка в конце)', authenticated_page)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_mailing_create_third_row_fill_fields_2(authenticated_page: Page, credentials):
    """
    Заполняет строку рассылки: периодичность и email, проверяет значения.
    Предполагает, что строка для заполнения уже создана предыдущим тестом.
    Сохраняет отредактированную строку и проверяет запрос PATCH
    """
    # Шаг №0: Находим редактируемую строку
    table = authenticated_page.locator('table.cdm-data-grid')
    row = find_editing_row(table)
    if row is None:
        fail_with_screenshot('Не найдена редактируемая строка для проверки', authenticated_page)
    # Шаг №1: Отключаем чекбокс "Активна"
    active_checkbox = row.locator('td').nth(1).locator('input[type="checkbox"]')
    if active_checkbox.is_checked():
        active_checkbox.uncheck()
    if active_checkbox.is_checked():
        fail_with_screenshot('Чекбокс "Активна" не отключился', authenticated_page)
    # Шаг №2: Вводим периодичность
    period_input = row.locator('td').nth(3).locator('input[type="text"]')
    period_input.fill('0 * * * *')
    # Шаг №3: Вводим 2 корректных адреса email
    address_input = row.locator('td').nth(4).locator('input[type="text"]')
    address_input.fill(f'{credentials["email"]},test2@codemaster.pro')
    # Шаг №4: Проверяем значения
    if period_input.input_value() != '0 * * * *':
        fail_with_screenshot('Поле "Периодичность" не заполнено значением 0 * * * *', authenticated_page)
    if address_input.input_value() != f'{credentials["email"]},test2@codemaster.pro':
        fail_with_screenshot('Поле "Адреса" не заполнено значением test2@codemaster.pro', authenticated_page)
    # Шаг №5: Ожидаем PATCH запроса с использованием expect_response
    with authenticated_page.expect_response(lambda resp: resp.request.method == "PATCH" and "/security-report-cron-jobs" in resp.url, timeout=10000) as resp_info:
        # Шаг №6: Нажимаем на кнопку 'Сохранить'
        save_btn = row.locator('button:has(span[title="Сохранить"])')
        save_btn.wait_for(state='visible', timeout=5000)
        save_btn.click()
    response = resp_info.value
    # Шаг №7: Проверяем, что получен ответ 200
    if response.status != 200:
        fail_with_screenshot("Не получен ответ 200, получен ответ со статусом {response.status}", authenticated_page)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_mailing_check_saved_data_display(authenticated_page: Page, credentials):
   """
   Проверяет, что сохраненные данные отображаются корректно
   """
   # Шаг №1: Находим таблицу
   table = authenticated_page.locator('table.cdm-data-grid')
   # Шаг №2: Ищем строку с "test_mail" (сохраненную в предыдущих тестах)
   locator = table.locator('tbody tr', has_text="test_mail")
   locator.wait_for(state='visible', timeout=15000)
   row = find_row_by_text(table, "test_mail")
   if row is None:
       fail_with_screenshot('Не найдена строка с рассылкой "test_mail"', authenticated_page)
   # Шаг №3: Проверяем, что все значения в строке отображаются корректно
   # Проверяем "Рассылка"
   mailing_cell = row.locator('td').nth(0)
   if 'test_mail' not in mailing_cell.inner_text():
       fail_with_screenshot('В ячейке "Рассылка" не отображается значение test_mail', authenticated_page)
   # Проверяем "Активна" (должно быть "Нет")
   active_cell = row.locator('td').nth(1)
   if 'Нет' not in active_cell.inner_text():
       fail_with_screenshot('В ячейке "Активна" не отображается значение "Нет"', authenticated_page)
   # Проверяем "Шаблон"
   template_cell = row.locator('td').nth(2)
   if 'test' not in template_cell.inner_text():
       fail_with_screenshot('В ячейке "Шаблон" не отображается значение test', authenticated_page)
   # Проверяем "Периодичность"
   period_cell = row.locator('td').nth(3)
   if '0 * * * *' not in period_cell.inner_text():
       fail_with_screenshot('В ячейке "Периодичность" не отображается значение 0 * * * *', authenticated_page)
   # Проверяем email
   address_cell = row.locator('td').nth(4)
   if f'{credentials["email"]}, test2@codemaster.pro' not in address_cell.inner_text():
       fail_with_screenshot('В ячейке "Адреса" не отображается email {credentials["email"]}, test2@codemaster.pro', authenticated_page)


"""-------------------------------------Фильтр Активна--------------------------------------- """


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_mailing_filter_positive_active_yes(authenticated_page: Page, credentials):
    """
    Проверяет поизтивную фильтрацию по "Активна": Да
    """
    filter_name = "Активна"
    severity_text = "Да"
    check_filter_by_select(authenticated_page, filter_name, severity_text)


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_mailing_filter_negative_active_yes(authenticated_page: Page, credentials):
    """
    Проверяет негативную фильтрацию по "Активна": Да
    """
    filter_name = "Активна"
    severity_text = "Да"
    check_filter_by_select_negative_other_values(authenticated_page, filter_name, severity_text)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_mailing_filter_positive_active_no(authenticated_page: Page, credentials):
    """
    Проверяет поизтивную фильтрацию по "Активна": Нет
    """
    filter_name = "Активна"
    severity_text = "Нет"
    check_filter_by_select(authenticated_page, filter_name, severity_text)


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_mailing_filter_negative_active_no(authenticated_page: Page, credentials):
    """
    Проверяет негативную фильтрацию по "Активна": Нет
    """
    filter_name = "Активна"
    severity_text = "Нет"
    check_filter_by_select_negative_other_values(authenticated_page, filter_name, severity_text)


"""-------------------------------------Фильтр Шаблон--------------------------------------- """



@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_mailing_filter_positive_template_test(authenticated_page: Page, credentials):
    """
    Проверяет поизтивную фильтрацию по "Шаблон": test
    """
    filter_name = "Шаблон"
    severity_text = "test"
    check_filter_by_select(authenticated_page, filter_name, severity_text)


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_mailing_filter_negative_active_yes(authenticated_page: Page, credentials):
    """
    Проверяет негативную фильтрацию по "Шаблон": test
    """
    filter_name = "Шаблон"
    severity_text = "test"
    check_filter_by_select_negative_other_values(authenticated_page, filter_name, severity_text)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_mailing_filter_positive_active_no(authenticated_page: Page, credentials):
    """
    Проверяет поизтивную фильтрацию по "Шаблон": new_template
    """
    filter_name = "Шаблон"
    severity_text = "new_template"
    check_filter_by_select(authenticated_page, filter_name, severity_text)


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_mailing_filter_negative_active_no(authenticated_page: Page, credentials):
    """
    Проверяет негативную фильтрацию по "Шаблон": new_template
    """
    filter_name = "Шаблон"
    severity_text = "new_template"
    check_filter_by_select_negative_other_values(authenticated_page, filter_name, severity_text)


"""-------------------------------------Фильтр E-mail--------------------------------------- """


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_mailing_filter_positive_e_mail_valid(authenticated_page: Page, credentials):
    """
    Проверяет позитивную фильтрацию по "E-mail": Значение из cred.json (test@codemaster.pro)
    """
    filter_name = "E-mail"
    severity_text = credentials["email"]
    check_filter_by_input(authenticated_page, filter_name, severity_text)


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_mailing_filter_positive_e_mail_valid_insensitive(authenticated_page: Page, credentials):
    """
    Проверяет позитивную фильтрацию по "E-mail": TEST2@CODEMASTER.PRO (case-insensitive)
    """
    filter_name = "E-mail"
    severity_text = "TEST2@CODEMASTER.PRO"
    check_filter_by_input(authenticated_page, filter_name, severity_text)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_mailing_filter_negative_e_mail_qwerty123(authenticated_page: Page, credentials):
    """
    Проверяет негативную фильтрацию по "E-mail": qwerty123
    """
    filter_name = "E-mail"
    severity_text = "qwerty123"
    check_filter_by_input_negative_other_values(authenticated_page, filter_name, severity_text)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_mailing_filter_negative_e_mail_invalid(authenticated_page: Page, credentials):
    """
    Проверяет негативную фильтрацию по "E-mail": Значение из cred.json (test@codemaster.pro) + "o" (невалидный email)
    """
    filter_name = "E-mail"
    severity_text = credentials["email"] + "o"
    check_filter_by_input_negative_other_values(authenticated_page, filter_name, severity_text)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_mailing_filter_negative_e_mail_special_chars(authenticated_page: Page, credentials):
    """
    Проверяет негативную фильтрацию по "E-mail": спецсимволы
    """
    filter_name = "E-mail"
    severity_text = "!@#$%^&*()_+"
    check_filter_by_input_negative_other_values(authenticated_page, filter_name, severity_text)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_mailing_filter_negative_e_mail_long_string(authenticated_page: Page, credentials):
    """
    Проверяет негативную фильтрацию по "E-mail": очень длинная строка
    """
    filter_name = "E-mail"
    severity_text = "A" * 1024
    check_filter_by_input_negative_other_values(authenticated_page, filter_name, severity_text)

# @pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
# def test_page_mailing_filter_negative_e_mail_sql_injection(authenticated_page: Page, credentials):
#     """
#     Проверяет негативную фильтрацию по "E-mail": SQL-инъекция
#     """
#     filter_name = "E-mail"
#     severity_text = "' OR 1=1 --"
#     check_filter_by_input_negative_other_values(authenticated_page, filter_name, severity_text)


"""-------------------------------------Фильтр Периодичность--------------------------------------- """


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_mailing_filter_positive_periodicity_valid(authenticated_page: Page, credentials):
    """
    Проверяет позитивную фильтрацию по "Периодичность": 0 * * * *
    """
    filter_name = "Периодичность"
    severity_text = "0 * * * *"
    check_filter_by_input(authenticated_page, filter_name, severity_text)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_mailing_check_filter_by_input_first_row_periodicity(authenticated_page: Page, credentials):
    """
    Проверяет позитивную фильтрацию по "Периодичность": по первой строке
    """
    filter_name = "Периодичность"
    check_filter_by_input_first_row_value(authenticated_page, filter_name)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_mailing_filter_negative_periodicity_qwerty123(authenticated_page: Page, credentials):
    """
    Проверяет негативную фильтрацию по "Периодичность": qwerty123
    """
    filter_name = "Периодичность"
    severity_text = "qwerty123"
    check_filter_by_input_negative_other_values(authenticated_page, filter_name, severity_text)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_mailing_filter_negative_periodicity_invalid(authenticated_page: Page, credentials):
    """
    Проверяет негативную фильтрацию по "Периодичность": 0 * * * * *
    """
    filter_name = "Периодичность"
    severity_text = "0 * * * * *"
    check_filter_by_input_negative_other_values(authenticated_page, filter_name, severity_text)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_mailing_filter_negative_periodicity_invalid_2(authenticated_page: Page, credentials):
    """
    Проверяет негативную фильтрацию по "Периодичность": * * * * *
    """
    filter_name = "Периодичность"
    severity_text = "* * * * *"
    check_filter_by_input_negative_other_values(authenticated_page, filter_name, severity_text)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_mailing_filter_negative_periodicity_special_chars(authenticated_page: Page, credentials):
    """
    Проверяет негативную фильтрацию по "Периодичность": спецсимволы
    """
    filter_name = "Периодичность"
    severity_text = "!@#$%^&*()_+"
    check_filter_by_input_negative_other_values(authenticated_page, filter_name, severity_text)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_mailing_filter_negative_periodicity_long_string(authenticated_page: Page, credentials):
    """
    Проверяет негативную фильтрацию по "Периодичность": очень длинная строка
    """
    filter_name = "Периодичность"
    severity_text = "A" * 1024
    check_filter_by_input_negative_other_values(authenticated_page, filter_name, severity_text)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_mailing_filter_negative_periodicity_sql_injection(authenticated_page: Page, credentials):
    """
    Проверяет негативную фильтрацию по "Периодичность": SQL-инъекция
    """
    filter_name = "Периодичность"
    severity_text = "' OR 1=1 --"
    check_filter_by_input_negative_other_values(authenticated_page, filter_name, severity_text)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_mailing_filter_negative_periodicity_spaces(authenticated_page: Page, credentials):
    """
    Проверяет негативную фильтрацию по "Периодичность": только пробелы
    """
    filter_name = "Периодичность"
    severity_text = "   "
    check_filter_by_input_negative_other_values(authenticated_page, filter_name, severity_text)


"""-------------------------------------Проверка всплывающих подсказок--------------------------------------- """


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_mailing_header_periodicity_tooltip(authenticated_page: Page, credentials):
    """
    Проверяет, что при наведении на иконку подсказки в заголовке колонки "Периодичность"
    отображается тултип с текстом "Используется формат Cron" (через атрибут title).
    """
    # Шаг №1: Убеждаемся, что таблица видима
    if not authenticated_page.locator('table.cdm-data-grid').is_visible(timeout=5000):
        fail_with_screenshot('Таблица не видна', authenticated_page)
    # Шаг №2: Наводим и проверяем тултип по title
    hover_column_help_icon_and_assert_title(authenticated_page, "Периодичность", "Используется формат Cron")

# Новый тест: проверка тултипа в заголовке колонки "Адреса"
@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_mailing_header_addresses_tooltip(authenticated_page: Page, credentials):
    """
    Проверяет, что при наведении на иконку подсказки в заголовке колонки "Адреса" отображается
    тултип с текстом 'Адреса вводятся через "," или ";"'. В DOM атрибут title уже содержит
    раскодированную строку, поэтому в тесте используем обычные символы, а не html-последовательности.
    """
    if not authenticated_page.locator('table.cdm-data-grid').is_visible(timeout=5000):
        fail_with_screenshot('Таблица не видна', authenticated_page)
    hover_column_help_icon_and_assert_title(
        authenticated_page,
        "E-mail",
        'Адреса вводятся через "," или ";"'
    )


"""-------------------------------------Удаление строк и шаблонов--------------------------------------- """


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_mailing_delete_row_test_mail(authenticated_page: Page, credentials):
    """
    Удаляет строку с первой ячейкой 'test_mail' и ожидает успешного DELETE запроса.
    """
    endpoint_part = "/api/service/remote/logger-analytics/analytics-server/call/security-report-cron-jobs/"
    delete_row_by_first_cell(authenticated_page, "test_mail", endpoint_part)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_mailing_delete_first_row(authenticated_page: Page, credentials):
    """
    Удаляет первую строку и ожидает успешного DELETE запроса.
    """
    endpoint_part = "/api/service/remote/logger-analytics/analytics-server/call/security-report-cron-jobs/"
    delete_row_by_first_cell(authenticated_page, None, endpoint_part)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_create_delete_template_test(authenticated_page: Page, credentials):
    """
    Переходит на страницу "Создание отчетов" и удаляет шаблон 'test'.
    """
    # Шаг 0: Переходим на вкладку "Создание отчетов"
    navigate_and_check_url_with_tab(
        authenticated_page,
        "Аудит безопасности",
        "Отчетность",
        "Создание отчетов",
        "security-audit/reports/create",
        credentials,
    )

    # Шаг 1: Переключаемся на "Создать по шаблону"
    template_radio = authenticated_page.get_by_label("Создать по шаблону")
    template_radio.check()

    # Шаг 2: Открываем селект шаблонов
    select_button = authenticated_page.locator('div[role="button"]#templateId')
    select_button.click(force=True)

    # Шаг 3: Выбираем 'test' в выпадающем списке
    option = authenticated_page.locator('ul[role="listbox"] li', has_text="test")
    option.wait_for(state="visible", timeout=5000)
    if not option.is_visible():
        pytest.skip('Шаблон "test" не найден, пропускаем удаление')
    option.click()

    # Шаг 4: Кнопка удалить
    delete_btn = authenticated_page.locator('button span.cdm-icon-wrapper[title="Удалить"]')
    if not delete_btn.is_visible():
        pytest.skip('Кнопка "Удалить" не появилась, пропускаем удаление')
    # Шаг 5: Ожидаем DELETE запрос и подтверждаем
    with authenticated_page.expect_response(lambda resp: resp.request.method == "DELETE" and "/security-report-templates/" in resp.url, timeout=10000) as resp_info:
        delete_btn.click()
        confirm_modal = authenticated_page.locator('div[role="dialog"]:has-text("Вы уверены?")')
        confirm_modal.wait_for(state="visible")
        confirm_btn = confirm_modal.get_by_role("button", name="Удалить")
        confirm_btn.click()
    if resp_info.value.status != 200:
        fail_with_screenshot(f"DELETE шаблона 'test' вернул статус {resp_info.value.status}", authenticated_page)


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_create_delete_template_new_template(authenticated_page: Page, credentials):
    """
    Переходит на страницу "Создание отчетов" и удаляет шаблон 'new_template'.
    """
    navigate_and_check_url_with_tab(
        authenticated_page,
        "Аудит безопасности",
        "Отчетность",
        "Создание отчетов",
        "security-audit/reports/create",
        credentials,
    )

    # Шаг №1: Переключаемся на радио-кнопку "Создать по шаблону"
    template_radio = authenticated_page.get_by_label("Создать по шаблону")
    template_radio.check()

    # Шаг №2: Открываем селект шаблонов
    select_button = authenticated_page.locator('div[role="button"]#templateId')
    select_button.click(force=True)

    # Шаг №3: Выбираем шаблон 'new_template' в выпадающем списке
    option = authenticated_page.locator('ul[role="listbox"] li', has_text="new_template")
    option.wait_for(state="visible", timeout=5000)
    if not option.is_visible():
        pytest.skip('Шаблон "new_template" не найден, пропускаем удаление')
    option.click()

    # Шаг №4: Проверяем появление кнопки удалить
    delete_btn = authenticated_page.locator('button span.cdm-icon-wrapper[title="Удалить"]')
    if not delete_btn.is_visible():
        pytest.skip('Кнопка "Удалить" не появилась, пропускаем удаление')

    # Шаг №5: Ожидаем DELETE запрос и подтверждаем удаление
    with authenticated_page.expect_response(lambda resp: resp.request.method == "DELETE" and "/security-report-templates/" in resp.url, timeout=10000) as resp_info:
        delete_btn.click()
        confirm_modal = authenticated_page.locator('div[role="dialog"]:has-text("Вы уверены?")')
        confirm_modal.wait_for(state="visible")
        confirm_btn = confirm_modal.get_by_role("button", name="Удалить")
        confirm_btn.click()
    if resp_info.value.status != 200:
        fail_with_screenshot(f"DELETE шаблона 'new_template' вернул статус {resp_info.value.status}", authenticated_page)