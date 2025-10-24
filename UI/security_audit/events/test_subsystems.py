import pytest
from playwright.sync_api import expect, Page, Browser
from UI.other_tests.test_autentification_admin import _perform_login
import json
import re
from datetime import datetime, timedelta
from UI.universal_functions.filter import (
    filter_menu_appears,
    filter_date_time_appears,
    filter_date_time_set_and_remove,
    filter_date_time_positive_range,
    filter_date_time_future_empty,
    filter_date_time_inverted_range_empty,
    filter_date_time_exact_no_match,
    filter_date_time_only_from,
    filter_date_time_only_to,
    check_filter_by_select,
    check_filter_by_select_negative_other_values,
    check_filter_by_input,
    check_filter_by_input_negative_other_values,
    check_filter_by_input_first_row_value
)
from UI.universal_functions.sorted import (
    check_sorting_by_date_column,
    check_sorting_by_date_column_desc,
    check_sorting_by_text_column,
    check_sorting_by_text_column_desc,
    check_sorting_by_number_column,
    check_sorting_by_number_column_desc
)
from UI.universal_functions.click_on_body import (
    click_info_and_check_modal,
    wait_for_api_response_with_response
)

ROWS_COUNT_SUBSYSTEMS_PAGE = None

# --- Инициализация количества строк для вкладки "События сервисов" ---
def rows_count_subsystems(page: Page):
    global ROWS_COUNT_SUBSYSTEMS_PAGE
    page.reload()
    with wait_for_api_response_with_response(page, '/cycleLogs/count') as resp_info:
        pass
    response = resp_info.value
    ROWS_COUNT_SUBSYSTEMS_PAGE = response.json()["count"]

@pytest.fixture
def skip_if_no_data(authenticated_page: Page):
    empty_message = authenticated_page.locator('.cdm-data-grid__empty-message')
    if empty_message.is_visible():
        pytest.skip("Нет данных для проверки")

