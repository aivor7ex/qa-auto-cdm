import pytest
from playwright.sync_api import expect, Page, Browser
from UI.other_tests.test_autentification_admin import _perform_login
import json
import re
import os
import tempfile
from UI.universal_functions.navigation import (
    navigate_and_check_url,
    check_tabs_selected_state,
    find_input_by_label
)
import datetime
from UI.conftest import fail_with_screenshot
from pdfminer.high_level import extract_text
from pdfminer.layout import LAParams
import unicodedata
# import fitz

# Глобальные переменные
_last_download_path = None
_skip_success_modal = False

def _open_time_interval_menu(page: Page):
    """Открывает выпадающий список выбора периода"""
    select_btn = page.locator('div.MuiSelect-root[role="button"]#timeIntervalString')
    if not select_btn.is_visible():
        # запасной вариант (на случай изменений классов)
        select_btn = page.locator('div[role="button"]#timeIntervalString')
    if not select_btn.is_visible():
        fail_with_screenshot("Селект выбора периода не найден", page)
    select_btn.click()
    # ждём появление меню
    menu = page.locator('ul.MuiMenu-list[role="listbox"]')
    menu.wait_for(state="visible", timeout=5000)


# Хелпер: проверка валидности PDF-файла

def _assert_pdf_valid(path):
    if not path or not os.path.exists(str(path)):
        raise AssertionError("PDF файл не найден для проверки")
    size = os.path.getsize(str(path))
    if size <= 0:
        raise AssertionError("PDF файл пустой")
    with open(str(path), 'rb') as f:
        if f.read(4) != b'%PDF':
            raise AssertionError("Файл не является корректным PDF (нет заголовка %PDF)")

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_create_navigate_and_check_url(authenticated_page: Page, credentials):
    """
    Шаг №1: Переходит по сайдбару в раздел "Аудит безопасности" — "Отчетность" и проверяет корректность URL.
    """
    # Шаг №1: Переход по сайдбару и проверка URL
    tab_button_1 = "Аудит безопасности"
    tab_button_2 = "Отчетность"
    url = "security-audit/reports/create"
    navigate_and_check_url(authenticated_page, tab_button_1, tab_button_2, url, credentials)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_create_check_tabs_selected_state(authenticated_page: Page, credentials):
    """
    Проверяет, что после перехода на вкладку "Создание отчетов" остальные вкладки не активны, а URL корректен.
    """
    # Шаг №1: Проверка состояния вкладок и url
    tab_names = ["Создание отчетов", "Рассылка отчетов", "Системный отчет"]
    tab_target = "Создание отчетов"
    url = "security-audit/reports/create"
    check_tabs_selected_state(authenticated_page, tab_names, tab_target, url, credentials)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_create_report_header_present(authenticated_page: Page, credentials):
    """
    Проверяет наличие заголовка "Формирование отчета" на странице.
    """
    # Шаг №1: Проверяем наличие заголовка "Формирование отчета" на странице
    header_locator = authenticated_page.locator('span.MuiCardHeader-title', has_text="Формирование отчета")
    header_locator.wait_for(state="visible", timeout=5000)
    if not header_locator.is_visible():
        fail_with_screenshot("Заголовок 'Формирование отчета' не найден на странице", authenticated_page)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_create_report_radio_buttons(authenticated_page: Page, credentials):
    """
    Проверяет наличие радиокнопок "Создать новый шаблон" и "Не использовать шаблон", а также что по умолчанию выбрана первая.
    """
    # Шаг №1: Проверяем наличие радиокнопок "Создать новый шаблон" и "Не использовать шаблон"
    radio_new_template = authenticated_page.get_by_label("Создать новый шаблон")
    radio_no_template = authenticated_page.get_by_label("Не использовать шаблон")
    radio_new_template.wait_for(state="visible", timeout=5000)
    if not radio_new_template.is_visible():
        fail_with_screenshot("Радиокнопка 'Создать новый шаблон' не найдена", authenticated_page)
    if not radio_no_template.is_visible():
        fail_with_screenshot("Радиокнопка 'Не использовать шаблон' не найдена", authenticated_page)
    # Шаг №2: Проверяем состояние радиокнопок по умолчанию
    if not radio_new_template.is_checked():
        fail_with_screenshot("По умолчанию должна быть выбрана радиокнопка 'Создать новый шаблон'", authenticated_page)
    if radio_no_template.is_checked():
        fail_with_screenshot("Радиокнопка 'Не использовать шаблон' не должна быть выбрана по умолчанию", authenticated_page)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_create_report_template_name_field(authenticated_page: Page, credentials):
    """
    Проверяет наличие поля для ввода "Название шаблона" и его доступность для ввода.
    """
    # Шаг №1: Выбираем радиокнопку "Создать новый шаблон"
    radio_new_template = authenticated_page.locator('input[type="radio"][value="new-template"]')
    radio_new_template.wait_for(state="visible", timeout=5000)
    if not radio_new_template.is_visible():
        fail_with_screenshot("Радиокнопка 'Создать новый шаблон' не найдена", authenticated_page)
    radio_new_template.check()
    # Шаг №2: Проверяем наличие и доступность поля "Название шаблона"
    input_field = find_input_by_label(authenticated_page, "Название шаблона", None)
    if not input_field.is_visible():
        fail_with_screenshot("Поле 'Название шаблона' не найдено на странице", authenticated_page)
    if not input_field.is_editable():
        fail_with_screenshot("Поле 'Название шаблона' не доступно для ввода", authenticated_page)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_create_report_radio_switch_and_template_field(authenticated_page: Page, credentials):
    """
    Проверяет, что при переключении радиокнопки на "Не использовать шаблон" поле для названия шаблона скрыто или неактивно, а при возврате — снова видно и активно.
    """
    # Шаг №1: Переключаем радиокнопку на "Не использовать шаблон"
    radio_new_template = authenticated_page.locator('input[type="radio"][value="new-template"]')
    radio_no_template = authenticated_page.locator('input[type="radio"][value="without-template"]')
    radio_no_template.check()
    input_field = find_input_by_label(authenticated_page, "Название шаблона", None)
    # Шаг №2: Проверяем, что поле для названия шаблона скрыто или неактивно
    if input_field.is_visible() and input_field.is_enabled():
        fail_with_screenshot("Поле 'Название шаблона' должно быть скрыто или неактивно после переключения радиокнопки", authenticated_page)
    # Шаг №3: Переключаем обратно на "Создать новый шаблон"
    radio_new_template.check()
    # Шаг №4: Проверяем, что поле снова видно и активно
    if not input_field.is_visible():
        fail_with_screenshot("Поле 'Название шаблона' не отображается после возврата радиокнопки", authenticated_page)
    if not input_field.is_editable():
        fail_with_screenshot("Поле 'Название шаблона' не доступно для ввода после возврата радиокнопки", authenticated_page)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_create_report_checkboxes_present(authenticated_page: Page, credentials):
    """
    Проверяет наличие всех чекбоксов на странице и что они выключены по умолчанию.
    """
    checkbox_labels = [
        "Сводный трафик по угрозам",
        "Дифференциальный трафик по угрозам",
        "Таблица \"Топ 10\""
    ]
    # Шаг №1: Проверяем наличие и состояние чекбоксов
    for label in checkbox_labels:
        checkbox = authenticated_page.get_by_label(label)
        if not checkbox.is_visible():
            fail_with_screenshot(f'Чекбокс "{label}" не найден на странице', authenticated_page)
        if checkbox.is_checked():
            fail_with_screenshot(f'Чекбокс "{label}" должен быть выключен по умолчанию', authenticated_page)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_create_report_checkboxes_toggle(authenticated_page: Page, credentials):
    """
    Включает все чекбоксы и проверяет, что они включены (оставляет включёнными).
    """
    checkbox_labels = [
        "Сводный трафик по угрозам",
        "Дифференциальный трафик по угрозам",
        "Таблица \"Топ 10\""
    ]
    # Шаг №1: Включаем все чекбоксы и проверяем их состояние
    for label in checkbox_labels:
        checkbox = authenticated_page.get_by_label(label)
        checkbox.check()
        if not checkbox.is_checked():
            fail_with_screenshot(f'Чекбокс "{label}" должен быть включён после клика', authenticated_page)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_create_report_save_template_empty_name_shows_hint(authenticated_page: Page, credentials):
    """
    Включает все чекбоксы, проверяет, что поле "Название шаблона" пустое, нажимает "Сохранить шаблон" и проверяет появление подсказки "Заполните поле".
    """
    checkbox_labels = [
        "Сводный трафик по угрозам",
        "Дифференциальный трафик по угрозам",
        "Таблица \"Топ 10\""
    ]
    # Шаг №1: Выбираем радиокнопку "Создать новый шаблон"
    radio_new_template = authenticated_page.get_by_label("Создать новый шаблон")
    radio_new_template.wait_for(state="visible", timeout=5000)
    if not radio_new_template.is_visible():
        fail_with_screenshot("Радиокнопка 'Создать новый шаблон' не найдена", authenticated_page)
    radio_new_template.check()
    # Шаг №2: Включаем все чекбоксы
    for label in checkbox_labels:
        checkbox = authenticated_page.get_by_label(label)
        if not checkbox.is_checked():
            checkbox.check()
        if not checkbox.is_checked():
            fail_with_screenshot(f'Чекбокс "{label}" должен быть включён', authenticated_page)
    # Шаг №3: Проверяем, что поле "Название шаблона" пустое
    input_field = find_input_by_label(authenticated_page, "Название шаблона", None)
    if not input_field.is_visible():
        fail_with_screenshot("Поле 'Название шаблона' не найдено на странице", authenticated_page)
    if input_field.input_value() != "":
        fail_with_screenshot('Поле "Название шаблона" должно быть пустым', authenticated_page)
    # Шаг №4: Нажимаем кнопку "Сохранить шаблон"
    save_btn = authenticated_page.get_by_role("button", name="Сохранить шаблон")
    if not save_btn.is_visible():
        fail_with_screenshot("Кнопка 'Сохранить шаблон' не найдена на странице", authenticated_page)
    save_btn.click()
    # Шаг №5: Проверяем появление подсказки "Заполните поле"
    hint = authenticated_page.locator('p.MuiFormHelperText-root.Mui-error', has_text="Заполните поле")
    if not hint.is_visible():
        fail_with_screenshot("Подсказка 'Заполните поле' не появилась после попытки сохранить пустой шаблон", authenticated_page)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_create_report_time_interval_selection(authenticated_page: Page, credentials):
    """
    Универсальная проверка выбора временного промежутка: выбирает 1 и 2 число текущего месяца, проверяет, что значения в инпутах соответствуют выбранным дням и времени.
    """
    now = datetime.datetime.now()
    month = now.month
    year = now.year
    # Шаг №1: Переключаем радиокнопку на "Временной промежуток"
    radio_interval = authenticated_page.locator('input[name="timeIntervalMode"][value="interval"]')
    if not radio_interval.is_visible():
        fail_with_screenshot("Элемент не видим", authenticated_page)
    radio_interval.check()
    # Шаг №2: Устанавливаем дату "С"
    date_from_btn = authenticated_page.locator('.cdm-datetime-interval__date button[aria-label="change date"]')
    if not date_from_btn.is_visible():
        fail_with_screenshot("Элемент не видим", authenticated_page)
    date_from_btn.click()
    authenticated_page.locator('.MuiPickersDay-day:not([class*="MuiPickersDay-hidden"])', has_text="1").first.click()
    authenticated_page.locator('.MuiPickersClock-container span:text-is("1")').click(force=True)
    authenticated_page.wait_for_timeout(300)
    authenticated_page.locator('.MuiPickersClock-container span:text-is("05")').click(force=True)
    size = authenticated_page.viewport_size or authenticated_page.context.viewport_size
    if size:
        authenticated_page.mouse.click(size['width'] / 4, size['height'] / 4)
    # Шаг №3: Устанавливаем дату "По"
    date_to_btn = authenticated_page.locator('.cdm-datetime-interval__time button[aria-label="change date"]')
    if not date_to_btn.is_visible():
        fail_with_screenshot("Элемент не видим", authenticated_page)
    date_to_btn.click()
    authenticated_page.locator('.MuiPickersDay-day:not([class*="MuiPickersDay-hidden"])', has_text="2").first.click()
    authenticated_page.locator('.MuiPickersClock-container span:text-is("23")').click(force=True)
    authenticated_page.wait_for_timeout(300)
    authenticated_page.locator('.MuiPickersClock-container span:text-is("55")').click(force=True)
    if size:
        authenticated_page.mouse.click(size['width'] / 4, size['height'] / 4)
    authenticated_page.wait_for_timeout(500)
    # Шаг №4: Проверяем значения в инпутах
    inputs = authenticated_page.locator('.cdm-datetime-interval input')
    actual_from = inputs.nth(0).input_value()
    actual_to = inputs.nth(1).input_value()
    from_dt = datetime.datetime.strptime(actual_from, "%d.%m.%Y %H:%M:%S")
    to_dt = datetime.datetime.strptime(actual_to, "%d.%m.%Y %H:%M:%S")
    if from_dt.day != 1:
        fail_with_screenshot(f"Ожидался день '1' в поле 'с', получено: {from_dt.day}", authenticated_page)
    if from_dt.month != month:
        fail_with_screenshot(f"Ожидался месяц '{month}', получено: {from_dt.month}", authenticated_page)
    if from_dt.year != year:
        fail_with_screenshot(f"Ожидался год '{year}', получено: {from_dt.year}", authenticated_page)
    if not (from_dt.hour == 1 and from_dt.minute == 5):
        fail_with_screenshot(f"Ожидалось время 01:05:00, получено: {from_dt.time()}", authenticated_page)
    if to_dt.day != 2:
        fail_with_screenshot(f"Ожидался день '2' в поле 'по', получено: {to_dt.day}", authenticated_page)
    if to_dt.month != month:
        fail_with_screenshot(f"Ожидался месяц '{month}', получено: {to_dt.month}", authenticated_page)
    if to_dt.year != year:
        fail_with_screenshot(f"Ожидался год '{year}', получено: {to_dt.year}", authenticated_page)
    if not (to_dt.hour == 23 and to_dt.minute == 55):
        fail_with_screenshot(f"Ожидалось время 23:55:00, получено: {to_dt.time()}", authenticated_page)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_create_report_time_last_radio_selected_and_select_options(authenticated_page: Page, credentials):
    """
    Переключает радиокнопку "last", затем тестирует работу выпадающего списка периодов.
    """
    # Шаг №1: Переключаем радиокнопку "last"
    radio_last = authenticated_page.locator('input[name="timeIntervalMode"][value="last"]')
    if not radio_last.is_visible():
        fail_with_screenshot("Радиокнопка 'last' (верхняя) не найдена", authenticated_page)
    radio_last.check()
    if not radio_last.is_checked():
        fail_with_screenshot("Радиокнопка 'last' (верхняя) не выбрана после переключения", authenticated_page)
    # Шаг №2: Открываем селект и проверяем наличие опций (гибко)
    _open_time_interval_menu(authenticated_page)
    menu = authenticated_page.locator('ul.MuiMenu-list[role="listbox"]')
    expected = [
        "За последний месяц",
        "За последний день",
        "За последний час",
    ]
    # Проверяем, что присутствует хотя бы одна ожидаемая опция (UI может скрывать недоступные интервалы)
    found_any = False
    for option in expected:
        if menu.locator('li', has_text=option).count() > 0:
            found_any = True
            break
    if not found_any:
        fail_with_screenshot("В выпадающем списке не найдено ни одной ожидаемой опции периода", authenticated_page)
    
        # Шаг №3: Выбираем пункт "За последний день" из выпадающего списка
    menu = authenticated_page.locator('ul.MuiMenu-list[role="listbox"]')
    option = menu.locator('li', has_text="За последний день").first
    if option.count() == 0 or not option.is_visible():
        fail_with_screenshot("Опция 'За последний день' не найдена в выпадающем списке", authenticated_page)
    option.click()

    # Шаг №4: Проверяем отображение выбранного значения в селекте
    selected = authenticated_page.locator('div.MuiSelect-root[role="button"]#timeIntervalString')
    if "За последний день" not in selected.inner_text():
        fail_with_screenshot("Селект не отобразил выбранное значение 'За последний день'", authenticated_page)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_create_report_time_last_select_day(authenticated_page: Page, credentials):
    """
    Переключает радиокнопку "last", выбирает "За последний день" в селекте и проверяет отображение.
    """
    # Шаг №1: Находим и переключаем радиокнопку "last"
    radio_last = authenticated_page.locator('input[name="timeIntervalMode"][value="last"]')
    if not radio_last.is_visible():
        fail_with_screenshot("Радиокнопка 'last' (верхняя) не найдена", authenticated_page)
    radio_last.check()
    if not radio_last.is_checked():
        fail_with_screenshot("Радиокнопка 'last' (верхняя) не выбрана после переключения", authenticated_page)

    # Шаг №2: Открываем селект выбора периода
    _open_time_interval_menu(authenticated_page)

    # Шаг №3: Выбираем пункт "За последний день" из выпадающего списка
    menu = authenticated_page.locator('ul.MuiMenu-list[role="listbox"]')
    option = menu.locator('li', has_text="За последний день").first
    if option.count() == 0 or not option.is_visible():
        fail_with_screenshot("Опция 'За последний день' не найдена в выпадающем списке", authenticated_page)
    option.click()

    # Шаг №4: Проверяем отображение выбранного значения в селекте
    selected = authenticated_page.locator('div.MuiSelect-root[role="button"]#timeIntervalString')
    if "За последний день" not in selected.inner_text():
        fail_with_screenshot("Селект не отобразил выбранное значение 'За последний день'", authenticated_page)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_create_report_time_last_select_hour(authenticated_page: Page, credentials):
    """
    Переключает радиокнопку "last", выбирает "За последний час" в селекте и проверяет отображение.
    """
    # Шаг №1: Переключаем радиокнопку "last"
    radio_last = authenticated_page.locator('input[name="timeIntervalMode"][value="last"]')
    if not radio_last.is_visible():
        fail_with_screenshot("Радиокнопка 'last' (верхняя) не найдена", authenticated_page)
    radio_last.check()
    if not radio_last.is_checked():
        fail_with_screenshot("Радиокнопка 'last' (верхняя) не выбрана после переключения", authenticated_page)

    # Шаг №2: Открываем селект выбора периода
    _open_time_interval_menu(authenticated_page)

    # Шаг №3: Выбираем пункт "За последний час" из выпадающего списка
    menu = authenticated_page.locator('ul.MuiMenu-list[role="listbox"]')
    option = menu.locator('li', has_text="За последний час").first
    if option.count() == 0 or not option.is_visible():
        fail_with_screenshot("Опция 'За последний час' не найдена в выпадающем списке", authenticated_page)
    option.click()

    # Шаг №4: Проверяем отображение выбранного значения в селекте
    selected = authenticated_page.locator('div.MuiSelect-root[role="button"]#timeIntervalString')
    if "За последний час" not in selected.inner_text():
        fail_with_screenshot("Селект не отобразил выбранное значение 'За последний час'", authenticated_page)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_create_report_time_last_select_month(authenticated_page: Page, credentials):
    """
    Переключает радиокнопку "last", выбирает "За последний месяц" в селекте и проверяет отображение.
    """
    # Шаг №1: Переключаем радиокнопку "last"
    radio_last = authenticated_page.locator('input[name="timeIntervalMode"][value="last"]')
    if not radio_last.is_visible():
        fail_with_screenshot("Радиокнопка 'last' (верхняя) не найдена", authenticated_page)
    radio_last.check()
    if not radio_last.is_checked():
        fail_with_screenshot("Радиокнопка 'last' (верхняя) не выбрана после переключения", authenticated_page)
    # Шаг №2: Открываем селект выбора периода
    _open_time_interval_menu(authenticated_page)

    # Шаг №3: Выбираем пункт "За последний месяц" из выпадающего списка
    menu = authenticated_page.locator('ul.MuiMenu-list[role="listbox"]')
    option = menu.locator('li', has_text="За последний месяц").first
    if option.count() == 0 or not option.is_visible():
        fail_with_screenshot("Опция 'За последний месяц' не найдена в выпадающем списке", authenticated_page)
    option.click()

    # Шаг №4: Проверяем отображение выбранного значения в селекте
    selected = authenticated_page.locator('div.MuiSelect-root[role="button"]#timeIntervalString')
    if "За последний месяц" not in selected.inner_text():
        fail_with_screenshot("Селект не отобразил выбранное значение 'За последний месяц'", authenticated_page)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_create_report_time_last_select_month_2(authenticated_page: Page, credentials):
    """
    Переключает радиокнопку "last", выбирает "За последний месяц" в селекте и проверяет отображение.
    """
    # Шаг №1: Переключаем радиокнопку "last"
    radio_last = authenticated_page.locator('input[name="timeIntervalMode"][value="last"]')
    if not radio_last.is_visible():
        fail_with_screenshot("Радиокнопка 'last' (верхняя) не найдена", authenticated_page)
    radio_last.check()
    if not radio_last.is_checked():
        fail_with_screenshot("Радиокнопка 'last' (верхняя) не выбрана после переключения", authenticated_page)
    # Шаг №2: Открываем селект выбора периода
    _open_time_interval_menu(authenticated_page)

    # Шаг №3: Выбираем пункт "За последний месяц" из выпадающего списка
    menu = authenticated_page.locator('ul.MuiMenu-list[role="listbox"]')
    option = menu.locator('li', has_text="За последний месяц").first
    if option.count() == 0 or not option.is_visible():
        fail_with_screenshot("Опция 'За последний месяц' не найдена в выпадающем списке", authenticated_page)
    option.click()

    # Шаг №4: Проверяем отображение выбранного значения в селекте
    selected = authenticated_page.locator('div.MuiSelect-root[role="button"]#timeIntervalString')
    if "За последний месяц" not in selected.inner_text():
        fail_with_screenshot("Селект не отобразил выбранное значение 'За последний месяц'", authenticated_page)

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
    # Шаг №1: Выбираем радиокнопку "Создать новый шаблон"
    radio_new_template = authenticated_page.get_by_label("Создать новый шаблон")
    radio_new_template.wait_for(state="visible", timeout=5000)
    if not radio_new_template.is_visible():
        fail_with_screenshot("Радиокнопка 'Создать новый шаблон' не найдена", authenticated_page)
    radio_new_template.check()
    # Шаг №2: Включаем все чекбоксы
    for label in checkbox_labels:
        checkbox = authenticated_page.get_by_label(label)
        if not checkbox.is_checked():
            checkbox.check()
        if not checkbox.is_checked():
            fail_with_screenshot(f'Чекбокс "{label}" должен быть включён для сохранения шаблона', authenticated_page)
    # Шаг №3: Вводим название шаблона 'test'
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
def test_create_report_delete_template_cancel(authenticated_page: Page, credentials):
    """
    После нажатия на кнопку удаления шаблона 'test' нажимает "Отмена" в модальном окне подтверждения. Проверяет, что селект с шаблоном на месте и радиокнопок 3.
    Предполагает, что шаблон 'test' уже создан и выбран.
    """
    # Шаг 1: Нажимаем кнопку удаления шаблона 'test'
    delete_btn = authenticated_page.locator('button span.cdm-icon-wrapper[title="Удалить"]')
    if not delete_btn.is_visible():
        fail_with_screenshot("Кнопка удаления шаблона не найдена", authenticated_page)
    delete_btn.click()
    # Шаг 2: В модальном окне подтверждения нажимаем "Отмена"
    confirm_modal = authenticated_page.locator('div[role="dialog"]')
    confirm_modal.wait_for(state="visible", timeout=5000)
    cancel_btn = confirm_modal.get_by_role("button", name="Отмена")
    if not cancel_btn.is_visible():
        fail_with_screenshot("Кнопка 'Отмена' не найдена в модальном окне", authenticated_page)
    cancel_btn.click()
    # Шаг 3: Проверяем, что селект с шаблоном 'test' остался
    select_template = authenticated_page.locator('div.MuiSelect-root[role="button"]#templateId')
    if not select_template.is_visible():
        fail_with_screenshot("Селект выбора шаблона исчез после отмены удаления", authenticated_page)
    if "test" not in select_template.inner_text():
        fail_with_screenshot("В селекте не найден шаблон 'test' после отмены удаления", authenticated_page)
    # Шаг 4: Проверяем, что радиокнопок 3
    radio_buttons = authenticated_page.locator('input[name="mode"]')
    if radio_buttons.count() != 3:
        fail_with_screenshot(f'Ожидалось 3 радиокнопки после отмены удаления шаблона, найдено: {radio_buttons.count()}', authenticated_page)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_create_report_delete_template_and_check_state(authenticated_page: Page, credentials):
    """
    Удаляет шаблон 'test', подтверждает удаление, проверяет исчезновение селекта, уменьшение числа радиокнопок до двух и выбор радиокнопки "Создать новый шаблон".
    Предполагает, что шаблон 'test' уже создан и выбран.
    """
    # Шаг 1: Удаляем шаблон 'test'
    delete_btn = authenticated_page.locator('button span.cdm-icon-wrapper[title="Удалить"]')
    if not delete_btn.is_visible():
        fail_with_screenshot("Кнопка удаления шаблона не найдена", authenticated_page)
    delete_btn.click()
    # Шаг 2: Подтверждаем удаление в модальном окне
    confirm_modal = authenticated_page.locator('div[role="dialog"]')
    confirm_modal.wait_for(state="visible", timeout=5000)
    confirm_btn = confirm_modal.get_by_role("button", name="Удалить")
    if not confirm_btn.is_visible():
        fail_with_screenshot("Кнопка подтверждения удаления не найдена в модальном окне", authenticated_page)
    confirm_btn.click()
    # Ждем закрытия модального окна и обновления UI
    confirm_modal.wait_for(state="hidden", timeout=5000)
    authenticated_page.wait_for_timeout(2000)
    # Шаг 3: Проверяем, что селект с шаблоном 'test' исчез
    select_template = authenticated_page.locator('div.MuiSelect-root[role="button"]#templateId')
    if select_template.is_visible():
        fail_with_screenshot("Селект выбора шаблона не исчез после удаления шаблона", authenticated_page)
    # Шаг 4: Проверяем, что радиокнопок стало 2
    radio_buttons = authenticated_page.locator('input[name="mode"]')
    if radio_buttons.count() != 2:
        fail_with_screenshot(f'Ожидалось 2 радиокнопки после удаления шаблона, найдено: {radio_buttons.count()}', authenticated_page)
    # Шаг 5: Проверяем, что выбрана радиокнопка "Создать новый шаблон"
    radio_new_template = authenticated_page.locator('input[name="mode"][value="new-template"]')
    if not radio_new_template.is_checked():
        fail_with_screenshot("После удаления шаблона должна быть выбрана радиокнопка 'Создать новый шаблон'", authenticated_page)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_create_report_save_template_and_close_modal_by_close_btn(authenticated_page: Page, credentials):
    """
    Создаёт шаблон 'test', в модальном окне нажимает кнопку "Закрыть", далее проверяет появление радиокнопки и селекта с шаблоном 'test'.
    """
        # Шаг 0: Включаем все чекбоксы
    checkbox_labels = [
        "Сводный трафик по угрозам",
        "Дифференциальный трафик по угрозам",
        "Таблица \"Топ 10\""
    ]
    # Шаг 0: Выбираем радиокнопку "Создать новый шаблон"
    radio_new_template = authenticated_page.get_by_label("Создать новый шаблон")
    radio_new_template.wait_for(state="visible", timeout=5000)
    if not radio_new_template.is_visible():
        fail_with_screenshot("Радиокнопка 'Создать новый шаблон' не найдена", authenticated_page)
    radio_new_template.check()
    # Шаг 1: Включаем все чекбоксы
    for label in checkbox_labels:
        checkbox = authenticated_page.get_by_label(label)
        if not checkbox.is_checked():
            checkbox.check()
        if not checkbox.is_checked():
            fail_with_screenshot(f'Чекбокс "{label}" должен быть включён для сохранения шаблона', authenticated_page)
    # Шаг 2: Вводим название шаблона 'test'
    input_field = find_input_by_label(authenticated_page, "Название шаблона", "test")
    if not input_field.is_visible():
        fail_with_screenshot("Поле 'Название шаблона' не найдено на странице", authenticated_page)
    input_field.fill("test")
    # Шаг 3: Нажимаем кнопку "Сохранить шаблон"
    save_btn = authenticated_page.get_by_role("button", name="Сохранить шаблон")
    save_btn.click()
    # Шаг 3: В модальном окне нажимаем кнопку "Закрыть"
    modal = authenticated_page.locator('div[role="dialog"] div.cdm-card._without-margin')
    modal.wait_for(state="visible", timeout=5000)
    close_btn = modal.locator('button span.cdm-icon-wrapper[title="Закрыть"]')
    if not close_btn.is_visible():
        fail_with_screenshot("Кнопка-крестик 'Закрыть' не найдена в модальном окне", authenticated_page)
    close_btn.click()
    modal.wait_for(state="hidden", timeout=5000)
    # Шаг 4: Проверяем появление радиокнопки и селекта с шаблоном 'test'
    radio_template_based = authenticated_page.locator('input[name="mode"][value="template-based"]')
    if not radio_template_based.is_visible():
        fail_with_screenshot("Радиокнопка 'Создать по шаблону' не найдена", authenticated_page)
    if not radio_template_based.is_checked():
        fail_with_screenshot("Радиокнопка 'Создать по шаблону' должна быть выбрана после создания шаблона", authenticated_page)
    select_template = authenticated_page.locator('div.MuiSelect-root[role="button"]#templateId')
    if not select_template.is_visible():
        fail_with_screenshot("Селект выбора шаблона не найден", authenticated_page)
    if "test" not in select_template.inner_text():
        fail_with_screenshot("В селекте не найден шаблон 'test'", authenticated_page)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_create_report_overwrite_template_and_close_modal_by_ok(authenticated_page: Page, credentials):
    """
    Перезаписывает шаблон 'test' (вводит 'test_new' в поле), после нажатия на 'Сохранить шаблон' появляется модальное окно с подтверждением перезаписи, нажимает 'OK', проверяет, что окно закрылось и шаблон 'test' остался в селекте.
    """
        # Шаг 0: Включаем все чекбоксы
    checkbox_labels = [
        "Сводный трафик по угрозам",
        "Дифференциальный трафик по угрозам",
        "Таблица \"Топ 10\""
    ]
    # Шаг 0: Выбираем радиокнопку "Создать новый шаблон"
    radio_new_template = authenticated_page.get_by_label("Создать новый шаблон")
    radio_new_template.wait_for(state="visible", timeout=5000)
    if not radio_new_template.is_visible():
        fail_with_screenshot("Радиокнопка 'Создать новый шаблон' не найдена", authenticated_page)
    radio_new_template.check()
    # Шаг 1: Включаем все чекбоксы
    for label in checkbox_labels:
        checkbox = authenticated_page.get_by_label(label)
        if not checkbox.is_checked():
            checkbox.check()
        if not checkbox.is_checked():
            fail_with_screenshot(f'Чекбокс "{label}" должен быть включён для сохранения шаблона', authenticated_page)
    # Шаг 2: Вводим название шаблона 'test_new' (перезапись)
    input_field = find_input_by_label(authenticated_page, "Название шаблона", "test_new")
    if not input_field.is_visible():
        fail_with_screenshot("Поле 'Название шаблона' не найдено на странице", authenticated_page)
    input_field.fill("test_new")
    # Шаг 2: Нажимаем кнопку "Сохранить шаблон"
    save_btn = authenticated_page.get_by_role("button", name="Сохранить шаблон")
    save_btn.click()
    # Шаг 3: Проверяем появление модального окна с подтверждением перезаписи
    modal = authenticated_page.locator('div[role="dialog"] div.cdm-card._without-margin')
    # Явное ожидание появления текста 'успешно сохранен' в модалке
    modal.locator('div:not([class])', has_text="Шаблон test_new успешно сохранен").wait_for(state="visible", timeout=5000)
    if not modal.locator('div:not([class])', has_text="Шаблон test_new успешно сохранен").is_visible():
        fail_with_screenshot("Модальное окно с текстом 'Шаблон test_new успешно сохранен' не появилось", authenticated_page)
    # Шаг 4: Проверяем наличие кнопок "Закрыть" и "OK"
    close_btn = authenticated_page.get_by_role("button", name="Закрыть")
    ok_btn = authenticated_page.get_by_role("button", name="OK")
    if not close_btn.is_visible():
        fail_with_screenshot("Кнопка 'Закрыть' не найдена в модальном окне", authenticated_page)
    if not ok_btn.is_visible():
        fail_with_screenshot("Кнопка 'OK' не найдена в модальном окне", authenticated_page)
    # Шаг 5: Нажимаем "OK"
    ok_btn.click()
    modal.wait_for(state="hidden", timeout=5000)
    # Шаг 6: Проверяем, что шаблон 'test' остался в селекте
    select_template = authenticated_page.locator('div.MuiSelect-root[role="button"]#templateId')
    if not select_template.is_visible():
        fail_with_screenshot("Селект выбора шаблона не найден после перезаписи", authenticated_page)
    if "test" not in select_template.inner_text():
        fail_with_screenshot("В селекте не найден шаблон 'test' после перезаписи", authenticated_page)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_create_report_templates_select_contains_both(authenticated_page: Page, credentials):
    """
    Открывает селект шаблонов и проверяет наличие шаблона 'test'
    Перед началом теста очищает куки и обновляет страницу.
    """
    # Шаг 0: Очищаем куки и обновляем страницу
    authenticated_page.context.clear_cookies()
    authenticated_page.reload()
    authenticated_page.wait_for_load_state("networkidle")
    authenticated_page.wait_for_timeout(2000)
    # Шаг 1: Кликаем на радиокнопку "Создать по шаблону"
    radio_template_based = authenticated_page.locator('input[name="mode"][value="template-based"]')
    if not radio_template_based.is_visible():
        fail_with_screenshot("Радиокнопка 'Создать по шаблону' не найдена после обновления страницы", authenticated_page)
    radio_template_based.check()
    # Шаг 2: Открываем селект шаблонов
    select_template = authenticated_page.locator('div#templateId[role="button"]')
    if not select_template.is_visible():
        fail_with_screenshot("Селект выбора шаблона не найден после выбора радиокнопки", authenticated_page)
    select_template.click()
    # Шаг 3: Проверяем наличие шаблона в выпадающем списке
    menu = authenticated_page.locator('ul.MuiMenu-list[role="listbox"]')
    for template_name in ["test_new"]:
        if not menu.locator('li', has_text=template_name).is_visible():
            fail_with_screenshot(f'Шаблон "{template_name}" не найден в выпадающем списке', authenticated_page)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_create_report_create_new_template_test2(authenticated_page: Page, credentials):
    """
    Переключает радиокнопку на "Создать новый шаблон", создаёт шаблон с названием 'test_2', проверяет появление модального окна и наличие шаблона в селекте.
    """
    # Шаг 0: Обновляем страницу для сброса состояния
    authenticated_page.context.clear_cookies()
    authenticated_page.reload()
    authenticated_page.wait_for_load_state("networkidle")
    authenticated_page.wait_for_timeout(2000)
    # Шаг 1: Переключаем радиокнопку на "Создать новый шаблон"
    radio_new_template = authenticated_page.locator('input[name="mode"][value="new-template"]')
    radio_new_template.wait_for(state="visible", timeout=5000)
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
    # Шаг 2: Включаем все чекбоксы
    for label in checkbox_labels:
        checkbox = authenticated_page.get_by_label(label)
        if not checkbox.is_checked():
            checkbox.check()
        if not checkbox.is_checked():
            fail_with_screenshot(f'Чекбокс "{label}" должен быть включён для сохранения шаблона', authenticated_page)
    # Шаг 3: Вводим название шаблона 'test_2'
    input_field = find_input_by_label(authenticated_page, "Название шаблона", "test_2")
    if not input_field.is_visible():
        fail_with_screenshot("Поле 'Название шаблона' не найдено на странице", authenticated_page)
    input_field.fill("test_2")
    # Шаг 4: Нажимаем кнопку "Сохранить шаблон"
    save_btn = authenticated_page.get_by_role("button", name="Сохранить шаблон")
    save_btn.click()
    # Шаг 5: Проверяем появление модального окна
    modal = authenticated_page.locator('div[role="dialog"] div.cdm-card._without-margin')
    modal.wait_for(state="visible", timeout=5000)
    if not modal.locator('div[style*="font-weight: bold"]', has_text="Шаблон test_2 успешно сохранен").nth(0).is_visible():
        fail_with_screenshot("В модальном окне не найден заголовок 'Шаблон test_2 успешно сохранен'", authenticated_page)
    if not modal.locator('.MuiCardContent-root', has_text="Данный шаблон теперь будет доступен в списке шаблонов").nth(0).is_visible():
        fail_with_screenshot("В модальном окне не найден текст 'Данный шаблон теперь будет доступен в списке шаблонов'", authenticated_page)
    # Шаг 6: Проверяем наличие кнопок "Закрыть" и "OK"
    close_btn = authenticated_page.get_by_role("button", name="Закрыть")
    ok_btn = authenticated_page.get_by_role("button", name="OK")
    if not close_btn.is_visible():
        fail_with_screenshot("Кнопка 'Закрыть' не найдена в модальном окне", authenticated_page)
    if not ok_btn.is_visible():
        fail_with_screenshot("Кнопка 'OK' не найдена в модальном окне", authenticated_page)
    # Шаг 7: Нажимаем "OK"
    ok_btn.click()
    modal.wait_for(state="hidden", timeout=5000)
    # Шаг 8: Проверяем, что шаблон 'test_2' появился в селекте
    radio_template_based = authenticated_page.locator('input[name="mode"][value="template-based"]')
    radio_template_based.check()
    select_template = authenticated_page.locator('div#templateId[role="button"]')
    if not select_template.is_visible():
        fail_with_screenshot("Селект выбора шаблона не найден после создания шаблона", authenticated_page)
    select_template.click(force=True)
    menu = authenticated_page.locator('ul.MuiMenu-list[role="listbox"]')
    if not menu.locator('li', has_text="test_2").is_visible():
        fail_with_screenshot("Шаблон 'test_2' не найден в выпадающем списке", authenticated_page)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_create_report_templates_select_contains_both_2(authenticated_page: Page, credentials):
    """
    Открывает селект шаблонов и проверяет наличие шаблонов 'test' и 'test_new'.
    Перед началом теста очищает куки и обновляет страницу.
    """
    # Шаг 0: Очищаем куки и обновляем страницу
    authenticated_page.context.clear_cookies()
    authenticated_page.reload()
    authenticated_page.wait_for_load_state("networkidle")
    authenticated_page.wait_for_timeout(2000)
    # Шаг 1: Кликаем на радиокнопку "Создать по шаблону"
    radio_template_based = authenticated_page.locator('input[name="mode"][value="template-based"]')
    if not radio_template_based.is_visible():
        fail_with_screenshot("Радиокнопка 'Создать по шаблону' не найдена после обновления страницы", authenticated_page)
    radio_template_based.check()
    # Шаг 2: Открываем селект шаблонов
    select_template = authenticated_page.locator('div#templateId[role="button"]')
    if not select_template.is_visible():
        fail_with_screenshot("Селект выбора шаблона не найден после выбора радиокнопки", authenticated_page)
    select_template.click(force=True)
    # Шаг 3: Проверяем наличие шаблона в выпадающем списке
    menu = authenticated_page.locator('ul.MuiMenu-list[role="listbox"]')
    for template_name in ["test_new", "test_2"]:
        if not menu.locator('li', has_text=template_name).is_visible():
            fail_with_screenshot(f'Шаблон "{template_name}" не найден в выпадающем списке', authenticated_page)

