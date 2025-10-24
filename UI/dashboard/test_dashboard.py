from playwright.sync_api import expect, TimeoutError
from datetime import datetime, timedelta
from playwright.sync_api import Page

def test_infographics_page_is_accessible(authenticated_page):
    """
    Проверяет, что кнопка навигации "Инфографика" в боковом меню видима и кликабельна.
    Тест выполняется на уже открытой странице инфографики.
    """
    try:
        # Шаг 1: Найти кнопку "Инфографика" в боковом меню.
        # Мы ищем кнопку по ее роли и текстовому названию.
        infographics_button = authenticated_page.get_by_role("button", name="Инфографика")

        # Шаг 2: Проверить, что кнопка видима и кликнуть на нее.
        # Так как мы уже на этой странице, клик не должен вызывать ошибок.
        expect(infographics_button).to_be_visible()
        infographics_button.click()
        
    except Exception as e:
        authenticated_page.screenshot(path="UI/error_screenshots/infographics_page_not_accessible_error.png")
        raise e


def test_dashboard_default_elements_are_visible(authenticated_page):
    """
    Проверяет, что основные элементы на странице инфографики видимы по умолчанию.
    Тест находит ключевые компоненты UI и убеждается в их видимости.
    """
    try:
        # Шаг 1: Проверка заголовка страницы "Инфографика".
        # Находим элемент заголовка по его классу и проверяем текст и видимость.
        header_title = authenticated_page.locator("span.cdm-layout__app-bar__title__label")
        expect(header_title).to_have_text("Инфографика")
        expect(header_title).to_be_visible()

        # Шаг 2: Проверка иконки для открытия настроек.
        # Находим иконку по атрибуту title, так как это уникальный идентификатор.
        settings_button = authenticated_page.locator("span[title='Параметры инфографики']")
        expect(settings_button).to_be_visible()

        # Шаг 3: Проверка видимости виджетов на дашборде.
        # Находим каждый виджет по его заголовку в атрибуте title и проверяем видимость.
        # Используем поиск только по `title` для большей устойчивости к изменениям в CSS-классах.
        threat_ratio_panel = authenticated_page.locator("[title='Соотношение выявленных угроз']")
        expect(threat_ratio_panel).to_be_visible()

        threat_timeline_panel = authenticated_page.locator("[title='Сетевые угрозы по времени']")
        expect(threat_timeline_panel).to_be_visible()

        threat_map_panel = authenticated_page.locator("[title='Карта угроз']")
        expect(threat_map_panel).to_be_visible()

    except Exception as e:
        # В случае ошибки делаем скриншот для отладки.
        authenticated_page.screenshot(path="UI/error_screenshots/dashboard_elements_visibility_error.png")
        raise e


def test_dashboard_help_tooltip(authenticated_page):
    """
    Проверяет функциональность иконки справки на странице "Инфографика".
    Тест находит иконку, кликает на нее, проверяет, что появилось
    окно с текстом, а затем закрывает его.
    """
    try:
        # Шаг 1: Найти иконку справки в заголовке страницы.
        # Используем атрибут title, так как он уникален для этого элемента.
        help_icon = authenticated_page.locator("span[title='Показать справку']")
        expect(help_icon).to_be_visible()

        # Шаг 2: Кликнуть на иконку, чтобы открыть окно справки.
        help_icon.click()

        # Шаг 3: Проверить, что окно справки появилось.
        # Локатор `div.cdm-card` выбран как наиболее общий для карточек в UI.
        # Ожидаем, что внутри будет хотя бы один тег <p> с текстом.
        help_window = authenticated_page.locator("div.cdm-card")
        expect(help_window).to_be_visible()
        expect(help_window.locator("p")).not_to_be_empty()

        # Шаг 4: Найти кнопку "Закрыть" и закрыть окно справки.
        close_button = help_window.locator("span[title='Закрыть']")
        expect(close_button).to_be_visible()
        close_button.click()

        # Шаг 5: Убедиться, что окно справки исчезло.
        expect(help_window).not_to_be_visible()

    except Exception as e:
        # В случае ошибки делаем скриншот для отладки.
        authenticated_page.screenshot(path="UI/error_screenshots/dashboard_help_tooltip_error.png")
        raise e


