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
    navigate_and_check_url_with_tab,
    check_tabs_selected_state,
    find_input_by_label
)
from UI.universal_functions.click_on_body import (
    wait_for_api_response,
    wait_for_api_response_with_response,
    get_cell_by_header,
    validate_cell_input_error_negative,
    validate_cell_input_error_positive,
    select_option_in_cell_and_verify,
    toggle_cell_switch_state,
    click_form_row_save_and_wait,
    find_row_by_columns,
    assert_no_row_by_columns,
    click_row_edit_and_wait_editable,
    click_row_delete_and_wait
)
import time


'''-------------------------Вспомогательные функции-----------------------------'''





'''-------------------------Основные тесты-----------------------------'''


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_navigate_and_check_url_with_tab(authenticated_page: Page, credentials):
    """
    Проверяет переход на вкладку "Статические правила" в разделе "Правила фильтрации" и корректность URL для "Статические правила".
    """
    tab_button_1 = "Межсетевое экранирование"
    tab_button_2 = "Правила фильтрации"
    tab_name = "Статические правила"
    url = "firewall/filtering/white-rules"
    navigate_and_check_url_with_tab(authenticated_page, tab_button_1, tab_button_2, tab_name, url, credentials)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_check_tabs_selected_state(authenticated_page: Page, credentials):
    """
    Проверяет, что вкладки "Статические правила" и "Белые правила" выбраны.
    """
    tab_names = ["Динамические правила", "Статические правила"]
    active_tab = "Статические правила"
    expected_path = "firewall/filtering/white-rules"
    check_tabs_selected_state(authenticated_page, tab_names, active_tab, expected_path, credentials)


'''-------------------------Проверки содержимого созданной строки-----------------------------'''


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_form_row_weight_input_visible(authenticated_page: Page, credentials):
    """
    Проверяет, что поле 'Вес' отображается в форм-строке.
    """
    page = authenticated_page

    # Шаг №1. Обеспечиваем наличие форм-строки и берём ячейку колонки "Вес"
    cell = get_cell_by_header(page, header_text="Вес", create_row=True)

    # Шаг №2. В ячейке должен быть текстовый input
    weight_input = cell.locator('input[type="text"]')
    if weight_input.count() == 0 or not weight_input.first.is_visible():
        fail_with_screenshot("Поле 'Вес' (text input) не отображается", page)


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_form_row_action_select_visible(authenticated_page: Page, credentials):
    """
    Проверяет, что селект 'Действие' отображается в форм-строке.
    """
    page = authenticated_page

    # Шаг №1. Форм-строка + ячейка "Действие"
    cell = get_cell_by_header(page, header_text="Действие", create_row=True)

    # Шаг №2. В ячейке должен быть селект с id="action"
    action_select = cell.locator('div#action[role="button"]')
    if action_select.count() == 0 or not action_select.first.is_visible():
        fail_with_screenshot("Селект 'Действие' (id=action) не отображается", page)


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_form_row_proto_select_visible(authenticated_page: Page, credentials):
    """
    Проверяет, что селект 'Тип/Протокол' отображается в форм-строке.
    """
    page = authenticated_page

    # Шаг №1. Форм-строка + ячейка "Тип"
    cell = get_cell_by_header(page, header_text="Тип", create_row=True)

    # Шаг №2. В ячейке должен быть селект с id="proto"
    proto_select = cell.locator('div#proto[role="button"]')
    if proto_select.count() == 0 or not proto_select.first.is_visible():
        fail_with_screenshot("Селект 'Тип/Протокол' (id=proto) не отображается", page)


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_form_row_source_textarea_visible(authenticated_page: Page, credentials):
    """
    Проверяет, что textarea 'Сеть/адрес источника' отображается в форм-строке.
    """
    page = authenticated_page

    # Шаг №1. Форм-строка + ячейка "Сеть/адрес-источника"
    cell = get_cell_by_header(page, header_text="Сеть/адрес-источника", create_row=True)

    # Шаг №2. В ячейке должна быть textarea
    textarea = cell.locator("textarea")
    if textarea.count() == 0 or not textarea.first.is_visible():
        fail_with_screenshot("Textarea 'Сеть/адрес источника' не отображается", page)


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_form_row_destination_textarea_visible(authenticated_page: Page, credentials):
    """
    Проверяет, что textarea 'Сеть/адрес назначения' отображается в форм-строке.
    """
    page = authenticated_page

    # Шаг №1. Форм-строка + ячейка "Сеть/адрес назначения"
    cell = get_cell_by_header(page, header_text="Сеть/адрес назначения", create_row=True)

    # Шаг №2. В ячейке должна быть textarea
    textarea = cell.locator("textarea")
    if textarea.count() == 0 or not textarea.first.is_visible():
        fail_with_screenshot("Textarea 'Сеть/адрес назначения' не отображается", page)


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_form_row_dst_port_textarea_visible(authenticated_page: Page, credentials):
    """
    Проверяет, что textarea 'Порт получателя' отображается в форм-строке.
    """
    page = authenticated_page

    # Шаг №1. Форм-строка + ячейка "Порт получателя"
    cell = get_cell_by_header(page, header_text="Порт получателя", create_row=True)

    # Шаг №2. В ячейке должна быть textarea
    textarea = cell.locator("textarea")
    if textarea.count() == 0 or not textarea.first.is_visible():
        fail_with_screenshot("Textarea 'Порт получателя' не отображается", page)


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_form_row_status_switch_visible(authenticated_page: Page, credentials):
    """
    Проверяет, что переключатель 'Статус' отображается в форм-строке.
    """
    page = authenticated_page

    # Шаг №1. Форм-строка + ячейка "Статус"
    cell = get_cell_by_header(page, header_text="Статус", create_row=True)

    # Шаг №2. В ячейке должен быть чекбокс name=active
    status_switch_input = cell.locator('input[name="active"][type="checkbox"]')
    if status_switch_input.count() == 0 or not status_switch_input.first.is_visible():
        fail_with_screenshot("Переключатель 'Статус' (checkbox name=active) не отображается", page)


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_form_row_comment_input_visible(authenticated_page: Page, credentials):
    """
    Проверяет, что поле 'Комментарий' отображается в форм-строке.
    """
    page = authenticated_page

    # Шаг №1. Форм-строка + ячейка "Комментарий"
    cell = get_cell_by_header(page, header_text="Комментарий", create_row=True)

    # Шаг №2. В ячейке должен быть текстовый input
    comment_input = cell.locator('input[type="text"]')
    if comment_input.count() == 0 or not comment_input.first.is_visible():
        fail_with_screenshot("Поле 'Комментарий' (text input) не отображается", page)


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_form_row_action_buttons_visible(authenticated_page: Page, credentials):
    """
    Проверяет, что кнопки 'Сохранить' и 'Отмена' отображаются в форм-строке.
    """
    page = authenticated_page

    # Шаг №1. Через универсальную функцию обеспечиваем форм-строку (берём любую колонку, например 'Вес')
    any_cell = get_cell_by_header(page, header_text="Вес", create_row=True)
    form_row = any_cell.locator("xpath=ancestor::tr[contains(@class,'cdm-data-grid__body__form-row')]")

    # Шаг №2. Проверяем наличие кнопок действий в этой же строке
    save_btn = form_row.locator('.cdm-data-grid__body__row__actions-cell .cdm-icon-wrapper[title="Сохранить"]')
    cancel_btn = form_row.locator('.cdm-data-grid__body__row__actions-cell .cdm-icon-wrapper[title="Отмена"]')

    if save_btn.count() == 0 or not save_btn.first.is_visible():
        fail_with_screenshot("Кнопка 'Сохранить' в форм-строке не отображается", page)
    if cancel_btn.count() == 0 or not cancel_btn.first.is_visible():
        fail_with_screenshot("Кнопка 'Отмена' в форм-строке не отображается", page)


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_form_row_only_one_visible(authenticated_page: Page, credentials):
    """
    Проверяет, что одновременно видна только одна форм-строка.
    """
    page = authenticated_page

    # Шаг №1. Через универсальную функцию обеспечиваем появление форм-строки (любой столбец, например 'Вес')
    _ = get_cell_by_header(page, header_text="Вес", create_row=True)

    # Шаг №2. Проверяем, что форм-строка ровно одна
    form_rows = page.locator('tr.cdm-data-grid__body__form-row')
    if form_rows.count() != 1:
        fail_with_screenshot(f"Ожидалась 1 форм-строка, найдено: {form_rows.count()}", page)