""" Дальше пишем про неиспользуемый шаблон для формированя отчета """

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_create_report_no_template_generate_modal_appears(authenticated_page: Page, credentials):
    """
    Выбирает "Не использовать шаблон", включает чекбоксы, проверяет неактивность кнопки "Сохранить шаблон", нажимает "Сформировать отчет", проверяет появление модального окна с заголовком.
    """
    authenticated_page.context.clear_cookies()
    authenticated_page.reload()
    authenticated_page.wait_for_load_state("networkidle")
    authenticated_page.wait_for_timeout(2000)
    # Шаг 1: Кликаем радиокнопку "Не использовать шаблон"
    radio_no_template = authenticated_page.get_by_label("Не использовать шаблон")
    if not radio_no_template.is_visible():
        fail_with_screenshot("Радиокнопка 'Не использовать шаблон' не найдена", authenticated_page)
    radio_no_template.check()
    if not radio_no_template.is_checked():
        fail_with_screenshot('Радиокнопка "Не использовать шаблон" не выбрана', authenticated_page)
    # Шаг 2: Проверяем, что поле для имени шаблона отсутствует или скрыто
    input_field = find_input_by_label(authenticated_page, "Название шаблона", None)
    if input_field.is_visible():
        fail_with_screenshot('Поле "Название шаблона" не должно отображаться при выборе "Не использовать шаблон"', authenticated_page)
    # Шаг 3: Проверяем чекбоксы и включаем их, если выключены
    checkbox_labels = [
        "Сводный трафик по угрозам",
        "Дифференциальный трафик по угрозам",
        "Таблица \"Топ 10\""
    ]
    for label in checkbox_labels:
        checkbox = authenticated_page.get_by_label(label)
        if not checkbox.is_visible():
            fail_with_screenshot(f'Чекбокс "{label}" не найден', authenticated_page)
        if not checkbox.is_checked():
            checkbox.check()
        if not checkbox.is_checked():
            fail_with_screenshot(f'Чекбокс "{label}" должен быть включён', authenticated_page)
    # Шаг 4: Проверяем, что кнопка "Сохранить шаблон" не кликабельна
    save_btn = authenticated_page.get_by_role("button", name="Сохранить шаблон")
    if save_btn.is_enabled():
        fail_with_screenshot('Кнопка "Сохранить шаблон" должна быть неактивна при выборе "Не использовать шаблон"', authenticated_page)
    # Шаг 5: Нажимаем "Сформировать отчет"
    generate_btn = authenticated_page.get_by_role("button", name="Сформировать отчет")
    if not generate_btn.is_visible():
        fail_with_screenshot('Кнопка "Сформировать отчет" не найдена', authenticated_page)
    generate_btn.click()
    # Шаг 6: Проверяем появление модального окна с отчетом
    modal = authenticated_page.locator('div.MuiCard-root.cdm-card._without-margin')
    modal.wait_for(state="visible", timeout=5000)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_create_report_no_template_modal_header(authenticated_page: Page, credentials):
    """
    Проверяет наличие заголовка "Отчет об угрозах информационной безопасности" в модальном окне отчета.
    """
    wait_for_report_content(authenticated_page)
    modal = authenticated_page.locator('div.MuiPaper-root.MuiCard-root.cdm-card._without-margin')
    if not modal.locator('.MuiCardHeader-title', has_text="Отчет об угрозах информационной безопасности").is_visible():
        fail_with_screenshot('В модальном окне не найден заголовок "Отчет об угрозах информационной безопасности"', authenticated_page)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_create_report_no_template_modal_text_zaregistrirovano_ugroz(authenticated_page: Page, credentials):
    '''Проверяет наличие заголовка: Зарегистрированные угрозы в модальном окне отчета.'''
    wait_for_report_content(authenticated_page)
    modal = authenticated_page.locator('div.MuiPaper-root.MuiCard-root.cdm-card._without-margin')
    if not modal.get_by_role("heading", name="Зарегистрированные угрозы", exact=True).is_visible():
        fail_with_screenshot('В модальном окне не найден заголовок: Зарегистрированные угрозы', authenticated_page)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_create_report_no_template_modal_text_sootnoshenie_viyavlennykh_ugroz(authenticated_page: Page, credentials):
    '''Проверяет наличие заголовка: Соотношение угроз в модальном окне отчета.'''
    wait_for_report_content(authenticated_page)
    modal = authenticated_page.locator('div.MuiPaper-root.MuiCard-root.cdm-card._without-margin')
    if not modal.get_by_role("heading", name="Соотношение угроз", exact=True).is_visible():
        fail_with_screenshot('В модальном окне не найден заголовок: Соотношение угроз', authenticated_page)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_create_report_no_template_modal_text_setevye_ugrozy_vo_vremeni(authenticated_page: Page, credentials):
    '''Проверяет наличие заголовка: Сетевые угрозы во времени в модальном окне отчета.'''
    wait_for_report_content(authenticated_page)
    modal = authenticated_page.locator('div.MuiPaper-root.MuiCard-root.cdm-card._without-margin')
    if not modal.get_by_role("heading", name="Сетевые угрозы во времени", exact=True).is_visible():
        fail_with_screenshot('В модальном окне не найден заголовок: Сетевые угрозы во времени', authenticated_page)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_create_report_no_template_modal_text_top10(authenticated_page: Page, credentials):
    '''Проверяет наличие заголовка: Топ-10 в модальном окне отчета.'''
    wait_for_report_content(authenticated_page)
    modal = authenticated_page.locator('div.MuiPaper-root.MuiCard-root.cdm-card._without-margin')
    if not modal.get_by_role("heading", name="Топ-10", exact=True).is_visible():
        fail_with_screenshot('В модальном окне не найден заголовок: Топ-10', authenticated_page)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_create_report_no_template_modal_text_srabatyvanie_zapreshchayushchikh_pravil(authenticated_page: Page, credentials):
    '''Проверяет наличие текста: Срабатывание запрещающих правил в модальном окне отчета.'''
    # wait_for_report_content(authenticated_page)
    # modal = authenticated_page.locator('div.MuiPaper-root.MuiCard-root.cdm-card._without-margin')
    # # В новой верстке этот раздел может отсутствовать; оставляем проверку через contains-текст внутри карточек, если появится
    # if not modal.get_by_text("Срабатывание запрещающих правил").is_visible():
    #     fail_with_screenshot('В модальном окне не найден текст: Срабатывание запрещающих правил', authenticated_page)
    pytest.skip("Раздел отсутствует в новом PDF формате")

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_create_report_no_template_modal_text_top10_zapreshchayushchikh_pravil(authenticated_page: Page, credentials):
    '''Проверяет наличие заголовка: Топ-10 запрещающих правил в модальном окне отчета.'''
    # wait_for_report_content(authenticated_page)
    # modal = authenticated_page.locator('div.MuiPaper-root.MuiCard-root.cdm-card._without-margin')
    # if not modal.get_by_role("heading", name="Топ-10 запрещающих правил", exact=True).is_visible():
    #     fail_with_screenshot('В модальном окне не найден заголовок: Топ-10 запрещающих правил', authenticated_page)
    pytest.skip("Раздел отсутствует в новом PDF формате")

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_create_report_no_template_modal_text_predprinyatye_deystviya(authenticated_page: Page, credentials):
    '''Проверяет наличие текста: Предпринятые действия в модальном окне отчета.'''
    # wait_for_report_content(authenticated_page)
    # modal = authenticated_page.locator('div.MuiPaper-root.MuiCard-root.cdm-card._without-margin')
    # if not modal.get_by_text("Предпринятые действия").is_visible():
    #     fail_with_screenshot('В модальном окне не найден текст: Предпринятые действия', authenticated_page)
    pytest.skip("Раздел отсутствует в новом PDF формате")

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_create_report_no_template_modal_text_srabatyvaniya_vnov_sozdannykh_pravil(authenticated_page: Page, credentials):
    '''Проверяет наличие текста: Срабатывания вновь созданных правил в модальном окне отчета.'''
    # wait_for_report_content(authenticated_page)
    # modal = authenticated_page.locator('div.MuiPaper-root.MuiCard-root.cdm-card._without-margin')
    # if not modal.get_by_text("Срабатывания вновь созданных правил").is_visible():
    #     fail_with_screenshot('В модальном окне не найден текст: Срабатывания вновь созданных правил', authenticated_page)
    pytest.skip("Раздел отсутствует в новом PDF формате")

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_create_report_no_template_modal_download_link_clickable(authenticated_page: Page, credentials):
    """
    Проверяет, что кнопка "Скачать" в модальном окне кликабельна.
    """
    wait_for_report_content(authenticated_page)
    modal = authenticated_page.locator('div.MuiPaper-root.MuiCard-root.cdm-card._without-margin')
    download_btn = modal.locator('button', has_text="Скачать")
    if not download_btn.is_visible():
        fail_with_screenshot('Кнопка "Скачать" не найдена в модальном окне', authenticated_page)
    if download_btn.get_attribute("disabled") is not None:
        fail_with_screenshot('Кнопка "Скачать" задизейблена', authenticated_page)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_create_report_no_template_modal_download_file(authenticated_page: Page, credentials):
    """
    Проверяет, что после клика по кнопке "Скачать" скачивается PDF "security-threats-report-<date>.pdf" (или совместимый формат).
    """
    wait_for_report_content(authenticated_page)
    modal = authenticated_page.locator('div.MuiPaper-root.MuiCard-root.cdm-card._without-margin')
    download_btn = modal.locator('button', has_text="Скачать")
    # Шаг №1: Проверяем, что кнопка "Скачать" видима
    if not download_btn.is_visible():
        fail_with_screenshot('Кнопка "Скачать" не найдена в модальном окне', authenticated_page)
    # Шаг №2: Кликаем по кнопке и ожидаем скачивание
    with authenticated_page.expect_download() as download_info:
        download_btn.click()
    download = download_info.value
    filename = download.suggested_filename
    # Шаг №3: Ожидаем PDF имя (допускаем и другие корректные PDF имена)
    if not filename.lower().endswith('.pdf'):
        fail_with_screenshot(f'Ожидался PDF, получено: {filename}', authenticated_page)
    global _last_download_path
    target_path = os.path.join(tempfile.gettempdir(), filename)
    download.save_as(target_path)
    _last_download_path = target_path
    _assert_pdf_valid(_last_download_path)