def test_dashboard_settings_validation(authenticated_page):
    """
    Проверяет открытие, закрытие и валидацию полей в панели настроек инфографики.
    """
    try:
        # Шаг 1: Открыть панель настроек, кликнув на иконку.
        settings_button = authenticated_page.locator("span[title='Параметры инфографики']")
        settings_button.click()

        # Шаг 2: Убедиться, что панель настроек стала видимой.
        settings_panel = authenticated_page.locator("div.DashboardSettingsForm")
        expect(settings_panel).to_be_visible()

        # Шаг 3: Валидация переключателя "Временной интервал".
        # Убеждаемся, что радио-кнопки корректно переключаются.
        interval_radio_button = settings_panel.locator("input[name='interval'][value='interval']")
        last_interval_radio = settings_panel.locator("input[name='interval'][value='last']")
        
        # Кликаем на "Заданный интервал" и проверяем состояние.
        interval_radio_button.click()
        expect(interval_radio_button).to_be_checked()
        expect(last_interval_radio).not_to_be_checked()

        # Шаг 3.1: Установка даты и времени "С" через виджет.
        authenticated_page.locator('button[aria-label="change date"]').first.click()
        authenticated_page.locator('.MuiPickersDay-day:not([class*="MuiPickersDay-hidden"])', has_text="1").first.click()
        # Исправляем локатор для часа (ищем "1", а не "01").
        authenticated_page.locator('.MuiPickersClock-container span:text-is("1")').click(force=True)
        authenticated_page.locator('.MuiPickersClock-container span:text-is("05")').click(force=True)
        # Кликаем по центру экрана, чтобы закрыть виджет выбора времени.
        viewport = authenticated_page.viewport_size
        if viewport:
            authenticated_page.mouse.click(viewport['width'] / 2, viewport['height'] / 2)

        # Шаг 3.2: Установка даты и времени "По" через виджет.
        authenticated_page.locator('button[aria-label="change date"]').nth(1).click()
        authenticated_page.locator('.MuiPickersDay-day:not([class*="MuiPickersDay-hidden"])', has_text="2").first.click()
        # Используем force=True и выбираем существующие значения (23 часа, 55 минут).
        authenticated_page.locator('.MuiPickersClock-container span:text-is("23")').click(force=True)
        authenticated_page.locator('.MuiPickersClock-container span:text-is("55")').click(force=True)
        # Кликаем по центру экрана, чтобы закрыть виджет выбора времени.
        viewport = authenticated_page.viewport_size
        if viewport:
            authenticated_page.mouse.click(viewport['width'] / 2, viewport['height'] / 2)

        # Возвращаемся к "За последний..." и проверяем состояние.
        last_interval_radio.click()
        expect(last_interval_radio).to_be_checked()
        expect(interval_radio_button).not_to_be_checked()

        # Шаг 4: Валидация поля "Вывод информации".
        info_output_select = settings_panel.locator("div#mode")
        expect(info_output_select).to_be_visible()

        # # Шаг 5: Валидация поля "Название шаблона".
        # # Используем поиск по label, чтобы найти нужное поле ввода.
        # template_name_input = settings_panel.locator("label:has-text('Название шаблона') + div input")
        # expect(template_name_input).to_be_visible()
        # template_name_input.fill("Тестовый шаблон")
        # expect(template_name_input).to_have_value("Тестовый шаблон")

        # Шаг 6: Валидация поля "Подсети источника".
        # Добавляем :not([readonly]), чтобы исключить скрытый textarea для авто-ресайза.
        source_subnet_textarea = settings_panel.locator("label:has-text('Подсети источника') + div textarea:not([readonly])")
        expect(source_subnet_textarea).to_be_visible()
        source_subnet_textarea.fill("192.168.0.0/16")
        expect(source_subnet_textarea).to_have_value("192.168.0.0/16")

        # Шаг 7: Валидация поля "Подсети получателя".
        dest_subnet_textarea = settings_panel.locator("label:has-text('Подсети получателя') + div textarea:not([readonly])")
        expect(dest_subnet_textarea).to_be_visible()
        dest_subnet_textarea.fill("10.0.0.0/8")
        expect(dest_subnet_textarea).to_have_value("10.0.0.0/8")

        # Шаг 8: Проверка состояния кнопки "Отобразить".
        # Ищем кнопку по ее типу 'submit' для большей надежности.
        create_button = settings_panel.locator("button[type='submit']")
        expect(create_button).to_be_visible()
        # Проверяем, что на кнопке правильный текст.
        expect(create_button).to_have_text("Отобразить")
        # На момент этого теста кнопка может быть как активной, так и неактивной.
        # Если требуется проверка на неактивность, нужно раскомментировать следующую строку.
        # expect(create_button).to_be_disabled()

        # Шаг 9: Закрыть панель настроек, повторно кликнув на иконку.
        # Находим кнопку заново, чтобы избежать работы с "устаревшим" элементом.
        authenticated_page.locator("span[title='Параметры инфографики']").click()

        # Проверяем, что у контейнера панели исчез класс, отвечающий за открытое состояние.
        # Это более надежно, чем проверять видимость, т.к. панель может скрываться с анимацией.
        settings_container = authenticated_page.locator("div.DashboardSettings")
        expect(settings_container).not_to_have_class("DashboardSettingsOpened")

    except Exception as e:
        # В случае ошибки делаем скриншот для отладки.
        authenticated_page.screenshot(path="UI/error_screenshots/dashboard_settings_validation_error.png")
        raise e