@pytest.fixture
def skip_if_no_pagination(authenticated_page: Page):
    rows_count_subsystems(authenticated_page)
    if ROWS_COUNT_SUBSYSTEMS_PAGE is not None and ROWS_COUNT_SUBSYSTEMS_PAGE <= 10:
        pytest.skip("Пагинация не отображается при количестве записей ≤ 10")

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_subsystems_subsystems_events_tab_navigation_and_url(authenticated_page: Page, credentials):
    """
    Проверяет переход на вкладку "События сервисов" в разделе "Аудит безопасности" -> "Журналы регистрации"
    и корректность URL.
    """
    global ROWS_COUNT_SUBSYSTEMS_PAGE
    page = authenticated_page
    try:
        # Ожидаем полной загрузки сайдбара после авторизации
        expect(page.locator('.cdm-sidebar')).to_be_visible()

        # Шаг № 2: Клик по "Аудит безопасности"
        security_audit_button = page.get_by_text("Аудит безопасности")
        expect(security_audit_button).to_be_visible()
        security_audit_button.click()
        page.wait_for_timeout(300)

        # Шаг № 3: Клик по "Журналы регистрации"
        logs_button = page.get_by_text("Журналы регистрации")
        expect(logs_button).to_be_visible()
        logs_button.click()
        page.wait_for_timeout(300)

        # Шаг № 4: Клик по вкладке "События сервисов" с ожиданием запроса
        with page.expect_response(lambda response: "/cycleLogs/count" in response.url) as resp_info:
            subsystems_events_tab = page.get_by_role("tab", name="События сервисов ")
            expect(subsystems_events_tab).to_be_visible()
            subsystems_events_tab.click()
            page.wait_for_timeout(300)
        response = resp_info.value
        ROWS_COUNT_SUBSYSTEMS_PAGE = response.json()["count"]

        # Шаг № 5: Проверка URL
        expect(page).to_have_url(f"https://{credentials['ip']}/security-audit/events/subsystems")

    except Exception as e:
        if page:
            page.screenshot(path="UI/error_screenshots/subsystems_events_tab_navigation_error.png")
        raise e

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_subsystems_subsystems_events_tab_others_not_selected(authenticated_page: Page, credentials):
    """
    Проверяет, что после перехода на вкладку "События сервисов" остальные вкладки
    ("События безопасности", "Аудит доступа", "Аудит настроек") не активны (не выбраны).
    """
    page = authenticated_page
    try:
        # Ожидаем полной загрузки сайдбара после авторизации
        expect(page.locator('.cdm-sidebar')).to_be_visible()

        # Шаг № 2: Клик по "Аудит безопасности"
        security_audit_button = page.get_by_text("Аудит безопасности")
        expect(security_audit_button).to_be_visible()
        security_audit_button.click()
        page.wait_for_timeout(300)

        # Шаг № 3: Клик по "Журналы регистрации"
        logs_button = page.get_by_text("Журналы регистрации")
        expect(logs_button).to_be_visible()
        logs_button.click()
        page.wait_for_timeout(300)

        # Шаг № 4: Клик по вкладке "События сервисов"
        subsystems_events_tab = page.get_by_role("tab", name="События сервисов ")
        expect(subsystems_events_tab).to_be_visible()
        subsystems_events_tab.click()
        page.wait_for_timeout(300)

        # Шаг № 5: Проверка, что вкладка "События сервисов" активна
        expect(subsystems_events_tab).to_have_attribute("aria-selected", "true")

        # Шаг № 6: Проверка, что другие вкладки не активны
        security_events_tab = page.get_by_role("tab", name="События безопасности ")
        expect(security_events_tab).to_have_attribute("aria-selected", "false")

        access_events_tab = page.get_by_role("tab", name="Аудит доступа ")
        expect(access_events_tab).to_have_attribute("aria-selected", "false")

        settings_events_tab = page.get_by_role("tab", name="Аудит настроек ")
        expect(settings_events_tab).to_have_attribute("aria-selected", "false")

    except Exception as e:
        if page:
            page.screenshot(path="UI/error_screenshots/subsystems_events_tab_others_not_selected_error.png")
        raise e

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_subsystems_update_button_and_api_call(authenticated_page: Page, credentials):
    """
    Проверяет функциональность кнопки 'Обновить' и связанный с ней API-запрос
    на вкладке "События сервисов".
    """
    page = authenticated_page
    try:
        # Шаг № 1: Находим и кликаем на кнопку "Обновить"
        update_button = page.get_by_text("Обновить")
        expect(update_button).to_be_visible()

        # Ожидаем сетевой запрос после клика по кнопке "Обновить"
        with page.expect_response(lambda response: "api/service/remote/logger-analytics/analytics-server/call/cycleLogs" in response.url) as response_info:
            update_button.click()
        
        # Проверяем статус ответа
        response = response_info.value
        assert response.status in [200, 304], f"Unexpected status code: {response.status}"

    except Exception as e:
        if page:
            page.screenshot(path="UI/error_screenshots/update_button_api_call_subsystems_error.png")
        raise e

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_subsystems_download_button_modal_and_close(authenticated_page: Page, credentials):
    """
    Проверяет появление окна скачивания после нажатия на кнопку 'Скачать',
    кликабельность кнопок 'Да', 'Нет', крестика, и закрытие окна по кнопке 'Нет'.
    """
    page = authenticated_page
    try:
        # Находим и кликаем на кнопку "Скачать"
        download_button = page.get_by_text("Скачать")
        expect(download_button).to_be_visible()
        download_button.click()
        page.wait_for_timeout(300)

        # Проверяем появление окна с заголовком
        modal_title = page.get_by_text("Скачать файл в кодировке UTF-8")
        expect(modal_title).to_be_visible()

        # Проверяем кликабельность кнопок "Да", "Нет" и крестика
        yes_button = page.get_by_role("button", name="Да")
        no_button = page.get_by_role("button", name="Нет")
        close_button = page.locator('button:has(span[title="Закрыть"])')
        expect(yes_button).to_be_visible()
        expect(no_button).to_be_visible()
        expect(close_button).to_be_visible()

        # Нажимаем "Нет" и проверяем, что окно закрылось
        no_button.click()
        page.wait_for_timeout(300)
        expect(modal_title).not_to_be_visible()

    except Exception as e:
        if page:
            page.screenshot(path="UI/error_screenshots/download_modal_subsystems_error.png")
        raise e

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_subsystems_download_modal_close_by_cross(authenticated_page: Page, credentials, skip_if_no_data):
    """
    Проверяет, что модальное окно скачивания закрывается по нажатию на крестик (События сервисов).
    """
    page = authenticated_page
    # Открываем окно скачивания
    download_button = page.get_by_text("Скачать")
    expect(download_button).to_be_visible()
    download_button.click()
    page.wait_for_timeout(300)
    # Проверяем появление окна
    modal_title = page.get_by_text("Скачать файл в кодировке UTF-8")
    expect(modal_title).to_be_visible()
    # Нажимаем на крестик
    close_button = page.locator('button:has(span[title="Закрыть"])')
    expect(close_button).to_be_visible()
    close_button.click()
    page.wait_for_timeout(300)
    # Проверяем, что окно закрылось
    expect(modal_title).not_to_be_visible()

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_subsystems_subsystems_pagination_navigation(authenticated_page: Page, credentials, skip_if_no_data, skip_if_no_pagination):
    """
    Проверяет работу пагинации на вкладке "События сервисов": переходы между страницами (вперёд, назад, первая, последняя).
    """
    page = authenticated_page
    # Шаг 1: Проверяем, что пагинация отображается
    pagination = page.locator('.MuiTablePagination-root.cdm-pagination')
    expect(pagination).to_be_visible()
    # Шаг 2: Получаем локаторы кнопок пагинации
    action_buttons = page.locator('.cdm-pagination__action-buttons')
    buttons = action_buttons.locator('button')
    first_btn = buttons.nth(0)
    prev_btn = buttons.nth(1)
    next_btn = buttons.nth(-2)
    last_btn = buttons.nth(-1)
    # Шаг 3: Переход на последнюю страницу
    if last_btn.is_enabled():
        last_btn.click()
        page.wait_for_timeout(300)
        assert not next_btn.is_enabled(), "Кнопка 'следующая' должна быть неактивна на последней странице"
        assert not last_btn.is_enabled(), "Кнопка 'последняя' должна быть неактивна на последней странице"
    # Шаг 4: Переход на первую страницу
    if first_btn.is_enabled():
        first_btn.click()
        page.wait_for_timeout(300)
        assert not first_btn.is_enabled(), "Кнопка 'первая' должна быть неактивна на первой странице"
        assert not prev_btn.is_enabled(), "Кнопка 'предыдущая' должна быть неактивна на первой странице"
    # Шаг 5: Переход на вторую страницу (если есть)
    page_buttons = action_buttons.locator('button:not([disabled]) .MuiButton-label')
    if page_buttons.count() > 1:
        page_buttons.nth(1).click()
        page.wait_for_timeout(300)
        selected = action_buttons.locator('.MuiButton-root._selected')
        assert selected.count() == 1, "Должна быть выбрана одна страница"
    # Шаг 6: Возврат на первую страницу
    if first_btn.is_enabled():
        first_btn.click()
        page.wait_for_timeout(300)
        assert not first_btn.is_enabled(), "Кнопка 'первая' должна быть неактивна на первой странице после возврата"

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_subsystems_page_size_10(authenticated_page: Page, credentials, skip_if_no_data, skip_if_no_pagination):
    """
    Проверяет, что при выборе 10 записей на странице отображается не больше 10 строк (или меньше, если данных меньше).
    """
    rows_count_subsystems(authenticated_page)
    global ROWS_COUNT_SUBSYSTEMS_PAGE
    assert ROWS_COUNT_SUBSYSTEMS_PAGE is not None, "ROWS_COUNT_SUBSYSTEMS_PAGE не определён"
    page = authenticated_page
    # Шаг 1: Открываем меню выбора количества записей
    page_size_button = page.locator('.MuiSelect-root[role="button"]')
    expect(page_size_button).to_be_visible()
    page_size_button.click()
    # Шаг 2: Выбираем 10 записей
    option = page.locator('li[role="option"][data-value="10"]')
    expect(option).to_be_visible()
    option.click()
    page.wait_for_timeout(500)
    # Шаг 3: Считаем количество строк в таблице
    rows = page.locator('.cdm-data-grid tbody tr')
    row_count = rows.count()
    # Шаг 4: Проверяем соответствие количества строк
    assert row_count == min(10, ROWS_COUNT_SUBSYSTEMS_PAGE), f"Ожидалось {min(10, ROWS_COUNT_SUBSYSTEMS_PAGE)} строк, найдено {row_count}"

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_subsystems_page_size_30(authenticated_page: Page, credentials, skip_if_no_data, skip_if_no_pagination):
    """
    Проверяет, что при выборе 30 записей на странице отображается не больше 30 строк (или меньше, если данных меньше).
    """
    rows_count_subsystems(authenticated_page)
    global ROWS_COUNT_SUBSYSTEMS_PAGE
    assert ROWS_COUNT_SUBSYSTEMS_PAGE is not None, "ROWS_COUNT_SUBSYSTEMS_PAGE не определён"
    page = authenticated_page
    # Шаг 1: Открываем меню выбора количества записей
    page_size_button = page.locator('.MuiSelect-root[role="button"]')
    expect(page_size_button).to_be_visible()
    page_size_button.click()
    # Шаг 2: Выбираем 30 записей
    option = page.locator('li[role="option"][data-value="30"]')
    expect(option).to_be_visible()
    option.click()
    page.wait_for_timeout(500)
    # Шаг 3: Считаем количество строк в таблице
    rows = page.locator('.cdm-data-grid tbody tr')
    row_count = rows.count()
    # Шаг 4: Проверяем соответствие количества строк
    assert row_count == min(30, ROWS_COUNT_SUBSYSTEMS_PAGE), f"Ожидалось {min(30, ROWS_COUNT_SUBSYSTEMS_PAGE)} строк, найдено {row_count}"

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_subsystems_page_size_50(authenticated_page: Page, credentials, skip_if_no_data, skip_if_no_pagination):
    """
    Проверяет, что при выборе 50 записей на странице отображается не больше 50 строк (или меньше, если данных меньше).
    """
    rows_count_subsystems(authenticated_page)
    global ROWS_COUNT_SUBSYSTEMS_PAGE
    assert ROWS_COUNT_SUBSYSTEMS_PAGE is not None, "ROWS_COUNT_SUBSYSTEMS_PAGE не определён"
    page = authenticated_page
    # Шаг 1: Открываем меню выбора количества записей
    page_size_button = page.locator('.MuiSelect-root[role="button"]')
    expect(page_size_button).to_be_visible()
    page_size_button.click()
    # Шаг 2: Выбираем 50 записей
    option = page.locator('li[role="option"][data-value="50"]')
    expect(option).to_be_visible()
    option.click()
    page.wait_for_timeout(500)
    # Шаг 3: Считаем количество строк в таблице
    rows = page.locator('.cdm-data-grid tbody tr')
    row_count = rows.count()
    # Шаг 4: Проверяем соответствие количества строк
    assert row_count == min(50, ROWS_COUNT_SUBSYSTEMS_PAGE), f"Ожидалось {min(50, ROWS_COUNT_SUBSYSTEMS_PAGE)} строк, найдено {row_count}"

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_subsystems_page_size_100(authenticated_page: Page, credentials, skip_if_no_data, skip_if_no_pagination):
    """
    Проверяет, что при выборе 100 записей на странице отображается не больше 100 строк (или меньше, если данных меньше).
    """
    rows_count_subsystems(authenticated_page)
    global ROWS_COUNT_SUBSYSTEMS_PAGE
    assert ROWS_COUNT_SUBSYSTEMS_PAGE is not None, "ROWS_COUNT_SUBSYSTEMS_PAGE не определён"
    page = authenticated_page
    # Шаг 1: Открываем меню выбора количества записей
    page_size_button = page.locator('.MuiSelect-root[role="button"]')
    expect(page_size_button).to_be_visible()
    page_size_button.click()
    # Шаг 2: Выбираем 100 записей
    option = page.locator('li[role="option"][data-value="100"]')
    expect(option).to_be_visible()
    option.click()
    page.wait_for_timeout(800)
    # Шаг 3: Считаем количество строк в таблице
    rows = page.locator('.cdm-data-grid tbody tr')
    row_count = rows.count()
    # Шаг 4: Проверяем соответствие количества строк
    assert row_count == min(100, ROWS_COUNT_SUBSYSTEMS_PAGE), f"Ожидалось {min(100, ROWS_COUNT_SUBSYSTEMS_PAGE)} строк, найдено {row_count}"