'''-------------------------Проверки валидации поля "Вес"-----------------------------'''
'''-------------------------Негативные тест-кейсы"-----------------------------'''


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_weight_validation_min_value(authenticated_page: Page, credentials):
    """
    Проверяет валидацию поля "Вес": "Значение должно быть больше или равно 0"
    """
    page = authenticated_page
    validate_cell_input_error_negative(
        page,
        header_text="Вес",
        value_to_fill="-1",
        expected_error="Значение должно быть больше или равно 0",
        create_row=True,
        match_mode="exact",
    )


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_weight_validation_max_value(authenticated_page: Page, credentials):
    """
    Проверяет валидацию поля "Вес": "Значение должно быть меньше или равно 120000"
    """
    page = authenticated_page
    validate_cell_input_error_negative(
        page,
        header_text="Вес",
        value_to_fill="120001",
        expected_error="Значение должно быть меньше или равно 120000",
        create_row=True,
        match_mode="exact",
    )


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_weight_validation_number_required(authenticated_page: Page, credentials):
    """
    Проверяет валидацию поля "Вес": "Введите число"
    """
    page = authenticated_page
    validate_cell_input_error_negative(
        page,
        header_text="Вес",
        value_to_fill="abc",
        expected_error="Введите число",
        create_row=True,
        match_mode="exact",
    )


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_weight_validation_not_number_comma(authenticated_page: Page, credentials):
    """
    Проверяет, что при вводе значения с запятой в поле "Вес"
    отображается ошибка "Введите число".
    """
    page = authenticated_page
    # Шаг №1. Вводим "12,3" (запятая вместо точки) и ожидаем "Введите число"
    validate_cell_input_error_negative(
        page,
        header_text="Вес",
        value_to_fill="12,3",
        expected_error="Введите число",
        create_row=True,
        blur_action="tab",
    )


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_weight_validation_not_number_space_inside(authenticated_page: Page, credentials):
    """
    Проверяет, что при вводе значения с пробелом в поле "Вес"
    отображается ошибка "Введите число".
    """
    page = authenticated_page
    # Шаг №1. Вводим "1 2" и ожидаем "Введите число"
    validate_cell_input_error_negative(
        page,
        header_text="Вес",
        value_to_fill="1 2",
        expected_error="Введите число",
        create_row=True,
        blur_action="tab",
    )


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_weight_validation_not_number_double_minus(authenticated_page: Page, credentials):
    """
    Проверяет, что при вводе некорректного знака в поле "Вес"
    отображается ошибка "Введите число".
    """
    page = authenticated_page
    # Шаг №1. Вводим "--1" и ожидаем "Введите число"
    validate_cell_input_error_negative(
        page,
        header_text="Вес",
        value_to_fill="--1",
        expected_error="Введите число",
        create_row=True,
        blur_action="tab",
    )


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_weight_validation_not_number_nan(authenticated_page: Page, credentials):
    """
    Проверяет, что при вводе 'NaN' в поле "Вес"
    отображается ошибка "Введите число".
    """
    page = authenticated_page
    # Шаг №1. Вводим "NaN" и ожидаем "Введите число"
    validate_cell_input_error_negative(
        page,
        header_text="Вес",
        value_to_fill="NaN",
        expected_error="Введите число",
        create_row=True,
        blur_action="tab",
    )


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_weight_validation_not_number_infinity(authenticated_page: Page, credentials):
    """
    Проверяет, что при вводе символа бесконечности в поле "Вес"
    отображается ошибка "Введите число".
    """
    page = authenticated_page
    # Шаг №1. Вводим "∞" и ожидаем "Введите число"
    validate_cell_input_error_negative(
        page,
        header_text="Вес",
        value_to_fill="∞",
        expected_error="Введите число",
        create_row=True,
        blur_action="tab",
    )


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_weight_validation_required_empty(authenticated_page: Page, credentials):
    """
    Проверяет, что при пустом значении в поле "Вес"
    отображается ошибка "Заполните поле Введите число".
    """
    page = authenticated_page
    # Шаг №1. Оставляем поле пустым и ожидаем сообщение об обязательности
    validate_cell_input_error_negative(
        page,
        header_text="Вес",
        value_to_fill="",
        expected_error="Заполните поле Введите число",
        create_row=True,
        blur_action="tab",
    )


'''-------------------------Позитивные тест-кейсы"-----------------------------'''


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_weight_validation_positive(authenticated_page: Page, credentials):
    """
    Проверяет, что при вводе корректного значения в поле "Вес"
    не отображается ошибка валидации.
    """
    page = authenticated_page

    # Вводим корректное значение (например, "100")
    validate_cell_input_error_positive(
        page,
        header_text="Вес",
        value_to_fill="100",
        create_row=True
    )


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_weight_validation_min_boundary(authenticated_page: Page, credentials):
    """
    Проверяет, что значение '0' в поле 'Вес' валидно (граница снизу включительно).
    """
    page = authenticated_page
    # Шаг №1. Вводим 0 и убеждаемся, что ошибки валидации нет
    validate_cell_input_error_positive(
        page,
        header_text="Вес",
        value_to_fill="0",
        create_row=True,
        blur_action="tab",
    )


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_weight_validation_max_boundary(authenticated_page: Page, credentials):
    """
    Проверяет, что значение '120000' в поле 'Вес' валидно (граница сверху включительно).
    """
    page = authenticated_page
    # Шаг №1. Вводим 120000 и убеждаемся, что ошибки валидации нет
    validate_cell_input_error_positive(
        page,
        header_text="Вес",
        value_to_fill="120000",
        create_row=True,
        blur_action="tab",
    )


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_weight_validation_typical_value(authenticated_page: Page, credentials):
    """
    Проверяет, что типичное значение '500' в поле 'Вес' валидно.
    """
    page = authenticated_page
    # Шаг №1. Вводим 500 и убеждаемся, что ошибки валидации нет
    validate_cell_input_error_positive(
        page,
        header_text="Вес",
        value_to_fill="500",
        create_row=True,
        blur_action="tab",
    )


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_weight_validation_almost_max(authenticated_page: Page, credentials):
    """
    Проверяет, что значение '119999' (почти максимум) валидно и не даёт ошибку.
    """
    page = authenticated_page
    # Шаг №1. Вводим 119999 и убеждаемся, что ошибки нет
    validate_cell_input_error_positive(
        page,
        header_text="Вес",
        value_to_fill="119999",
        create_row=True,
        blur_action="tab",
    )


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_weight_validation_almost_min(authenticated_page: Page, credentials):
    """
    Проверяет, что значение '1' (над нижней границей) валидно.
    """
    page = authenticated_page
    # Шаг №1. Вводим 1 и убеждаемся, что ошибки нет
    validate_cell_input_error_positive(
        page,
        header_text="Вес",
        value_to_fill="1",
        create_row=True,
        blur_action="tab",
    )


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_weight_validation_leading_zeros(authenticated_page: Page, credentials):
    """
    Проверяет, что значение с лидирующими нулями '0005' валидно и не вызывает ошибок.
    """
    page = authenticated_page
    # Шаг №1. Вводим 0005 и убеждаемся, что ошибки нет
    validate_cell_input_error_positive(
        page,
        header_text="Вес",
        value_to_fill="0005",
        create_row=True,
        blur_action="tab",
    )


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_weight_validation_leading_plus(authenticated_page: Page, credentials):
    """
    Проверяет, что значение с лидирующим плюсом '+10' валидно (если контрол это допускает).
    """
    page = authenticated_page
    # Шаг №1. Вводим +10 и убеждаемся, что ошибки нет
    validate_cell_input_error_positive(
        page,
        header_text="Вес",
        value_to_fill="+10",
        create_row=True,
        blur_action="tab",
    )


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_weight_validation_trim_spaces(authenticated_page: Page, credentials):
    """
    Проверяет, что значение с пробелами по краям '  42  ' триммится/принимается без ошибки.
    """
    page = authenticated_page
    # Шаг №1. Вводим '  42  ' и убеждаемся, что ошибки нет
    validate_cell_input_error_positive(
        page,
        header_text="Вес",
        value_to_fill="  42  ",
        create_row=True,
        blur_action="tab",
    )


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_weight_validation_paste_like(authenticated_page: Page, credentials):
    """
    Проверяет, что значение '3500', введённое "как вставка", валидно и ошибка не появляется.
    """
    page = authenticated_page
    # Шаг №1. Вводим 3500 и убеждаемся, что ошибки нет
    validate_cell_input_error_positive(
        page,
        header_text="Вес",
        value_to_fill="3500",
        create_row=True,
        blur_action="tab",
    )


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_weight_validation_error_disappears_after_fix(authenticated_page: Page, credentials):
    """
    Проверяет, что после ввода невалидного значения и последующего исправления на валидное '10'
    ошибка исчезает (в финале — ошибки нет).
    """
    page = authenticated_page
    # Шаг №1. Вводим сначала невалидное значение (для провокации ошибки), блюрим
    validate_cell_input_error_negative(
        page,
        header_text="Вес",
        value_to_fill="-1",
        expected_error="Значение должно быть больше или равно 0",
        create_row=True,
        match_mode="exact",
    )

    # Шаг №2. Теперь вводим валидное значение через универсальную позитивную проверку
    validate_cell_input_error_positive(
        page,
        header_text="Вес",
        value_to_fill="119999",
        create_row=True,   # форм-строка уже открыта
        blur_action="tab",
    )
    

'''-------------------------Проверки селекта "Действие"-----------------------------'''


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_action_select_choose_drop(authenticated_page: Page, credentials):
    """
    Проверяет, что в колонке "Действие" можно выбрать 'drop' и выбранное корректно отображается.
    """
    page = authenticated_page
    select_option_in_cell_and_verify(
        page,
        header_text="Действие",
        option_to_select="drop",
        create_row=True,
    )

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_action_select_choose_allow(authenticated_page: Page, credentials):
    """
    Проверяет, что в колонке "Действие" можно выбрать 'allow' и выбранное корректно отображается.
    """
    page = authenticated_page
    select_option_in_cell_and_verify(
        page,
        header_text="Действие",
        option_to_select="allow",
        create_row=True,
    )


'''-------------------------Проверки селекта "Тип"-----------------------------'''


# 1) IP (0)
@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_type_select_choose_ip(authenticated_page: Page, credentials):
    """
    Проверяет, что в колонке "Тип" можно выбрать 'IP (0)'.
    """
    page = authenticated_page
    select_option_in_cell_and_verify(page, header_text="Тип", option_to_select="IP (0)", create_row=True)

# 2) TCP (6)
@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_type_select_choose_tcp(authenticated_page: Page, credentials):
    """
    Проверяет, что в колонке "Тип" можно выбрать 'TCP (6)'.
    """
    page = authenticated_page
    select_option_in_cell_and_verify(page, header_text="Тип", option_to_select="TCP (6)", create_row=True)

# 3) UDP (17)
@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_type_select_choose_udp(authenticated_page: Page, credentials):
    """
    Проверяет, что в колонке "Тип" можно выбрать 'UDP (17)'.
    """
    page = authenticated_page
    select_option_in_cell_and_verify(page, header_text="Тип", option_to_select="UDP (17)", create_row=True)

# 4) TCP+UDP (6,17)
@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_type_select_choose_tcp_udp(authenticated_page: Page, credentials):
    """
    Проверяет, что в колонке "Тип" можно выбрать 'TCP+UDP (6,17)'.
    """
    page = authenticated_page
    select_option_in_cell_and_verify(page, header_text="Тип", option_to_select="TCP+UDP (6,17)", create_row=True)

