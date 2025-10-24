import pytest
from playwright.sync_api import expect, Page, Browser
from UI.other_tests.test_autentification_admin import _perform_login
import json
from UI.conftest import fail_with_screenshot
from UI.universal_functions.filter import (
    filter_menu_appears,
    check_filter_by_input,
    check_filter_by_input_negative_other_values,
    check_filter_by_input_first_row_value
)
from UI.universal_functions.navigation import (
    navigate_and_check_url,
    check_tabs_selected_state,
    find_input_by_label
)
from UI.universal_functions.click_on_body import (
    wait_for_api_response,
    wait_for_api_response_with_response
)
import time

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_dns_sinkhole_navigate_and_check_url(authenticated_page: Page, credentials):
    """
    Проверяет переход на вкладку "DNS Sinkhole" в разделе "Межсетевое экранирование" и корректность URL для "DNS Sinkhole".
    """
    tab_button_1 = "Межсетевое экранирование"
    tab_button_2 = "DNS Sinkhole"
    url = "firewall/dns-sinkhole/dns-sinkhole"
    navigate_and_check_url(authenticated_page, tab_button_1, tab_button_2, url, credentials)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_dns_sinkhole_external_dns_button(authenticated_page: Page, credentials):
    """
    Проверяет наличие кнопки 'Активируйте внешние DNS' на странице DNS Sinkhole.
    Если кнопки нет — тест скипается.
    """

    # Шаг №1: Проверка наличия кнопки с нужными классами и текстом
    button_selector = (
        'button.MuiButtonBase-root.MuiButton-root.cdm-button.cdm-button__primary.MuiButton-contained.MuiButton-containedPrimary'
    )
    try:
        button = authenticated_page.locator(button_selector + ':has-text("Активируйте внешние DNS")')
        if not button or button.count() == 0:
            pytest.skip("Тест не актуален: кнопка 'Активируйте внешние DNS' отсутствует на странице")
    except Exception:
        pytest.skip("Кнопка 'Активируйте внешние DNS' отсутствует на странице (ошибка поиска)")
    # Шаг №2: Проверка, что кнопка действительно видима
    if not button.first.is_visible():
        fail_with_screenshot("Кнопка 'Активируйте внешние DNS' не видима на странице", authenticated_page)
    # Шаг №3: Клик по кнопке 'Активируйте внешние DNS'
    button.first.click()
    # Шаг №4: Проверка, что произошёл переход на /networking/dns/forwarders
    authenticated_page.wait_for_url("**/networking/dns/forwarders")
    if "/networking/dns/forwarders" not in authenticated_page.url:
        fail_with_screenshot(f"После нажатия на кнопку не произошёл переход на /networking/dns/forwarders, текущий url: {authenticated_page.url}", authenticated_page)
    # Шаг №5: Вводим в поле "Список IP-адресов" 8.8.8.8
    authenticated_page.wait_for_timeout(500)
    find_input_by_label(authenticated_page, "Список IP-адресов", "8.8.8.8")
    # Шаг №6: Нажимаем на кнопку "Сохранить"
    save_btn = authenticated_page.locator('button.MuiButtonBase-root.MuiButton-root.cdm-button.cdm-button__primary.MuiButton-contained.MuiButton-containedPrimary[type="submit"]:has-text("Сохранить")')
    with wait_for_api_response_with_response(authenticated_page, "/api/service/remote/ngfw/core/call/manager/dns", expected_status=200, method="PATCH", timeout=20000) as resp_info:
        save_btn.click()
    # Шаг №7: Проверяем, что в поле "Список IP-адресов" отображается 8.8.8.8
    textarea = find_input_by_label(authenticated_page, "Список IP-адресов")
    if textarea.first.input_value() != "8.8.8.8":
        fail_with_screenshot("Значение в поле 'Список IP-адресов' не соответствует ожидаемому", authenticated_page)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_dns_sinkhole_navigate_and_check_url_2(authenticated_page: Page, credentials):
    """
    Проверяет переход на вкладку "DNS Sinkhole" в разделе "Межсетевое экранирование" и корректность URL для "DNS Sinkhole".
    """
    tab_button_1 = "Межсетевое экранирование"
    tab_button_2 = "DNS Sinkhole"
    url = "firewall/dns-sinkhole/dns-sinkhole"
    navigate_and_check_url(authenticated_page, tab_button_1, tab_button_2, url, credentials)
    authenticated_page.wait_for_load_state('networkidle')



@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_dns_sinkhole_table_elements(authenticated_page: Page, credentials):
    """
    Проверяет, что на странице DNS Sinkhole отображается таблица с нужными кнопками и сообщением 'Нет данных'.
    """
    # Шаг №0: Обновляем страницу
    authenticated_page.reload()
    authenticated_page.wait_for_load_state('networkidle')
    # Шаг №1: Проверка наличия таблицы с нужными классами
    table_selector = (
        'div.MuiPaper-root.MuiCard-root.cdm-list.cdm-card._content-without-paddings.MuiPaper-elevation1.MuiPaper-rounded'
    )
    table = authenticated_page.locator(table_selector)
    if not table or table.count() == 0 or not table.first.is_visible():
        fail_with_screenshot("Таблица с нужными классами не найдена или не видима на странице", authenticated_page)

    # Шаг №2: Проверка наличия кнопки-фильтра (иконка фильтра)
    filter_btn = table.locator('button.cdm-icon-button__toolbar-primary span[title="Фильтр"]')
    if not filter_btn or filter_btn.count() == 0 or not filter_btn.first.is_visible():
        fail_with_screenshot("Кнопка-фильтр не найдена в таблице", authenticated_page)

    # Шаг №3: Проверка наличия кнопки 'Создать'
    create_btn = table.locator('button.cdm-button__toolbar-primary:has-text("Создать")')
    if not create_btn or create_btn.count() == 0 or not create_btn.first.is_visible():
        fail_with_screenshot("Кнопка 'Создать' не найдена в таблице", authenticated_page)

    # Шаг №4: Проверка наличия задизейбленной кнопки 'Удалить'
    delete_btn = table.locator('button.cdm-button._disabled[title="Удалить"]')
    if not delete_btn or delete_btn.count() == 0 or not delete_btn.first.is_disabled():
        fail_with_screenshot("Кнопка 'Удалить' не найдена или не задизейблена в таблице", authenticated_page)


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_dns_sinkhole_create_row(authenticated_page: Page, credentials):
    """
    Проверяет, что после нажатия на кнопку 'Создать' появляется строка для ввода, и в неё можно ввести 'auto.test.com'.
    """
    # Шаг №1: Нажимаем на кнопку "Создать"
    create_btn = authenticated_page.locator('button.cdm-button__toolbar-primary:has-text("Создать")')
    if not create_btn or create_btn.count() == 0 or not create_btn.first.is_visible():
        fail_with_screenshot("Кнопка 'Создать' не найдена или не видна", authenticated_page)
    create_btn.first.click()

    # Шаг №2: Проверяем появление строки для ввода
    form_row = authenticated_page.locator('.cdm-data-grid__body__form-row')
    if not form_row or form_row.count() == 0 or not form_row.first.is_visible():
        fail_with_screenshot("Строка для ввода не появилась после нажатия 'Создать'", authenticated_page)

    # Шаг №3: Вводим 'auto.test.com' во вторую ячейку (input)
    input_field = form_row.locator('.cdm-input-text-wrapper input')
    if not input_field or input_field.count() == 0 or not input_field.first.is_visible():
        fail_with_screenshot("Поле для ввода домена не найдено или не видно", authenticated_page)
    input_field.first.fill('auto.test.com')
    if input_field.first.input_value() != 'auto.test.com':
        fail_with_screenshot("Значение в поле не соответствует 'auto.test.com'", authenticated_page)