# --- Негативные тесты ---

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_subsystems_no_page_size_menu_if_few_rows(authenticated_page: Page, credentials, skip_if_no_data):
    """
    Проверяет, что меню выбора количества строк не отображается, если строк меньше 10 (События сервисов).
    """
    rows_count_subsystems(authenticated_page)
    global ROWS_COUNT_SUBSYSTEMS_PAGE
    assert ROWS_COUNT_SUBSYSTEMS_PAGE is not None, "ROWS_COUNT_SUBSYSTEMS_PAGE не определён"
    page = authenticated_page
    if ROWS_COUNT_SUBSYSTEMS_PAGE <= 10:
        page_size_button = page.locator('.MuiSelect-root[role="button"]')
        assert not page_size_button.is_visible(), "Меню выбора количества строк не должно отображаться при малом числе строк"
    else:
        pytest.skip("Строк больше 10, тест не актуален")

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_subsystems_page_size_more_than_rows(authenticated_page: Page, credentials, skip_if_no_data, skip_if_no_pagination):
    """
    Проверяет, что при выборе количества строк больше, чем есть в таблице, отображаются все строки и UI не ломается (События сервисов).
    """
    rows_count_subsystems(authenticated_page)
    global ROWS_COUNT_SUBSYSTEMS_PAGE
    assert ROWS_COUNT_SUBSYSTEMS_PAGE is not None, "ROWS_COUNT_SUBSYSTEMS_PAGE не определён"
    page = authenticated_page
    if ROWS_COUNT_SUBSYSTEMS_PAGE <= 10:
        pytest.skip("Меню выбора количества строк не отображается при количестве строк <= 10")
    if ROWS_COUNT_SUBSYSTEMS_PAGE < 100:
        page_size_button = page.locator('.MuiSelect-root[role="button"]')
        expect(page_size_button).to_be_visible()
        page_size_button.click()
        option = page.locator('li[role="option"][data-value="100"]')
        expect(option).to_be_visible()
        option.click()
        page.wait_for_timeout(500)
        rows = page.locator('.cdm-data-grid tbody tr')
        row_count = rows.count()
        assert row_count == ROWS_COUNT_SUBSYSTEMS_PAGE, f"Ожидалось {ROWS_COUNT_SUBSYSTEMS_PAGE} строк, найдено {row_count} при выборе 100 строк"
    else:
        pytest.skip("Строк 100 или больше, тест не актуален")

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_subsystems_pagination_inactive_buttons(authenticated_page: Page, credentials, skip_if_no_data, skip_if_no_pagination):
    """
    Проверяет, что неактивные кнопки пагинации действительно неактивны и страница не меняется (События сервисов).
    """
    page = authenticated_page
    pagination = page.locator('.MuiTablePagination-root.cdm-pagination')
    expect(pagination).to_be_visible()
    action_buttons = page.locator('.cdm-pagination__action-buttons')
    buttons = action_buttons.locator('button')
    first_btn = buttons.nth(0)
    prev_btn = buttons.nth(1)
    next_btn = buttons.nth(-2)
    last_btn = buttons.nth(-1)
    # На первой странице: first и prev неактивны
    if not first_btn.is_enabled() and not prev_btn.is_enabled():
        selected_before = action_buttons.locator('.MuiButton-root._selected').inner_text()
        assert not first_btn.is_enabled(), "Кнопка 'первая' должна быть неактивна на первой странице"
        assert not prev_btn.is_enabled(), "Кнопка 'предыдущая' должна быть неактивна на первой странице"
        selected_after = action_buttons.locator('.MuiButton-root._selected').inner_text()
        assert selected_before == selected_after, "Страница не должна меняться при неактивных кнопках на первой странице"
    # Переходим на последнюю страницу
    if last_btn.is_enabled():
        last_btn.click()
        page.wait_for_timeout(300)
    # На последней странице: next и last неактивны
    if not next_btn.is_enabled() and not last_btn.is_enabled():
        selected_before = action_buttons.locator('.MuiButton-root._selected').inner_text()
        assert not next_btn.is_enabled(), "Кнопка 'следующая' должна быть неактивна на последней странице"
        assert not last_btn.is_enabled(), "Кнопка 'последняя' должна быть неактивна на последней странице"
        selected_after = action_buttons.locator('.MuiButton-root._selected').inner_text()
        assert selected_before == selected_after, "Страница не должна меняться при неактивных кнопках на последней странице"

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_subsystems_update_button_multiple_clicks(authenticated_page: Page, credentials, skip_if_no_data):
    """
    Проверяет, что при многократном клике по кнопке 'Обновить' не возникает ошибок и UI не зависает.
    """
    page = authenticated_page
    update_button = page.get_by_text("Обновить")
    expect(update_button).to_be_visible()
    for _ in range(5):
        update_button.click()
        page.wait_for_timeout(100)
    expect(update_button).to_be_enabled()

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_subsystems_buttons_active_no_data(authenticated_page: Page, credentials):
    """
    Проверяет, что при отсутствии данных кнопки 'Скачать' и 'Обновить' активны и не вызывают ошибок.
    """
    page = authenticated_page
    empty_message = page.locator('.cdm-data-grid__empty-message')
    if not empty_message.is_visible():
        pytest.skip("Данные есть, тест не актуален")
    update_button = page.get_by_text("Обновить")
    download_button = page.get_by_text("Скачать")
    expect(update_button).to_be_enabled()
    expect(download_button).to_be_enabled()
    update_button.click()
    page.wait_for_timeout(300)
    download_button.click()
    page.wait_for_timeout(300)
    # Закрываем модалку кликом по координатам (1/4 ширины и высоты экрана)
    size = page.viewport_size or page.context.viewport_size
    if size:
        x = size['width'] // 4
        y = size['height'] // 4
        page.mouse.click(x, y)
        page.wait_for_timeout(300)
    # Проверяем, что модальное окно закрылось
    modal_title = page.locator('text=Скачать файл в кодировке UTF-8')
    assert not modal_title.is_visible(), "Модальное окно должно закрыться после клика по фону"
    error_modal = page.locator('.MuiDialog-root .MuiDialogTitle-root:has-text("Ошибка")')
    assert error_modal.count() == 0, "Не должно появляться модальное окно с ошибкой"

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_subsystems_no_pagination_and_page_size_menu_if_few_rows(authenticated_page: Page, credentials, skip_if_no_data):
    """
    Проверяет, что при количестве строк <= 10 пагинация и меню выбора количества строк отсутствуют в DOM.
    """
    rows_count_subsystems(authenticated_page)
    global ROWS_COUNT_SUBSYSTEMS_PAGE
    assert ROWS_COUNT_SUBSYSTEMS_PAGE is not None, "ROWS_COUNT_SUBSYSTEMS_PAGE не определён"
    page = authenticated_page
    if ROWS_COUNT_SUBSYSTEMS_PAGE <= 10:
        pagination = page.locator('.MuiTablePagination-root.cdm-pagination')
        page_size_button = page.locator('.MuiSelect-root[role="button"]')
        assert pagination.count() == 0, "Пагинация не должна отображаться при малом числе строк"
        assert page_size_button.count() == 0, "Меню выбора количества строк не должно отображаться при малом числе строк"
    else:
        pytest.skip("Строк больше 10, тест не актуален")

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_subsystems_tab_persists_after_reload(authenticated_page: Page, credentials):
    """
    Проверяет, что после обновления страницы остаётся та же вкладка (События сервисов).
    """
    page = authenticated_page
    subsystems_tab = page.get_by_role("tab", name="События сервисов ")
    expect(subsystems_tab).to_have_attribute("aria-selected", "true")
    page.reload()
    page.wait_for_timeout(800)
    subsystems_tab = page.get_by_role("tab", name="События сервисов ")
    expect(subsystems_tab).to_be_visible()
    expect(subsystems_tab).to_have_attribute("aria-selected", "true")