# 5) ICMP (1)
@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_type_select_choose_icmp(authenticated_page: Page, credentials):
    """
    Проверяет, что в колонке "Тип" можно выбрать 'ICMP (1)'.
    """
    page = authenticated_page
    select_option_in_cell_and_verify(page, header_text="Тип", option_to_select="ICMP (1)", create_row=True)

# 6) IGMP (2)
@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_type_select_choose_igmp(authenticated_page: Page, credentials):
    """
    Проверяет, что в колонке "Тип" можно выбрать 'IGMP (2)'.
    """
    page = authenticated_page
    select_option_in_cell_and_verify(page, header_text="Тип", option_to_select="IGMP (2)", create_row=True)

# 7) IPENCAP (4)
@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_type_select_choose_ipencap(authenticated_page: Page, credentials):
    """
    Проверяет, что в колонке "Тип" можно выбрать 'IPENCAP (4)'.
    """
    page = authenticated_page
    select_option_in_cell_and_verify(page, header_text="Тип", option_to_select="IPENCAP (4)", create_row=True)

# 8) DCCP (33)
@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_type_select_choose_dccp(authenticated_page: Page, credentials):
    """
    Проверяет, что в колонке "Тип" можно выбрать 'DCCP (33)'.
    """
    page = authenticated_page
    select_option_in_cell_and_verify(page, header_text="Тип", option_to_select="DCCP (33)", create_row=True)

# 9) GRE (47)
@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_type_select_choose_gre(authenticated_page: Page, credentials):
    """
    Проверяет, что в колонке "Тип" можно выбрать 'GRE (47)'.
    """
    page = authenticated_page
    select_option_in_cell_and_verify(page, header_text="Тип", option_to_select="GRE (47)", create_row=True)

# 10) ESP (50)
@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_type_select_choose_esp(authenticated_page: Page, credentials):
    """
    Проверяет, что в колонке "Тип" можно выбрать 'ESP (50)'.
    """
    page = authenticated_page
    select_option_in_cell_and_verify(page, header_text="Тип", option_to_select="ESP (50)", create_row=True)

# 11) AH (51)
@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_type_select_choose_ah(authenticated_page: Page, credentials):
    """
    Проверяет, что в колонке "Тип" можно выбрать 'AH (51)'.
    """
    page = authenticated_page
    select_option_in_cell_and_verify(page, header_text="Тип", option_to_select="AH (51)", create_row=True)

# 12) EIGRP (88)
@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_type_select_choose_eigrp(authenticated_page: Page, credentials):
    """
    Проверяет, что в колонке "Тип" можно выбрать 'EIGRP (88)'.
    """
    page = authenticated_page
    select_option_in_cell_and_verify(page, header_text="Тип", option_to_select="EIGRP (88)", create_row=True)

# 13) OSPF (89)
@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_type_select_choose_ospf(authenticated_page: Page, credentials):
    """
    Проверяет, что в колонке "Тип" можно выбрать 'OSPF (89)'.
    """
    page = authenticated_page
    select_option_in_cell_and_verify(page, header_text="Тип", option_to_select="OSPF (89)", create_row=True)

# 14) ETHERIP (97)
@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_type_select_choose_etherip(authenticated_page: Page, credentials):
    """
    Проверяет, что в колонке "Тип" можно выбрать 'ETHERIP (97)'.
    """
    page = authenticated_page
    select_option_in_cell_and_verify(page, header_text="Тип", option_to_select="ETHERIP (97)", create_row=True)

# 15) ENCAP (98)
@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_type_select_choose_encap(authenticated_page: Page, credentials):
    """
    Проверяет, что в колонке "Тип" можно выбрать 'ENCAP (98)'.
    """
    page = authenticated_page
    select_option_in_cell_and_verify(page, header_text="Тип", option_to_select="ENCAP (98)", create_row=True)

# 16) PIM (103)
@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_type_select_choose_pim(authenticated_page: Page, credentials):
    """
    Проверяет, что в колонке "Тип" можно выбрать 'PIM (103)'.
    """
    page = authenticated_page
    select_option_in_cell_and_verify(page, header_text="Тип", option_to_select="PIM (103)", create_row=True)

# 17) VRRP (112)
@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_type_select_choose_vrrp(authenticated_page: Page, credentials):
    """
    Проверяет, что в колонке "Тип" можно выбрать 'VRRP (112)'.
    """
    page = authenticated_page
    select_option_in_cell_and_verify(page, header_text="Тип", option_to_select="VRRP (112)", create_row=True)

# 18) L2TP (115)
@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_type_select_choose_l2tp(authenticated_page: Page, credentials):
    """
    Проверяет, что в колонке "Тип" можно выбрать 'L2TP (115)'.
    """
    page = authenticated_page
    select_option_in_cell_and_verify(page, header_text="Тип", option_to_select="L2TP (115)", create_row=True)

# 19) ISIS (124)
@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_type_select_choose_isis(authenticated_page: Page, credentials):
    """
    Проверяет, что в колонке "Тип" можно выбрать 'ISIS (124)'.
    """
    page = authenticated_page
    select_option_in_cell_and_verify(page, header_text="Тип", option_to_select="ISIS (124)", create_row=True)

# 20) SCTP (132)
@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_type_select_choose_sctp(authenticated_page: Page, credentials):
    """
    Проверяет, что в колонке "Тип" можно выбрать 'SCTP (132)'.
    """
    page = authenticated_page
    select_option_in_cell_and_verify(page, header_text="Тип", option_to_select="SCTP (132)", create_row=True)

# 21) FC (133)
@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_type_select_choose_fc(authenticated_page: Page, credentials):
    """
    Проверяет, что в колонке "Тип" можно выбрать 'FC (133)'.
    """
    page = authenticated_page
    select_option_in_cell_and_verify(page, header_text="Тип", option_to_select="FC (133)", create_row=True)

# 22) MPLS-IN-IP (137)
@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_type_select_choose_mpls_in_ip(authenticated_page: Page, credentials):
    """
    Проверяет, что в колонке "Тип" можно выбрать 'MPLS-IN-IP (137)'.
    """
    page = authenticated_page
    select_option_in_cell_and_verify(page, header_text="Тип", option_to_select="MPLS-IN-IP (137)", create_row=True)