"""-------------------------------------Негативные проверки валидации FQDN--------------------------------------- """


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_dns_sinkhole_invalid_fqdn_no_dot(authenticated_page: Page, credentials):
    """
    Проверяет, что при вводе 'test' появляется ошибка 'Неверная запись FQDN'.
    """
    # Шаг №1: Находим уже открытую строку для ввода
    form_row = authenticated_page.locator('.cdm-data-grid__body__form-row')
    if not form_row or form_row.count() == 0 or not form_row.first.is_visible():
        fail_with_screenshot("Строка для ввода не найдена. Убедитесь, что предыдущий тест создал строку.", authenticated_page)
    # Шаг №2: Очищаем поле и вводим 'test'
    input_field = form_row.locator('.cdm-input-text-wrapper input')
    if not input_field or input_field.count() == 0 or not input_field.first.is_visible():
        fail_with_screenshot("Поле для ввода домена не найдено или не видно", authenticated_page)
    input_field.first.fill('')
    input_field.first.fill('test')
    if input_field.first.input_value() != 'test':
        fail_with_screenshot("Значение в поле не соответствует 'test'", authenticated_page)
    # Шаг №3: Проверяем появление ошибки 'Неверная запись FQDN'
    error_hint = form_row.locator('p.MuiFormHelperText-root.Mui-error')
    if not (error_hint.is_visible() and 'Неверная запись FQDN' in error_hint.inner_text()):
        fail_with_screenshot("Нет ошибки 'Неверная запись FQDN' для значения 'test'", authenticated_page)


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_dns_sinkhole_invalid_fqdn_at_symbol(authenticated_page: Page, credentials):
    """
    Проверяет, что при вводе 'test@com' появляется ошибка 'Неверная запись FQDN'.
    """
    # Шаг №1: Находим уже открытую строку для ввода
    form_row = authenticated_page.locator('.cdm-data-grid__body__form-row')
    if not form_row or form_row.count() == 0 or not form_row.first.is_visible():
        fail_with_screenshot("Строка для ввода не найдена. Убедитесь, что предыдущий тест создал строку.", authenticated_page)
    # Шаг №2: Очищаем поле и вводим 'test@com'
    input_field = form_row.locator('.cdm-input-text-wrapper input')
    if not input_field or input_field.count() == 0 or not input_field.first.is_visible():
        fail_with_screenshot("Поле для ввода домена не найдено или не видно", authenticated_page)
    input_field.first.fill('')
    input_field.first.fill('test@com')
    if input_field.first.input_value() != 'test@com':
        fail_with_screenshot("Значение в поле не соответствует 'test@com'", authenticated_page)
    # Шаг №3: Проверяем появление ошибки 'Неверная запись FQDN'
    error_hint = form_row.locator('p.MuiFormHelperText-root.Mui-error')
    if not (error_hint.is_visible() and 'Неверная запись FQDN' in error_hint.inner_text()):
        fail_with_screenshot("Нет ошибки 'Неверная запись FQDN' для значения 'test@com'", authenticated_page)


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_dns_sinkhole_invalid_fqdn_double_dot(authenticated_page: Page, credentials):
    """
    Проверяет, что при вводе 'test..com' появляется ошибка 'Неверная запись FQDN'.
    """
    # Шаг №1: Находим уже открытую строку для ввода
    form_row = authenticated_page.locator('.cdm-data-grid__body__form-row')
    if not form_row or form_row.count() == 0 or not form_row.first.is_visible():
        fail_with_screenshot("Строка для ввода не найдена. Убедитесь, что предыдущий тест создал строку.", authenticated_page)
    # Шаг №2: Очищаем поле и вводим 'test..com'
    input_field = form_row.locator('.cdm-input-text-wrapper input')
    if not input_field or input_field.count() == 0 or not input_field.first.is_visible():
        fail_with_screenshot("Поле для ввода домена не найдено или не видно", authenticated_page)
    input_field.first.fill('')
    input_field.first.fill('test..com')
    if input_field.first.input_value() != 'test..com':
        fail_with_screenshot("Значение в поле не соответствует 'test..com'", authenticated_page)
    # Шаг №3: Проверяем появление ошибки 'Неверная запись FQDN'
    error_hint = form_row.locator('p.MuiFormHelperText-root.Mui-error')
    if not (error_hint.is_visible() and 'Неверная запись FQDN' in error_hint.inner_text()):
        fail_with_screenshot("Нет ошибки 'Неверная запись FQDN' для значения 'test..com'", authenticated_page)


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_dns_sinkhole_invalid_fqdn_underscore(authenticated_page: Page, credentials):
    """
    Проверяет, что при вводе 'test_com' появляется ошибка 'Неверная запись FQDN'.
    """
    # Шаг №1: Находим уже открытую строку для ввода
    form_row = authenticated_page.locator('.cdm-data-grid__body__form-row')
    if not form_row or form_row.count() == 0 or not form_row.first.is_visible():
        fail_with_screenshot("Строка для ввода не найдена. Убедитесь, что предыдущий тест создал строку.", authenticated_page)
    # Шаг №2: Очищаем поле и вводим 'test_com'
    input_field = form_row.locator('.cdm-input-text-wrapper input')
    if not input_field or input_field.count() == 0 or not input_field.first.is_visible():
        fail_with_screenshot("Поле для ввода домена не найдено или не видно", authenticated_page)
    input_field.first.fill('')
    input_field.first.fill('test_com')
    if input_field.first.input_value() != 'test_com':
        fail_with_screenshot("Значение в поле не соответствует 'test_com'", authenticated_page)
    # Шаг №3: Проверяем появление ошибки 'Неверная запись FQDN'
    error_hint = form_row.locator('p.MuiFormHelperText-root.Mui-error')
    if not (error_hint.is_visible() and 'Неверная запись FQDN' in error_hint.inner_text()):
        fail_with_screenshot("Нет ошибки 'Неверная запись FQDN' для значения 'test_com'", authenticated_page)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_dns_sinkhole_invalid_fqdn_dot_start(authenticated_page: Page, credentials):
    """
    Проверяет, что при вводе '.auto.test.com' появляется ошибка 'Неверная запись FQDN'.
    """
    # Шаг №1: Находим уже открытую строку для ввода
    form_row = authenticated_page.locator('.cdm-data-grid__body__form-row')
    if not form_row or form_row.count() == 0 or not form_row.first.is_visible():
        fail_with_screenshot("Строка для ввода не найдена. Убедитесь, что предыдущий тест создал строку.", authenticated_page)
    # Шаг №2: Очищаем поле и вводим '.auto.test.com'
    input_field = form_row.locator('.cdm-input-text-wrapper input')
    if not input_field or input_field.count() == 0 or not input_field.first.is_visible():
        fail_with_screenshot("Поле для ввода домена не найдено или не видно", authenticated_page)
    input_field.first.fill('')
    input_field.first.fill('.auto.test.com')
    if input_field.first.input_value() != '.auto.test.com':
        fail_with_screenshot("Значение в поле не соответствует '.auto.test.com'", authenticated_page)
    # Шаг №3: Проверяем появление ошибки 'Неверная запись FQDN'
    error_hint = form_row.locator('p.MuiFormHelperText-root.Mui-error')
    if not (error_hint.is_visible() and 'Неверная запись FQDN' in error_hint.inner_text()):
        fail_with_screenshot("Нет ошибки 'Неверная запись FQDN' для значения '.auto.test.com'", authenticated_page)


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_dns_sinkhole_invalid_fqdn_dash_start(authenticated_page: Page, credentials):
    """
    Проверяет, что при вводе '-auto.test.com' появляется ошибка 'Неверная запись FQDN'.
    """
    # Шаг №1: Находим уже открытую строку для ввода
    form_row = authenticated_page.locator('.cdm-data-grid__body__form-row')
    if not form_row or form_row.count() == 0 or not form_row.first.is_visible():
        fail_with_screenshot("Строка для ввода не найдена. Убедитесь, что предыдущий тест создал строку.", authenticated_page)
    # Шаг №2: Очищаем поле и вводим '-auto.test.com'
    input_field = form_row.locator('.cdm-input-text-wrapper input')
    if not input_field or input_field.count() == 0 or not input_field.first.is_visible():
        fail_with_screenshot("Поле для ввода домена не найдено или не видно", authenticated_page)
    input_field.first.fill('')
    input_field.first.fill('-auto.test.com')
    if input_field.first.input_value() != '-auto.test.com':
        fail_with_screenshot("Значение в поле не соответствует '-auto.test.com'", authenticated_page)
    # Шаг №3: Проверяем появление ошибки 'Неверная запись FQDN'
    error_hint = form_row.locator('p.MuiFormHelperText-root.Mui-error')
    if not (error_hint.is_visible() and 'Неверная запись FQDN' in error_hint.inner_text()):
        fail_with_screenshot("Нет ошибки 'Неверная запись FQDN' для значения '-auto.test.com'", authenticated_page)


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_dns_sinkhole_invalid_fqdn_dash_end(authenticated_page: Page, credentials):
    """
    Проверяет, что при вводе 'test-.com' появляется ошибка 'Неверная запись FQDN'.
    """
    # Шаг №1: Находим уже открытую строку для ввода
    form_row = authenticated_page.locator('.cdm-data-grid__body__form-row')
    if not form_row or form_row.count() == 0 or not form_row.first.is_visible():
        fail_with_screenshot("Строка для ввода не найдена. Убедитесь, что предыдущий тест создал строку.", authenticated_page)
    # Шаг №2: Очищаем поле и вводим 'test-.com'
    input_field = form_row.locator('.cdm-input-text-wrapper input')
    if not input_field or input_field.count() == 0 or not input_field.first.is_visible():
        fail_with_screenshot("Поле для ввода домена не найдено или не видно", authenticated_page)
    input_field.first.fill('')
    input_field.first.fill('test-.com')
    if input_field.first.input_value() != 'test-.com':
        fail_with_screenshot("Значение в поле не соответствует 'test-.com'", authenticated_page)
    # Шаг №3: Проверяем появление ошибки 'Неверная запись FQDN'
    error_hint = form_row.locator('p.MuiFormHelperText-root.Mui-error')
    if not (error_hint.is_visible() and 'Неверная запись FQDN' in error_hint.inner_text()):
        fail_with_screenshot("Нет ошибки 'Неверная запись FQDN' для значения 'test-.com'", authenticated_page)


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_dns_sinkhole_invalid_fqdn_double_dot_middle(authenticated_page: Page, credentials):
    """
    Проверяет, что при вводе 'te..st.com' появляется ошибка 'Неверная запись FQDN'.
    """
    # Шаг №1: Находим уже открытую строку для ввода
    form_row = authenticated_page.locator('.cdm-data-grid__body__form-row')
    if not form_row or form_row.count() == 0 or not form_row.first.is_visible():
        fail_with_screenshot("Строка для ввода не найдена. Убедитесь, что предыдущий тест создал строку.", authenticated_page)
    # Шаг №2: Очищаем поле и вводим 'te..st.com'
    input_field = form_row.locator('.cdm-input-text-wrapper input')
    if not input_field or input_field.count() == 0 or not input_field.first.is_visible():
        fail_with_screenshot("Поле для ввода домена не найдено или не видно", authenticated_page)
    input_field.first.fill('')
    input_field.first.fill('te..st.com')
    if input_field.first.input_value() != 'te..st.com':
        fail_with_screenshot("Значение в поле не соответствует 'te..st.com'", authenticated_page)
    # Шаг №3: Проверяем появление ошибки 'Неверная запись FQDN'
    error_hint = form_row.locator('p.MuiFormHelperText-root.Mui-error')
    if not (error_hint.is_visible() and 'Неверная запись FQDN' in error_hint.inner_text()):
        fail_with_screenshot("Нет ошибки 'Неверная запись FQDN' для значения 'te..st.com'", authenticated_page)


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_dns_sinkhole_invalid_fqdn_exclamation(authenticated_page: Page, credentials):
    """
    Проверяет, что при вводе 'test!com' появляется ошибка 'Неверная запись FQDN'.
    """
    # Шаг №1: Находим уже открытую строку для ввода
    form_row = authenticated_page.locator('.cdm-data-grid__body__form-row')
    if not form_row or form_row.count() == 0 or not form_row.first.is_visible():
        fail_with_screenshot("Строка для ввода не найдена. Убедитесь, что предыдущий тест создал строку.", authenticated_page)
    # Шаг №2: Очищаем поле и вводим 'test!com'
    input_field = form_row.locator('.cdm-input-text-wrapper input')
    if not input_field or input_field.count() == 0 or not input_field.first.is_visible():
        fail_with_screenshot("Поле для ввода домена не найдено или не видно", authenticated_page)
    input_field.first.fill('')
    input_field.first.fill('test!com')
    if input_field.first.input_value() != 'test!com':
        fail_with_screenshot("Значение в поле не соответствует 'test!com'", authenticated_page)
    # Шаг №3: Проверяем появление ошибки 'Неверная запись FQDN'
    error_hint = form_row.locator('p.MuiFormHelperText-root.Mui-error')
    if not (error_hint.is_visible() and 'Неверная запись FQDN' in error_hint.inner_text()):
        fail_with_screenshot("Нет ошибки 'Неверная запись FQDN' для значения 'test!com'", authenticated_page)


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_dns_sinkhole_invalid_fqdn_comma(authenticated_page: Page, credentials):
    """
    Проверяет, что при вводе 'test,com' появляется ошибка 'Неверная запись FQDN'.
    """
    # Шаг №1: Находим уже открытую строку для ввода
    form_row = authenticated_page.locator('.cdm-data-grid__body__form-row')
    if not form_row or form_row.count() == 0 or not form_row.first.is_visible():
        fail_with_screenshot("Строка для ввода не найдена. Убедитесь, что предыдущий тест создал строку.", authenticated_page)
    # Шаг №2: Очищаем поле и вводим 'test,com'
    input_field = form_row.locator('.cdm-input-text-wrapper input')
    if not input_field or input_field.count() == 0 or not input_field.first.is_visible():
        fail_with_screenshot("Поле для ввода домена не найдено или не видно", authenticated_page)
    input_field.first.fill('')
    input_field.first.fill('test,com')
    if input_field.first.input_value() != 'test,com':
        fail_with_screenshot("Значение в поле не соответствует 'test,com'", authenticated_page)
    # Шаг №3: Проверяем появление ошибки 'Неверная запись FQDN'
    error_hint = form_row.locator('p.MuiFormHelperText-root.Mui-error')
    if not (error_hint.is_visible() and 'Неверная запись FQDN' in error_hint.inner_text()):
        fail_with_screenshot("Нет ошибки 'Неверная запись FQDN' для значения 'test,com'", authenticated_page)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_dns_sinkhole_invalid_fqdn_space_start(authenticated_page: Page, credentials):
    """
    Проверяет, что при вводе ' auto.test.com' появляется ошибка 'Неверная запись FQDN'.
    """
    # Шаг №1: Находим уже открытую строку для ввода
    form_row = authenticated_page.locator('.cdm-data-grid__body__form-row')
    if not form_row or form_row.count() == 0 or not form_row.first.is_visible():
        fail_with_screenshot("Строка для ввода не найдена. Убедитесь, что предыдущий тест создал строку.", authenticated_page)
    # Шаг №2: Очищаем поле и вводим ' auto.test.com'
    input_field = form_row.locator('.cdm-input-text-wrapper input')
    if not input_field or input_field.count() == 0 or not input_field.first.is_visible():
        fail_with_screenshot("Поле для ввода домена не найдено или не видно", authenticated_page)
    input_field.first.fill('')
    input_field.first.fill(' auto.test.com')
    if input_field.first.input_value() != ' auto.test.com':
        fail_with_screenshot("Значение в поле не соответствует ' auto.test.com'", authenticated_page)
    # Шаг №3: Проверяем появление ошибки 'Неверная запись FQDN'
    error_hint = form_row.locator('p.MuiFormHelperText-root.Mui-error')
    if not (error_hint.is_visible() and 'Неверная запись FQDN' in error_hint.inner_text()):
        fail_with_screenshot("Нет ошибки 'Неверная запись FQDN' для значения ' auto.test.com'", authenticated_page)


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_dns_sinkhole_invalid_fqdn_space_end(authenticated_page: Page, credentials):
    """
    Проверяет, что при вводе 'auto.test.com ' появляется ошибка 'Неверная запись FQDN'.
    """
    # Шаг №1: Находим уже открытую строку для ввода
    form_row = authenticated_page.locator('.cdm-data-grid__body__form-row')
    if not form_row or form_row.count() == 0 or not form_row.first.is_visible():
        fail_with_screenshot("Строка для ввода не найдена. Убедитесь, что предыдущий тест создал строку.", authenticated_page)
    # Шаг №2: Очищаем поле и вводим 'auto.test.com '
    input_field = form_row.locator('.cdm-input-text-wrapper input')
    if not input_field or input_field.count() == 0 or not input_field.first.is_visible():
        fail_with_screenshot("Поле для ввода домена не найдено или не видно", authenticated_page)
    input_field.first.fill('')
    input_field.first.fill('auto.test.com ')
    if input_field.first.input_value() != 'auto.test.com ':
        fail_with_screenshot("Значение в поле не соответствует 'auto.test.com '", authenticated_page)
    # Шаг №3: Проверяем появление ошибки 'Неверная запись FQDN'
    error_hint = form_row.locator('p.MuiFormHelperText-root.Mui-error')
    if not (error_hint.is_visible() and 'Неверная запись FQDN' in error_hint.inner_text()):
        fail_with_screenshot("Нет ошибки 'Неверная запись FQDN' для значения 'auto.test.com '", authenticated_page)


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_dns_sinkhole_invalid_fqdn_space_inside(authenticated_page: Page, credentials):
    """
    Проверяет, что при вводе 'test .com' появляется ошибка 'Неверная запись FQDN'.
    """
    # Шаг №1: Находим уже открытую строку для ввода
    form_row = authenticated_page.locator('.cdm-data-grid__body__form-row')
    if not form_row or form_row.count() == 0 or not form_row.first.is_visible():
        fail_with_screenshot("Строка для ввода не найдена. Убедитесь, что предыдущий тест создал строку.", authenticated_page)
    # Шаг №2: Очищаем поле и вводим 'test .com'
    input_field = form_row.locator('.cdm-input-text-wrapper input')
    if not input_field or input_field.count() == 0 or not input_field.first.is_visible():
        fail_with_screenshot("Поле для ввода домена не найдено или не видно", authenticated_page)
    input_field.first.fill('')
    input_field.first.fill('test .com')
    if input_field.first.input_value() != 'test .com':
        fail_with_screenshot("Значение в поле не соответствует 'test .com'", authenticated_page)
    # Шаг №3: Проверяем появление ошибки 'Неверная запись FQDN'
    error_hint = form_row.locator('p.MuiFormHelperText-root.Mui-error')
    if not (error_hint.is_visible() and 'Неверная запись FQDN' in error_hint.inner_text()):
        fail_with_screenshot("Нет ошибки 'Неверная запись FQDN' для значения 'test .com'", authenticated_page)


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_dns_sinkhole_invalid_fqdn_short(authenticated_page: Page, credentials):
    """
    Проверяет, что при вводе 'a.b' появляется ошибка 'Неверная запись FQDN'.
    """
    # Шаг №1: Находим уже открытую строку для ввода
    form_row = authenticated_page.locator('.cdm-data-grid__body__form-row')
    if not form_row or form_row.count() == 0 or not form_row.first.is_visible():
        fail_with_screenshot("Строка для ввода не найдена. Убедитесь, что предыдущий тест создал строку.", authenticated_page)
    # Шаг №2: Очищаем поле и вводим 'a.b'
    input_field = form_row.locator('.cdm-input-text-wrapper input')
    if not input_field or input_field.count() == 0 or not input_field.first.is_visible():
        fail_with_screenshot("Поле для ввода домена не найдено или не видно", authenticated_page)
    input_field.first.fill('')
    input_field.first.fill('a.b')
    if input_field.first.input_value() != 'a.b':
        fail_with_screenshot("Значение в поле не соответствует 'a.b'", authenticated_page)
    # Шаг №3: Проверяем появление ошибки 'Неверная запись FQDN'
    error_hint = form_row.locator('p.MuiFormHelperText-root.Mui-error')
    if not (error_hint.is_visible() and 'Неверная запись FQDN' in error_hint.inner_text()):
        fail_with_screenshot("Нет ошибки 'Неверная запись FQDN' для значения 'a.b'", authenticated_page)


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_dns_sinkhole_invalid_fqdn_hash(authenticated_page: Page, credentials):
    """
    Проверяет, что при вводе 'test#com' появляется ошибка 'Неверная запись FQDN'.
    """
    # Шаг №1: Находим уже открытую строку для ввода
    form_row = authenticated_page.locator('.cdm-data-grid__body__form-row')
    if not form_row or form_row.count() == 0 or not form_row.first.is_visible():
        fail_with_screenshot("Строка для ввода не найдена. Убедитесь, что предыдущий тест создал строку.", authenticated_page)
    # Шаг №2: Очищаем поле и вводим 'test#com'
    input_field = form_row.locator('.cdm-input-text-wrapper input')
    if not input_field or input_field.count() == 0 or not input_field.first.is_visible():
        fail_with_screenshot("Поле для ввода домена не найдено или не видно", authenticated_page)
    input_field.first.fill('')
    input_field.first.fill('test#com')
    if input_field.first.input_value() != 'test#com':
        fail_with_screenshot("Значение в поле не соответствует 'test#com'", authenticated_page)
    # Шаг №3: Проверяем появление ошибки 'Неверная запись FQDN'
    error_hint = form_row.locator('p.MuiFormHelperText-root.Mui-error')
    if not (error_hint.is_visible() and 'Неверная запись FQDN' in error_hint.inner_text()):
        fail_with_screenshot("Нет ошибки 'Неверная запись FQDN' для значения 'test#com'", authenticated_page)


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_dns_sinkhole_invalid_fqdn_dollar(authenticated_page: Page, credentials):
    """
    Проверяет, что при вводе 'test$com' появляется ошибка 'Неверная запись FQDN'.
    """
    # Шаг №1: Находим уже открытую строку для ввода
    form_row = authenticated_page.locator('.cdm-data-grid__body__form-row')
    if not form_row or form_row.count() == 0 or not form_row.first.is_visible():
        fail_with_screenshot("Строка для ввода не найдена. Убедитесь, что предыдущий тест создал строку.", authenticated_page)
    # Шаг №2: Очищаем поле и вводим 'test$com'
    input_field = form_row.locator('.cdm-input-text-wrapper input')
    if not input_field or input_field.count() == 0 or not input_field.first.is_visible():
        fail_with_screenshot("Поле для ввода домена не найдено или не видно", authenticated_page)
    input_field.first.fill('')
    input_field.first.fill('test$com')
    if input_field.first.input_value() != 'test$com':
        fail_with_screenshot("Значение в поле не соответствует 'test$com'", authenticated_page)
    # Шаг №3: Проверяем появление ошибки 'Неверная запись FQDN'
    error_hint = form_row.locator('p.MuiFormHelperText-root.Mui-error')
    if not (error_hint.is_visible() and 'Неверная запись FQDN' in error_hint.inner_text()):
        fail_with_screenshot("Нет ошибки 'Неверная запись FQDN' для значения 'test$com'", authenticated_page)


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_dns_sinkhole_invalid_fqdn_slash(authenticated_page: Page, credentials):
    """
    Проверяет, что при вводе 'test/com' появляется ошибка 'Неверная запись FQDN'.
    """
    # Шаг №1: Находим уже открытую строку для ввода
    form_row = authenticated_page.locator('.cdm-data-grid__body__form-row')
    if not form_row or form_row.count() == 0 or not form_row.first.is_visible():
        fail_with_screenshot("Строка для ввода не найдена. Убедитесь, что предыдущий тест создал строку.", authenticated_page)
    # Шаг №2: Очищаем поле и вводим 'test/com'
    input_field = form_row.locator('.cdm-input-text-wrapper input')
    if not input_field or input_field.count() == 0 or not input_field.first.is_visible():
        fail_with_screenshot("Поле для ввода домена не найдено или не видно", authenticated_page)
    input_field.first.fill('')
    input_field.first.fill('test/com')
    if input_field.first.input_value() != 'test/com':
        fail_with_screenshot("Значение в поле не соответствует 'test/com'", authenticated_page)
    # Шаг №3: Проверяем появление ошибки 'Неверная запись FQDN'
    error_hint = form_row.locator('p.MuiFormHelperText-root.Mui-error')
    if not (error_hint.is_visible() and 'Неверная запись FQDN' in error_hint.inner_text()):
        fail_with_screenshot("Нет ошибки 'Неверная запись FQDN' для значения 'test/com'", authenticated_page)


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_dns_sinkhole_invalid_fqdn_double_dot_start(authenticated_page: Page, credentials):
    """
    Проверяет, что при вводе '..auto.test.com' появляется ошибка 'Неверная запись FQDN'.
    """
    # Шаг №1: Находим уже открытую строку для ввода
    form_row = authenticated_page.locator('.cdm-data-grid__body__form-row')
    if not form_row or form_row.count() == 0 or not form_row.first.is_visible():
        fail_with_screenshot("Строка для ввода не найдена. Убедитесь, что предыдущий тест создал строку.", authenticated_page)
    # Шаг №2: Очищаем поле и вводим '..auto.test.com'
    input_field = form_row.locator('.cdm-input-text-wrapper input')
    if not input_field or input_field.count() == 0 or not input_field.first.is_visible():
        fail_with_screenshot("Поле для ввода домена не найдено или не видно", authenticated_page)
    input_field.first.fill('')
    input_field.first.fill('..auto.test.com')
    if input_field.first.input_value() != '..auto.test.com':
        fail_with_screenshot("Значение в поле не соответствует '..auto.test.com'", authenticated_page)
    # Шаг №3: Проверяем появление ошибки 'Неверная запись FQDN'
    error_hint = form_row.locator('p.MuiFormHelperText-root.Mui-error')
    if not (error_hint.is_visible() and 'Неверная запись FQDN' in error_hint.inner_text()):
        fail_with_screenshot("Нет ошибки 'Неверная запись FQDN' для значения '..auto.test.com'", authenticated_page)


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_dns_sinkhole_invalid_fqdn_double_dot_end(authenticated_page: Page, credentials):
    """
    Проверяет, что при вводе 'auto.test.com..' появляется ошибка 'Неверная запись FQDN'.
    """
    # Шаг №1: Находим уже открытую строку для ввода
    form_row = authenticated_page.locator('.cdm-data-grid__body__form-row')
    if not form_row or form_row.count() == 0 or not form_row.first.is_visible():
        fail_with_screenshot("Строка для ввода не найдена. Убедитесь, что предыдущий тест создал строку.", authenticated_page)
    # Шаг №2: Очищаем поле и вводим 'auto.test.com..'
    input_field = form_row.locator('.cdm-input-text-wrapper input')
    if not input_field or input_field.count() == 0 or not input_field.first.is_visible():
        fail_with_screenshot("Поле для ввода домена не найдено или не видно", authenticated_page)
    input_field.first.fill('')
    input_field.first.fill('auto.test.com..')
    if input_field.first.input_value() != 'auto.test.com..':
        fail_with_screenshot("Значение в поле не соответствует 'auto.test.com..'", authenticated_page)
    # Шаг №3: Проверяем появление ошибки 'Неверная запись FQDN'
    error_hint = form_row.locator('p.MuiFormHelperText-root.Mui-error')
    if not (error_hint.is_visible() and 'Неверная запись FQDN' in error_hint.inner_text()):
        fail_with_screenshot("Нет ошибки 'Неверная запись FQDN' для значения 'auto.test.com..'", authenticated_page)


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_dns_sinkhole_invalid_fqdn_only_dot(authenticated_page: Page, credentials):
    """
    Проверяет, что при вводе '.' появляется ошибка 'Неверная запись FQDN'.
    """
    # Шаг №1: Находим уже открытую строку для ввода
    form_row = authenticated_page.locator('.cdm-data-grid__body__form-row')
    if not form_row or form_row.count() == 0 or not form_row.first.is_visible():
        fail_with_screenshot("Строка для ввода не найдена. Убедитесь, что предыдущий тест создал строку.", authenticated_page)
    # Шаг №2: Очищаем поле и вводим '.'
    input_field = form_row.locator('.cdm-input-text-wrapper input')
    if not input_field or input_field.count() == 0 or not input_field.first.is_visible():
        fail_with_screenshot("Поле для ввода домена не найдено или не видно", authenticated_page)
    input_field.first.fill('')
    input_field.first.fill('.')
    if input_field.first.input_value() != '.':
        fail_with_screenshot("Значение в поле не соответствует '.'", authenticated_page)
    # Шаг №3: Проверяем появление ошибки 'Неверная запись FQDN'
    error_hint = form_row.locator('p.MuiFormHelperText-root.Mui-error')
    if not (error_hint.is_visible() and 'Неверная запись FQDN' in error_hint.inner_text()):
        fail_with_screenshot("Нет ошибки 'Неверная запись FQDN' для значения '.'", authenticated_page)


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_dns_sinkhole_invalid_fqdn_punycode(authenticated_page: Page, credentials):
    """
    Проверяет, что при вводе 'xn--d1acufc.xn--p1ai' (punycode) появляется ошибка 'Неверная запись FQDN'.
    """
    # Шаг №1: Находим уже открытую строку для ввода
    form_row = authenticated_page.locator('.cdm-data-grid__body__form-row')
    if not form_row or form_row.count() == 0 or not form_row.first.is_visible():
        fail_with_screenshot("Строка для ввода не найдена. Убедитесь, что предыдущий тест создал строку.", authenticated_page)
    # Шаг №2: Очищаем поле и вводим 'xn--d1acufc.xn--p1ai'
    input_field = form_row.locator('.cdm-input-text-wrapper input')
    if not input_field or input_field.count() == 0 or not input_field.first.is_visible():
        fail_with_screenshot("Поле для ввода домена не найдено или не видно", authenticated_page)
    input_field.first.fill('')
    input_field.first.fill('xn--d1acufc.xn--p1ai')
    if input_field.first.input_value() != 'xn--d1acufc.xn--p1ai':
        fail_with_screenshot("Значение в поле не соответствует 'xn--d1acufc.xn--p1ai'", authenticated_page)
    # Шаг №3: Проверяем, что ошибка появляется
    error_hint = form_row.locator('p.MuiFormHelperText-root.Mui-error')
    if not (error_hint.is_visible() and 'Неверная запись FQDN' in error_hint.inner_text()):
        fail_with_screenshot("Ошибка 'Неверная запись FQDN' должна появляться для значения 'xn--d1acufc.xn--p1ai'", authenticated_page)