"""-------------------------------------Фильтр Дата и время--------------------------------------- """


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_subsystems_filter_menu_appears(authenticated_page: Page, credentials):
    """
    Проверяет, что меню фильтрации открывается и содержит указанное количество и название любого фильтра в меню 
    """
    count_filter = 4
    name_filter = "Дата и время"
    filter_menu_appears(authenticated_page, credentials, count_filter, name_filter)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_subsystems_filter_date_time_appears(authenticated_page: Page, credentials):
    """
    Проверяет, что после выбора фильтра "Дата и время" появляется блок фильтрации с полями "с" и "по".
    """
    filter_date_time_appears(authenticated_page, credentials)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_subsystems_filter_date_time_set_and_remove(authenticated_page: Page, credentials):
    """
    Проверяет установку фильтра по дате и времени, корректность отображения выбранных значений и удаление фильтра.
    """
    filter_date_time_set_and_remove(authenticated_page, credentials)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_subsystems_filter_date_time_positive_range(authenticated_page: Page, credentials, skip_if_no_data):
    """
    Проверяет фильтрацию по корректному диапазону дат: отображаются только строки, попадающие в указанный интервал, после удаления фильтра — возвращаются все строки.
    """
    filter_date_time_positive_range(authenticated_page, credentials, skip_if_no_data)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_subsystems_filter_date_time_future_empty(authenticated_page: Page, credentials, skip_if_no_data):
    """
    Проверяет, что при фильтрации по будущему диапазону дат таблица становится пустой, а после удаления фильтра данные возвращаются.
    """
    filter_date_time_future_empty(authenticated_page, credentials, skip_if_no_data)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_subsystems_filter_date_time_inverted_range_empty(authenticated_page: Page, credentials, skip_if_no_data):
    """
    Проверяет, что при перепутанных границах фильтра (дата "с" больше даты "по") таблица пуста, а после удаления фильтра данные возвращаются.
    """
    filter_date_time_inverted_range_empty(authenticated_page, credentials, skip_if_no_data)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_subsystems_filter_date_time_exact_no_match(authenticated_page: Page, credentials, skip_if_no_data):
    """
    Проверяет, что при фильтрации по дате, которой нет в данных (10 лет назад), таблица пуста, а после удаления фильтра данные возвращаются.
    """
    filter_date_time_exact_no_match(authenticated_page, credentials, skip_if_no_data)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_subsystems_filter_date_time_only_from(authenticated_page: Page, credentials, skip_if_no_data):
    """
    Проверяет фильтрацию только по дате "с": отображаются только строки с датой больше или равной выбранной, после удаления фильтра данные возвращаются.
    """
    filter_date_time_only_from(authenticated_page, credentials, skip_if_no_data)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_subsystems_filter_date_time_only_to(authenticated_page: Page, credentials, skip_if_no_data):
    """
    Проверяет фильтрацию только по дате "по": отображаются только строки с датой меньше или равной выбранной, после удаления фильтра данные возвращаются.
    """
    filter_date_time_only_to(authenticated_page, credentials, skip_if_no_data)