'''-------------------------Проверки валидации поля "Сеть/адрес-источника"-----------------------------'''
'''-------------------------Негативные тест-кейсы"-----------------------------'''

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_srcnet_validation_invalid_short(authenticated_page: Page, credentials):
    """
    Проверяет, что при вводе '1' в поле "Сеть/адрес-источника"
    отображается ошибка "Неверный формат IP-адреса/подсети".
    """
    page = authenticated_page
    # Шаг №1. Вводим невалидное значение и проверяем текст ошибки
    validate_cell_input_error_negative(
        page,
        header_text="Сеть/адрес-источника",
        value_to_fill="1",
        expected_error="Неверный формат IP-адреса/подсети",
        create_row=True,   # откроем форм-строку при необходимости
        blur_action="tab",
    )


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_srcnet_validation_invalid_octet_overflow(authenticated_page: Page, credentials):
    """
    Проверяет, что при вводе '10.10.10.256' в поле "Сеть/адрес-источника"
    отображается ошибка "Неверный формат IP-адреса/подсети".
    """
    page = authenticated_page
    # Шаг №1. Вводим невалидный IPv4 (октет > 255) и проверяем ошибку
    validate_cell_input_error_negative(
        page,
        header_text="Сеть/адрес-источника",
        value_to_fill="10.10.10.256",
        expected_error="Неверный формат IP-адреса/подсети",
        create_row=True,
        blur_action="tab",
    )


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_srcnet_validation_invalid_cidr_mask(authenticated_page: Page, credentials):
    """
    Проверяет, что при вводе '10.10.10.0/33' в поле "Сеть/адрес-источника"
    отображается ошибка "Неверный формат IP-адреса/подсети".
    """
    page = authenticated_page
    # Шаг №1. Невалидная маска CIDR и ожидание ошибки
    validate_cell_input_error_negative(
        page,
        header_text="Сеть/адрес-источника",
        value_to_fill="10.10.10.0/33",
        expected_error="Неверный формат IP-адреса/подсети",
        create_row=True,
        blur_action="tab",
    )


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_srcnet_invalid_too_few_octets(authenticated_page: Page, credentials):
    """
    Проверяет, что значение с тремя октетами '10.10.10' невалидно (меньше 4 октетов).
    """
    page = authenticated_page
    validate_cell_input_error_negative(
        page,
        header_text="Сеть/адрес-источника",
        value_to_fill="10.10.10",
        expected_error="Неверный формат IP-адреса/подсети",
        create_row=True,
    )

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_srcnet_invalid_too_many_octets(authenticated_page: Page, credentials):
    """
    Проверяет, что значение с пятью октетами '10.10.10.10.10' невалидно (больше 4 октетов).
    """
    page = authenticated_page
    validate_cell_input_error_negative(
        page,
        header_text="Сеть/адрес-источника",
        value_to_fill="10.10.10.10.10",
        expected_error="Неверный формат IP-адреса/подсети",
        create_row=True,
    )

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_srcnet_invalid_empty_octet(authenticated_page: Page, credentials):
    """
    Проверяет, что значение с пустым октетом '10.10..10.10' невалидно.
    """
    page = authenticated_page
    validate_cell_input_error_negative(
        page,
        header_text="Сеть/адрес-источника",
        value_to_fill="10.10..10.10",
        expected_error="Неверный формат IP-адреса/подсети",
        create_row=True,
    )

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_srcnet_invalid_octet_negative(authenticated_page: Page, credentials):
    """
    Проверяет, что значение с отрицательным октетом '10.10.10.-1' невалидно.
    """
    page = authenticated_page
    validate_cell_input_error_negative(
        page,
        header_text="Сеть/адрес-источника",
        value_to_fill="10.10.10.-1",
        expected_error="Неверный формат IP-адреса/подсети",
        create_row=True,
    )

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_srcnet_invalid_octet_overflow(authenticated_page: Page, credentials):
    """
    Проверяет, что значение с октетом >255 '10.10.10.256' невалидно.
    """
    page = authenticated_page
    validate_cell_input_error_negative(
        page,
        header_text="Сеть/адрес-источника",
        value_to_fill="10.10.10.256",
        expected_error="Неверный формат IP-адреса/подсети",
        create_row=True,
    )


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_srcnet_invalid_letters(authenticated_page: Page, credentials):
    """
    Проверяет, что не-числовые значения 'a.b.c.d' невалидны.
    """
    page = authenticated_page
    validate_cell_input_error_negative(
        page,
        header_text="Сеть/адрес-источника",
        value_to_fill="a.b.c.d",
        expected_error="Неверный формат IP-адреса/подсети",
        create_row=True,
    )

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_srcnet_invalid_russian_letters(authenticated_page: Page, credentials):
    """
    Проверяет, что кириллица 'текст' невалидна.
    """
    page = authenticated_page
    validate_cell_input_error_negative(
        page,
        header_text="Сеть/адрес-источника",
        value_to_fill="текст",
        expected_error="Неверный формат IP-адреса/подсети",
        create_row=True,
    )

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_srcnet_invalid_trailing_char(authenticated_page: Page, credentials):
    """
    Проверяет, что '10.10.10.10a' невалидно (постфиксный символ).
    """
    page = authenticated_page
    validate_cell_input_error_negative(
        page,
        header_text="Сеть/адрес-источника",
        value_to_fill="10.10.10.10a",
        expected_error="Неверный формат IP-адреса/подсети",
        create_row=True,
    )

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_srcnet_invalid_hash(authenticated_page: Page, credentials):
    """
    Проверяет, что '10.10.10.10#' невалидно (посторонний символ).
    """
    page = authenticated_page
    validate_cell_input_error_negative(
        page,
        header_text="Сеть/адрес-источника",
        value_to_fill="10.10.10.10#",
        expected_error="Неверный формат IP-адреса/подсети",
        create_row=True,
    )

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_srcnet_invalid_space_inside_octet(authenticated_page: Page, credentials):
    """
    Проверяет, что '10.10. 10.10' невалидно (пробел в октете).
    """
    page = authenticated_page
    validate_cell_input_error_negative(
        page,
        header_text="Сеть/адрес-источника",
        value_to_fill="10.10. 10.10",
        expected_error="Неверный формат IP-адреса/подсети",
        create_row=True,
    )


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_srcnet_invalid_cidr_empty_mask(authenticated_page: Page, credentials):
    """
    Проверяет, что '10.10.10.0/' невалидно (пустая маска).
    """
    page = authenticated_page
    validate_cell_input_error_negative(
        page,
        header_text="Сеть/адрес-источника",
        value_to_fill="10.10.10.0/",
        expected_error="Неверный формат IP-адреса/подсети",
        create_row=True,
    )

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_srcnet_invalid_cidr_non_numeric_mask(authenticated_page: Page, credentials):
    """
    Проверяет, что '10.10.10.0/abc' невалидно (нечисловая маска).
    """
    page = authenticated_page
    validate_cell_input_error_negative(
        page,
        header_text="Сеть/адрес-источника",
        value_to_fill="10.10.10.0/abc",
        expected_error="Неверный формат IP-адреса/подсети",
        create_row=True,
    )

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_srcnet_invalid_cidr_negative_mask(authenticated_page: Page, credentials):
    """
    Проверяет, что '10.10.10.0/-1' невалидно (маска < 0).
    """
    page = authenticated_page
    validate_cell_input_error_negative(
        page,
        header_text="Сеть/адрес-источника",
        value_to_fill="10.10.10.0/-1",
        expected_error="Неверный формат IP-адреса/подсети",
        create_row=True,
    )

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_srcnet_invalid_cidr_over_32(authenticated_page: Page, credentials):
    """
    Проверяет, что '10.10.10.0/33' невалидно (маска > 32).
    """
    page = authenticated_page
    validate_cell_input_error_negative(
        page,
        header_text="Сеть/адрес-источника",
        value_to_fill="10.10.10.0/33",
        expected_error="Неверный формат IP-адреса/подсети",
        create_row=True,
    )


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_srcnet_invalid_range_end_less_than_start(authenticated_page: Page, credentials):
    """
    Проверяет, что диапазон '10.0.0.10-10.0.0.1' невалиден (конец < начала).
    """
    page = authenticated_page
    validate_cell_input_error_negative(
        page,
        header_text="Сеть/адрес-источника",
        value_to_fill="10.0.0.10-10.0.0.1",
        expected_error="Неверный формат IP-адреса/подсети",
        create_row=True,
    )

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_srcnet_invalid_range_bad_end(authenticated_page: Page, credentials):
    """
    Проверяет, что диапазон с невалидной конечной границей '10.0.0.1-10.0.0.256' невалиден.
    """
    page = authenticated_page
    validate_cell_input_error_negative(
        page,
        header_text="Сеть/адрес-источника",
        value_to_fill="10.0.0.1-10.0.0.256",
        expected_error="Неверный формат IP-адреса/подсети",
        create_row=True,
    )

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_srcnet_invalid_range_half_open_start(authenticated_page: Page, credentials):
    """
    Проверяет, что ' -10.0.0.5' (полудиапазон без начала) невалиден.
    """
    page = authenticated_page
    validate_cell_input_error_negative(
        page,
        header_text="Сеть/адрес-источника",
        value_to_fill="-10.0.0.5",
        expected_error="Неверный формат IP-адреса/подсети",
        create_row=True,
    )

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_srcnet_invalid_range_half_open_end(authenticated_page: Page, credentials):
    """
    Проверяет, что '10.0.0.1-' (полудиапазон без конца) невалиден.
    """
    page = authenticated_page
    validate_cell_input_error_negative(
        page,
        header_text="Сеть/адрес-источника",
        value_to_fill="10.0.0.1-",
        expected_error="Неверный формат IP-адреса/подсети",
        create_row=True,
    )


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_srcnet_invalid_with_port_not_allowed(authenticated_page: Page, credentials):
    """
    Проверяет, что '10.0.0.1:80' невалидно, когда порт не разрешён (withPort по умолчанию False).
    """
    page = authenticated_page
    validate_cell_input_error_negative(
        page,
        header_text="Сеть/адрес-источника",
        value_to_fill="10.0.0.1:80",
        expected_error="Неверный формат IP-адреса/подсети",
        create_row=True,
    )

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_srcnet_invalid_port_zero(authenticated_page: Page, credentials):
    """
    Проверяет, что '10.0.0.1:0' невалидно (порт вне 1–65535).
    """
    page = authenticated_page
    validate_cell_input_error_negative(
        page,
        header_text="Сеть/адрес-источника",
        value_to_fill="10.0.0.1:0",
        expected_error="Неверный формат IP-адреса/подсети",
        create_row=True,
    )

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_srcnet_invalid_port_over_65535(authenticated_page: Page, credentials):
    """
    Проверяет, что '10.0.0.1:70000' невалидно (порт вне 1–65535).
    """
    page = authenticated_page
    validate_cell_input_error_negative(
        page,
        header_text="Сеть/адрес-источника",
        value_to_fill="10.0.0.1:70000",
        expected_error="Неверный формат IP-адреса/подсети",
        create_row=True,
    )


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_srcnet_invalid_wildcard_one_star(authenticated_page: Page, credentials):
    """
    Проверяет, что '10.10.10.*' невалидно (wildcard не разрешён).
    """
    page = authenticated_page
    validate_cell_input_error_negative(
        page,
        header_text="Сеть/адрес-источника",
        value_to_fill="10.10.10.*",
        expected_error="Неверный формат IP-адреса/подсети",
        create_row=True,
    )

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_srcnet_invalid_wildcard_two_stars(authenticated_page: Page, credentials):
    """
    Проверяет, что '10.10.*.*' невалидно (wildcard не разрешён).
    """
    page = authenticated_page
    validate_cell_input_error_negative(
        page,
        header_text="Сеть/адрес-источника",
        value_to_fill="10.10.*.*",
        expected_error="Неверный формат IP-адреса/подсети",
        create_row=True,
    )


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_srcnet_multi_with_one_invalid(authenticated_page: Page, credentials):
    """
    Проверяет, что список '10.10.10.10, 1' невалиден, если хотя бы одно значение неверно.
    """
    page = authenticated_page
    validate_cell_input_error_negative(
        page,
        header_text="Сеть/адрес-источника",
        # Предполагаем, что разделитель — запятая/пробел (как в UI)
        value_to_fill="10.10.10.10, 1",
        expected_error="Неверный формат IP-адреса/подсети",
        create_row=True,
    )


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_srcnet_multi_duplicates(authenticated_page: Page, credentials):
    """
    Проверяет, что дубли '10.10.10.1, 10.10.10.1' невалидны при uniq=true.
    """
    page = authenticated_page
    validate_cell_input_error_negative(
        page,
        header_text="Сеть/адрес-источника",
        value_to_fill="10.10.10.1, 10.10.10.1",
        expected_error="Значения должны быть уникальными",
        create_row=True,
    )