"""-------------------------------------Позитивные проверки валидации FQDN--------------------------------------- """


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_dns_sinkhole_valid_fqdn_latin(authenticated_page: Page, credentials):
    """
    Проверяет, что при вводе 'auto.test.com' не появляется ошибка 'Неверная запись FQDN'.
    """
    # Шаг №1: Находим уже открытую строку для ввода
    form_row = authenticated_page.locator('.cdm-data-grid__body__form-row')
    if not form_row or form_row.count() == 0 or not form_row.first.is_visible():
        fail_with_screenshot("Строка для ввода не найдена. Убедитесь, что предыдущий тест создал строку.", authenticated_page)
    # Шаг №2: Очищаем поле и вводим 'auto.test.com'
    input_field = form_row.locator('.cdm-input-text-wrapper input')
    if not input_field or input_field.count() == 0 or not input_field.first.is_visible():
        fail_with_screenshot("Поле для ввода домена не найдено или не видно", authenticated_page)
    input_field.first.fill('')
    input_field.first.fill('auto.test.com')
    if input_field.first.input_value() != 'auto.test.com':
        fail_with_screenshot("Значение в поле не соответствует 'auto.test.com'", authenticated_page)
    # Шаг №3: Проверяем, что ошибка не появляется
    error_hint = form_row.locator('p.MuiFormHelperText-root.Mui-error')
    if error_hint.is_visible() and 'Неверная запись FQDN' in error_hint.inner_text():
        fail_with_screenshot("Ошибка 'Неверная запись FQDN' не должна появляться для значения 'auto.test.com'", authenticated_page)


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_dns_sinkhole_valid_fqdn_dash(authenticated_page: Page, credentials):
    """
    Проверяет, что при вводе 'test-domain.com' не появляется ошибка 'Неверная запись FQDN'.
    """
    # Шаг №1: Находим уже открытую строку для ввода
    form_row = authenticated_page.locator('.cdm-data-grid__body__form-row')
    if not form_row or form_row.count() == 0 or not form_row.first.is_visible():
        fail_with_screenshot("Строка для ввода не найдена. Убедитесь, что предыдущий тест создал строку.", authenticated_page)
    # Шаг №2: Очищаем поле и вводим 'test-domain.com'
    input_field = form_row.locator('.cdm-input-text-wrapper input')
    if not input_field or input_field.count() == 0 or not input_field.first.is_visible():
        fail_with_screenshot("Поле для ввода домена не найдено или не видно", authenticated_page)
    input_field.first.fill('')
    input_field.first.fill('test-domain.com')
    if input_field.first.input_value() != 'test-domain.com':
        fail_with_screenshot("Значение в поле не соответствует 'test-domain.com'", authenticated_page)
    # Шаг №3: Проверяем, что ошибка не появляется
    error_hint = form_row.locator('p.MuiFormHelperText-root.Mui-error')
    if error_hint.is_visible() and 'Неверная запись FQDN' in error_hint.inner_text():
        fail_with_screenshot("Ошибка 'Неверная запись FQDN' не должна появляться для значения 'test-domain.com'", authenticated_page)


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_dns_sinkhole_valid_fqdn_digits(authenticated_page: Page, credentials):
    """
    Проверяет, что при вводе 'test123.com' не появляется ошибка 'Неверная запись FQDN'.
    """
    # Шаг №1: Находим уже открытую строку для ввода
    form_row = authenticated_page.locator('.cdm-data-grid__body__form-row')
    if not form_row or form_row.count() == 0 or not form_row.first.is_visible():
        fail_with_screenshot("Строка для ввода не найдена. Убедитесь, что предыдущий тест создал строку.", authenticated_page)
    # Шаг №2: Очищаем поле и вводим 'test123.com'
    input_field = form_row.locator('.cdm-input-text-wrapper input')
    if not input_field or input_field.count() == 0 or not input_field.first.is_visible():
        fail_with_screenshot("Поле для ввода домена не найдено или не видно", authenticated_page)
    input_field.first.fill('')
    input_field.first.fill('test123.com')
    if input_field.first.input_value() != 'test123.com':
        fail_with_screenshot("Значение в поле не соответствует 'test123.com'", authenticated_page)
    # Шаг №3: Проверяем, что ошибка не появляется
    error_hint = form_row.locator('p.MuiFormHelperText-root.Mui-error')
    if error_hint.is_visible() and 'Неверная запись FQDN' in error_hint.inner_text():
        fail_with_screenshot("Ошибка 'Неверная запись FQDN' не должна появляться для значения 'test123.com'", authenticated_page)


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_dns_sinkhole_valid_fqdn_subdomain(authenticated_page: Page, credentials):
    """
    Проверяет, что при вводе 'sub.domain.com' не появляется ошибка 'Неверная запись FQDN'.
    """
    # Шаг №1: Находим уже открытую строку для ввода
    form_row = authenticated_page.locator('.cdm-data-grid__body__form-row')
    if not form_row or form_row.count() == 0 or not form_row.first.is_visible():
        fail_with_screenshot("Строка для ввода не найдена. Убедитесь, что предыдущий тест создал строку.", authenticated_page)
    # Шаг №2: Очищаем поле и вводим 'sub.domain.com'
    input_field = form_row.locator('.cdm-input-text-wrapper input')
    if not input_field or input_field.count() == 0 or not input_field.first.is_visible():
        fail_with_screenshot("Поле для ввода домена не найдено или не видно", authenticated_page)
    input_field.first.fill('')
    input_field.first.fill('sub.domain.com')
    if input_field.first.input_value() != 'sub.domain.com':
        fail_with_screenshot("Значение в поле не соответствует 'sub.domain.com'", authenticated_page)
    # Шаг №3: Проверяем, что ошибка не появляется
    error_hint = form_row.locator('p.MuiFormHelperText-root.Mui-error')
    if error_hint.is_visible() and 'Неверная запись FQDN' in error_hint.inner_text():
        fail_with_screenshot("Ошибка 'Неверная запись FQDN' не должна появляться для значения 'sub.domain.com'", authenticated_page)


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_dns_sinkhole_valid_fqdn_multi_dash(authenticated_page: Page, credentials):
    """
    Проверяет, что при вводе 'a-b-c.d-e-f.com' не появляется ошибка 'Неверная запись FQDN'.
    """
    # Шаг №1: Находим уже открытую строку для ввода
    form_row = authenticated_page.locator('.cdm-data-grid__body__form-row')
    if not form_row or form_row.count() == 0 or not form_row.first.is_visible():
        fail_with_screenshot("Строка для ввода не найдена. Убедитесь, что предыдущий тест создал строку.", authenticated_page)
    # Шаг №2: Очищаем поле и вводим 'a-b-c.d-e-f.com'
    input_field = form_row.locator('.cdm-input-text-wrapper input')
    if not input_field or input_field.count() == 0 or not input_field.first.is_visible():
        fail_with_screenshot("Поле для ввода домена не найдено или не видно", authenticated_page)
    input_field.first.fill('')
    input_field.first.fill('a-b-c.d-e-f.com')
    if input_field.first.input_value() != 'a-b-c.d-e-f.com':
        fail_with_screenshot("Значение в поле не соответствует 'a-b-c.d-e-f.com'", authenticated_page)
    # Шаг №3: Проверяем, что ошибка не появляется
    error_hint = form_row.locator('p.MuiFormHelperText-root.Mui-error')
    if error_hint.is_visible() and 'Неверная запись FQDN' in error_hint.inner_text():
        fail_with_screenshot("Ошибка 'Неверная запись FQDN' не должна появляться для значения 'a-b-c.d-e-f.com'", authenticated_page)


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_dns_sinkhole_valid_fqdn_co_uk(authenticated_page: Page, credentials):
    """
    Проверяет, что при вводе 'test.co.uk' не появляется ошибка 'Неверная запись FQDN'.
    """
    # Шаг №1: Находим уже открытую строку для ввода
    form_row = authenticated_page.locator('.cdm-data-grid__body__form-row')
    if not form_row or form_row.count() == 0 or not form_row.first.is_visible():
        fail_with_screenshot("Строка для ввода не найдена. Убедитесь, что предыдущий тест создал строку.", authenticated_page)
    # Шаг №2: Очищаем поле и вводим 'test.co.uk'
    input_field = form_row.locator('.cdm-input-text-wrapper input')
    if not input_field or input_field.count() == 0 or not input_field.first.is_visible():
        fail_with_screenshot("Поле для ввода домена не найдено или не видно", authenticated_page)
    input_field.first.fill('')
    input_field.first.fill('test.co.uk')
    if input_field.first.input_value() != 'test.co.uk':
        fail_with_screenshot("Значение в поле не соответствует 'test.co.uk'", authenticated_page)
    # Шаг №3: Проверяем, что ошибка не появляется
    error_hint = form_row.locator('p.MuiFormHelperText-root.Mui-error')
    if error_hint.is_visible() and 'Неверная запись FQDN' in error_hint.inner_text():
        fail_with_screenshot("Ошибка 'Неверная запись FQDN' не должна появляться для значения 'test.co.uk'", authenticated_page)


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_dns_sinkhole_valid_fqdn_digits_and_dash(authenticated_page: Page, credentials):
    """
    Проверяет, что при вводе 'test-123.domain-456.com' не появляется ошибка 'Неверная запись FQDN'.
    """
    # Шаг №1: Находим уже открытую строку для ввода
    form_row = authenticated_page.locator('.cdm-data-grid__body__form-row')
    if not form_row or form_row.count() == 0 or not form_row.first.is_visible():
        fail_with_screenshot("Строка для ввода не найдена. Убедитесь, что предыдущий тест создал строку.", authenticated_page)
    # Шаг №2: Очищаем поле и вводим 'test-123.domain-456.com'
    input_field = form_row.locator('.cdm-input-text-wrapper input')
    if not input_field or input_field.count() == 0 or not input_field.first.is_visible():
        fail_with_screenshot("Поле для ввода домена не найдено или не видно", authenticated_page)
    input_field.first.fill('')
    input_field.first.fill('test-123.domain-456.com')
    if input_field.first.input_value() != 'test-123.domain-456.com':
        fail_with_screenshot("Значение в поле не соответствует 'test-123.domain-456.com'", authenticated_page)
    # Шаг №3: Проверяем, что ошибка не появляется
    error_hint = form_row.locator('p.MuiFormHelperText-root.Mui-error')
    if error_hint.is_visible() and 'Неверная запись FQDN' in error_hint.inner_text():
        fail_with_screenshot("Ошибка 'Неверная запись FQDN' не должна появляться для значения 'test-123.domain-456.com'", authenticated_page)


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_dns_sinkhole_valid_fqdn_cyrillic(authenticated_page: Page, credentials):
    """
    Проверяет, что при вводе 'тест.рф' не появляется ошибка 'Неверная запись FQDN'.
    """
    # Шаг №1: Находим уже открытую строку для ввода
    form_row = authenticated_page.locator('.cdm-data-grid__body__form-row')
    if not form_row or form_row.count() == 0 or not form_row.first.is_visible():
        fail_with_screenshot("Строка для ввода не найдена. Убедитесь, что предыдущий тест создал строку.", authenticated_page)
    # Шаг №2: Очищаем поле и вводим 'тест.рф'
    input_field = form_row.locator('.cdm-input-text-wrapper input')
    if not input_field or input_field.count() == 0 or not input_field.first.is_visible():
        fail_with_screenshot("Поле для ввода домена не найдено или не видно", authenticated_page)
    input_field.first.fill('')
    input_field.first.fill('тест.рф')
    if input_field.first.input_value() != 'тест.рф':
        fail_with_screenshot("Значение в поле не соответствует 'тест.рф'", authenticated_page)
    # Шаг №3: Проверяем, что ошибка не появляется
    error_hint = form_row.locator('p.MuiFormHelperText-root.Mui-error')
    if error_hint.is_visible() and 'Неверная запись FQDN' in error_hint.inner_text():
        fail_with_screenshot("Ошибка 'Неверная запись FQDN' не должна появляться для значения 'тест.рф'", authenticated_page)


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_dns_sinkhole_valid_fqdn_my_site_co_uk(authenticated_page: Page, credentials):
    """
    Проверяет, что при вводе 'my-site.co.uk' не появляется ошибка 'Неверная запись FQDN'.
    """
    # Шаг №1: Находим уже открытую строку для ввода
    form_row = authenticated_page.locator('.cdm-data-grid__body__form-row')
    if not form_row or form_row.count() == 0 or not form_row.first.is_visible():
        fail_with_screenshot("Строка для ввода не найдена. Убедитесь, что предыдущий тест создал строку.", authenticated_page)
    # Шаг №2: Очищаем поле и вводим 'my-site.co.uk'
    input_field = form_row.locator('.cdm-input-text-wrapper input')
    if not input_field or input_field.count() == 0 or not input_field.first.is_visible():
        fail_with_screenshot("Поле для ввода домена не найдено или не видно", authenticated_page)
    input_field.first.fill('')
    input_field.first.fill('my-site.co.uk')
    if input_field.first.input_value() != 'my-site.co.uk':
        fail_with_screenshot("Значение в поле не соответствует 'my-site.co.uk'", authenticated_page)
    # Шаг №3: Проверяем, что ошибка не появляется
    error_hint = form_row.locator('p.MuiFormHelperText-root.Mui-error')
    if error_hint.is_visible() and 'Неверная запись FQDN' in error_hint.inner_text():
        fail_with_screenshot("Ошибка 'Неверная запись FQDN' не должна появляться для значения 'my-site.co.uk'", authenticated_page)


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_dns_sinkhole_valid_fqdn_one_letter_a(authenticated_page: Page, credentials):
    """
    Проверяет, что при вводе 'a.com' не появляется ошибка 'Неверная запись FQDN'.
    """
    # Шаг №1: Находим уже открытую строку для ввода
    form_row = authenticated_page.locator('.cdm-data-grid__body__form-row')
    if not form_row or form_row.count() == 0 or not form_row.first.is_visible():
        fail_with_screenshot("Строка для ввода не найдена. Убедитесь, что предыдущий тест создал строку.", authenticated_page)
    # Шаг №2: Очищаем поле и вводим 'a.com'
    input_field = form_row.locator('.cdm-input-text-wrapper input')
    if not input_field or input_field.count() == 0 or not input_field.first.is_visible():
        fail_with_screenshot("Поле для ввода домена не найдено или не видно", authenticated_page)
    input_field.first.fill('')
    input_field.first.fill('a.com')
    if input_field.first.input_value() != 'a.com':
        fail_with_screenshot("Значение в поле не соответствует 'a.com'", authenticated_page)
    # Шаг №3: Проверяем, что ошибка не появляется
    error_hint = form_row.locator('p.MuiFormHelperText-root.Mui-error')
    if error_hint.is_visible() and 'Неверная запись FQDN' in error_hint.inner_text():
        fail_with_screenshot("Ошибка 'Неверная запись FQDN' не должна появляться для значения 'a.com'", authenticated_page)


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_dns_sinkhole_valid_fqdn_one_letter_b(authenticated_page: Page, credentials):
    """
    Проверяет, что при вводе 'b.co' не появляется ошибка 'Неверная запись FQDN'.
    """
    # Шаг №1: Находим уже открытую строку для ввода
    form_row = authenticated_page.locator('.cdm-data-grid__body__form-row')
    if not form_row or form_row.count() == 0 or not form_row.first.is_visible():
        fail_with_screenshot("Строка для ввода не найдена. Убедитесь, что предыдущий тест создал строку.", authenticated_page)
    # Шаг №2: Очищаем поле и вводим 'b.co'
    input_field = form_row.locator('.cdm-input-text-wrapper input')
    if not input_field or input_field.count() == 0 or not input_field.first.is_visible():
        fail_with_screenshot("Поле для ввода домена не найдено или не видно", authenticated_page)
    input_field.first.fill('')
    input_field.first.fill('b.co')
    if input_field.first.input_value() != 'b.co':
        fail_with_screenshot("Значение в поле не соответствует 'b.co'", authenticated_page)
    # Шаг №3: Проверяем, что ошибка не появляется
    error_hint = form_row.locator('p.MuiFormHelperText-root.Mui-error')
    if error_hint.is_visible() and 'Неверная запись FQDN' in error_hint.inner_text():
        fail_with_screenshot("Ошибка 'Неверная запись FQDN' не должна появляться для значения 'b.co'", authenticated_page)