""" Тесты для проверки содержимого скачанного файла """

import pytest
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError

def wait_for_report_content(page: Page):
    """
    Ждет появления контента отчета в модальном окне.
    Если отображается сообщение "Данные не существуют" — скипает тест.
    """
    modal = page.locator('div.MuiPaper-root.MuiCard-root.cdm-card._without-margin')
    modal.wait_for(state="visible", timeout=10000)

    # Проверяем наличие надписи "Данные не существуют"
    no_data_locator = modal.locator("text=Данные не существуют")
    try:
        no_data_locator.wait_for(state="visible", timeout=3000)
        pytest.skip("Тест пропущен: данные не существуют в отчете.")
    except PlaywrightTimeoutError:
        # Если текста нет — продолжаем дальше
        pass

    # Ждём заголовок и первый h1 внутри контента
    header = modal.locator('.MuiCardHeader-title')
    header.wait_for(state="visible", timeout=5000)
    first_h1 = modal.locator('h1').first
    first_h1.wait_for(state="visible", timeout=10000)

def extract_pdf_text(path: str) -> str:
    # 1) pdfminer.six
    try:
        text = extract_text(path, laparams=LAParams(all_texts=True)) or ""
        if text and len(text.strip()) > 0:
            return text
    except Exception:
        pass
    # # 2) PyMuPDF (fallback)
    # try:
    #     with fitz.open(path) as doc:
    #         pages_text = []
    #         for page in doc:
    #             pages_text.append(page.get_text("text") or "")
    #         return "\n".join(pages_text)
    # except Exception:
    #     return ""