'''-------------------------Позитивные тест-кейсы"-----------------------------'''


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_srcnet_valid_single_ip(authenticated_page: Page, credentials):
    """
    Проверяет, что валидный одиночный IPv4 '10.10.10.10' принимается без ошибок.
    """
    page = authenticated_page
    # Шаг №1. Вводим валидный IPv4 и убеждаемся, что ошибок нет
    validate_cell_input_error_positive(
        page,
        header_text="Сеть/адрес-источника",
        value_to_fill="10.10.10.10",
        create_row=True,
        blur_action="tab",
    )


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_srcnet_valid_single_ip_max(authenticated_page: Page, credentials):
    """
    Проверяет, что валидный IPv4 на границе '255.255.255.255' принимается без ошибок.
    """
    page = authenticated_page
    # Шаг №1. Вводим граничный валидный IPv4 и убеждаемся, что ошибок нет
    validate_cell_input_error_positive(
        page,
        header_text="Сеть/адрес-источника",
        value_to_fill="255.255.255.255",
        create_row=True,
        blur_action="tab",
    )


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_srcnet_valid_cidr_host_32(authenticated_page: Page, credentials):
    """
    Проверяет, что валидная подсеть-хост '192.168.1.1/32' принимается без ошибок.
    """
    page = authenticated_page
    # Шаг №1. Вводим валидный CIDR /32 и убеждаемся, что ошибок нет
    validate_cell_input_error_positive(
        page,
        header_text="Сеть/адрес-источника",
        value_to_fill="192.168.1.1/32",
        create_row=True,
        blur_action="tab",
    )


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_srcnet_valid_cidr_any_0(authenticated_page: Page, credentials):
    """
    Проверяет, что валидная «вся сеть» '0.0.0.0/0' принимается без ошибок.
    """
    page = authenticated_page
    # Шаг №1. Вводим валидный CIDR /0 и убеждаемся, что ошибок нет
    validate_cell_input_error_positive(
        page,
        header_text="Сеть/адрес-источника",
        value_to_fill="0.0.0.0/0",
        create_row=True,
        blur_action="tab",
    )


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_srcnet_valid_cidr_network(authenticated_page: Page, credentials):
    """
    Проверяет, что валидная подсеть '10.0.0.0/24' принимается без ошибок.
    """
    page = authenticated_page
    # Шаг №1. Вводим валидный CIDR /24 и убеждаемся, что ошибок нет
    validate_cell_input_error_positive(
        page,
        header_text="Сеть/адрес-источника",
        value_to_fill="10.0.0.0/24",
        create_row=True,
        blur_action="tab",
    )


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_srcnet_valid_ip_range(authenticated_page: Page, credentials):
    """
    Проверяет, что валидный диапазон IP '10.0.0.1-10.0.0.5' принимается без ошибок.
    """
    page = authenticated_page
    # Шаг №1. Вводим валидный диапазон и убеждаемся, что ошибок нет
    validate_cell_input_error_positive(
        page,
        header_text="Сеть/адрес-источника",
        value_to_fill="10.0.0.1-10.0.0.5",
        create_row=True,
        blur_action="tab",
    )


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_srcnet_valid_multi_two_ips(authenticated_page: Page, credentials):
    """
    Проверяет, что валидный список из двух IP '10.0.0.1, 10.0.0.2' принимается без ошибок.
    """
    page = authenticated_page
    # Шаг №1. Вводим два уникальных IP через запятую и убеждаемся, что ошибок нет
    validate_cell_input_error_positive(
        page,
        header_text="Сеть/адрес-источника",
        value_to_fill="10.0.0.1, 10.0.0.2",
        create_row=True,
        blur_action="tab",
    )


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_srcnet_valid_multi_ip_and_cidr(authenticated_page: Page, credentials):
    """
    Проверяет, что валидный список IP + подсеть '192.168.0.0/16, 10.0.0.1' принимается без ошибок.
    """
    page = authenticated_page
    # Шаг №1. Вводим IP + CIDR в одном списке и убеждаемся, что ошибок нет
    validate_cell_input_error_positive(
        page,
        header_text="Сеть/адрес-источника",
        value_to_fill="192.168.0.0/16, 10.0.0.1",
        create_row=True,
        blur_action="tab",
    )


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_srcnet_valid_multi_with_spaces(authenticated_page: Page, credentials):
    """
    Проверяет, что значения с пробелами вокруг '  10.0.0.1 ,   10.0.0.2  ' принимаются без ошибок (тримминг).
    """
    page = authenticated_page
    # Шаг №1. Вводим список с лишними пробелами и убеждаемся, что ошибок нет
    validate_cell_input_error_positive(
        page,
        header_text="Сеть/адрес-источника",
        value_to_fill="  10.0.0.1 ,   10.0.0.2  ",
        create_row=True,
        blur_action="tab",
    )


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_srcnet_valid_multi_range_and_ip(authenticated_page: Page, credentials):
    """
    Проверяет, что смесь диапазона и IP '10.0.0.1-10.0.0.3, 10.0.0.10' принимается без ошибок.
    """
    page = authenticated_page
    # Шаг №1. Вводим диапазон + одиночный IP и убеждаемся, что ошибок нет
    validate_cell_input_error_positive(
        page,
        header_text="Сеть/адрес-источника",
        value_to_fill="10.0.0.1-10.0.0.3, 10.0.0.10",
        create_row=True,
        blur_action="tab",
    )