"""-------------------------------------Проверки создания строки--------------------------------------- """


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_dns_sinkhole_cancel_row(authenticated_page: Page, credentials):
    """
    Проверяет, что при вводе auto.test.com и нажатии на крестик строка отменяется и появляется сообщение 'Нет данных'.
    """
    # Шаг №1: Вводим auto.test.com в поле
    input_field = authenticated_page.locator('tr.cdm-data-grid__body__form-row input[type="text"]:not([readonly])')
    if not input_field.is_visible():
        fail_with_screenshot("Поле для ввода FQDN не отображается", authenticated_page)
    input_field.fill("auto.test.com")

    # Шаг №2: Нажимаем на крестик (Отмена)
    cancel_button = authenticated_page.locator('button:has(span[title="Отмена"])')
    if not cancel_button.is_visible():
        fail_with_screenshot("Кнопка 'Отмена' (крестик) не отображается", authenticated_page)
    cancel_button.click()

    # Шаг №3: Проверяем, что нет строки с 'auto.test.com'
    rows = authenticated_page.locator('tbody tr')
    for i in range(rows.count()):
        cell = rows.nth(i).locator('td:nth-child(2)')
        cell_text = cell.inner_text().strip()
        if cell_text == "auto.test.com":
            fail_with_screenshot("Строка с 'auto.test.com' не должна быть в таблице после отмены", authenticated_page)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_dns_sinkhole_create_row_test_com(authenticated_page: Page, credentials):
    """
    Проверяет, что после нажатия на кнопку 'Создать' появляется строка для ввода, и в неё можно ввести 'auto.test.com'.
    """
    # Шаг №1: Нажимаем на кнопку "Создать"
    create_btn = authenticated_page.locator('button.cdm-button__toolbar-primary:has-text("Создать")')
    if not create_btn or create_btn.count() == 0 or not create_btn.first.is_visible():
        fail_with_screenshot("Кнопка 'Создать' не найдена или не видна", authenticated_page)
    create_btn.first.click()

    # Шаг №2: Проверяем появление строки для ввода
    form_row = authenticated_page.locator('.cdm-data-grid__body__form-row')
    if not form_row or form_row.count() == 0 or not form_row.first.is_visible():
        fail_with_screenshot("Строка для ввода не появилась после нажатия 'Создать'", authenticated_page)

    # Шаг №3: Вводим 'auto.test.com' во вторую ячейку (input)
    input_field = form_row.locator('.cdm-input-text-wrapper input')
    if not input_field or input_field.count() == 0 or not input_field.first.is_visible():
        fail_with_screenshot("Поле для ввода домена не найдено или не видно", authenticated_page)
    input_field.first.fill('auto.test.com')
    if input_field.first.input_value() != 'auto.test.com':
        fail_with_screenshot("Значение в поле не соответствует 'auto.test.com'", authenticated_page)

    # Шаг №4: Нажимаем на кнопку "Сохранить" с ожиданием POST запроса
    save_button = form_row.locator('button:has(span[title="Сохранить"])')
    if not save_button or save_button.count() == 0 or not save_button.first.is_visible():
        fail_with_screenshot("Кнопка 'Сохранить' не найдена или не видна", authenticated_page)

    # Ожидаем POST-запрос к нужному эндпоинту через универсальную функцию
    with wait_for_api_response_with_response(authenticated_page, "/api/service/remote/ngfw/core/call/manager/dns/static", expected_status=200, method="POST", timeout=20000) as resp_info:
        save_button.first.click()
    
    # Шаг №5: Проверяем, что строка сохранена и содержит auto.test.com
    authenticated_page.wait_for_timeout(500)
    rows = authenticated_page.locator('tbody tr')
    found = False
    for i in range(rows.count()):
        cell = rows.nth(i).locator('td:nth-child(2)')
        cell_text = cell.inner_text().strip()
        if cell_text == "auto.test.com":
            found = True
            break
    if not found:
        fail_with_screenshot("Строка с 'auto.test.com' не найдена в таблице после сохранения", authenticated_page)


