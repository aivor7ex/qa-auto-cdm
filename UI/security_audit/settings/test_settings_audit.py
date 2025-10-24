import pytest
from playwright.sync_api import expect, Page, Browser
from UI.other_tests.test_autentification_admin import _perform_login
import json
from UI.conftest import fail_with_screenshot
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
def test_page_settings_audit_navigate_and_check_url(authenticated_page: Page, credentials):
    """
    Проверяет переход на вкладку "Настройки Аудита" в разделе "Аудит безопасности" и корректность URL для "Системный отчет".
    """
    tab_button_1 = "Аудит безопасности"
    tab_button_2 = "Настройки Аудита"
    url = "security-audit/settings"
    navigate_and_check_url(authenticated_page, tab_button_1, tab_button_2, url, credentials)


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_settings_audit_input_label_and_enabled(authenticated_page: Page, credentials):
    """
    Проверяет, что у поля ввода "Объем хранения журналов (ГБ)" отображается заголовок
    и само поле доступно для ввода, а также что значение можно ввести.
    """
    page = authenticated_page

    # Используем универсальную функцию для поиска input по лейблу
    input_field = find_input_by_label(page, "Объем хранения журналов (ГБ)")

    # Проверяем наличие label
    label = page.locator('.cdm-input-text-wrapper label', has_text="Объем хранения журналов (ГБ)")
    label.wait_for(state='visible', timeout=3000)
    if not label.is_visible():
        fail_with_screenshot("Label 'Объем хранения журналов (ГБ)' не отображается", page)

    # Проверяем, что input доступен для ввода
    input_field.wait_for(state='visible', timeout=3000)
    if not input_field.is_visible():
        fail_with_screenshot("Input для 'Объем хранения журналов (ГБ)' не отображается", page)
    if not input_field.is_enabled():
        fail_with_screenshot("Input для 'Объем хранения журналов (ГБ)' недоступен для ввода", page)

    # Проверяем, что можно ввести значение
    test_value = "5"
    input_field.fill(test_value)
    if input_field.input_value() != test_value:
        fail_with_screenshot(f"Input не принимает значение '{test_value}'", page)


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_audit_log_level_slider_present(authenticated_page: Page, credentials):
    """
    Проверяет наличие слайдера 'Уровень логирования событий' и его элементов.
    """
    page = authenticated_page

    # Проверяем наличие обёртки слайдера
    slider_wrapper = page.locator('.cdm-slider')
    if not slider_wrapper.is_visible():
        fail_with_screenshot("Слайдер 'Уровень логирования событий' не отображается", page)

    # Проверяем наличие label
    label = slider_wrapper.locator('label', has_text="Уровень логирования событий")
    if not label.is_visible():
        fail_with_screenshot("Label 'Уровень логирования событий' не отображается", page)

    # Проверяем наличие самого слайдера
    slider = slider_wrapper.locator('.MuiSlider-root')
    if not slider.is_visible():
        fail_with_screenshot("Элемент MuiSlider-root не отображается", page)

    # Проверяем наличие всех трёх меток
    for mark_text in ["Ошибка", "Предупреждение", "Информация"]:
        mark = slider.locator('.MuiSlider-markLabel', has_text=mark_text)
        if not mark.is_visible():
            fail_with_screenshot(f"Метка '{mark_text}' не отображается на слайдере", page)

    # Проверяем наличие ползунка (thumb)
    thumb = slider.locator('.MuiSlider-thumb')
    if not thumb.is_visible():
        fail_with_screenshot("Ползунок (thumb) слайдера не отображается", page)


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_audit_save_button_visible_and_clickable(authenticated_page: Page, credentials):
    """
    Проверяет, что кнопка 'Сохранить' видна и кликабельна.
    """
    page = authenticated_page
    save_button = page.locator('button.cdm-button:has-text("Сохранить")')
    if not save_button.is_visible():
        fail_with_screenshot("Кнопка 'Сохранить' не отображается", page)
    if not save_button.is_enabled():
        fail_with_screenshot("Кнопка 'Сохранить' неактивна (нельзя кликнуть)", page)