"""-------------------------------------Фильтр Критичность--------------------------------------- """


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_subsystems_filter_positive_critical_error(authenticated_page: Page, credentials):
    """
    Проверяет поизивную фильтрацию по критичности: Ошибка
    """
    filter_name = "Критичность"
    severity_text = "Ошибка"
    # severity_value = "error"
    # check_filter_by_select(authenticated_page, filter_name, severity_text, severity_value)
    check_filter_by_select(authenticated_page, filter_name, severity_text)
            
@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_subsystems_filter_negative_critical_error(authenticated_page: Page, credentials):
    """
    Проверяет негативную фильтрацию по критичности: Ошибка
    """
    filter_name = "Критичность"
    severity_text = "Ошибка"
    # severity_value = "error"
    # check_filter_by_select_negative_other_values(authenticated_page, filter_name, severity_text, severity_value)
    check_filter_by_select_negative_other_values(authenticated_page, filter_name, severity_text)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_subsystems_filter_positive_critical_warn(authenticated_page: Page, credentials):
    """
    Проверяет поизивную фильтрацию по критичности: Предупреждение
    """
    filter_name = "Критичность"
    severity_text = "Предупреждение"
    check_filter_by_select(authenticated_page, filter_name, severity_text)
            
@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_subsystems_filter_negative_critical_warn(authenticated_page: Page, credentials):
    """
    Проверяет негативную фильтрацию по критичности: Предупреждение
    """
    filter_name = "Критичность"
    severity_text = "Предупреждение"
    check_filter_by_select_negative_other_values(authenticated_page, filter_name, severity_text)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_subsystems_filter_positive_critical_info(authenticated_page: Page, credentials):
    """
    Проверяет поизивную фильтрацию по критичности: Информация
    """
    filter_name = "Критичность"
    severity_text = "Информация"
    check_filter_by_select(authenticated_page, filter_name, severity_text)
            