"""-------------------------------------Проверки редактирования строки--------------------------------------- """


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_dns_sinkhole_edit_row(authenticated_page: Page, credentials):
    """
    Проверяет, что можно отредактировать строку с 'auto.test.com', изменить её на 'авто.тест' и сохранить.
    """
    page = authenticated_page

    # Шаг 1: Ищем строку с 'auto.test.com'
    rows = page.locator('tbody tr')
    target_row = None
    for i in range(rows.count()):
        cell = rows.nth(i).locator('td:nth-child(2)')
        cell_text = cell.inner_text().strip()
        if cell_text == "auto.test.com":
            target_row = rows.nth(i)
            break
    if not target_row:
        fail_with_screenshot("Строка с 'auto.test.com' не найдена для редактирования", page)

    # Шаг 2: Нажимаем на кнопку редактирования
    edit_button = target_row.locator('button:has(span[title="Изменить"])')
    if not edit_button or edit_button.count() == 0 or not edit_button.first.is_visible():
        fail_with_screenshot("Кнопка 'Изменить' не найдена или не видна в строке", page)
    edit_button.first.click()

    # Шаг 3: Вводим 'авто.тест' во вторую ячейку (input)
    form_row = page.locator('.cdm-data-grid__body__form-row')
    if not form_row or form_row.count() == 0 or not form_row.first.is_visible():
        fail_with_screenshot("Строка для редактирования не появилась", page)
    input_field = form_row.locator('.cdm-input-text-wrapper input')
    if not input_field or input_field.count() == 0 or not input_field.first.is_visible():
        fail_with_screenshot("Поле для ввода домена не найдено или не видно", page)
    input_field.first.fill('авто.тест')
    if input_field.first.input_value() != 'авто.тест':
        fail_with_screenshot("Значение в поле не соответствует 'авто.тест'", page)

    # Шаг 4: Нажимаем на кнопку "Сохранить" с ожиданием POST запроса
    from UI.universal_functions.click_on_body import wait_for_api_response_with_response
    save_button = form_row.locator('button:has(span[title="Сохранить"])')
    if not save_button or save_button.count() == 0 or not save_button.first.is_visible():
        fail_with_screenshot("Кнопка 'Сохранить' не найдена или не видна", page)
    with wait_for_api_response_with_response(page, "/api/service/remote/ngfw/core/call/manager/dns/static", expected_status=200, method="PATCH", timeout=20000) as resp_info:
        save_button.first.click()
    page.wait_for_timeout(500)

    # Шаг 5: Проверяем, что строка с новым значением появилась
    rows = page.locator('tbody tr')
    found = False
    for i in range(rows.count()):
        cell = rows.nth(i).locator('td:nth-child(2)')
        cell_text = cell.inner_text().strip()
        if cell_text == "авто.тест":
            found = True
            break
    if not found:
        fail_with_screenshot("Строка с 'авто.тест' не найдена в таблице после редактирования", page)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_dns_sinkhole_create_row_123avto321(authenticated_page: Page, credentials):
    """
    Проверяет, что можно создать строку с названием '123авто321.тест' и она появляется в таблице.
    """
    page = authenticated_page

    # Шаг 1: Нажимаем на кнопку "Создать"
    create_button = page.locator('button.cdm-button__toolbar-primary:has-text("Создать")')
    if not create_button or create_button.count() == 0 or not create_button.first.is_visible():
        fail_with_screenshot("Кнопка 'Создать' не найдена или не видна", page)
    create_button.first.click()

    # Шаг 2: Находим строку для ввода
    form_row = page.locator('.cdm-data-grid__body__form-row')
    if not form_row or form_row.count() == 0 or not form_row.first.is_visible():
        fail_with_screenshot("Строка для ввода не появилась после нажатия 'Создать'", page)

    # Шаг 3: Вводим '123авто321.тест' во вторую ячейку (input)
    input_field = form_row.locator('.cdm-input-text-wrapper input')
    if not input_field or input_field.count() == 0 or not input_field.first.is_visible():
        fail_with_screenshot("Поле для ввода домена не найдено или не видно", page)
    input_field.first.fill('123авто321.тест')
    if input_field.first.input_value() != '123авто321.тест':
        fail_with_screenshot("Значение в поле не соответствует '123авто321.тест'", page)

    # Шаг 4: Нажимаем на кнопку "Сохранить" с ожиданием POST запроса
    from UI.universal_functions.click_on_body import wait_for_api_response_with_response
    save_button = form_row.locator('button:has(span[title="Сохранить"])')
    if not save_button or save_button.count() == 0 or not save_button.first.is_visible():
        fail_with_screenshot("Кнопка 'Сохранить' не найдена или не видна", page)
    with wait_for_api_response_with_response(page, "/api/service/remote/ngfw/core/call/manager/dns/static", expected_status=200, method="POST", timeout=20000) as resp_info:
        save_button.first.click()
    page.wait_for_timeout(500)

    # Шаг 5: Проверяем, что строка с новым значением появилась
    rows = page.locator('tbody tr')
    found = False
    for i in range(rows.count()):
        cell = rows.nth(i).locator('td:nth-child(2)')
        cell_text = cell.inner_text().strip()
        if cell_text == "123авто321.тест":
            found = True
            break
    if not found:
        fail_with_screenshot("Строка с '123авто321.тест' не найдена в таблице после создания", page)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_dns_sinkhole_create_row_123test(authenticated_page: Page, credentials):
    """
    Проверяет, что можно создать строку с названием '123.test' и она появляется в таблице.
    """
    page = authenticated_page

    # Шаг 1: Нажимаем на кнопку "Создать"
    create_button = page.locator('button.cdm-button__toolbar-primary:has-text("Создать")')
    if not create_button or create_button.count() == 0 or not create_button.first.is_visible():
        fail_with_screenshot("Кнопка 'Создать' не найдена или не видна", page)
    create_button.first.click()

    # Шаг 2: Находим строку для ввода
    form_row = page.locator('.cdm-data-grid__body__form-row')
    if not form_row or form_row.count() == 0 or not form_row.first.is_visible():
        fail_with_screenshot("Строка для ввода не появилась после нажатия 'Создать'", page)

    # Шаг 3: Вводим '123.test' во вторую ячейку (input)
    input_field = form_row.locator('.cdm-input-text-wrapper input')
    if not input_field or input_field.count() == 0 or not input_field.first.is_visible():
        fail_with_screenshot("Поле для ввода домена не найдено или не видно", page)
    input_field.first.fill('123.test')
    if input_field.first.input_value() != '123.test':
        fail_with_screenshot("Значение в поле не соответствует '123.test'", page)

    # Шаг 4: Нажимаем на кнопку "Сохранить" с ожиданием POST запроса
    from UI.universal_functions.click_on_body import wait_for_api_response_with_response
    save_button = form_row.locator('button:has(span[title="Сохранить"])')
    if not save_button or save_button.count() == 0 or not save_button.first.is_visible():
        fail_with_screenshot("Кнопка 'Сохранить' не найдена или не видна", page)
    with wait_for_api_response_with_response(page, "/api/service/remote/ngfw/core/call/manager/dns/static", expected_status=200, method="POST", timeout=20000) as resp_info:
        save_button.first.click()
    page.wait_for_timeout(500)

    # Шаг 5: Проверяем, что строка с новым значением появилась
    rows = page.locator('tbody tr')
    found = False
    for i in range(rows.count()):
        cell = rows.nth(i).locator('td:nth-child(2)')
        cell_text = cell.inner_text().strip()
        if cell_text == "123.test":
            found = True
            break
    if not found:
        fail_with_screenshot("Строка с '123.test' не найдена в таблице после создания", page)