"""---------------------Проверка валидации поля 'Объем хранения журналов (ГБ)'-------------------------- """
"""---------------------Позитивные тесты---------------------------------------------------------------- """

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_settings_audit_input_validation_0001(authenticated_page: Page, credentials):
    """
    Проверяет, что при вводе '0.001' в поле 'Объем хранения журналов (ГБ)' не появляется ошибка валидации.
    """
    page = authenticated_page
    input_field = find_input_by_label(page, "Объем хранения журналов (ГБ)", value="0.001")
    time.sleep(0.3)
    if input_field.get_attribute("aria-invalid") == "true":
        fail_with_screenshot("Input 'Объем хранения журналов (ГБ)' в ошибочном состоянии при вводе '0.001'", page)
    error_text = page.locator('.cdm-input-text-wrapper:has(label:has-text("Объем хранения журналов (ГБ)")) .MuiFormHelperText-root.Mui-error')
    if error_text.is_visible():
        fail_with_screenshot("Ошибка валидации отображается при вводе '0.001': " + error_text.inner_text(), page)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_settings_audit_input_validation_1(authenticated_page: Page, credentials):
    """
    Проверяет, что при вводе '1' в поле 'Объем хранения журналов (ГБ)' не появляется ошибка валидации.
    """
    page = authenticated_page
    input_field = find_input_by_label(page, "Объем хранения журналов (ГБ)", value="1")
    time.sleep(0.3)
    if input_field.get_attribute("aria-invalid") == "true":
        fail_with_screenshot("Input 'Объем хранения журналов (ГБ)' в ошибочном состоянии при вводе '1'", page)
    error_text = page.locator('.cdm-input-text-wrapper:has(label:has-text("Объем хранения журналов (ГБ)")) .MuiFormHelperText-root.Mui-error')
    if error_text.is_visible():
        fail_with_screenshot("Ошибка валидации отображается при вводе '1': " + error_text.inner_text(), page)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_settings_audit_input_validation_10(authenticated_page: Page, credentials):
    """
    Проверяет, что при вводе '10' в поле 'Объем хранения журналов (ГБ)' не появляется ошибка валидации.
    """
    page = authenticated_page
    input_field = find_input_by_label(page, "Объем хранения журналов (ГБ)", value="10")
    time.sleep(0.3)
    if input_field.get_attribute("aria-invalid") == "true":
        fail_with_screenshot("Input 'Объем хранения журналов (ГБ)' в ошибочном состоянии при вводе '10'", page)
    error_text = page.locator('.cdm-input-text-wrapper:has(label:has-text("Объем хранения журналов (ГБ)")) .MuiFormHelperText-root.Mui-error')
    if error_text.is_visible():
        fail_with_screenshot("Ошибка валидации отображается при вводе '10': " + error_text.inner_text(), page)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_settings_audit_input_validation_100_5(authenticated_page: Page, credentials):
    """
    Проверяет, что при вводе '100.5' в поле 'Объем хранения журналов (ГБ)' не появляется ошибка валидации.
    """
    page = authenticated_page
    input_field = find_input_by_label(page, "Объем хранения журналов (ГБ)", value="100.5")
    time.sleep(0.3)
    if input_field.get_attribute("aria-invalid") == "true":
        fail_with_screenshot("Input 'Объем хранения журналов (ГБ)' в ошибочном состоянии при вводе '100.5'", page)
    error_text = page.locator('.cdm-input-text-wrapper:has(label:has-text("Объем хранения журналов (ГБ)")) .MuiFormHelperText-root.Mui-error')
    if error_text.is_visible():
        fail_with_screenshot("Ошибка валидации отображается при вводе '100.5': " + error_text.inner_text(), page)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_settings_audit_input_validation_99999(authenticated_page: Page, credentials):
    """
    Проверяет, что при вводе '99999' в поле 'Объем хранения журналов (ГБ)' не появляется ошибка валидации.
    """
    page = authenticated_page
    input_field = find_input_by_label(page, "Объем хранения журналов (ГБ)", value="99999")
    time.sleep(0.3)
    if input_field.get_attribute("aria-invalid") == "true":
        fail_with_screenshot("Input 'Объем хранения журналов (ГБ)' в ошибочном состоянии при вводе '99999'", page)
    error_text = page.locator('.cdm-input-text-wrapper:has(label:has-text("Объем хранения журналов (ГБ)")) .MuiFormHelperText-root.Mui-error')
    if error_text.is_visible():
        fail_with_screenshot("Ошибка валидации отображается при вводе '99999': " + error_text.inner_text(), page)