'''
-------------------------Проверки валидации поля "Сеть/адрес назначения"-----------------------------
-------------------------Негативные тест-кейсы-----------------------------
'''


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_destnet_validation_invalid_short(authenticated_page: Page, credentials):
    """
    Проверяет, что при вводе '1' в поле "Сеть/адрес назначения"
    отображается ошибка "Неверный формат IP-адреса/подсети".
    """
    page = authenticated_page
    # Шаг №1. Вводим невалидное значение и проверяем текст ошибки
    validate_cell_input_error_negative(
        page,
        header_text="Сеть/адрес назначения",
        value_to_fill="1",
        expected_error="Неверный формат IP-адреса/подсети",
        create_row=True,
        blur_action="tab",
    )


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_destnet_validation_invalid_octet_overflow(authenticated_page: Page, credentials):
    """
    Проверяет, что при вводе '10.10.10.256' в поле "Сеть/адрес назначения"
    отображается ошибка "Неверный формат IP-адреса/подсети".
    """
    page = authenticated_page
    # Шаг №1. Вводим невалидный IPv4 (октет > 255) и проверяем ошибку
    validate_cell_input_error_negative(
        page,
        header_text="Сеть/адрес назначения",
        value_to_fill="10.10.10.256",
        expected_error="Неверный формат IP-адреса/подсети",
        create_row=True,
        blur_action="tab",
    )


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_destnet_validation_invalid_cidr_mask(authenticated_page: Page, credentials):
    """
    Проверяет, что при вводе '10.10.10.0/33' в поле "Сеть/адрес назначения"
    отображается ошибка "Неверный формат IP-адреса/подсети".
    """
    page = authenticated_page
    # Шаг №1. Невалидная маска CIDR и ожидание ошибки
    validate_cell_input_error_negative(
        page,
        header_text="Сеть/адрес назначения",
        value_to_fill="10.10.10.0/33",
        expected_error="Неверный формат IP-адреса/подсети",
        create_row=True,
        blur_action="tab",
    )


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_destnet_invalid_too_few_octets(authenticated_page: Page, credentials):
    """
    Проверяет, что значение с тремя октетами '10.10.10' невалидно (меньше 4 октетов).
    """
    page = authenticated_page
    validate_cell_input_error_negative(
        page,
        header_text="Сеть/адрес назначения",
        value_to_fill="10.10.10",
        expected_error="Неверный формат IP-адреса/подсети",
        create_row=True,
    )

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_destnet_invalid_too_many_octets(authenticated_page: Page, credentials):
    """
    Проверяет, что значение с пятью октетами '10.10.10.10.10' невалидно (больше 4 октетов).
    """
    page = authenticated_page
    validate_cell_input_error_negative(
        page,
        header_text="Сеть/адрес назначения",
        value_to_fill="10.10.10.10.10",
        expected_error="Неверный формат IP-адреса/подсети",
        create_row=True,
    )

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_destnet_invalid_empty_octet(authenticated_page: Page, credentials):
    """
    Проверяет, что значение с пустым октетом '10.10..10.10' невалидно.
    """
    page = authenticated_page
    validate_cell_input_error_negative(
        page,
        header_text="Сеть/адрес назначения",
        value_to_fill="10.10..10.10",
        expected_error="Неверный формат IP-адреса/подсети",
        create_row=True,
    )

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_destnet_invalid_octet_negative(authenticated_page: Page, credentials):
    """
    Проверяет, что значение с отрицательным октетом '10.10.10.-1' невалидно.
    """
    page = authenticated_page
    validate_cell_input_error_negative(
        page,
        header_text="Сеть/адрес назначения",
        value_to_fill="10.10.10.-1",
        expected_error="Неверный формат IP-адреса/подсети",
        create_row=True,
    )

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_destnet_invalid_octet_overflow(authenticated_page: Page, credentials):
    """
    Проверяет, что значение с октетом >255 '10.10.10.256' невалидно.
    """
    page = authenticated_page
    validate_cell_input_error_negative(
        page,
        header_text="Сеть/адрес назначения",
        value_to_fill="10.10.10.256",
        expected_error="Неверный формат IP-адреса/подсети",
        create_row=True,
    )


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_destnet_invalid_letters(authenticated_page: Page, credentials):
    """
    Проверяет, что не-числовые значения 'a.b.c.d' невалидны.
    """
    page = authenticated_page
    validate_cell_input_error_negative(
        page,
        header_text="Сеть/адрес назначения",
        value_to_fill="a.b.c.d",
        expected_error="Неверный формат IP-адреса/подсети",
        create_row=True,
    )

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_destnet_invalid_russian_letters(authenticated_page: Page, credentials):
    """
    Проверяет, что кириллица 'текст' невалидна.
    """
    page = authenticated_page
    validate_cell_input_error_negative(
        page,
        header_text="Сеть/адрес назначения",
        value_to_fill="текст",
        expected_error="Неверный формат IP-адреса/подсети",
        create_row=True,
    )

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_destnet_invalid_trailing_char(authenticated_page: Page, credentials):
    """
    Проверяет, что '10.10.10.10a' невалидно (постфиксный символ).
    """
    page = authenticated_page
    validate_cell_input_error_negative(
        page,
        header_text="Сеть/адрес назначения",
        value_to_fill="10.10.10.10a",
        expected_error="Неверный формат IP-адреса/подсети",
        create_row=True,
    )

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_destnet_invalid_hash(authenticated_page: Page, credentials):
    """
    Проверяет, что '10.10.10.10#' невалидно (посторонний символ).
    """
    page = authenticated_page
    validate_cell_input_error_negative(
        page,
        header_text="Сеть/адрес назначения",
        value_to_fill="10.10.10.10#",
        expected_error="Неверный формат IP-адреса/подсети",
        create_row=True,
    )

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_destnet_invalid_space_inside_octet(authenticated_page: Page, credentials):
    """
    Проверяет, что '10.10. 10.10' невалидно (пробел в октете).
    """
    page = authenticated_page
    validate_cell_input_error_negative(
        page,
        header_text="Сеть/адрес назначения",
        value_to_fill="10.10. 10.10",
        expected_error="Неверный формат IP-адреса/подсети",
        create_row=True,
    )


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_destnet_invalid_cidr_empty_mask(authenticated_page: Page, credentials):
    """
    Проверяет, что '10.10.10.0/' невалидно (пустая маска).
    """
    page = authenticated_page
    validate_cell_input_error_negative(
        page,
        header_text="Сеть/адрес назначения",
        value_to_fill="10.10.10.0/",
        expected_error="Неверный формат IP-адреса/подсети",
        create_row=True,
    )

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_destnet_invalid_cidr_non_numeric_mask(authenticated_page: Page, credentials):
    """
    Проверяет, что '10.10.10.0/abc' невалидно (нечисловая маска).
    """
    page = authenticated_page
    validate_cell_input_error_negative(
        page,
        header_text="Сеть/адрес назначения",
        value_to_fill="10.10.10.0/abc",
        expected_error="Неверный формат IP-адреса/подсети",
        create_row=True,
    )

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_destnet_invalid_cidr_negative_mask(authenticated_page: Page, credentials):
    """
    Проверяет, что '10.10.10.0/-1' невалидно (маска < 0).
    """
    page = authenticated_page
    validate_cell_input_error_negative(
        page,
        header_text="Сеть/адрес назначения",
        value_to_fill="10.10.10.0/-1",
        expected_error="Неверный формат IP-адреса/подсети",
        create_row=True,
    )

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_destnet_invalid_cidr_over_32(authenticated_page: Page, credentials):
    """
    Проверяет, что '10.10.10.0/33' невалидно (маска > 32).
    """
    page = authenticated_page
    validate_cell_input_error_negative(
        page,
        header_text="Сеть/адрес назначения",
        value_to_fill="10.10.10.0/33",
        expected_error="Неверный формат IP-адреса/подсети",
        create_row=True,
    )


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_destnet_invalid_range_end_less_than_start(authenticated_page: Page, credentials):
    """
    Проверяет, что диапазон '10.0.0.10-10.0.0.1' невалиден (конец < начала).
    """
    page = authenticated_page
    validate_cell_input_error_negative(
        page,
        header_text="Сеть/адрес назначения",
        value_to_fill="10.0.0.10-10.0.0.1",
        expected_error="Неверный формат IP-адреса/подсети",
        create_row=True,
    )

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_destnet_invalid_range_bad_end(authenticated_page: Page, credentials):
    """
    Проверяет, что диапазон с невалидной конечной границей '10.0.0.1-10.0.0.256' невалиден.
    """
    page = authenticated_page
    validate_cell_input_error_negative(
        page,
        header_text="Сеть/адрес назначения",
        value_to_fill="10.0.0.1-10.0.0.256",
        expected_error="Неверный формат IP-адреса/подсети",
        create_row=True,
    )

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_destnet_invalid_range_half_open_start(authenticated_page: Page, credentials):
    """
    Проверяет, что ' -10.0.0.5' (полудиапазон без начала) невалиден.
    """
    page = authenticated_page
    validate_cell_input_error_negative(
        page,
        header_text="Сеть/адрес назначения",
        value_to_fill="-10.0.0.5",
        expected_error="Неверный формат IP-адреса/подсети",
        create_row=True,
    )

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_destnet_invalid_range_half_open_end(authenticated_page: Page, credentials):
    """
    Проверяет, что '10.0.0.1-' (полудиапазон без конца) невалиден.
    """
    page = authenticated_page
    validate_cell_input_error_negative(
        page,
        header_text="Сеть/адрес назначения",
        value_to_fill="10.0.0.1-",
        expected_error="Неверный формат IP-адреса/подсети",
        create_row=True,
    )


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_destnet_invalid_with_port_not_allowed(authenticated_page: Page, credentials):
    """
    Проверяет, что '10.0.0.1:80' невалидно, когда порт не разрешён (withPort по умолчанию False).
    """
    page = authenticated_page
    validate_cell_input_error_negative(
        page,
        header_text="Сеть/адрес назначения",
        value_to_fill="10.0.0.1:80",
        expected_error="Неверный формат IP-адреса/подсети",
        create_row=True,
    )

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_destnet_invalid_port_zero(authenticated_page: Page, credentials):
    """
    Проверяет, что '10.0.0.1:0' невалидно (порт вне 1–65535).
    """
    page = authenticated_page
    validate_cell_input_error_negative(
        page,
        header_text="Сеть/адрес назначения",
        value_to_fill="10.0.0.1:0",
        expected_error="Неверный формат IP-адреса/подсети",
        create_row=True,
    )

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_destnet_invalid_port_over_65535(authenticated_page: Page, credentials):
    """
    Проверяет, что '10.0.0.1:70000' невалидно (порт вне 1–65535).
    """
    page = authenticated_page
    validate_cell_input_error_negative(
        page,
        header_text="Сеть/адрес назначения",
        value_to_fill="10.0.0.1:70000",
        expected_error="Неверный формат IP-адреса/подсети",
        create_row=True,
    )


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_destnet_invalid_wildcard_one_star(authenticated_page: Page, credentials):
    """
    Проверяет, что '10.10.10.*' невалидно (wildcard не разрешён).
    """
    page = authenticated_page
    validate_cell_input_error_negative(
        page,
        header_text="Сеть/адрес назначения",
        value_to_fill="10.10.10.*",
        expected_error="Неверный формат IP-адреса/подсети",
        create_row=True,
    )

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_destnet_invalid_wildcard_two_stars(authenticated_page: Page, credentials):
    """
    Проверяет, что '10.10.*.*' невалидно (wildcard не разрешён).
    """
    page = authenticated_page
    validate_cell_input_error_negative(
        page,
        header_text="Сеть/адрес назначения",
        value_to_fill="10.10.*.*",
        expected_error="Неверный формат IP-адреса/подсети",
        create_row=True,
    )


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_destnet_multi_with_one_invalid(authenticated_page: Page, credentials):
    """
    Проверяет, что список '10.10.10.10, 1' невалиден, если хотя бы одно значение неверно.
    """
    page = authenticated_page
    validate_cell_input_error_negative(
        page,
        header_text="Сеть/адрес назначения",
        value_to_fill="10.10.10.10, 1",
        expected_error="Неверный формат IP-адреса/подсети",
        create_row=True,
    )


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_destnet_multi_duplicates(authenticated_page: Page, credentials):
    """
    Проверяет, что дубли '10.10.10.1, 10.10.10.1' невалидны при uniq=true.
    """
    page = authenticated_page
    validate_cell_input_error_negative(
        page,
        header_text="Сеть/адрес назначения",
        value_to_fill="10.10.10.1, 10.10.10.1",
        expected_error="Значения должны быть уникальными",
        create_row=True,
    )


'''
 -------------------------Позитивные тест-кейсы-----------------------------
'''
 
 
@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_destnet_valid_single_ip(authenticated_page: Page, credentials):
    """
    Проверяет, что одиночный IPv4 '10.0.0.1' в поле "Сеть/адрес назначения"
    валиден (ошибка не отображается).
    """
    page = authenticated_page
    validate_cell_input_error_positive(
        page,
        header_text="Сеть/адрес назначения",
        value_to_fill="10.0.0.1",
        create_row=True,
        blur_action="tab",
    )


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_destnet_valid_cidr_host_mask(authenticated_page: Page, credentials):
    """
    Проверяет, что IPv4 с маской '10.0.0.1/24' в поле "Сеть/адрес назначения"
    валиден (ошибка не отображается).
    Важно: используем адрес-хост с маской, а не сетевой адрес.
    """
    page = authenticated_page
    validate_cell_input_error_positive(
        page,
        header_text="Сеть/адрес назначения",
        value_to_fill="10.0.0.1/24",
        create_row=True,
        blur_action="tab",
    )


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_destnet_valid_cidr_32(authenticated_page: Page, credentials):
    """
    Проверяет, что IPv4 CIDR /32 '192.168.1.10/32' валиден
    (корректный формат хоста с маской /32).
    """
    page = authenticated_page
    validate_cell_input_error_positive(
        page,
        header_text="Сеть/адрес назначения",
        value_to_fill="192.168.1.10/32",
        create_row=True,
        blur_action="tab",
    )


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_destnet_valid_range(authenticated_page: Page, credentials):
    """
    Проверяет, что диапазон адресов '10.0.0.1-10.0.0.5' валиден
    (начало <= конец, оба конца корректные IPv4).
    """
    page = authenticated_page
    validate_cell_input_error_positive(
        page,
        header_text="Сеть/адрес назначения",
        value_to_fill="10.0.0.1-10.0.0.5",
        create_row=True,
        blur_action="tab",
    )


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_destnet_valid_multiple_values(authenticated_page: Page, credentials):
    """
    Проверяет, что список корректных значений '10.0.0.1, 10.0.0.2' валиден
    (значения корректные и уникальные).
    """
    page = authenticated_page
    validate_cell_input_error_positive(
        page,
        header_text="Сеть/адрес назначения",
        value_to_fill="10.0.0.1, 10.0.0.2",
        create_row=True,
        blur_action="tab",
    )


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_destnet_valid_trim_spaces(authenticated_page: Page, credentials):
    """
    Проверяет, что значение с ведущими/замыкающими пробелами ' 10.0.0.1 '
    корректно принимается и не вызывает ошибку.
    """
    page = authenticated_page
    validate_cell_input_error_positive(
        page,
        header_text="Сеть/адрес назначения",
        value_to_fill=" 10.0.0.1 ",
        create_row=True,
        blur_action="tab",
    )


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_destnet_valid_edge_zeros(authenticated_page: Page, credentials):
    """
    Проверяет граничный адрес '0.0.0.0' — валиден как одиночный IPv4.
    """
    page = authenticated_page
    validate_cell_input_error_positive(
        page,
        header_text="Сеть/адрес назначения",
        value_to_fill="0.0.0.0",
        create_row=True,
        blur_action="tab",
    )


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_destnet_valid_edge_broadcast(authenticated_page: Page, credentials):
    """
    Проверяет граничный адрес '255.255.255.255' — валиден как одиночный IPv4.
    """
    page = authenticated_page
    validate_cell_input_error_positive(
        page,
        header_text="Сеть/адрес назначения",
        value_to_fill="255.255.255.255",
        create_row=True,
        blur_action="tab",
    )