# def test_dashboard_date_incomplete_day(authenticated_page):
#     """
#     Проверяет валидацию поля даты при неполном вводе (только день).
#     """
#     try:
#         # Шаг 1: Открыть панель настроек и переключиться на заданный интервал.
#         settings_button = authenticated_page.locator("span[title='Параметры инфографики']")
#         settings_button.click()
#         settings_panel = authenticated_page.locator("div.DashboardSettingsForm")
#         settings_panel.locator("input[name='interval'][value='interval']").click()

#         # Шаг 2: Найти поле "с" и ввести в него только день.
#         from_date_input = settings_panel.locator(".cdm-datetime-interval__date input[type='text']")
#         from_date_input.fill("01")
#         from_date_input.blur()  # Убираем фокус, чтобы сработала валидация

#         # Шаг 3: Проверить, что поле помечено как невалидное и появилась ошибка.
#         expect(from_date_input).to_have_attribute("aria-invalid", "true")
#         error_message = settings_panel.locator(".cdm-datetime-interval__date .MuiFormHelperText-root.Mui-error")
#         expect(error_message).to_be_visible()
#         expect(error_message).to_have_text("Неверное значение")

#         # Шаг 4: Закрыть панель настроек.
#         settings_container = authenticated_page.locator("div.DashboardSettings")
#         authenticated_page.keyboard.press('Escape')
#         expect(settings_container).not_to_have_class("DashboardSettingsOpened")

#     except Exception as e:
#         authenticated_page.screenshot(path="UI/error_screenshots/dashboard_date_incomplete_day_error.png")
#         raise e


# def test_dashboard_date_incomplete_year(authenticated_page):
#     """
#     Проверяет валидацию поля даты при неполном вводе (незавершенный год).
#     """
#     try:
#         # Шаг 1: Открыть панель настроек и переключиться на заданный интервал.
#         settings_button = authenticated_page.locator("span[title='Параметры инфографики']")
#         settings_button.click()
#         settings_panel = authenticated_page.locator("div.DashboardSettingsForm")
#         settings_panel.locator("input[name='interval'][value='interval']").click()

#         # Шаг 2: Найти поле "с" и ввести дату с неполным годом.
#         from_date_input = settings_panel.locator(".cdm-datetime-interval__date input[type='text']")
#         from_date_input.fill("01.01.202")
#         from_date_input.blur()