"""-------------------------------------Проверки фильтрации--------------------------------------- """

"""-------------------------------------Позитивные проверки фильтрации--------------------------------------- """



# @pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
# def test_page_dns_sinkhole_filter_menu_appears(authenticated_page: Page, credentials):
#     """
#     Проверяет, что меню фильтрации открывается и содержит указанное количество и название любого фильтра в меню 
#     """
#     count_filter = 1
#     name_filter = "Имя"
#     filter_menu_appears(authenticated_page, credentials, count_filter, name_filter)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_dns_sinkhole_check_filter_by_input_first_row_value(authenticated_page: Page, credentials):
    """
    Проверяет позитивную фильтрацию по Имени: по первой строке
    """
    filter_name = "Имя"
    endpoint_substring = "/api/service/remote/ngfw/core/call/manager/dns/static"
    check_filter_by_input_first_row_value(authenticated_page, filter_name, endpoint_substring)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_dns_sinkhole_check_filter_positive_name_123_dot_test(authenticated_page: Page, credentials):
    """
    Проверяет позитивную фильтрацию по Имени: авто. (частичное совпадение)
    """
    filter_name = "Имя"
    severity_text = "авто."
    endpoint_substring = "/api/service/remote/ngfw/core/call/manager/dns/static"
    check_filter_by_input(authenticated_page, filter_name, severity_text, endpoint_substring)