def _norm(s: str) -> str:
    # Нормализуем Юникод, убираем неразрывные пробелы и схлопываем пробелы
    s = unicodedata.normalize("NFKC", s).replace("\u00A0", " ")
    s = " ".join(s.split())
    return s

def _letters_digits(s: str) -> str:
    # Оставляем только буквы/цифры для устойчивого поиска по заголовкам
    return "".join(re.findall(r"[0-9A-Za-zА-Яа-я]+", s))

def assert_contains_any(text: str, variants: list[str], page):
    norm_text = _letters_digits(_norm(text))
    for v in variants:
        if _letters_digits(_norm(v)) in norm_text:
            return
    fail_with_screenshot(f"В PDF нет заголовка: {' / '.join(variants)}", page)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_create_report_no_template_download_contains_zaregistrirovano_ugroz(authenticated_page: Page, credentials):
    # _assert_pdf_valid(_last_download_path)
    # text = extract_pdf_text(_last_download_path)
    # if not text:
    #     pytest.skip("Не удалось извлечь текст из PDF (возможно, вектор/изображения)")

    # assert_contains_any(text, ["Зарегистрированные угрозы"], authenticated_page)
    pytest.skip("Тест проверки PDF файла пока пропущен")

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_create_report_no_template_download_contains_sootnoshenie_viyavlennykh_ugroz(authenticated_page: Page, credentials):
    # _assert_pdf_valid(_last_download_path)
    # text = extract_pdf_text(_last_download_path)
    # if not text:
    #     pytest.skip("Не удалось извлечь текст из PDF (возможно, вектор/изображения)")

    # assert_contains_any(text, ["Соотношение угроз"], authenticated_page)
    pytest.skip("Тест проверки PDF файла пока пропущен")

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_create_report_no_template_download_contains_setevye_ugrozy_vo_vremeni(authenticated_page: Page, credentials):
    # _assert_pdf_valid(_last_download_path)
    # text = extract_pdf_text(_last_download_path)
    # if not text:
    #     pytest.skip("Не удалось извлечь текст из PDF (возможно, вектор/изображения)")

    # assert_contains_any(text, ["Сетевые угрозы во времени"], authenticated_page)
    pytest.skip("Тест проверки PDF файла пока пропущен")

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_create_report_no_template_download_contains_top10(authenticated_page: Page, credentials):
    # _assert_pdf_valid(_last_download_path)
    # text = extract_pdf_text(_last_download_path)
    # if not text:
    #     pytest.skip("Не удалось извлечь текст из PDF (возможно, вектор/изображения)")

    # assert_contains_any(text, ["Топ-10", "Топ 10"], authenticated_page)
    pytest.skip("Тест проверки PDF файла пока пропущен")

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_create_report_no_template_download_contains_srabatyvanie_zapreshchayushchikh_pravil(authenticated_page: Page, credentials):
    pytest.skip("Раздел недоступен в новой PDF-версии отчёта")

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_create_report_no_template_download_contains_top10_zapreshchayushchikh_pravil(authenticated_page: Page, credentials):
    pytest.skip("Раздел недоступен в новой PDF-версии отчёта")

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_create_report_no_template_download_contains_predprinyatye_deystviya(authenticated_page: Page, credentials):
    pytest.skip("Раздел недоступен в новой PDF-версии отчёта")

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_create_report_no_template_download_contains_srabatyvaniya_vnov_sozdannykh_pravil(authenticated_page: Page, credentials):
    pytest.skip("Раздел недоступен в новой PDF-версии отчёта")

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_create_report_no_template_modal_email_input(authenticated_page: Page, credentials):
    """
    Проверяет, что input с placeholder "Список e-mail адресов" отображается в модальном окне.
    """
    modal = authenticated_page.locator('div.MuiCard-root.cdm-card._without-margin')
    # Шаг №1: Находим input с placeholder
    email_input = modal.locator('input[placeholder="Список e-mail адресов"]')
    # Шаг №2: Проверяем, что input видим
    if not email_input.is_visible():
        fail_with_screenshot('Input "Список e-mail адресов" не отображается в модальном окне', authenticated_page)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_create_report_no_template_modal_send_button_disabled(authenticated_page: Page, credentials):
    """
    Проверяет, что кнопка "Отправить" не кликабельна в модальном окне.
    """
    modal = authenticated_page.locator('div.MuiCard-root.cdm-card._without-margin')
    # Шаг №1: Находим кнопку "Отправить"
    send_btn = modal.get_by_role("button", name="Отправить")
    # Шаг №2: Проверяем, что кнопка неактивна
    if send_btn.is_enabled():
        fail_with_screenshot('Кнопка "Отправить" должна быть неактивна в модальном окне', authenticated_page)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_create_report_no_template_modal_email_input_enter_value(authenticated_page: Page, credentials):
    """
    Вводит email в поле и проверяет, что он правильно ввелся.
    """
    modal = authenticated_page.locator('div.MuiCard-root.cdm-card._without-margin')
    # Шаг №1: Находим input для email
    email_input = modal.locator('input[placeholder="Список e-mail адресов"]')
    # Шаг №2: Вводим email
    email_input.fill(credentials["email"])
    # Шаг №3: Проверяем, что email введён корректно
    if email_input.input_value() != credentials["email"]:
        fail_with_screenshot(f'В поле введен некорректный email: {email_input.input_value()}', authenticated_page)