"""---------------------Негативные тесты с типом данных------------------------------------------------ """

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_settings_audit_input_validation_letters(authenticated_page: Page, credentials):
    """
    Проверяет, что при вводе только букв в поле 'Объем хранения журналов (ГБ)' появляется ошибка валидации, и кнопка 'Сохранить' неактивна.
    """
    page = authenticated_page
    value = "abcde"
    input_field = find_input_by_label(page, "Объем хранения журналов (ГБ)", value=value)
    save_button = page.locator('button.cdm-button:has-text("Сохранить")')
    # Проверяем, что кнопка неактивна
    if save_button.get_attribute("disabled") is None:
        fail_with_screenshot("Кнопка 'Сохранить' должна быть неактивна при невалидном вводе", page)
    time.sleep(0.3)
    # Проверяем ошибку валидации
    if input_field.get_attribute("aria-invalid") != "true":
        fail_with_screenshot(f"Input не в ошибочном состоянии при вводе '{value}'", page)
    error_text = page.locator('.cdm-input-text-wrapper:has(label:has-text("Объем хранения журналов (ГБ)")) .MuiFormHelperText-root.Mui-error')
    if not error_text.is_visible():
        fail_with_screenshot(f"Ошибка валидации не отображается при вводе '{value}'", page)
    # Проверяем отсутствие модального окна
    modal = page.locator('.MuiDialog-paper[role="dialog"]')
    if modal.is_visible():
        fail_with_screenshot("Появилось модальное окно подтверждения при невалидном вводе!", page)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_settings_audit_input_validation_special_chars(authenticated_page: Page, credentials):
    """
    Проверяет, что при вводе только спецсимволов в поле 'Объем хранения журналов (ГБ)' появляется ошибка валидации.
    """
    page = authenticated_page
    value = "!@#$%^&*()_+"
    input_field = find_input_by_label(page, "Объем хранения журналов (ГБ)", value=value)
    save_button = page.locator('button.cdm-button:has-text("Сохранить")')
    # Проверяем, что кнопка неактивна
    if save_button.get_attribute("disabled") is None:
        fail_with_screenshot("Кнопка 'Сохранить' должна быть неактивна при невалидном вводе", page)
    time.sleep(0.3)
    # Проверяем ошибку валидации
    if input_field.get_attribute("aria-invalid") != "true":
        fail_with_screenshot(f"Input не в ошибочном состоянии при вводе '{value}'", page)
    error_text = page.locator('.cdm-input-text-wrapper:has(label:has-text("Объем хранения журналов (ГБ)")) .MuiFormHelperText-root.Mui-error')
    if not error_text.is_visible():
        fail_with_screenshot(f"Ошибка валидации не отображается при вводе '{value}'", page)
    # Проверяем отсутствие модального окна
    modal = page.locator('.MuiDialog-paper[role="dialog"]')
    if modal.is_visible():
        fail_with_screenshot("Появилось модальное окно подтверждения при невалидном вводе!", page)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_settings_audit_input_validation_letters_digits(authenticated_page: Page, credentials):
    """
    Проверяет, что при вводе букв+цифр в поле 'Объем хранения журналов (ГБ)' появляется ошибка валидации.
    """
    page = authenticated_page
    value = "abc123"
    input_field = find_input_by_label(page, "Объем хранения журналов (ГБ)", value=value)
    save_button = page.locator('button.cdm-button:has-text("Сохранить")')
    # Проверяем, что кнопка неактивна
    if save_button.get_attribute("disabled") is None:
        fail_with_screenshot("Кнопка 'Сохранить' должна быть неактивна при невалидном вводе", page)
    time.sleep(0.3)
    # Проверяем ошибку валидации
    if input_field.get_attribute("aria-invalid") != "true":
        fail_with_screenshot(f"Input не в ошибочном состоянии при вводе '{value}'", page)
    error_text = page.locator('.cdm-input-text-wrapper:has(label:has-text("Объем хранения журналов (ГБ)")) .MuiFormHelperText-root.Mui-error')
    if not error_text.is_visible():
        fail_with_screenshot(f"Ошибка валидации не отображается при вводе '{value}'", page)
    # Проверяем отсутствие модального окна
    modal = page.locator('.MuiDialog-paper[role="dialog"]')
    if modal.is_visible():
        fail_with_screenshot("Появилось модальное окно подтверждения при невалидном вводе!", page)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_settings_audit_input_validation_letters_digits_special(authenticated_page: Page, credentials):
    """
    Проверяет, что при вводе букв+цифр+спецсимволов в поле 'Объем хранения журналов (ГБ)' появляется ошибка валидации.
    """
    page = authenticated_page
    value = "abc123!@#"
    input_field = find_input_by_label(page, "Объем хранения журналов (ГБ)", value=value)
    save_button = page.locator('button.cdm-button:has-text("Сохранить")')
    # Проверяем, что кнопка неактивна
    if save_button.get_attribute("disabled") is None:
        fail_with_screenshot("Кнопка 'Сохранить' должна быть неактивна при невалидном вводе", page)
    time.sleep(0.3)
    # Проверяем ошибку валидации
    if input_field.get_attribute("aria-invalid") != "true":
        fail_with_screenshot(f"Input не в ошибочном состоянии при вводе '{value}'", page)
    error_text = page.locator('.cdm-input-text-wrapper:has(label:has-text("Объем хранения журналов (ГБ)")) .MuiFormHelperText-root.Mui-error')
    if not error_text.is_visible():
        fail_with_screenshot(f"Ошибка валидации не отображается при вводе '{value}'", page)
    # Проверяем отсутствие модального окна
    modal = page.locator('.MuiDialog-paper[role="dialog"]')
    if modal.is_visible():
        fail_with_screenshot("Появилось модальное окно подтверждения при невалидном вводе!", page)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_settings_audit_input_validation_special_letters(authenticated_page: Page, credentials):
    """
    Проверяет, что при вводе спецсимволов+букв в поле 'Объем хранения журналов (ГБ)' появляется ошибка валидации.
    """
    page = authenticated_page
    value = "!@#abc"
    input_field = find_input_by_label(page, "Объем хранения журналов (ГБ)", value=value)
    save_button = page.locator('button.cdm-button:has-text("Сохранить")')
    # Проверяем, что кнопка неактивна
    if save_button.get_attribute("disabled") is None:
        fail_with_screenshot("Кнопка 'Сохранить' должна быть неактивна при невалидном вводе", page)
    time.sleep(0.3)
    # Проверяем ошибку валидации
    if input_field.get_attribute("aria-invalid") != "true":
        fail_with_screenshot(f"Input не в ошибочном состоянии при вводе '{value}'", page)
    error_text = page.locator('.cdm-input-text-wrapper:has(label:has-text("Объем хранения журналов (ГБ)")) .MuiFormHelperText-root.Mui-error')
    if not error_text.is_visible():
        fail_with_screenshot(f"Ошибка валидации не отображается при вводе '{value}'", page)
    # Проверяем отсутствие модального окна
    modal = page.locator('.MuiDialog-paper[role="dialog"]')
    if modal.is_visible():
        fail_with_screenshot("Появилось модальное окно подтверждения при невалидном вводе!", page)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_settings_audit_input_validation_special_digits(authenticated_page: Page, credentials):
    """
    Проверяет, что при вводе спецсимволов+цифр в поле 'Объем хранения журналов (ГБ)' появляется ошибка валидации.
    """
    page = authenticated_page
    value = "!@#123"
    input_field = find_input_by_label(page, "Объем хранения журналов (ГБ)", value=value)
    save_button = page.locator('button.cdm-button:has-text("Сохранить")')
    # Проверяем, что кнопка неактивна
    if save_button.get_attribute("disabled") is None:
        fail_with_screenshot("Кнопка 'Сохранить' должна быть неактивна при невалидном вводе", page)
    time.sleep(0.3)
    # Проверяем ошибку валидации
    if input_field.get_attribute("aria-invalid") != "true":
        fail_with_screenshot(f"Input не в ошибочном состоянии при вводе '{value}'", page)
    error_text = page.locator('.cdm-input-text-wrapper:has(label:has-text("Объем хранения журналов (ГБ)")) .MuiFormHelperText-root.Mui-error')
    if not error_text.is_visible():
        fail_with_screenshot(f"Ошибка валидации не отображается при вводе '{value}'", page)
    # Проверяем отсутствие модального окна
    modal = page.locator('.MuiDialog-paper[role="dialog"]')
    if modal.is_visible():
        fail_with_screenshot("Появилось модальное окно подтверждения при невалидном вводе!", page)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_settings_audit_input_validation_spaces(authenticated_page: Page, credentials):
    """
    Проверяет, что при вводе только пробелов поле невалидно.
    """
    page = authenticated_page
    value = "   "
    input_field = find_input_by_label(page, "Объем хранения журналов (ГБ)", value=value)
    save_button = page.locator('button.cdm-button:has-text("Сохранить")')
    # Проверяем, что кнопка неактивна
    if save_button.get_attribute("disabled") is None:
        fail_with_screenshot("Кнопка 'Сохранить' должна быть неактивна при невалидном вводе", page)
    time.sleep(0.3)
    # Проверяем ошибку валидации
    if input_field.get_attribute("aria-invalid") != "true":
        fail_with_screenshot(f"Input не в ошибочном состоянии при вводе только пробелов", page)
    error_text = page.locator('.cdm-input-text-wrapper:has(label:has-text("Объем хранения журналов (ГБ)")) .MuiFormHelperText-root.Mui-error')
    if not error_text.is_visible():
        fail_with_screenshot(f"Ошибка валидации не отображается при вводе только пробелов", page)
    # Проверяем отсутствие модального окна
    modal = page.locator('.MuiDialog-paper[role="dialog"]')
    if modal.is_visible():
        fail_with_screenshot("Появилось модальное окно подтверждения при невалидном вводе!", page)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_settings_audit_input_validation_dot(authenticated_page: Page, credentials):
    """
    Проверяет, что при вводе только точки поле невалидно.
    """
    page = authenticated_page
    value = "."
    input_field = find_input_by_label(page, "Объем хранения журналов (ГБ)", value=value)
    save_button = page.locator('button.cdm-button:has-text("Сохранить")')
    # Проверяем, что кнопка неактивна
    if save_button.get_attribute("disabled") is None:
        fail_with_screenshot("Кнопка 'Сохранить' должна быть неактивна при невалидном вводе", page)
    time.sleep(0.3)
    # Проверяем ошибку валидации
    if input_field.get_attribute("aria-invalid") != "true":
        fail_with_screenshot(f"Input не в ошибочном состоянии при вводе '.'", page)
    error_text = page.locator('.cdm-input-text-wrapper:has(label:has-text("Объем хранения журналов (ГБ)")) .MuiFormHelperText-root.Mui-error')
    if not error_text.is_visible():
        fail_with_screenshot(f"Ошибка валидации не отображается при вводе '.'", page)
    # Проверяем отсутствие модального окна
    modal = page.locator('.MuiDialog-paper[role="dialog"]')
    if modal.is_visible():
        fail_with_screenshot("Появилось модальное окно подтверждения при невалидном вводе!", page)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_settings_audit_input_validation_comma(authenticated_page: Page, credentials):
    """
    Проверяет, что при вводе только запятой поле невалидно.
    """
    page = authenticated_page
    value = ","
    input_field = find_input_by_label(page, "Объем хранения журналов (ГБ)", value=value)
    save_button = page.locator('button.cdm-button:has-text("Сохранить")')
    # Проверяем, что кнопка неактивна
    if save_button.get_attribute("disabled") is None:
        fail_with_screenshot("Кнопка 'Сохранить' должна быть неактивна при невалидном вводе", page)
    time.sleep(0.3)
    # Проверяем ошибку валидации
    if input_field.get_attribute("aria-invalid") != "true":
        fail_with_screenshot(f"Input не в ошибочном состоянии при вводе ','", page)
    error_text = page.locator('.cdm-input-text-wrapper:has(label:has-text("Объем хранения журналов (ГБ)")) .MuiFormHelperText-root.Mui-error')
    if not error_text.is_visible():
        fail_with_screenshot(f"Ошибка валидации не отображается при вводе ','", page)
    # Проверяем отсутствие модального окна
    modal = page.locator('.MuiDialog-paper[role="dialog"]')
    if modal.is_visible():
        fail_with_screenshot("Появилось модальное окно подтверждения при невалидном вводе!", page)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_settings_audit_input_validation_multiple_dots(authenticated_page: Page, credentials):
    """
    Проверяет, что при вводе нескольких точек поле невалидно.
    """
    page = authenticated_page
    value = "1..2"
    input_field = find_input_by_label(page, "Объем хранения журналов (ГБ)", value=value)
    save_button = page.locator('button.cdm-button:has-text("Сохранить")')
    # Проверяем, что кнопка неактивна
    if save_button.get_attribute("disabled") is None:
        fail_with_screenshot("Кнопка 'Сохранить' должна быть неактивна при невалидном вводе", page)
    time.sleep(0.3)
    # Проверяем ошибку валидации
    if input_field.get_attribute("aria-invalid") != "true":
        fail_with_screenshot(f"Input не в ошибочном состоянии при вводе '1..2'", page)
    error_text = page.locator('.cdm-input-text-wrapper:has(label:has-text("Объем хранения журналов (ГБ)")) .MuiFormHelperText-root.Mui-error')
    if not error_text.is_visible():
        fail_with_screenshot(f"Ошибка валидации не отображается при вводе '1..2'", page)
    # Проверяем отсутствие модального окна
    modal = page.locator('.MuiDialog-paper[role="dialog"]')
    if modal.is_visible():
        fail_with_screenshot("Появилось модальное окно подтверждения при невалидном вводе!", page)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_settings_audit_input_validation_multiple_commas(authenticated_page: Page, credentials):
    """
    Проверяет, что при вводе нескольких запятых поле невалидно.
    """
    page = authenticated_page
    value = "1,,2"
    input_field = find_input_by_label(page, "Объем хранения журналов (ГБ)", value=value)
    save_button = page.locator('button.cdm-button:has-text("Сохранить")')
    # Проверяем, что кнопка неактивна
    if save_button.get_attribute("disabled") is None:
        fail_with_screenshot("Кнопка 'Сохранить' должна быть неактивна при невалидном вводе", page)
    time.sleep(0.3)
    # Проверяем ошибку валидации
    if input_field.get_attribute("aria-invalid") != "true":
        fail_with_screenshot(f"Input не в ошибочном состоянии при вводе '1,,2'", page)
    error_text = page.locator('.cdm-input-text-wrapper:has(label:has-text("Объем хранения журналов (ГБ)")) .MuiFormHelperText-root.Mui-error')
    if not error_text.is_visible():
        fail_with_screenshot(f"Ошибка валидации не отображается при вводе '1,,2'", page)
    # Проверяем отсутствие модального окна
    modal = page.locator('.MuiDialog-paper[role="dialog"]')
    if modal.is_visible():
        fail_with_screenshot("Появилось модальное окно подтверждения при невалидном вводе!", page)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_settings_audit_input_validation_space_inside(authenticated_page: Page, credentials):
    """
    Проверяет, что при вводе значения с пробелом внутри поле невалидно.
    """
    page = authenticated_page
    value = "10 10"
    input_field = find_input_by_label(page, "Объем хранения журналов (ГБ)", value=value)
    save_button = page.locator('button.cdm-button:has-text("Сохранить")')
    # Проверяем, что кнопка неактивна
    if save_button.get_attribute("disabled") is None:
        fail_with_screenshot("Кнопка 'Сохранить' должна быть неактивна при невалидном вводе", page)
    time.sleep(0.3)
    # Проверяем ошибку валидации
    if input_field.get_attribute("aria-invalid") != "true":
        fail_with_screenshot(f"Input не в ошибочном состоянии при вводе '10 10'", page)
    error_text = page.locator('.cdm-input-text-wrapper:has(label:has-text("Объем хранения журналов (ГБ)")) .MuiFormHelperText-root.Mui-error')
    if not error_text.is_visible():
        fail_with_screenshot(f"Ошибка валидации не отображается при вводе '10 10'", page)
    # Проверяем отсутствие модального окна
    modal = page.locator('.MuiDialog-paper[role="dialog"]')
    if modal.is_visible():
        fail_with_screenshot("Появилось модальное окно подтверждения при невалидном вводе!", page)