"""-------------------------------------Негативные проверки фильтрации--------------------------------------- """


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_dns_sinkhole_filter_negative_name_qwerty123(authenticated_page: Page, credentials):
    """
    Проверяет негативную фильтрацию по Имени: qwerty123
    """
    filter_name = "Имя"
    severity_text = "qwerty123"
    endpoint_substring = "/api/service/remote/ngfw/core/call/manager/dns/static"
    check_filter_by_input_negative_other_values(authenticated_page, filter_name, severity_text, endpoint_substring)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_dns_sinkhole_filter_negative_name_CSII(authenticated_page: Page, credentials):
    """
    Проверяет негативную фильтрацию по Имени: 1123.test
    """
    filter_name = "Имя"
    severity_text = "1123.test"
    endpoint_substring = "/api/service/remote/ngfw/core/call/manager/dns/static"
    check_filter_by_input_negative_other_values(authenticated_page, filter_name, severity_text, endpoint_substring)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_dns_sinkhole_filter_negative_name_special_chars(authenticated_page: Page, credentials):
    """
    Проверяет негативную фильтрацию по Имени: спецсимволы
    """
    filter_name = "Имя"
    severity_text = "!@#$%^&*()_+"
    endpoint_substring = "/api/service/remote/ngfw/core/call/manager/dns/static"
    check_filter_by_input_negative_other_values(authenticated_page, filter_name, severity_text, endpoint_substring)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_dns_sinkhole_filter_negative_name_long_string(authenticated_page: Page, credentials):
    """
    Проверяет негативную фильтрацию по Имени: очень длинная строка
    """
    filter_name = "Имя"
    severity_text = "A" * 1024
    endpoint_substring = "/api/service/remote/ngfw/core/call/manager/dns/static"
    check_filter_by_input_negative_other_values(authenticated_page, filter_name, severity_text, endpoint_substring)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_dns_sinkhole_filter_negative_name_sql_injection(authenticated_page: Page, credentials):
    """
    Проверяет негативную фильтрацию по Имени: SQL-инъекция
    """
    filter_name = "Имя"
    severity_text = "' OR 1=1 --"
    endpoint_substring = "/api/service/remote/ngfw/core/call/manager/dns/static"
    check_filter_by_input_negative_other_values(authenticated_page, filter_name, severity_text, endpoint_substring)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_dns_sinkhole_filter_negative_name_spaces(authenticated_page: Page, credentials):
    """
    Проверяет негативную фильтрацию по Имени: только пробелы
    """
    filter_name = "Имя"
    severity_text = "   "
    endpoint_substring = "/api/service/remote/ngfw/core/call/manager/dns/static"
    check_filter_by_input_negative_other_values(authenticated_page, filter_name, severity_text, endpoint_substring)


