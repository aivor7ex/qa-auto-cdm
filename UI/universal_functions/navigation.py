from playwright.sync_api import Page, expect
from urllib.parse import urlparse
from UI.conftest import fail_with_screenshot


def navigate_and_check_url(page: Page, sidebar_btn1: str, sidebar_btn2: str, expected_path: str, credentials: dict):
    """
    Универсальная функция для перехода по сайдбару (2 кнопки) и проверки URL.
    :param page: Playwright Page
    :param sidebar_btn1: название первой кнопки в сайдбаре (например, "Аудит безопасности")
    :param sidebar_btn2: название второй кнопки в сайдбаре (например, "Отчетность")
    :param expected_path: ожидаемый путь после перехода (например, 'security-audit/reports/create')
    :param credentials: словарь с ключом 'ip' для формирования полного url
    """
    # Шаг №1: Ожидаем загрузки сайдбара
    sidebar = page.locator('.cdm-sidebar')
    if not sidebar.is_visible():
        fail_with_screenshot("Сайдбар не видим", page)
    # Шаг №2: Проверяем, видна ли вторая кнопка (подраздел)
    btn2 = page.locator('div[role="button"]', has_text=sidebar_btn2)
    if not btn2.is_visible():
        # Шаг №3: Кликаем по первой кнопке (раздел), если нужно раскрыть меню
        btn1 = page.locator('div[role="button"]', has_text=sidebar_btn1)
        if not btn1.is_visible():
            fail_with_screenshot(f"Кнопка '{sidebar_btn1}' не видна", page)
        btn1.click()
        page.wait_for_timeout(500)
    # Шаг №4: Кликаем по второй кнопке (подраздел)
    if not btn2.is_visible():
        fail_with_screenshot(f"Кнопка '{sidebar_btn2}' не видна", page)
    btn2.click()
    page.wait_for_timeout(300)
    # Шаг №5: Проверка полного URL
    expected_url = f"https://{credentials['ip']}/{expected_path}"
    if page.url != expected_url:
        fail_with_screenshot(f"URL не совпадает. Ожидался: {expected_url}, получен: {page.url}", page)


def navigate_and_check_url_with_tab(page: Page, sidebar_btn1: str, sidebar_btn2: str, tab_name: str, expected_path: str, credentials: dict):
    """
    Универсальная функция для перехода по сайдбару (2 кнопки), затем по вкладке, и проверки URL.
    :param page: Playwright Page
    :param sidebar_btn1: название первой кнопки в сайдбаре
    :param sidebar_btn2: название второй кнопки в сайдбаре
    :param tab_name: имя вкладки, по которой нужно кликнуть
    :param expected_path: ожидаемый путь после перехода
    :param credentials: словарь с ключом 'ip' для формирования полного url
    """
    # Шаг №1: Ожидаем загрузки сайдбара
    sidebar = page.locator('.cdm-sidebar')
    if not sidebar.is_visible():
        fail_with_screenshot("Сайдбар не видим", page)
    # Шаг №2: Проверяем, видна ли вторая кнопка (подраздел)
    btn2 = page.locator('div[role="button"]', has_text=sidebar_btn2)
    if not btn2.is_visible():
        # Шаг №3: Кликаем по первой кнопке (раздел), если нужно раскрыть меню
        btn1 = page.locator('div[role="button"]', has_text=sidebar_btn1)
        if not btn1.is_visible():
            fail_with_screenshot(f"Кнопка '{sidebar_btn1}' не видна", page)
        btn1.click()
        page.wait_for_timeout(500)
    # Шаг №4: Кликаем по второй кнопке (подраздел)
    if not btn2.is_visible():
        fail_with_screenshot(f"Кнопка '{sidebar_btn2}' не видна", page)
    btn2.click()
    page.wait_for_timeout(300)
    # Шаг №5: Клик по вкладке
    tab = page.get_by_role("tab", name=tab_name)
    if not tab.is_visible():
        fail_with_screenshot(f"Вкладка '{tab_name}' не видна", page)
    tab.click()
    page.wait_for_timeout(300)
    # Шаг №6: Проверка полного URL
    expected_url = f"https://{credentials['ip']}/{expected_path}"
    if page.url != expected_url:
        fail_with_screenshot(f"URL не совпадает. Ожидался: {expected_url}, получен: {page.url}", page)


def check_tabs_selected_state(page: Page, tab_names: list, active_tab: str, expected_path: str, credentials: dict):
    """
    Проверяет, что только нужная вкладка выбрана, остальные неактивны, и что url совпадает с ожидаемым (полный url).
    :param page: Playwright Page
    :param tab_names: список всех вкладок (например, ["Создание отчетов", "Архив отчетов", ...])
    :param active_tab: имя вкладки, которая должна быть выбрана
    :param expected_path: ожидаемый путь для выбранной вкладки (например, 'security-audit/reports/create')
    :param credentials: словарь с ключом 'ip' для формирования полного url
    """
    # Шаг №1: Проверяем состояние всех вкладок
    for tab_name in tab_names:
        tab = page.get_by_role("tab", name=tab_name)
        if not tab.is_visible():
            fail_with_screenshot(f"Вкладка '{tab_name}' не видна", page)
        if tab_name == active_tab:
            if tab.get_attribute("aria-selected") != "true":
                fail_with_screenshot(f"Вкладка '{tab_name}' должна быть выбрана", page)
        else:
            if tab.get_attribute("aria-selected") != "false":
                fail_with_screenshot(f"Вкладка '{tab_name}' не должна быть выбрана", page)
    # Шаг №2: Проверяем полный URL
    expected_url = f"https://{credentials['ip']}/{expected_path}"
    if page.url != expected_url:
        fail_with_screenshot(f"URL не совпадает. Ожидался: {expected_url}, получен: {page.url}", page)


def find_input_by_label(page, label_text, value=None, wrapper_class='cdm-input-text-wrapper'):
    """
    Универсальный поиск input или textarea по тексту лейбла внутри указанного класса-обёртки.
    Если value не None, сразу вызывает fill(value) только для первого редактируемого поля (без readonly). Если value=None — только возвращает локатор.

    :param page: Playwright Page
    :param label_text: Текст лейбла (например, 'Общее имя (Common name)')
    :param value: Текст, который нужно ввести в поле (или None, если только искать)
    :param wrapper_class: Класс-обёртка, внутри которой искать (по умолчанию 'cdm-input-text-wrapper')
    :return: Playwright Locator для input или textarea (только редактируемые)
    """
    # Шаг №1: Ищем div-обёртку по классу и лейблу
    wrapper = page.locator(f'.{wrapper_class}:has(label:has-text("{label_text}"))')
    # Шаг №2: Ищем input или textarea без readonly внутри найденной обёртки
    input_field = wrapper.locator('input:not([readonly]), textarea:not([readonly])')
    # Шаг №3: Если передано значение, вводим его только в первый найденный
    if value is not None:
        input_field.first.fill(value)
    return input_field 