"""---------------------Негативные тесты с граничными значениями------------------------------------------------ """

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_settings_audit_input_validation_zero(authenticated_page: Page, credentials):
    """
    Проверяет, что при вводе '0' поле невалидно.
    """
    page = authenticated_page
    value = "0"
    input_field = find_input_by_label(page, "Объем хранения журналов (ГБ)", value=value)
    save_button = page.locator('button.cdm-button:has-text("Сохранить")')
    # Проверяем, что кнопка неактивна
    if save_button.get_attribute("disabled") is None:
        fail_with_screenshot("Кнопка 'Сохранить' должна быть неактивна при невалидном вводе", page)
    time.sleep(0.3)
    # Проверяем ошибку валидации
    if input_field.get_attribute("aria-invalid") != "true":
        fail_with_screenshot("Input не в ошибочном состоянии при вводе '0'", page)
    error_text = page.locator('.cdm-input-text-wrapper:has(label:has-text("Объем хранения журналов (ГБ)")) .MuiFormHelperText-root.Mui-error')
    if not error_text.is_visible():
        fail_with_screenshot("Ошибка валидации не отображается при вводе '0'", page)
    # Проверяем отсутствие модального окна
    modal = page.locator('.MuiDialog-paper[role="dialog"]')
    if modal.is_visible():
        fail_with_screenshot("Появилось модальное окно подтверждения при невалидном вводе!", page)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_settings_audit_input_validation_less_than_min(authenticated_page: Page, credentials):
    """
    Проверяет, что при вводе значения меньше 0.001 поле невалидно.
    """
    page = authenticated_page
    value = "0.0009"
    input_field = find_input_by_label(page, "Объем хранения журналов (ГБ)", value=value)
    save_button = page.locator('button.cdm-button:has-text("Сохранить")')
    # Проверяем, что кнопка неактивна
    if save_button.get_attribute("disabled") is None:
        fail_with_screenshot("Кнопка 'Сохранить' должна быть неактивна при невалидном вводе", page)
    time.sleep(0.3)
    # Проверяем ошибку валидации
    if input_field.get_attribute("aria-invalid") != "true":
        fail_with_screenshot("Input не в ошибочном состоянии при вводе '0.0009'", page)
    error_text = page.locator('.cdm-input-text-wrapper:has(label:has-text("Объем хранения журналов (ГБ)")) .MuiFormHelperText-root.Mui-error')
    if not error_text.is_visible():
        fail_with_screenshot("Ошибка валидации не отображается при вводе '0.0009'", page)
    # Проверяем отсутствие модального окна
    modal = page.locator('.MuiDialog-paper[role="dialog"]')
    if modal.is_visible():
        fail_with_screenshot("Появилось модальное окно подтверждения при невалидном вводе!", page)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_settings_audit_input_validation_min_minus_epsilon(authenticated_page: Page, credentials):
    """
    Проверяет, что при вводе значения чуть меньше 0.001 поле невалидно.
    """
    page = authenticated_page
    value = "0.00099"
    input_field = find_input_by_label(page, "Объем хранения журналов (ГБ)", value=value)
    save_button = page.locator('button.cdm-button:has-text("Сохранить")')
    # Проверяем, что кнопка неактивна
    if save_button.get_attribute("disabled") is None:
        fail_with_screenshot("Кнопка 'Сохранить' должна быть неактивна при невалидном вводе", page)
    time.sleep(0.3)
    # Проверяем ошибку валидации
    if input_field.get_attribute("aria-invalid") != "true":
        fail_with_screenshot("Input не в ошибочном состоянии при вводе '0.00099'", page)
    error_text = page.locator('.cdm-input-text-wrapper:has(label:has-text("Объем хранения журналов (ГБ)")) .MuiFormHelperText-root.Mui-error')
    if not error_text.is_visible():
        fail_with_screenshot("Ошибка валидации не отображается при вводе '0.00099'", page)
    # Проверяем отсутствие модального окна
    modal = page.locator('.MuiDialog-paper[role="dialog"]')
    if modal.is_visible():
        fail_with_screenshot("Появилось модальное окно подтверждения при невалидном вводе!", page)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_settings_audit_input_validation_negative(authenticated_page: Page, credentials):
    """
    Проверяет, что при вводе отрицательного числа поле невалидно.
    """
    page = authenticated_page
    value = "-1"
    input_field = find_input_by_label(page, "Объем хранения журналов (ГБ)", value=value)
    save_button = page.locator('button.cdm-button:has-text("Сохранить")')
    # Проверяем, что кнопка неактивна
    if save_button.get_attribute("disabled") is None:
        fail_with_screenshot("Кнопка 'Сохранить' должна быть неактивна при невалидном вводе", page)
    time.sleep(0.3)
    # Проверяем ошибку валидации
    if input_field.get_attribute("aria-invalid") != "true":
        fail_with_screenshot("Input не в ошибочном состоянии при вводе '-1'", page)
    error_text = page.locator('.cdm-input-text-wrapper:has(label:has-text("Объем хранения журналов (ГБ)")) .MuiFormHelperText-root.Mui-error')
    if not error_text.is_visible():
        fail_with_screenshot("Ошибка валидации не отображается при вводе '-1'", page)
    # Проверяем отсутствие модального окна
    modal = page.locator('.MuiDialog-paper[role="dialog"]')
    if modal.is_visible():
        fail_with_screenshot("Появилось модальное окно подтверждения при невалидном вводе!", page)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_settings_audit_input_validation_empty(authenticated_page: Page, credentials):
    """
    Проверяет, что при пустом поле появляется ошибка валидации.
    """
    page = authenticated_page
    value = ""
    input_field = find_input_by_label(page, "Объем хранения журналов (ГБ)", value=value)
    save_button = page.locator('button.cdm-button:has-text("Сохранить")')
    # Проверяем, что кнопка неактивна
    if save_button.get_attribute("disabled") is None:
        fail_with_screenshot("Кнопка 'Сохранить' должна быть неактивна при невалидном вводе", page)
    time.sleep(0.3)
    # Проверяем ошибку валидации
    if input_field.get_attribute("aria-invalid") != "true":
        fail_with_screenshot("Input не в ошибочном состоянии при пустом поле", page)
    error_text = page.locator('.cdm-input-text-wrapper:has(label:has-text("Объем хранения журналов (ГБ)")) .MuiFormHelperText-root.Mui-error')
    if not error_text.is_visible():
        fail_with_screenshot("Ошибка валидации не отображается при пустом поле", page)
    # Проверяем отсутствие модального окна
    modal = page.locator('.MuiDialog-paper[role="dialog"]')
    if modal.is_visible():
        fail_with_screenshot("Появилось модальное окно подтверждения при невалидном вводе!", page)