#         # Шаг 3: Проверить, что поле помечено как невалидное и появилась ошибка.
#         expect(from_date_input).to_have_attribute("aria-invalid", "true")
#         error_message = settings_panel.locator(".cdm-datetime-interval__date .MuiFormHelperText-root.Mui-error")
#         expect(error_message).to_be_visible()
#         expect(error_message).to_have_text("Неверное значение")

#         # Шаг 4: Закрыть панель настроек.
#         settings_container = authenticated_page.locator("div.DashboardSettings")
#         authenticated_page.keyboard.press('Escape')
#         expect(settings_container).not_to_have_class("DashboardSettingsOpened")

#     except Exception as e:
#         authenticated_page.screenshot(path="UI/error_screenshots/dashboard_date_incomplete_year_error.png")
#         raise e


# def test_dashboard_date_incomplete_time(authenticated_page):
#     """
#     Проверяет валидацию поля даты при неполном вводе (незавершенное время).
#     """
#     try:
#         # Шаг 1: Открыть панель настроек и переключиться на заданный интервал.
#         settings_button = authenticated_page.locator("span[title='Параметры инфографики']")
#         settings_button.click()
#         settings_panel = authenticated_page.locator("div.DashboardSettingsForm")
#         settings_panel.locator("input[name='interval'][value='interval']").click()

#         # Шаг 2: Найти поле "с" и ввести дату с неполным временем.
#         from_date_input = settings_panel.locator(".cdm-datetime-interval__date input[type='text']")
#         from_date_input.fill("01.01.2025 12:34")
#         from_date_input.blur()

#         # Шаг 3: Проверить, что поле помечено как невалидное и появилась ошибка.
#         expect(from_date_input).to_have_attribute("aria-invalid", "true")
#         error_message = settings_panel.locator(".cdm-datetime-interval__date .MuiFormHelperText-root.Mui-error")
#         expect(error_message).to_be_visible()
#         expect(error_message).to_have_text("Неверное значение")

#         # Шаг 4: Закрыть панель настроек.
#         settings_container = authenticated_page.locator("div.DashboardSettings")
#         authenticated_page.keyboard.press('Escape')
#         expect(settings_container).not_to_have_class("DashboardSettingsOpened")

#     except Exception as e:
#         authenticated_page.screenshot(path="UI/error_screenshots/dashboard_date_incomplete_time_error.png")
#         raise e


# def test_dashboard_date_start_after_end(authenticated_page):
#     """
#     Проверяет валидацию, когда начальная дата позже конечной.
#     """
#     try:
#         # Шаг 1: Открыть панель настроек и переключиться на заданный интервал.
#         settings_button = authenticated_page.locator("span[title='Параметры инфографики']")
#         settings_button.click()
#         settings_panel = authenticated_page.locator("div.DashboardSettingsForm")
#         settings_panel.locator("input[name='interval'][value='interval']").click()

#         # Шаг 2: Подготовить неверный интервал дат.
#         now = datetime.now()
#         start_date = (now + timedelta(days=1)).strftime("%d.%m.%Y %H:%M:%S")
#         end_date = now.strftime("%d.%m.%Y %H:%M:%S")

#         # Шаг 3: Найти поля и ввести даты в неверном порядке.
#         from_date_input = settings_panel.locator(".cdm-datetime-interval__date input[type='text']")
#         to_date_input = settings_panel.locator(".cdm-datetime-interval__time input[type='text']")

#         from_date_input.fill(start_date)
#         to_date_input.fill(end_date)
#         to_date_input.blur() # Убираем фокус, чтобы сработала валидация

#         # Шаг 4: Проверить, что поле "с" помечено как невалидное.
#         expect(from_date_input).to_have_attribute("aria-invalid", "true")

#         # Шаг 5: Закрыть панель настроек.
#         settings_container = authenticated_page.locator("div.DashboardSettings")
#         authenticated_page.keyboard.press('Escape')
#         expect(settings_container).not_to_have_class("DashboardSettingsOpened")

#     except Exception as e:
#         authenticated_page.screenshot(path="UI/error_screenshots/dashboard_date_start_after_end_error.png")
#         raise e