@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_subsystems_filter_negative_critical_info(authenticated_page: Page, credentials):
    """
    Проверяет негативную фильтрацию по критичности: Информация
    """
    filter_name = "Критичность"
    severity_text = "Информация"
    check_filter_by_select_negative_other_values(authenticated_page, filter_name, severity_text)


"""-------------------------------------Фильтр Сервис--------------------------------------- """


# @pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
# def test_page_subsystems_filter_positive_service_CSI(authenticated_page: Page, credentials):
#     """
#     Проверяет позитивную фильтрацию по Сервису: ngfw.core
#     """
#     filter_name = "Сервис"
#     severity_text = "CSI"
#     check_filter_by_input(authenticated_page, filter_name, severity_text)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_subsystems_check_filter_by_input_first_row_value(authenticated_page: Page, credentials):
    """
    Проверяет позитивную фильтрацию по Сервису: по первой строке
    """
    filter_name = "Сервис"
    check_filter_by_input_first_row_value(authenticated_page, filter_name)

# @pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
# def test_page_subsystems_filter_positive_service_case_csi_insensitive(authenticated_page: Page, credentials):
#     """
#     Проверяет позитивную фильтрацию по Сервису: csi (case-insensitive)
#     """
#     filter_name = "Сервис"
#     severity_text = "csi"
#     check_filter_by_input(authenticated_page, filter_name, severity_text)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_security_filter_negative_service_qwerty123(authenticated_page: Page, credentials):
    """
    Проверяет негативную фильтрацию по Сервису: qwerty123
    """
    filter_name = "Сервис"
    severity_text = "qwerty123"
    check_filter_by_input_negative_other_values(authenticated_page, filter_name, severity_text)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_security_filter_negative_service_CSII(authenticated_page: Page, credentials):
    """
    Проверяет негативную фильтрацию по Сервису: ngfw.coree
    """
    filter_name = "Сервис"
    severity_text = "CSII"
    check_filter_by_input_negative_other_values(authenticated_page, filter_name, severity_text)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_subsystems_filter_negative_service_special_chars(authenticated_page: Page, credentials):
    """
    Проверяет негативную фильтрацию по Сервису: спецсимволы
    """
    filter_name = "Сервис"
    severity_text = "!@#$%^&*()_+"
    check_filter_by_input_negative_other_values(authenticated_page, filter_name, severity_text)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_subsystems_filter_negative_service_long_string(authenticated_page: Page, credentials):
    """
    Проверяет негативную фильтрацию по Сервису: очень длинная строка
    """
    filter_name = "Сервис"
    severity_text = "A" * 1024
    check_filter_by_input_negative_other_values(authenticated_page, filter_name, severity_text)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_subsystems_filter_negative_service_sql_injection(authenticated_page: Page, credentials):
    """
    Проверяет негативную фильтрацию по Сервису: SQL-инъекция
    """
    filter_name = "Сервис"
    severity_text = "' OR 1=1 --"
    check_filter_by_input_negative_other_values(authenticated_page, filter_name, severity_text)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_subsystems_filter_negative_service_spaces(authenticated_page: Page, credentials):
    """
    Проверяет негативную фильтрацию по Сервису: только пробелы
    """
    filter_name = "Сервис"
    severity_text = "   "
    check_filter_by_input_negative_other_values(authenticated_page, filter_name, severity_text)


"""------------------------------Фильтр пользователь--------------------------------------- """


# @pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
# def test_page_subsystems_filter_positive_first_row_user(authenticated_page: Page, credentials):
#     """
#     Проверяет позитивную фильтрацию по Пользователю: по первой строке
#     """
#     filter_name = "Пользователь"
#     check_filter_by_input_first_row_value(authenticated_page, filter_name)