# (Опционально) полезный сквозной сценарий: ошибка исчезает после исправления.
@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_destnet_error_disappears_after_fix(authenticated_page: Page, credentials):
    """
    Проверяет, что после ввода невалидного значения и последующего исправления на валидное
    ошибка исчезает (в финале — ошибки нет).
    """
    page = authenticated_page

    # 1) Провоцируем ошибку
    validate_cell_input_error_negative(
        page,
        header_text="Сеть/адрес назначения",
        value_to_fill="10.10.10.256",  # невалидный октет
        expected_error="Неверный формат IP-адреса/подсети",
        create_row=True,
        blur_action="tab",
    )

    # 2) Исправляем на валидное значение
    validate_cell_input_error_positive(
        page,
        header_text="Сеть/адрес назначения",
        value_to_fill="10.10.10.1",
        create_row=True,
        blur_action="tab",
    )


'''
 -------------------------Проверки валидации поля "Порт получателя"-----------------------------
 -------------------------Негативные тест-кейсы-----------------------------
'''


PORT_ERR = [
    "Введите число от 0 до 65535",
    "Значения должны быть уникальными"
]

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_dstport_invalid_negative_single(authenticated_page: Page, credentials):
    """
    Проверяет, что отрицательное значение '-1' в поле 'Порт получателя' невалидно.
    """
    validate_cell_input_error_negative(
        authenticated_page,
        header_text="Порт получателя",
        value_to_fill="-1",
        expected_error=PORT_ERR,
        create_row=True,
    )


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_dstport_invalid_over_max_single(authenticated_page: Page, credentials):
    """
    Проверяет, что значение больше 65535 '70000' невалидно.
    """
    validate_cell_input_error_negative(
        authenticated_page,
        header_text="Порт получателя",
        value_to_fill="70000",
        expected_error=PORT_ERR,
        create_row=True,
    )


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_dstport_invalid_float(authenticated_page: Page, credentials):
    """
    Проверяет, что дробное значение '80.5' невалидно.
    """
    validate_cell_input_error_negative(
        authenticated_page,
        header_text="Порт получателя",
        value_to_fill="80.5",
        expected_error=PORT_ERR,
        create_row=True,
    )


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_dstport_invalid_text(authenticated_page: Page, credentials):
    """
    Проверяет, что текст 'eighty' невалиден.
    """
    validate_cell_input_error_negative(
        authenticated_page,
        header_text="Порт получателя",
        value_to_fill="eighty",
        expected_error=PORT_ERR,
        create_row=True,
    )


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_dstport_invalid_mixed_text_number(authenticated_page: Page, credentials):
    """
    Проверяет, что смешанное значение '80a' невалидно.
    """
    validate_cell_input_error_negative(
        authenticated_page,
        header_text="Порт получателя",
        value_to_fill="80a",
        expected_error=PORT_ERR,
        create_row=True,
    )


# ---- некорректные списки через запятую

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_dstport_invalid_list_with_text_item(authenticated_page: Page, credentials):
    """
    Проверяет, что '80,abc,443' (нечисловой элемент) невалидно.
    """
    validate_cell_input_error_negative(
        authenticated_page,
        header_text="Порт получателя",
        value_to_fill="80,abc,443",
        expected_error=PORT_ERR,
        create_row=True,
    )


# ---- диапазоны

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_dstport_invalid_range_reversed(authenticated_page: Page, credentials):
    """
    Проверяет, что диапазон с концом меньше начала '100-90' невалиден.
    """
    validate_cell_input_error_negative(
        authenticated_page,
        header_text="Порт получателя",
        value_to_fill="100-90",
        expected_error=PORT_ERR,
        create_row=True,
    )


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_dstport_invalid_range_open_end(authenticated_page: Page, credentials):
    """
    Проверяет, что '80-' (нет правой границы) невалидно.
    """
    validate_cell_input_error_negative(
        authenticated_page,
        header_text="Порт получателя",
        value_to_fill="80-",
        expected_error=PORT_ERR,
        create_row=True,
    )


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_dstport_invalid_range_open_start(authenticated_page: Page, credentials):
    """
    Проверяет, что '-90' (нет левой границы) невалидно.
    """
    validate_cell_input_error_negative(
        authenticated_page,
        header_text="Порт получателя",
        value_to_fill="-90",
        expected_error=PORT_ERR,
        create_row=True,
    )


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_dstport_invalid_range_with_text(authenticated_page: Page, credentials):
    """
    Проверяет, что '10-abc' (нечисловая правая граница) невалидно.
    """
    validate_cell_input_error_negative(
        authenticated_page,
        header_text="Порт получателя",
        value_to_fill="10-abc",
        expected_error=PORT_ERR,
        create_row=True,
    )


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_dstport_invalid_range_over_max(authenticated_page: Page, credentials):
    """
    Проверяет, что диапазон с границей >65535 '65000-70000' невалиден.
    """
    validate_cell_input_error_negative(
        authenticated_page,
        header_text="Порт получателя",
        value_to_fill="65000-70000",
        expected_error=PORT_ERR,
        create_row=True,
    )


# ---- комбинации списков и диапазонов с ошибками

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_dstport_invalid_combo_contains_bad_item(authenticated_page: Page, credentials):
    """
    Проверяет, что комбинация '22, 80-90, x' невалидна (есть нечисловой элемент).
    """
    validate_cell_input_error_negative(
        authenticated_page,
        header_text="Порт получателя",
        value_to_fill="22, 80-90, x",
        expected_error=PORT_ERR,
        create_row=True,
    )


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_dstport_invalid_combo_range_reversed(authenticated_page: Page, credentials):
    """
    Проверяет, что комбинация '22, 90-80, 443' невалидна (обратный диапазон).
    """
    validate_cell_input_error_negative(
        authenticated_page,
        header_text="Порт получателя",
        value_to_fill="22, 90-80, 443",
        expected_error=PORT_ERR,
        create_row=True,
    )


# ---- прочее

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_dstport_invalid_symbols(authenticated_page: Page, credentials):
    """
    Проверяет, что посторонние символы '80#' невалидны.
    """
    validate_cell_input_error_negative(
        authenticated_page,
        header_text="Порт получателя",
        value_to_fill="80#",
        expected_error=PORT_ERR,
        create_row=True,
    )


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_dstport_invalid_duplicates(authenticated_page: Page, credentials):
    """
    Проверяет, что повторяющиеся значения портов '80, 80, 443'
    невалидны и отображается ошибка "Значения должны быть уникальными".
    """
    page = authenticated_page
    validate_cell_input_error_negative(
        page,
        header_text="Порт получателя",
        value_to_fill="80, 80, 443",
        expected_error=PORT_ERR,
        create_row=True,
        blur_action="tab",
    )


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_dstport_invalid_range_degenerate(authenticated_page: Page, credentials):
    """
    Проверяет, что вырожденный диапазон '443-443' невалиден.
    """
    validate_cell_input_error_negative(
        authenticated_page,
        header_text="Порт получателя",
        value_to_fill="443-443",
        expected_error=PORT_ERR,
        create_row=True,
        blur_action="tab"
    )


# -------------------------Позитивные тест-кейсы-----------------------------


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_dstport_valid_single_min(authenticated_page: Page, credentials):
    """
    Проверяет, что одиночное значение '0' валидно.
    """
    validate_cell_input_error_positive(
        authenticated_page,
        header_text="Порт получателя",
        value_to_fill="0",
        create_row=True,
    )


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_dstport_valid_single_common(authenticated_page: Page, credentials):
    """
    Проверяет, что одиночное значение '80' валидно.
    """
    validate_cell_input_error_positive(
        authenticated_page,
        header_text="Порт получателя",
        value_to_fill="80",
        create_row=True,
    )


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_dstport_valid_single_max(authenticated_page: Page, credentials):
    """
    Проверяет, что одиночное значение '65535' валидно.
    """
    validate_cell_input_error_positive(
        authenticated_page,
        header_text="Порт получателя",
        value_to_fill="65535",
        create_row=True,
    )


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_dstport_valid_list_basic(authenticated_page: Page, credentials):
    """
    Проверяет, что список портов '22,80,443' валиден.
    """
    validate_cell_input_error_positive(
        authenticated_page,
        header_text="Порт получателя",
        value_to_fill="22,80,443",
        create_row=True,
    )


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_dstport_valid_list_with_spaces(authenticated_page: Page, credentials):
    """
    Проверяет, что список портов с пробелами '22, 80, 443' валиден.
    """
    validate_cell_input_error_positive(
        authenticated_page,
        header_text="Порт получателя",
        value_to_fill="22, 80, 443",
        create_row=True,
    )


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_dstport_valid_range_middle(authenticated_page: Page, credentials):
    """
    Проверяет, что диапазон '1000-2000' валиден.
    """
    validate_cell_input_error_positive(
        authenticated_page,
        header_text="Порт получателя",
        value_to_fill="1000-2000",
        create_row=True,
    )


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_dstport_valid_range_full_bounds(authenticated_page: Page, credentials):
    """
    Проверяет, что диапазон граничных значений '0-65535' валиден.
    """
    validate_cell_input_error_positive(
        authenticated_page,
        header_text="Порт получателя",
        value_to_fill="0-65535",
        create_row=True,
    )


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_dstport_valid_mixed_list_and_range(authenticated_page: Page, credentials):
    """
    Проверяет, что комбинация списка и диапазона '22,80-90,443' валидна.
    """
    validate_cell_input_error_positive(
        authenticated_page,
        header_text="Порт получателя",
        value_to_fill="22,80-90,443",
        create_row=True,
    )


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_dstport_valid_multiple_ranges(authenticated_page: Page, credentials):
    """
    Проверяет, что несколько диапазонов '20-21,80-81,443-445' валидны.
    """
    validate_cell_input_error_positive(
        authenticated_page,
        header_text="Порт получателя",
        value_to_fill="20-21,80-81,443-445",
        create_row=True,
    )


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_dstport_valid_long_list(authenticated_page: Page, credentials):
    """
    Проверяет, что длинный список '1,2,3,4,5' валиден.
    """
    validate_cell_input_error_positive(
        authenticated_page,
        header_text="Порт получателя",
        value_to_fill="1,2,3,4,5",
        create_row=True,
    )


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_dstport_valid_list_with_bounds(authenticated_page: Page, credentials):
    """
    Проверяет, что список с граничными значениями '0,65535' валиден.
    """
    validate_cell_input_error_positive(
        authenticated_page,
        header_text="Порт получателя",
        value_to_fill="0,65535",
        create_row=True,
    )