"""---------------------Проверки закрытия модального окна------------------------------------------------ """


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_modal_close_by_cancel(authenticated_page: Page, credentials):
    """
    Проверяет, что модальное окно закрывается по нажатию на кнопку 'Отмена'.
    """
    page = authenticated_page
    # Шаг №1: Вводим валидное значение, чтобы вызвать модалку
    input_field = find_input_by_label(page, "Объем хранения журналов (ГБ)", value="321")
    # Шаг №2: Кликаем по кнопке 'Сохранить'
    save_button = page.locator('button.cdm-button:has-text("Сохранить")')
    save_button.click()
    # Шаг №3: Ждём появления модального окна
    modal = page.locator('.MuiDialog-paper[role="dialog"]')
    if not modal.is_visible():
        fail_with_screenshot("Модальное окно не появилось после клика на 'Сохранить'", page)
    # Шаг №4: Нажимаем кнопку 'Отмена'
    cancel_button = modal.locator('button:has-text("Отмена")')
    cancel_button.click()
    time.sleep(0.3)
    # Шаг №5: Проверяем, что модальное окно закрылось
    if modal.is_visible():
        fail_with_screenshot("Модальное окно не закрылось после нажатия 'Отмена'", page)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_modal_close_by_cross(authenticated_page: Page, credentials):
    """
    Проверяет, что модальное окно закрывается по нажатию на крестик.
    """
    page = authenticated_page
    # Шаг №1: Вводим валидное значение, чтобы вызвать модалку
    input_field = find_input_by_label(page, "Объем хранения журналов (ГБ)", value="321")
    # Шаг №2: Кликаем по кнопке 'Сохранить'
    save_button = page.locator('button.cdm-button:has-text("Сохранить")')
    save_button.click()
    # Шаг №3: Ждём появления модального окна
    modal = page.locator('.MuiDialog-paper[role="dialog"]')
    if not modal.is_visible():
        fail_with_screenshot("Модальное окно не появилось после клика на 'Сохранить'", page)
    # Шаг №4: Нажимаем на крестик (иконка с title="Закрыть")
    cross_button = modal.locator('button[tabindex="0"] .cdm-icon-wrapper[title="Закрыть"]')
    if not cross_button.is_visible():
        fail_with_screenshot("Крестик для закрытия модального окна не найден", page)
    cross_button.click()
    time.sleep(0.3)
    # Шаг №5: Проверяем, что модальное окно закрылось
    if modal.is_visible():
        fail_with_screenshot("Модальное окно не закрылось после нажатия на крестик", page)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_modal_close_by_click_outside(authenticated_page: Page, credentials):
    """
    Проверяет, что модальное окно закрывается по клику вне окна (по фону).
    """
    page = authenticated_page
    # Шаг №1: Вводим валидное значение, чтобы вызвать модалку
    input_field = find_input_by_label(page, "Объем хранения журналов (ГБ)", value="321")
    # Шаг №2: Кликаем по кнопке 'Сохранить'
    save_button = page.locator('button.cdm-button:has-text("Сохранить")')
    save_button.click()
    # Шаг №3: Ждём появления модального окна
    modal = page.locator('.MuiDialog-paper[role="dialog"]')
    if not modal.is_visible():
        fail_with_screenshot("Модальное окно не появилось после клика на 'Сохранить'", page)
    # Шаг №4: Кликаем вне модального окна (по координатам 1/4 ширины и высоты)
    size = page.viewport_size or page.context.viewport_size
    if size:
        x = size['width'] // 4
        y = size['height'] // 4
        page.mouse.click(x, y)
        time.sleep(0.3)
        # Шаг №5: Проверяем, что модальное окно закрылось
        if modal.is_visible():
            fail_with_screenshot("Модальное окно не закрылось после клика по фону", page)
    else:
        fail_with_screenshot("Не удалось получить размер экрана для клика по фону", page)