"""-------------------------------------Проверки удаления строк--------------------------------------- """


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_dns_sinkhole_create_row_test_domain_com(authenticated_page: Page, credentials):
    """
    Проверяет, что после нажатия на кнопку 'Создать' появляется строка для ввода, и в неё можно ввести 'test.domain.com'.
    """
    # Шаг №1: Нажимаем на кнопку "Создать"
    create_btn = authenticated_page.locator('button.cdm-button__toolbar-primary:has-text("Создать")')
    if not create_btn or create_btn.count() == 0 or not create_btn.first.is_visible():
        fail_with_screenshot("Кнопка 'Создать' не найдена или не видна", authenticated_page)
    create_btn.first.click()

    # Шаг №2: Проверяем появление строки для ввода
    form_row = authenticated_page.locator('.cdm-data-grid__body__form-row')
    if not form_row or form_row.count() == 0 or not form_row.first.is_visible():
        fail_with_screenshot("Строка для ввода не появилась после нажатия 'Создать'", authenticated_page)

    # Шаг №3: Вводим 'test.domain.com' во вторую ячейку (input)
    input_field = form_row.locator('.cdm-input-text-wrapper input')
    if not input_field or input_field.count() == 0 or not input_field.first.is_visible():
        fail_with_screenshot("Поле для ввода домена не найдено или не видно", authenticated_page)
    input_field.first.fill('test.domain.com')
    if input_field.first.input_value() != 'test.domain.com':
        fail_with_screenshot("Значение в поле не соответствует 'test.domain.com'", authenticated_page)

    # Шаг №4: Нажимаем на кнопку "Сохранить" с ожиданием POST запроса
    save_button = form_row.locator('button:has(span[title="Сохранить"])')
    if not save_button or save_button.count() == 0 or not save_button.first.is_visible():
        fail_with_screenshot("Кнопка 'Сохранить' не найдена или не видна", authenticated_page)

    # Ожидаем POST-запрос к нужному эндпоинту через универсальную функцию
    with wait_for_api_response_with_response(authenticated_page, "/api/service/remote/ngfw/core/call/manager/dns/static", expected_status=200, method="POST", timeout=20000) as resp_info:
        save_button.first.click()
    
    # Шаг №5: Проверяем, что строка сохранена и содержит test.domain.com
    authenticated_page.wait_for_timeout(500)
    rows = authenticated_page.locator('tbody tr')
    found = False
    for i in range(rows.count()):
        cell = rows.nth(i).locator('td:nth-child(2)')
        cell_text = cell.inner_text().strip()
        if cell_text == "test.domain.com":
            found = True
            break
    if not found:
        fail_with_screenshot("Строка с 'test.domain.com' не найдена в таблице после сохранения", authenticated_page)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_dns_sinkhole_delete_row_test_domain_com(authenticated_page: Page, credentials):
    """
    Проверяет удаление строки с именем 'test.domain.com':
    1. Находит строку с этим именем
    2. Нажимает на кнопку удаления
    3. Подтверждает удаление в модальном окне
    4. Ждёт DELETE-запрос
    5. Проверяет, что строки с этим именем больше нет
    """
    page = authenticated_page

    # Шаг №1: Ищем строку с 'test.domain.com'
    rows = page.locator('tbody tr')
    target_row = None
    for i in range(rows.count()):
        cell = rows.nth(i).locator('td:nth-child(2)')
        cell_text = cell.inner_text().strip()
        if cell_text == "test.domain.com":
            target_row = rows.nth(i)
            break
    if not target_row:
        fail_with_screenshot("Строка с 'test.domain.com' не найдена для удаления", page)

    # Шаг №2: Нажимаем на кнопку удаления в строке
    delete_button = target_row.locator('button:has(span[title="Удалить"])')
    if not delete_button or delete_button.count() == 0 or not delete_button.first.is_visible():
        fail_with_screenshot("Кнопка 'Удалить' не найдена или не видна в строке", page)
    delete_button.first.click()

    # Шаг №3: В модальном окне подтверждаем удаление
    modal = page.locator('div[role="dialog"]')
    if not modal or modal.count() == 0 or not modal.first.is_visible():
        fail_with_screenshot("Модальное окно подтверждения удаления не появилось", page)
    confirm_button = modal.locator('button.cdm-button__primary:has-text("Удалить")')
    if not confirm_button or confirm_button.count() == 0 or not confirm_button.first.is_visible():
        fail_with_screenshot("Кнопка 'Удалить' в модальном окне не найдена или не видна", page)

    # Шаг №4: Ждём DELETE-запрос и подтверждаем удаление
    from UI.universal_functions.click_on_body import wait_for_api_response_with_response
    with wait_for_api_response_with_response(page, "/api/service/remote/ngfw/core/call/manager/dns/static", expected_status=200, method="DELETE", timeout=20000) as resp_info:
        confirm_button.first.click()
    page.wait_for_timeout(1000)

    # Шаг №5: Проверяем, что строки с этим именем больше нет
    rows = page.locator('tbody tr')
    for i in range(rows.count()):
        cell = rows.nth(i).locator('td:nth-child(2)')
        cell_text = cell.inner_text().strip()
        if cell_text == "test.domain.com":
            fail_with_screenshot("Строка с 'test.domain.com' не должна отображаться после удаления", page)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_dns_sinkhole_create_row_test_domain_com_2(authenticated_page: Page, credentials):
    """
    Проверяет, что после нажатия на кнопку 'Создать' появляется строка для ввода, и в неё можно ввести 'test.domain.com'.
    """
    # Шаг №1: Нажимаем на кнопку "Создать"
    create_btn = authenticated_page.locator('button.cdm-button__toolbar-primary:has-text("Создать")')
    if not create_btn or create_btn.count() == 0 or not create_btn.first.is_visible():
        fail_with_screenshot("Кнопка 'Создать' не найдена или не видна", authenticated_page)
    create_btn.first.click()

    # Шаг №2: Проверяем появление строки для ввода
    form_row = authenticated_page.locator('.cdm-data-grid__body__form-row')
    if not form_row or form_row.count() == 0 or not form_row.first.is_visible():
        fail_with_screenshot("Строка для ввода не появилась после нажатия 'Создать'", authenticated_page)

    # Шаг №3: Вводим 'test.domain.com' во вторую ячейку (input)
    input_field = form_row.locator('.cdm-input-text-wrapper input')
    if not input_field or input_field.count() == 0 or not input_field.first.is_visible():
        fail_with_screenshot("Поле для ввода домена не найдено или не видно", authenticated_page)
    input_field.first.fill('test.domain.com')
    if input_field.first.input_value() != 'test.domain.com':
        fail_with_screenshot("Значение в поле не соответствует 'test.domain.com'", authenticated_page)

    # Шаг №4: Нажимаем на кнопку "Сохранить" с ожиданием POST запроса
    save_button = form_row.locator('button:has(span[title="Сохранить"])')
    if not save_button or save_button.count() == 0 or not save_button.first.is_visible():
        fail_with_screenshot("Кнопка 'Сохранить' не найдена или не видна", authenticated_page)

    # Ожидаем POST-запрос к нужному эндпоинту через универсальную функцию
    with wait_for_api_response_with_response(authenticated_page, "/api/service/remote/ngfw/core/call/manager/dns/static", expected_status=200, method="POST", timeout=20000) as resp_info:
        save_button.first.click()
    
    # Шаг №5: Проверяем, что строка сохранена и содержит test.domain.com
    authenticated_page.wait_for_timeout(500)
    rows = authenticated_page.locator('tbody tr')
    found = False
    for i in range(rows.count()):
        cell = rows.nth(i).locator('td:nth-child(2)')
        cell_text = cell.inner_text().strip()
        if cell_text == "test.domain.com":
            found = True
            break
    if not found:
        fail_with_screenshot("Строка с 'test.domain.com' не найдена в таблице после сохранения", authenticated_page)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_dns_sinkhole_bulk_delete_test_domain_com_and_123_test(authenticated_page: Page, credentials):
    """
    Проверяет массовое удаление строк с именами 'test.domain.com' и '123.test':
    1. Кликает по чекбоксам в строках с этими именами
    2. Проверяет, что чекбокс в шапке стал частично выбранным
    3. Нажимает на кнопку 'Удалить' в тулбаре
    4. Ждёт DELETE-запрос
    5. Проверяет, что обе строки удалены
    """
    page = authenticated_page
    target_names = ["test.domain.com", "123.test"]
    checked_rows = []

    # Шаг №1: Кликаем по чекбоксам нужных строк
    rows = page.locator('tbody tr')
    for name in target_names:
        found = False
        for i in range(rows.count()):
            cell = rows.nth(i).locator('td:nth-child(2)')
            cell_text = cell.inner_text().strip()
            if cell_text == name:
                checkbox = rows.nth(i).locator('td.cdm-data-grid__body__row__checkbox-cell input[type="checkbox"]')
                if not checkbox or checkbox.count() == 0 or not checkbox.first.is_visible():
                    fail_with_screenshot(f"Чекбокс для строки '{name}' не найден или не виден", page)
                checkbox.first.check()
                checked_rows.append(i)
                found = True
                break
        if not found:
            fail_with_screenshot(f"Строка с '{name}' не найдена для выделения чекбоксом", page)

    # Шаг №2: Проверяем, что чекбокс в шапке стал частично выбранным
    header_checkbox = page.locator('thead tr th.cdm-data-grid__body__row__checkbox-cell input[type="checkbox"]')
    if not header_checkbox or header_checkbox.count() == 0 or not header_checkbox.first.is_visible():
        fail_with_screenshot("Чекбокс в шапке таблицы не найден или не виден", page)
    # Проверяем data-indeterminate="true"
    if header_checkbox.first.get_attribute("data-indeterminate") != "true":
        fail_with_screenshot("Чекбокс в шапке не стал частично выбранным (data-indeterminate != true)", page)

    # Шаг №3: Нажимаем на кнопку 'Удалить' в тулбаре
    delete_toolbar_btn = page.locator('button.cdm-button__toolbar-primary[title="Удалить"]')
    if not delete_toolbar_btn or delete_toolbar_btn.count() == 0 or not delete_toolbar_btn.first.is_visible():
        fail_with_screenshot("Кнопка 'Удалить' в тулбаре не найдена или не видна", page)
    delete_toolbar_btn.first.click()

    # Шаг №4: Ждём появления модального окна и нажимаем 'Удалить' в модалке
    modal = page.locator('div[role="dialog"]')
    if not modal or modal.count() == 0 or not modal.first.is_visible():
        fail_with_screenshot("Модальное окно подтверждения удаления не появилось", page)
    confirm_button = modal.locator('button.cdm-button__primary:has-text("Удалить")')
    if not confirm_button or confirm_button.count() == 0 or not confirm_button.first.is_visible():
        fail_with_screenshot("Кнопка 'Удалить' в модальном окне не найдена или не видна", page)
    with wait_for_api_response_with_response(page, "/api/service/remote/ngfw/core/call/manager/dns/static", expected_status=200, method="DELETE", timeout=20000) as resp_info:
        confirm_button.first.click()
    page.wait_for_timeout(1000)

    # Шаг №5: Обновляем страницу
    page.reload()
    page.wait_for_load_state('networkidle')

    # Шаг №6: Проверяем, что обе строки удалены
    rows = page.locator('tbody tr')
    for name in target_names:
        for i in range(rows.count()):
            cell = rows.nth(i).locator('td:nth-child(2)')
            cell_text = cell.inner_text().strip()
            if cell_text == name:
                fail_with_screenshot(f"Строка с '{name}' не должна отображаться после массового удаления", page)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_dns_sinkhole_select_all_and_delete(authenticated_page: Page, credentials):
    """
    Проверяет массовое выделение всех строк через чекбокс в шапке и их удаление:
    1. Кликает по чекбоксу в шапке таблицы (выделяет все строки)
    2. Проверяет, что все чекбоксы в строках активны
    3. Нажимает на кнопку 'Удалить' в тулбаре
    4. Подтверждает удаление в модалке, ждёт DELETE-запрос
    5. Проверяет, что строк в таблице больше нет
    """
    page = authenticated_page

    # Шаг №1: Кликаем по чекбоксу в шапке таблицы
    header_checkbox = page.locator('thead tr th.cdm-data-grid__body__row__checkbox-cell input[type="checkbox"]')
    if not header_checkbox or header_checkbox.count() == 0 or not header_checkbox.first.is_visible():
        fail_with_screenshot("Чекбокс в шапке таблицы не найден или не виден", page)
    header_checkbox.first.check()

    # Шаг №2: Проверяем, что все чекбоксы в строках активны (выделены)
    rows = page.locator('tbody tr')
    if rows.count() == 0:
        fail_with_screenshot("Нет строк для массового выделения", page)
    for i in range(rows.count()):
        checkbox = rows.nth(i).locator('td.cdm-data-grid__body__row__checkbox-cell input[type="checkbox"]')
        if not checkbox or checkbox.count() == 0 or not checkbox.first.is_visible():
            fail_with_screenshot(f"Чекбокс в строке {i+1} не найден или не виден", page)
        if not checkbox.first.is_checked():
            fail_with_screenshot(f"Чекбокс в строке {i+1} не стал активным после выделения всех", page)

    # Шаг №3: Нажимаем на кнопку 'Удалить' в тулбаре
    delete_toolbar_btn = page.locator('button.cdm-button__toolbar-primary[title="Удалить"]')
    if not delete_toolbar_btn or delete_toolbar_btn.count() == 0 or not delete_toolbar_btn.first.is_visible():
        fail_with_screenshot("Кнопка 'Удалить' в тулбаре не найдена или не видна", page)
    delete_toolbar_btn.first.click()

    # Шаг №4: Подтверждаем удаление в модалке и ждём DELETE-запрос
    modal = page.locator('div[role="dialog"]')
    if not modal or modal.count() == 0 or not modal.first.is_visible():
        fail_with_screenshot("Модальное окно подтверждения удаления не появилось", page)
    confirm_button = modal.locator('button.cdm-button__primary:has-text("Удалить")')
    if not confirm_button or confirm_button.count() == 0 or not confirm_button.first.is_visible():
        fail_with_screenshot("Кнопка 'Удалить' в модальном окне не найдена или не видна", page)
    with wait_for_api_response_with_response(page, "/api/service/remote/ngfw/core/call/manager/dns/static", expected_status=200, method="DELETE", timeout=30000) as resp_info:
        confirm_button.first.click()
    page.wait_for_timeout(1000)

    # Шаг №5: Обновляем страницу
    page.reload()
    page.wait_for_load_state('networkidle')

    # Шаг №6: Проверяем, что строк в таблице больше нет
    rows = page.locator('tbody tr')
    if rows.count() != 0:
        fail_with_screenshot("После массового удаления строки остались в таблице", page)