'''-------------------------Проверки валидации поля "Коментарий"-----------------------------'''


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_comment_valid(authenticated_page: Page, credentials):
    """
    Проверяет, что отсутствует валидация у поля "Комментарий"
    """
    validate_cell_input_error_positive(
        authenticated_page,
        header_text="Комментарий",
        value_to_fill="комментарийcomment123#",
        create_row=True
    )


'''-------------------------Проверки смены тоггла "Статус"-----------------------------'''


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_switch_toggle_on(authenticated_page: Page, credentials):
    """
    Проверяет, что тоггл в колонке "Статус" успешно меняет состояние (вкл/выкл).
    """
    page = authenticated_page

    toggle_cell_switch_state(
        page,
        header_text="Статус",
        create_row=True,
    )


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_save_triggers_request(authenticated_page: Page, credentials):
    """
    Проверяет, что нажатие на кнопку 'Сохранить' в форм-строке отправляет запрос
    на указанный endpoint ожидаемым методом и с ожидаемым кодом ответа.
    """
    page = authenticated_page

    click_form_row_save_and_wait(
        page,
        endpoint_part="/api/service/remote/ngfw/core/call/whiteLists",
        method="POST",
        expected_status=200,
        timeout=15000,
    )


'''-------------------------Проверки отображения добавленной строки и её редактирование-----------------------------'''


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_row_visible_after_refresh(authenticated_page: Page, credentials):
    """
    Проверяет, что после обновления страницы отображается ранее сохранённая строка
    и значения в указанных колонках совпадают с ожидаемыми.
    """
    page = authenticated_page

    # --- Значения, ожидаемые в строке после сохранения ---
    expectations = {
        "Действие": "allow",
        "Тип": "MPLS-IN-IP (137)",
        "Сеть/адрес-источника": "10.0.0.1-10.0.0.3,10.0.0.10",
        "Сеть/адрес назначения": "10.10.10.1",
        "Порт получателя": "0,65535",
        "Вес": "119999",
        "Статус": "Активно",
        "Комментарий": "комментарийcomment123#",
    }

    # Шаг №1. Обновляем страницу и ждём загрузки таблицы
    page.reload(wait_until="networkidle")

    # Шаг №2. Проверяем, что строка с нужными данными присутствует
    find_row_by_columns(page, expectations, match_mode="exact")


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_edit_row_opens_form(authenticated_page: Page, credentials):
    """
    Проверяет, что по клику на «Изменить» строка с указанным значением в колонке «Комментарий» переходит в режим редактирования.

    Предусловие:
      Строка с комментарием target_value уже существует (создана ранее).
    """
    page = authenticated_page

    # --- Настройки теста ---
    target_column = "Комментарий"
    target_value = "комментарийcomment123#"

    form_row = click_row_edit_and_wait_editable(
        page,
        header_text=target_column,
        expected_value=target_value,
    )


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_weight_2(authenticated_page: Page, credentials):
    """
    Проверяет, что при вводе корректного значения в поле "Вес"
    не отображается ошибка валидации.
    """
    page = authenticated_page

    # Вводим корректное значение (например, "100")
    validate_cell_input_error_positive(
        page,
        header_text="Вес",
        value_to_fill="111111",
        create_row=True
    )


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_action_select_choose_drop_2(authenticated_page: Page, credentials):
    """
    Проверяет, что в колонке "Действие" можно выбрать 'drop' и выбранное корректно отображается.
    """
    page = authenticated_page
    select_option_in_cell_and_verify(
        page,
        header_text="Действие",
        option_to_select="drop",
        create_row=True,
    )


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_type_select_choose_ip_2(authenticated_page: Page, credentials):
    """
    Проверяет, что в колонке "Тип" можно выбрать 'IP (0)'.
    """
    page = authenticated_page
    select_option_in_cell_and_verify(
        page,
        header_text="Тип",
        option_to_select="IP (0)",
        create_row=True
    )


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_srcnet_valid_single_ip_2(authenticated_page: Page, credentials):
    """
    Проверяет, что одиночный IPv4 '100.100.100.100' в поле "Сеть/адрес-источника"
    валиден (ошибка не отображается).
    """
    page = authenticated_page
    validate_cell_input_error_positive(
        page,
        header_text="Сеть/адрес-источника",
        value_to_fill="100.100.100.100",
        create_row=True,
        blur_action="tab",
    )


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_dstnet_valid_single_ip_2(authenticated_page: Page, credentials):
    """
    Проверяет, что одиночный IPv4 '200.200.200.200' в поле "Сеть/адрес назначения"
    валиден (ошибка не отображается).
    """
    page = authenticated_page
    validate_cell_input_error_positive(
        page,
        header_text="Сеть/адрес назначения",
        value_to_fill="200.200.200.200",
        create_row=True,
        blur_action="tab",
    )


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_dstport_valid_single_2(authenticated_page: Page, credentials):
    """
    Проверяет, что одиночное значение '0' валидно.
    """
    validate_cell_input_error_positive(
        authenticated_page,
        header_text="Порт получателя",
        value_to_fill="333",
        create_row=True,
    )


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_switch_toggle_off(authenticated_page: Page, credentials):
    """
    Проверяет, что тоггл в колонке "Статус" успешно меняет состояние (вкл/выкл).
    """
    page = authenticated_page

    toggle_cell_switch_state(
        page,
        header_text="Статус",
        create_row=True,
    )


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_comment_valid_2(authenticated_page: Page, credentials):
    """
    Проверяет, что отсутствует валидация у поля "Комментарий"
    """
    validate_cell_input_error_positive(
        authenticated_page,
        header_text="Комментарий",
        value_to_fill="test_comment",
        create_row=True
    )


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_save_triggers_request_2(authenticated_page: Page, credentials):
    """
    Проверяет, что нажатие на кнопку 'Сохранить' в форм-строке отправляет запрос
    на указанный endpoint ожидаемым методом и с ожидаемым кодом ответа.
    """
    page = authenticated_page

    click_form_row_save_and_wait(
        page,
        endpoint_part="/api/service/remote/ngfw/core/call",
        method="PATCH",
        expected_status=200,
        timeout=15000,
    )


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_row_visible_after_refresh_2(authenticated_page: Page, credentials):
    """
    Проверяет, что после обновления страницы отображается ранее сохранённая строка
    и значения в указанных колонках совпадают с ожидаемыми.
    """
    page = authenticated_page

    # --- Значения, ожидаемые в строке после сохранения ---
    expectations = {
        "Действие": "drop",
        "Тип": "IP (0)",
        "Сеть/адрес-источника": "100.100.100.100",
        "Сеть/адрес назначения": "200.200.200.200",
        "Порт получателя": "333",
        "Вес": "111111",
        "Статус": "Не активно",
        "Комментарий": "test_comment",
    }

    # Шаг №1. Обновляем страницу и ждём загрузки таблицы
    page.reload(wait_until="networkidle")

    # Шаг №2. Проверяем, что строка с нужными данными присутствует
    find_row_by_columns(page, expectations, match_mode="exact")


'''-------------------------Проверки удаления добавленной строки и её редактирование-----------------------------'''


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_delete_row_and_wait_request(authenticated_page: Page, credentials):
    """
    Проверяет, что нажатие на кнопку 'Удалить' и подтверждение в модалке отправляет запрос
    на указанный endpoint ожидаемым методом и с ожидаемым кодом ответа.
    """
    page = authenticated_page

    # --- Настройки теста ---
    target_column = "Комментарий"
    target_value = "test_comment"
    endpoint_part = "/api/service/remote/ngfw/core/call/"
    method = "DELETE"
    expected_status=200
    timeout=15000

    click_row_delete_and_wait(
        page,
        header_text=target_column,
        expected_value=target_value,
        endpoint_part=endpoint_part,
        method=method,
        expected_status=expected_status,
        timeout=timeout
    )


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_white_rules_row_no_visible_after_refresh_2(authenticated_page: Page, credentials):
    """
    Проверяет, что после обновления страницы не отображается удаленная строка
    """
    page = authenticated_page

    # --- Значения удаленной строки ---
    expectations = {
        "Действие": "drop",
        "Тип": "IP (0)",
        "Сеть/адрес-источника": "100.100.100.100",
        "Сеть/адрес назначения": "200.200.200.200",
        "Порт получателя": "333",
        "Вес": "111111",
        "Статус": "Не активно",
        "Комментарий": "test_comment",
    }

    # Шаг №1. Обновляем страницу и ждём загрузки таблицы
    page.reload(wait_until="networkidle")

    # Шаг №2. Проверяем, что строка с нужными данными отсутствует
    assert_no_row_by_columns(page, expectations, match_mode="exact")