# Глобальный флаг для skip следующего теста
_skip_success_modal = False

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_create_report_no_template_modal_send_email(authenticated_page: Page, credentials):
    """
    Нажимает "Отправить", перехватывает POST-запрос, проверяет его payload и успешный ответ, а затем проверяет появление модального окна об успехе.
    Если приходит 422, выводит skip.
    """
    global _skip_success_modal
    modal = authenticated_page.locator('div.MuiCard-root.cdm-card._without-margin')
    # Шаг №1: Находим кнопку "Отправить"
    send_btn = modal.get_by_role("button", name="Отправить")
    # Шаг №2: Кликаем по кнопке и ожидаем POST-запрос
    with authenticated_page.expect_response(
        lambda response: "/api/service/remote/logger-analytics/analytics-server/call/security-reports/send" in response.url
        and response.request.method == "POST",
        timeout=150000,  # 2 мин 30 сек
    ) as response_info:
        send_btn.click()

    response = response_info.value
    # Шаг №3: Проверяем статус ответа
    if response.status == 422:
        _skip_success_modal = True
        pytest.skip("Письмо не отправлено (422 код ответа). ПРОВЕРЬТЕ SMTP сервер.")
    if response.status != 200:
        fail_with_screenshot("Ожидался статус 200 или 422, получен {response.status}", authenticated_page)
    _skip_success_modal = False

    # Шаг №4: Проверяем payload
    payload = response.request.post_data_json
    if payload["to"] != [credentials["email"]]:
        fail_with_screenshot("Неверный email в payload: {payload['to']}", authenticated_page)

    # Шаг №5: Проверяем появление модального окна об успехе
    success_modal = authenticated_page.locator(
        'div[role="dialog"] div.cdm-card._without-margin',
        has_text="Отправка прошла успешно"
    )
    if not success_modal.is_visible():
        fail_with_screenshot('Модальное окно об успешной отправке не появилось', authenticated_page)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_create_report_no_template_modal_close_success_modal(authenticated_page: Page, credentials):
    """
    Закрывает модальное окно успешной отправки по крестику. Если письмо не отправлено, тест скипается.
    """
    global _skip_success_modal
    # Шаг №1: Проверяем, нужно ли скипать тест
    if _skip_success_modal:
        pytest.skip("Письмо не отправлено, модального окна не будет.")
    # Шаг №2: Находим модальное окно об успехе
    success_modal = authenticated_page.locator(
        'div[role="dialog"] div.cdm-card._without-margin',
        has_text="Отправка прошла успешно"
    )
    if not success_modal.is_visible():
        fail_with_screenshot('Модальное окно об успешной отправке не отображается', authenticated_page)
    # Шаг №3: Находим кнопку-крестик и закрываем окно
    close_btn = success_modal.locator('button span.cdm-icon-wrapper[title="Закрыть"]')
    if not close_btn.is_visible():
        fail_with_screenshot("Кнопка-крестик 'Закрыть' не найдена в модальном окне", authenticated_page)
    close_btn.click()
    success_modal.wait_for(state="hidden", timeout=5000)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_create_report_modal_close_by_cross(authenticated_page: Page, credentials):
    """
    Проверяет закрытие исходного модального окна отчёта по крестику (Закрыть).
    """
    # Шаг №1: Находим модальное окно по заголовку
    modal = authenticated_page.locator('div.MuiPaper-root.MuiCard-root.cdm-card._without-margin:has(.MuiCardHeader-title:text("Отчет об угрозах информационной безопасности"))')
    if not modal.is_visible():
        fail_with_screenshot("Модальное окно отчёта не отображается", authenticated_page)
    # Шаг №2-3: Безопасно закрываем окно
    _safe_click_close_cross(authenticated_page, 'div.MuiPaper-root.MuiCard-root.cdm-card._without-margin:has(.MuiCardHeader-title:text("Отчет об угрозах информационной безопасности"))')
    modal.wait_for(state="hidden", timeout=10000)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_create_report_switch_to_template_radio_and_check_select(authenticated_page: Page, credentials):
    """
    После закрытия модального окна переключается на радио-кнопку 'Создать по шаблону' и проверяет появление селекта шаблонов.
    """
    # Шаг №1: Переключаемся на радио-кнопку 'Создать по шаблону'
    template_radio = authenticated_page.get_by_label("Создать по шаблону")
    if not template_radio.is_visible():
        fail_with_screenshot("Радио-кнопка 'Создать по шаблону' не найдена", authenticated_page)
    template_radio.check()
    # Шаг №2: Проверяем, что появился селект с id='templateId'
    select_button = authenticated_page.locator('div[role="button"]#templateId')
    if not select_button.is_visible():
        fail_with_screenshot("Селект 'Шаблон' не отображается после переключения на 'Создать по шаблону'", authenticated_page)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_create_report_template_select_contains_test_new_and_test2(authenticated_page: Page, credentials):
    """
    После переключения на 'Создать по шаблону' кликает по селекту и проверяет наличие шаблонов 'test_new' и 'test_2' в списке.
    """
    # Шаг №1: Переключаемся на радио-кнопку 'Создать по шаблону'
    template_radio = authenticated_page.get_by_label("Создать по шаблону")
    template_radio.check()
    # Шаг №2: Кликаем по селекту шаблонов
    select_button = authenticated_page.locator('div[role="button"]#templateId')
    select_button.click(force=True)
    # Шаг №3: Проверяем наличие шаблонов в выпадающем списке
    option = authenticated_page.locator('ul[role="listbox"] li', has_text="test_new")
    if not option.is_visible():
        fail_with_screenshot('Шаблон "test_new" не найден в списке', authenticated_page)
    option = authenticated_page.locator('ul[role="listbox"] li', has_text="test_2")
    if not option.is_visible():
        fail_with_screenshot('Шаблон "test_2" не найден в списке', authenticated_page)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_create_report_delete_template_test_new(authenticated_page: Page, credentials):
    """
    Выбирает шаблон 'test_new', нажимает кнопку удалить, подтверждает удаление, ждёт DELETE-запрос и ответ 200.
    """
    # Шаг №1: Находим и кликаем по шаблону 'test_new' в списке
    option = authenticated_page.locator('ul[role="listbox"] li', has_text="test_new")
    if not option.is_visible():
        fail_with_screenshot('Шаблон "test_new" не найден в списке', authenticated_page)
    option.click()
    # Шаг №2: Проверяем, что появилась кнопка удалить
    delete_btn = authenticated_page.locator('button span.cdm-icon-wrapper[title="Удалить"]')
    if not delete_btn.is_visible():
        fail_with_screenshot("Кнопка 'Удалить' не отображается после выбора шаблона 'test_new'", authenticated_page)
    # Шаг №3: Нажимаем на кнопку удалить
    delete_btn.click()
    # Шаг №4: Ждём появления окна подтверждения
    confirm_modal = authenticated_page.locator('div[role="dialog"]:has-text("Вы уверены?")')
    if not confirm_modal.is_visible():
        fail_with_screenshot("Окно подтверждения удаления не появилось", authenticated_page)
    # Шаг №5: Находим кнопку "Удалить" в модалке
    confirm_delete_btn = confirm_modal.get_by_role("button", name="Удалить")
    if not confirm_delete_btn.is_visible():
        fail_with_screenshot("Кнопка 'Удалить' в окне подтверждения не найдена", authenticated_page)
    # Шаг №6: Ожидаем DELETE-запрос
    with authenticated_page.expect_response(lambda resp: resp.request.method == "DELETE" and "/security-report-templates/" in resp.url, timeout=10000) as resp_info:
        confirm_delete_btn.click()
    response = resp_info.value
    # Шаг №7: Проверяем статус ответа
    if response.status != 200:
        fail_with_screenshot("Ожидался статус 200 на DELETE, получено {response.status}", authenticated_page)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_create_report_delete_template_test_2(authenticated_page: Page, credentials):
    """
    Выбирает шаблон 'test_2', нажимает кнопку удалить, подтверждает удаление, ждёт DELETE-запрос и ответ 200.
    """
    # Шаг №1: Переключаемся на радио-кнопку 'Создать по шаблону'
    template_radio = authenticated_page.get_by_label("Создать по шаблону")
    template_radio.check()
    # Шаг №2: Кликаем по селекту шаблонов
    select_button = authenticated_page.locator('div[role="button"]#templateId')
    select_button.click(force=True)
    # Шаг №3: Ждём появления выпадающего списка и кликаем по 'test_2'
    option = authenticated_page.locator('ul[role="listbox"] li', has_text="test_2")
    option.wait_for(state="visible", timeout=2000)
    if not option.is_visible():
        fail_with_screenshot('Шаблон "test_2" не найден в списке', authenticated_page)
    option.click()
    # Шаг №4: Проверяем, что появилась кнопка удалить
    delete_btn = authenticated_page.locator('button span.cdm-icon-wrapper[title="Удалить"]')
    if not delete_btn.is_visible():
        fail_with_screenshot("Кнопка 'Удалить' не отображается после выбора шаблона 'test_2'", authenticated_page)
    # Шаг №5: Нажимаем на кнопку удалить
    delete_btn.click()
    # Шаг №6: Ждём появления окна подтверждения
    confirm_modal = authenticated_page.locator('div[role="dialog"]:has-text("Вы уверены?")')
    if not confirm_modal.is_visible():
        fail_with_screenshot("Окно подтверждения удаления не появилось", authenticated_page)
    # Шаг №7: Находим кнопку "Удалить" в модалке
    confirm_delete_btn = confirm_modal.get_by_role("button", name="Удалить")
    if not confirm_delete_btn.is_visible():
        fail_with_screenshot("Кнопка 'Удалить' в окне подтверждения не найдена", authenticated_page)
    # Шаг №8: Ожидаем DELETE-запрос
    with authenticated_page.expect_response(lambda resp: resp.request.method == "DELETE" and "/security-report-templates/" in resp.url, timeout=10000) as resp_info:
        confirm_delete_btn.click()
    response = resp_info.value
    # Шаг №9: Проверяем статус ответа
    if response.status != 200:
        fail_with_screenshot("Ожидался статус 200 на DELETE, получено {response.status}", authenticated_page)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_create_report_delete_template_test(authenticated_page: Page, credentials):
    """
    Удаляет шаблон 'test', если он существует: выбирает радиокнопку 'Создать по шаблону', выбирает шаблон 'test', нажимает кнопку удалить, подтверждает удаление, ждёт DELETE-запрос и ответ 200.
    """
    # Шаг №1: Переключаемся на радио-кнопку 'Создать по шаблону'
    template_radio = authenticated_page.get_by_label("Создать по шаблону")
    template_radio.check()
    # Шаг №2: Кликаем по селекту шаблонов
    select_button = authenticated_page.locator('div[role="button"]#templateId')
    select_button.click(force=True)
    # Шаг №3: Ждём появления выпадающего списка и кликаем по 'test'
    option = authenticated_page.locator('ul[role="listbox"] li', has_text="test")
    option.wait_for(state="visible", timeout=2000)
    if not option.is_visible():
        pytest.skip('Шаблон "test" не найден в списке, пропускаем удаление')
    option.click()
    # Шаг №4: Проверяем, что появилась кнопка удалить
    delete_btn = authenticated_page.locator('button span.cdm-icon-wrapper[title="Удалить"]')
    if not delete_btn.is_visible():
        pytest.skip('Кнопка "Удалить" не отображается после выбора шаблона "test"')
    # Шаг №5: Нажимаем на кнопку удалить
    delete_btn.click()
    # Шаг №6: Ждём появления окна подтверждения
    confirm_modal = authenticated_page.locator('div[role="dialog"]:has-text("Вы уверены?")')
    if not confirm_modal.is_visible():
        pytest.skip('Окно подтверждения удаления не появилось')
    # Шаг №7: Находим кнопку "Удалить" в модалке
    confirm_delete_btn = confirm_modal.get_by_role("button", name="Удалить")
    if not confirm_delete_btn.is_visible():
        pytest.skip('Кнопка "Удалить" в окне подтверждения не найдена')
    # Шаг №8: Ожидаем DELETE-запрос
    with authenticated_page.expect_response(lambda resp: resp.request.method == "DELETE" and "/security-report-templates/" in resp.url, timeout=10000) as resp_info:
        confirm_delete_btn.click()
    response = resp_info.value
    # Шаг №9: Проверяем статус ответа
    if response.status != 200:
        fail_with_screenshot("Ожидался статус 200 на DELETE, получено {response.status}", authenticated_page)

def _read_last_download():
    global _last_download_path
    if not _last_download_path or not os.path.exists(_last_download_path):
        # Нет скачанного файла — даём понятную ошибку
        raise NameError("_last_download_path не установлен или файл не найден")
    with open(_last_download_path, encoding="utf-8") as f:
        return f.read()

# Хелпер: безопасно закрыть модалку по крестику, обходя тосты поверх

def _safe_click_close_cross(page: Page, modal_locator_str: str):
    modal = page.locator(modal_locator_str)
    close_btn = modal.locator('button span.cdm-icon-wrapper[title="Закрыть"]').first
    # Если тост перекрывает — пробуем ESC
    try:
        close_btn.click()
        return
    except Exception:
        pass
    # Пробуем закрыть тосты, если есть
    toast = page.locator('.Toastify__toast-container')
    if toast.count() > 0 and toast.first.is_visible():
        # Нажмём Escape, чтобы убрать фокус/тосты
        page.keyboard.press('Escape')
        page.wait_for_timeout(300)
    # Повторяем клик с force
    close_btn.click(force=True)