# @pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
# def test_page_subsystems_filter_positive_user_system(authenticated_page: Page, credentials):
#     """
#     Проверяет позитивную фильтрацию по Пользователю: system
#     """
#     filter_name = "Пользователь"
#     severity_text = "system"
#     check_filter_by_input(authenticated_page, filter_name, severity_text)

# @pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
# def test_page_subsystems_filter_positive_user_system_insensitive(authenticated_page: Page, credentials):
#     """
#     Проверяет позитивную фильтрацию по Пользователю: SYSTEM (case-insensitive)
#     """
#     filter_name = "Пользователь"
#     severity_text = "SYSTEM"
#     check_filter_by_input(authenticated_page, filter_name, severity_text)

# @pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
# def test_page_subsystems_filter_negative_user_qwerty123(authenticated_page: Page, credentials):
#     """
#     Проверяет негативную фильтрацию по Пользователю: qwerty123
#     """
#     filter_name = "Пользователь"
#     severity_text = "qwerty123"
#     check_filter_by_input_negative_other_values(authenticated_page, filter_name, severity_text)

# @pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
# def test_page_subsystems_filter_negative_user_adminn(authenticated_page: Page, credentials):
#     """
#     Проверяет негативную фильтрацию по Пользователю: adminn
#     """
#     filter_name = "Пользователь"
#     severity_text = "adminn"
#     check_filter_by_input_negative_other_values(authenticated_page, filter_name, severity_text)

# @pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
# def test_page_subsystems_filter_negative_user_special_chars(authenticated_page: Page, credentials):
#     """
#     Проверяет негативную фильтрацию по Пользователю: спецсимволы
#     """
#     filter_name = "Пользователь"
#     severity_text = "!@#$%^&*()_+"
#     check_filter_by_input_negative_other_values(authenticated_page, filter_name, severity_text)

# @pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
# def test_page_subsystems_filter_negative_user_long_string(authenticated_page: Page, credentials):
#     """
#     Проверяет негативную фильтрацию по Пользователю: очень длинная строка
#     """
#     filter_name = "Пользователь"
#     severity_text = "A" * 1024
#     check_filter_by_input_negative_other_values(authenticated_page, filter_name, severity_text)

# @pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
# def test_page_subsystems_filter_negative_user_sql_injection(authenticated_page: Page, credentials):
#     """
#     Проверяет негативную фильтрацию по Пользователю: SQL-инъекция
#     """
#     filter_name = "Пользователь"
#     severity_text = "' OR 1=1 --"
#     check_filter_by_input_negative_other_values(authenticated_page, filter_name, severity_text)

# @pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
# def test_page_subsystems_filter_negative_user_spaces(authenticated_page: Page, credentials):
#     """
#     Проверяет негативную фильтрацию по Пользователю: только пробелы
#     """
#     filter_name = "Пользователь"
#     severity_text = "   "
#     check_filter_by_input_negative_other_values(authenticated_page, filter_name, severity_text)


"""------------------------------Фильтр Описание события--------------------------------------- """


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_subsystems_filter_positive_first_row_event(authenticated_page: Page, credentials):
    """
    Проверяет позитивную фильтрацию по Описанию события: по первой строке
    """
    filter_name = "Описание события"
    check_filter_by_input_first_row_value(authenticated_page, filter_name)


# @pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
# def test_page_subsystems_filter_positive_event_start(authenticated_page: Page, credentials):
#     """
#     Проверяет позитивную фильтрацию по Описанию события: start
#     """
#     filter_name = "Описание события"
#     severity_text = "start"
#     check_filter_by_input(authenticated_page, filter_name, severity_text)

# @pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
# def test_page_subsystems_filter_positive_event_start_insensitive(authenticated_page: Page, credentials):
#     """
#     Проверяет позитивную фильтрацию по Описанию события: DIE (case-insensitive)
#     """
#     filter_name = "Описание события"
#     severity_text = "DIE"
#     check_filter_by_input(authenticated_page, filter_name, severity_text)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_subsystems_filter_negative_event_qwerty123(authenticated_page: Page, credentials):
    """
    Проверяет негативную фильтрацию по Описанию события: qwerty123
    """
    filter_name = "Описание события"
    severity_text = "qwerty123"
    check_filter_by_input_negative_other_values(authenticated_page, filter_name, severity_text)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_subsystems_filter_negative_event_alloww(authenticated_page: Page, credentials):
    """
    Проверяет негативную фильтрацию по Описанию события: alloww
    """
    filter_name = "Описание события"
    severity_text = "alloww"
    check_filter_by_input_negative_other_values(authenticated_page, filter_name, severity_text)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_subsystems_filter_negative_event_special_chars(authenticated_page: Page, credentials):
    """
    Проверяет негативную фильтрацию по Описанию события: спецсимволы
    """
    filter_name = "Описание события"
    severity_text = "!@#$%^&*()_+"
    check_filter_by_input_negative_other_values(authenticated_page, filter_name, severity_text)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_subsystems_filter_negative_event_long_string(authenticated_page: Page, credentials):
    """
    Проверяет негативную фильтрацию по Описанию события: очень длинная строка
    """
    filter_name = "Описание события"
    severity_text = "A" * 1024
    check_filter_by_input_negative_other_values(authenticated_page, filter_name, severity_text)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_subsystems_filter_negative_event_sql_injection(authenticated_page: Page, credentials):
    """
    Проверяет негативную фильтрацию по Описанию события: SQL-инъекция
    """
    filter_name = "Описание события"
    severity_text = "' OR 1=1 --"
    check_filter_by_input_negative_other_values(authenticated_page, filter_name, severity_text)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_subsystems_filter_negative_event_spaces(authenticated_page: Page, credentials):
    """
    Проверяет негативную фильтрацию по Описанию события: только пробелы
    """
    filter_name = "Описание события"
    severity_text = "   "
    check_filter_by_input_negative_other_values(authenticated_page, filter_name, severity_text)