"""---------------------Проверки сохранения значения------------------------------------------------ """


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_settings_audit_save_value_45_and_slider_error(authenticated_page: Page, credentials):
    """
    Вводит в поле 'Объем хранения журналов (ГБ)' значение '45', 
    перетаскивает слайдер на 'Ошибка', нажимает 'Сохранить', 
    подтверждает модалку и проверяет успешный POST-запрос.
    """
    page = authenticated_page

    # Шаг №1: Вводим значение "45" в поле
    input_field = find_input_by_label(page, "Объем хранения журналов (ГБ)", value="45")

    # Шаг №2: Перетаскиваем слайдер на "Ошибка"
    slider = page.locator('.cdm-slider .MuiSlider-root')
    error_mark = slider.locator('.MuiSlider-markLabel', has_text="Ошибка")
    if not error_mark.is_visible():
        fail_with_screenshot("Метка 'Ошибка' на слайдере не найдена", page)
    error_mark.click()
    time.sleep(0.3)

    # Шаг №3: Ждём POST-запрос через универсальную функцию
    with wait_for_api_response_with_response(
        page,
        "/api/service/environment/logger-analytics/logstash",
        expected_status=200,
        method="POST",
        timeout=10000
    ) as resp_info:
        # Шаг №4: Нажимаем кнопку "Сохранить"
        save_button = page.locator('button.cdm-button:has-text("Сохранить")')
        save_button.click()
        # Шаг №5: Если появляется модалка, подтверждаем "Да"
        modal = page.locator('.MuiDialog-paper[role="dialog"]')
        if modal.is_visible():
            yes_button = modal.locator('button:has-text("Да")')
            if not yes_button.is_visible():
                fail_with_screenshot("Кнопка 'Да' в модальном окне не найдена", page)
            yes_button.click()
    time.sleep(1)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_settings_audit_reload_and_check_values_45_and_slider_error(authenticated_page: Page, credentials):
    """
    После обновления страницы ждет GET-запрос к logstash, проверяет код ответа и значения в ответе,
    а также что в поле input отображается 45 и слайдер установлен в состояние 'Ошибка'.
    """
    page = authenticated_page

    # Шаг №1: Начинаем слушать GET-запрос
    with wait_for_api_response_with_response(
        page,
        "/api/service/environment/logger-analytics/logstash",
        expected_status=200,
        method="GET",
        timeout=10000
    ) as resp_info:
        # Шаг №2: Обновляем страницу
        page.reload()

    # Шаг №3: Проверяем ответ
    response = resp_info.value
    if response.status not in [200, 304]:
        fail_with_screenshot(f"GET-запрос к logstash вернул статус {response.status}, ожидался 200 или 304", page)
    data = response.json()
    if data.get("LOGS_STORE_SIZE_BYTES") != "45000000000":
        fail_with_screenshot(f"LOGS_STORE_SIZE_BYTES={data.get('LOGS_STORE_SIZE_BYTES')}, ожидалось '45000000000'", page)
    if data.get("SECURITY_AUDIT_LOG_LEVEL") != "1":
        fail_with_screenshot(f"SECURITY_AUDIT_LOG_LEVEL={data.get('SECURITY_AUDIT_LOG_LEVEL')}, ожидалось '1'", page)

    # Шаг №4: Проверяем, что в поле input отображается 45
    input_field = find_input_by_label(page, "Объем хранения журналов (ГБ)")
    if input_field.input_value() != "45":
        fail_with_screenshot(f"В поле 'Объем хранения журналов (ГБ)' отображается '{input_field.input_value()}', ожидалось '45'", page)

    # Шаг №5: Проверяем, что слайдер установлен в состояние 'Ошибка'
    slider = page.locator('.cdm-slider .MuiSlider-root')
    thumb = slider.locator('.MuiSlider-thumb')
    if not thumb.is_visible():
        fail_with_screenshot("Ползунок слайдера не найден", page)
    try:
        thumb.wait_for(state="visible", timeout=3000)
        page.wait_for_timeout(200)
        page.locator('.cdm-slider .MuiSlider-thumb[aria-valuenow="0"]').wait_for(state="visible", timeout=3000)
    except Exception:
        value_now = thumb.get_attribute("aria-valuenow")
        fail_with_screenshot(f"Слайдер не в состоянии 'Ошибка' (aria-valuenow={value_now})", page)
    time.sleep(1)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_settings_audit_save_value_30_and_slider_warn(authenticated_page: Page, credentials):
    """
    Вводит в поле 'Объем хранения журналов (ГБ)' значение '30', 
    перетаскивает слайдер на 'Предупреждение', нажимает 'Сохранить', 
    подтверждает модалку и проверяет успешный POST-запрос.
    """
    page = authenticated_page

    # Шаг №1: Вводим значение "30" в поле
    input_field = find_input_by_label(page, "Объем хранения журналов (ГБ)", value="30")

    # Шаг №2: Перетаскиваем слайдер на "Предупреждение"
    slider = page.locator('.cdm-slider .MuiSlider-root')
    warn_mark = slider.locator('.MuiSlider-markLabel', has_text="Предупреждение")
    if not warn_mark.is_visible():
        fail_with_screenshot("Метка 'Предупреждение' на слайдере не найдена", page)
    warn_mark.click()
    time.sleep(0.3)

    # Шаг №3: Ждём POST-запрос через универсальную функцию
    with wait_for_api_response_with_response(
        page,
        "/api/service/environment/logger-analytics/logstash",
        expected_status=200,
        method="POST",
        timeout=10000
    ) as resp_info:
        # Шаг №4: Нажимаем кнопку "Сохранить"
        save_button = page.locator('button.cdm-button:has-text("Сохранить")')
        save_button.click()
        # Шаг №5: Если появляется модалка, подтверждаем "Да"
        modal = page.locator('.MuiDialog-paper[role="dialog"]')
        if modal.is_visible():
            yes_button = modal.locator('button:has-text("Да")')
            if not yes_button.is_visible():
                fail_with_screenshot("Кнопка 'Да' в модальном окне не найдена", page)
            yes_button.click()
    time.sleep(1)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_settings_audit_reload_and_check_values_30_and_slider_warn(authenticated_page: Page, credentials):
    """
    После обновления страницы ждет GET-запрос к logstash, проверяет код ответа и значения в ответе,
    а также что в поле input отображается 30 и слайдер установлен в состояние 'Предупреждение'.
    """
    page = authenticated_page

    # Шаг №1: Начинаем слушать GET-запрос
    with wait_for_api_response_with_response(
        page,
        "/api/service/environment/logger-analytics/logstash",
        expected_status=200,
        method="GET",
        timeout=10000
    ) as resp_info:
        # Шаг №2: Обновляем страницу
        page.reload()

    # Шаг №3: Проверяем ответ
    response = resp_info.value
    if response.status not in [200, 304]:
        fail_with_screenshot(f"GET-запрос к logstash вернул статус {response.status}, ожидался 200 или 304", page)
    data = response.json()
    if data.get("LOGS_STORE_SIZE_BYTES") != "30000000000":
        fail_with_screenshot(f"LOGS_STORE_SIZE_BYTES={data.get('LOGS_STORE_SIZE_BYTES')}, ожидалось '30000000000'", page)
    if data.get("SECURITY_AUDIT_LOG_LEVEL") != "2":
        fail_with_screenshot(f"SECURITY_AUDIT_LOG_LEVEL={data.get('SECURITY_AUDIT_LOG_LEVEL')}, ожидалось '2'", page)

    # Шаг №4: Проверяем, что в поле input отображается 30
    input_field = find_input_by_label(page, "Объем хранения журналов (ГБ)")
    if input_field.input_value() != "30":
        fail_with_screenshot(f"В поле 'Объем хранения журналов (ГБ)' отображается '{input_field.input_value()}', ожидалось '30'", page)

    # Шаг №5: Проверяем, что слайдер установлен в состояние 'Предупреждение'
    slider = page.locator('.cdm-slider .MuiSlider-root')
    thumb = slider.locator('.MuiSlider-thumb')
    if not thumb.is_visible():
        fail_with_screenshot("Ползунок слайдера не найден", page)
    try:
        thumb.wait_for(state="visible", timeout=3000)
        page.wait_for_timeout(200)
        page.locator('.cdm-slider .MuiSlider-thumb[aria-valuenow="1"]').wait_for(state="visible", timeout=3000)
    except Exception:
        value_now = thumb.get_attribute("aria-valuenow")
        fail_with_screenshot(f"Слайдер не в состоянии 'Предупреждение' (aria-valuenow={value_now})", page)
    time.sleep(1)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_settings_audit_save_value_10_and_slider_info(authenticated_page: Page, credentials):
    """
    Вводит в поле 'Объем хранения журналов (ГБ)' значение '10', 
    перетаскивает слайдер на 'Информация', нажимает 'Сохранить', 
    подтверждает модалку и проверяет успешный POST-запрос.
    """
    page = authenticated_page

    # Шаг №1: Вводим значение "10" в поле
    input_field = find_input_by_label(page, "Объем хранения журналов (ГБ)", value="10")

    # Шаг №2: Перетаскиваем слайдер на "Информация"
    slider = page.locator('.cdm-slider .MuiSlider-root')
    info_mark = slider.locator('.MuiSlider-markLabel', has_text="Информация")
    if not info_mark.is_visible():
        fail_with_screenshot("Метка 'Информация' на слайдере не найдена", page)
    info_mark.click()
    time.sleep(0.3)

    # Шаг №3: Ждём POST-запрос через универсальную функцию
    with wait_for_api_response_with_response(
        page,
        "/api/service/environment/logger-analytics/logstash",
        expected_status=200,
        method="POST",
        timeout=10000
    ) as resp_info:
        # Шаг №4: Нажимаем кнопку "Сохранить"
        save_button = page.locator('button.cdm-button:has-text("Сохранить")')
        save_button.click()
        # Шаг №5: Если появляется модалка, подтверждаем "Да"
        modal = page.locator('.MuiDialog-paper[role="dialog"]')
        if modal.is_visible():
            yes_button = modal.locator('button:has-text("Да")')
            if not yes_button.is_visible():
                fail_with_screenshot("Кнопка 'Да' в модальном окне не найдена", page)
            yes_button.click()
    time.sleep(1)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_settings_audit_reload_and_check_values_10_and_slider_info(authenticated_page: Page, credentials):
    """
    После обновления страницы ждет GET-запрос к logstash, проверяет код ответа и значения в ответе,
    а также что в поле input отображается 10 и слайдер установлен в состояние 'Информация'.
    """
    page = authenticated_page

    # Шаг №1: Начинаем слушать GET-запрос
    with wait_for_api_response_with_response(
        page,
        "/api/service/environment/logger-analytics/logstash",
        expected_status=200,
        method="GET",
        timeout=10000
    ) as resp_info:
        # Шаг №2: Обновляем страницу
        page.reload()

    # Шаг №3: Проверяем ответ
    response = resp_info.value
    if response.status not in [200, 304]:
        fail_with_screenshot(f"GET-запрос к logstash вернул статус {response.status}, ожидался 200 или 304", page)
    data = response.json()
    if data.get("LOGS_STORE_SIZE_BYTES") != "10000000000":
        fail_with_screenshot(f"LOGS_STORE_SIZE_BYTES={data.get('LOGS_STORE_SIZE_BYTES')}, ожидалось '10000000000'", page)
    if data.get("SECURITY_AUDIT_LOG_LEVEL") != "3":
        fail_with_screenshot(f"SECURITY_AUDIT_LOG_LEVEL={data.get('SECURITY_AUDIT_LOG_LEVEL')}, ожидалось '1'", page)

    # Шаг №4: Проверяем, что в поле input отображается 10
    input_field = find_input_by_label(page, "Объем хранения журналов (ГБ)")
    if input_field.input_value() != "10":
        fail_with_screenshot(f"В поле 'Объем хранения журналов (ГБ)' отображается '{input_field.input_value()}', ожидалось '10'", page)

    # Шаг №5: Проверяем, что слайдер установлен в состояние 'Информация'
    slider = page.locator('.cdm-slider .MuiSlider-root')
    thumb = slider.locator('.MuiSlider-thumb')
    if not thumb.is_visible():
        fail_with_screenshot("Ползунок слайдера не найден", page)
    try:
        thumb.wait_for(state="visible", timeout=3000)
        page.wait_for_timeout(200)
        page.locator('.cdm-slider .MuiSlider-thumb[aria-valuenow="2"]').wait_for(state="visible", timeout=3000)
    except Exception:
        value_now = thumb.get_attribute("aria-valuenow")
        fail_with_screenshot(f"Слайдер не в состоянии 'Информация' (aria-valuenow={value_now})", page)
    time.sleep(1)