"""------------------------------Сортировка по Дате--------------------------------------- """


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_subsystems_sorted_positive_date_first_state(authenticated_page: Page, credentials):
    """
    Проверяет позитивный кейс фильтрации по убыванию (состояние 1) по Дате
    """
    column_name = "Дата и время"
    endpoint_substring = "/api/service/remote/logger-analytics/analytics-server/call/cycleLogs?filter="
    check_sorting_by_date_column(authenticated_page, column_name, endpoint_substring)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_subsystems_sorted_positive_date_second_state(authenticated_page: Page, credentials):
    """
    Проверяет позитивный кейс фильтрации по возрастанию (состояние 2) по Дате
    """
    column_name = "Дата и время"
    endpoint_substring = "/api/service/remote/logger-analytics/analytics-server/call/cycleLogs?filter="
    check_sorting_by_date_column_desc(authenticated_page, column_name, endpoint_substring)


"""------------------------------Сортировка по Критичности--------------------------------------- """


# @pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
# def test_page_subsystems_sorted_positive_critical_first_state(authenticated_page: Page, credentials):
#     """
#     Проверяет позитивный кейс фильтрации по убыванию (состояние 1) по Критичности
#     """
#     column_name = "Критичность"
#     endpoint_substring = "/api/service/remote/logger-analytics/analytics-server/call/cycleLogs?filter="
#     check_sorting_by_text_column(authenticated_page, column_name, endpoint_substring)

# @pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
# def test_page_subsystems_sorted_positive_critical_second_state(authenticated_page: Page, credentials):
#     """
#     Проверяет позитивный кейс фильтрации по возрастанию (состояние 2) по Критичности
#     """
#     column_name = "Критичность"
#     endpoint_substring = "/api/service/remote/logger-analytics/analytics-server/call/cycleLogs?filter="
#     check_sorting_by_text_column_desc(authenticated_page, column_name, endpoint_substring)


"""------------------------------Сортировка по Пользователю--------------------------------------- """


# @pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
# def test_page_subsystems_sorted_positive_user_first_state(authenticated_page: Page, credentials):
#     """
#     Проверяет позитивный кейс фильтрации по убыванию (состояние 1) по Пользователю
#     """
#     column_name = "Пользователь"
#     endpoint_substring = "/api/service/remote/logger-analytics/analytics-server/call/cycleLogs?filter="
#     check_sorting_by_text_column(authenticated_page, column_name, endpoint_substring)

# @pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
# def test_page_subsystems_sorted_positive_user_second_state(authenticated_page: Page, credentials):
#     """
#     Проверяет позитивный кейс фильтрации по возрастанию (состояние 2) по Пользователю
#     """
#     column_name = "Пользователь"
#     endpoint_substring = "/api/service/remote/logger-analytics/analytics-server/call/cycleLogs?filter="
#     check_sorting_by_text_column_desc(authenticated_page, column_name, endpoint_substring)


"""------------------------------Сортировка по Сервису--------------------------------------- """


# @pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
# def test_page_subsystems_sorted_positive_service_first_state(authenticated_page: Page, credentials):
#     """
#     Проверяет позитивный кейс фильтрации по убыванию (состояние 1) по Сервису
#     """
#     column_name = "Сервис"
#     endpoint_substring = "/api/service/remote/logger-analytics/analytics-server/call/cycleLogs?filter="
#     check_sorting_by_text_column(authenticated_page, column_name, endpoint_substring)

# @pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
# def test_page_subsystems_sorted_positive_service_second_state(authenticated_page: Page, credentials):
#     """
#     Проверяет позитивный кейс фильтрации по возрастанию (состояние 2) по Сервису
#     """
#     column_name = "Сервис"
#     endpoint_substring = "/api/service/remote/logger-analytics/analytics-server/call/cycleLogs?filter="
#     check_sorting_by_text_column_desc(authenticated_page, column_name, endpoint_substring)


"""------------------------------Сортировка по Описанию события--------------------------------------- """


# @pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
# def test_page_subsystems_sorted_positive_event_first_state(authenticated_page: Page, credentials):
#     """
#     Проверяет позитивный кейс фильтрации по убыванию (состояние 1) по Описанию события
#     """
#     column_name = "Описание события"
#     endpoint_substring = "/api/service/remote/logger-analytics/analytics-server/call/cycleLogs?filter="
#     check_sorting_by_text_column(authenticated_page, column_name, endpoint_substring)

# @pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
# def test_page_subsystems_sorted_positive_event_second_state(authenticated_page: Page, credentials):
#     """
#     Проверяет позитивный кейс фильтрации по возрастанию (состояние 2) по Описанию события
#     """
#     column_name = "Описание события"
#     endpoint_substring = "/api/service/remote/logger-analytics/analytics-server/call/cycleLogs?filter="
#     check_sorting_by_text_column_desc(authenticated_page, column_name, endpoint_substring)


"""------------------------------Проверка модального окна информации в теле--------------------------------------- """


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_subsystems_check_modal_window_info_positive(authenticated_page: Page, credentials, skip_if_no_data):
    """
    Проверяет отображение модального окна с информацией по первой строке по умолчанию
    """
    click_info_and_check_modal(authenticated_page)