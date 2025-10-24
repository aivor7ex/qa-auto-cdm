import pytest
from playwright.sync_api import expect, Page
from datetime import datetime, timedelta
from urllib.parse import urlparse, urlunparse
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from UI.conftest import fail_with_screenshot


# Вспомогательные функции

def skip_if_no_data(page):
    empty_message = page.locator('.cdm-data-grid__empty-message')
    rows = page.locator('tbody tr')
    if (rows.count() == 0) and empty_message.is_visible():
        pytest.skip("Нет данных для теста.")

def ceil_to_5(x):
    """Округляет число x вверх до ближайшего большего, кратного 5."""
    # Шаг 1: Округление x вверх до ближайшего большего, кратного 5
    return ((x + 4) // 5) * 5

def floor_to_5(x):
    """Округляет число x вниз до ближайшего меньшего, кратного 5."""
    # Шаг 1: Округление x вниз до ближайшего меньшего, кратного 5
    return (x // 5) * 5

def get_future_datetime_range_from_max_dt(max_dt):
    """
    Возвращает кортеж (date_from, date_to) для фильтрации по будущему диапазону:
    - date_from: ближайшие к max_dt минуты, кратные 5 (вверх)
    - date_to: +5 минут к date_from, если не 60, иначе следующий час, минуты 00
    """
    # Шаг 1: Округляем минуты max_dt вверх до ближайших, кратных 5
    from_minute = ceil_to_5(max_dt.minute)
    from_hour = max_dt.hour
    from_date = max_dt
    # Шаг 2: Проверяем, не равны ли минуты 60, если да — переходим на следующий час
    if from_minute == 60:
        from_minute = 0
        from_hour += 1
        if from_hour == 24:
            from_hour = 0
            from_date = max_dt + timedelta(days=1)
        else:
            from_date = max_dt
        from_date = from_date.replace(hour=from_hour, minute=0, second=0)
    else:
        from_date = max_dt.replace(minute=from_minute, second=0)
    # Шаг 3: Определяем дату "по" (to_date) — либо +5 минут, либо следующий час
    if from_minute + 5 < 60:
        to_minute = from_minute + 5
        to_hour = from_hour
        to_date = from_date.replace(minute=to_minute)
    else:
        to_minute = 0
        to_hour = from_hour + 1
        if to_hour == 24:
            to_hour = 0
            to_date = from_date + timedelta(days=1)
        else:
            to_date = from_date
        to_date = to_date.replace(hour=to_hour, minute=0)
    # Шаг 4: Возвращаем кортеж дат (от, до)
    return from_date, to_date

def go_to_events_with_500_rows(page):
    """
    Переходит по базовому URL страницы событий с параметрами ?filter%5Bpage%5D=1&filter%5BrowsPerPage%5D=500
    и ожидает загрузки таблицы событий (строки).
    Если таблица не загрузилась — выбрасывает fail.
    """
    current_url = page.url
    parsed = urlparse(current_url)
    base_url = urlunparse((parsed.scheme, parsed.netloc, parsed.path, '', '', ''))
    new_url = f"{base_url}?filter%5Bpage%5D=1&filter%5BrowsPerPage%5D=500"
    page.goto(new_url)
    try:
        page.wait_for_selector('table.MuiTable-root.cdm-data-grid._sortable', timeout=20000)
        # Ждём либо строку, либо сообщение о пустой таблице
        page.wait_for_selector('tbody tr, .cdm-data-grid__empty-message', timeout=20000, state='visible')
    except PlaywrightTimeoutError:
        # Используем fail_with_screenshot вместо pytest.fail
        fail_with_screenshot("Таблица событий не загрузилась за отведённое время!", page)

def safe_pick_minute(page, minute):
    """
    Безопасно выбирает минуты на часах. Округляет вверх до ближайших, кратных 5.
    Если получилось 60 — выбирает 00.
    """
    # Округляем вверх до ближайших, кратных 5
    minute_rounded = ((minute + 4) // 5) * 5
    if minute_rounded == 60:
        minute_rounded = 0
    minute_str = f"{minute_rounded:02d}"
    minute_locator = page.locator(f'.MuiPickersClock-container span:text-is("{minute_str}")')
    if minute_locator.count() > 0 and minute_locator.first.is_visible():
        minute_locator.first.click(force=True)
    else:
        raise Exception(f"Не удалось выбрать минуты: {minute_str} на часах")

def remove_all_filters(page):
    """
    Удаляет все видимые фильтры на странице.
    """
    while True:
        filter_blocks = page.locator('.cdm-list-filter__filter-item')
        count = filter_blocks.count()
        if count == 0:
            break
        block = filter_blocks.first
        if block.is_visible():
            # Ищем именно кнопку с нужным классом и вложенным span с title="Удалить"
            delete_btn = block.locator('button.cdm-icon-button:has(span.cdm-icon-wrapper[title="Удалить"])')
            if delete_btn.is_visible():
                delete_btn.click(force=True)
                try:
                    block.wait_for(state='detached', timeout=20000)
                except Exception:
                    try:
                        block.wait_for(state='hidden', timeout=5000)
                    except Exception:
                        fail_with_screenshot("Фильтр не был удален", page, "remove_all_filters")

def wait_for_api_response(page, endpoint_substring):
    """
    Ожидает GET-запрос к endpoint_substring и возвращает объект ответа.
    Параметры:
        page: объект Playwright Page
        endpoint_substring: часть URL, по которой ищется нужный запрос
    Возвращает:
        response: объект ответа Playwright
    """
    with page.expect_response(lambda resp: resp.request.method == "GET" and endpoint_substring in resp.url) as resp_info:
        pass
    return resp_info.value

# Основные функции (без префикса test_)

def open_filter_menu(page: Page):
    # Шаг 1: Ищем уже открытое меню фильтра по дате и времени
    filter_menu = page.locator('.MuiMenu-paper').filter(has_text="Дата и время")
    if filter_menu.is_visible():
        # Шаг 2: Если меню уже открыто — возвращаем его
        return filter_menu
    # Шаг 3: Ищем и дожидаемся появления кнопки фильтра
    filter_button = page.locator('button.cdm-icon-button__toolbar-primary span[title="Фильтр"]')
    filter_button.wait_for(state='visible', timeout=3000)
    filter_button.locator('xpath=ancestor::button').click()
    # Шаг 4: Ожидаем появления меню фильтра
    filter_menu = page.locator('.MuiMenu-paper:has(ul.MuiMenu-list[role="menu"]:not(.userbar__menu))')
    if not filter_menu.is_visible():
        fail_with_screenshot("Меню фильтра не появилось", page)
    return filter_menu

def filter_menu_appears(authenticated_page: Page, credentials, count_filter, name_filter):
    """
    Проверяет, что меню фильтрации открывается и содержит указанное количество и название любого фильтра в меню 
    Параметры:
    page: объект Playwright Page
    credentials: креды
    count_filter: Количество фильтров в раскрывающемся списке
    name_filter: Название фильтра для проверки того, что он там содержится
    """
    # Шаг 1: Открываем меню фильтра
    page = authenticated_page
    filter_menu = open_filter_menu(page)
    # Шаг 2: Проверяем количество пунктов меню
    menu_items = filter_menu.locator('li')
    if menu_items.count() != int(count_filter):
        fail_with_screenshot(f"Ожидалось {count_filter} пунктов меню, найдено {menu_items.count()}", page)
    # Шаг 3: Проверяем наличие пункта "Дата и время"
    if menu_items.nth(0).inner_text() != str(name_filter):
        fail_with_screenshot(f"Ожидался пункт '{name_filter}', найден '{menu_items.nth(0).inner_text()}'", page)

def filter_date_time_appears(authenticated_page: Page, credentials):
    """
    Проверяет, что после выбора фильтра "Дата и время" появляется блок фильтрации с полями "с" и "по".
    """
    # Шаг 1: Открываем меню фильтра
    page = authenticated_page
    filter_menu = open_filter_menu(page)
    try:
        # Шаг 2: Находим и кликаем по пункту "Дата и время"
        date_item = filter_menu.locator('li').filter(has_text="Дата и время")
        if not date_item.is_visible():
            fail_with_screenshot("Пункт 'Дата и время' не найден в меню фильтра", page)
        date_item.click()
        # Шаг 3: Ждём появления блока фильтра по дате
        page.wait_for_timeout(500)
        filter_block = page.locator('.cdm-list-filter__filter-item')
        # Ждём исчезновения меню фильтра с небольшой задержкой
        page.wait_for_timeout(500)
        if filter_menu.is_visible():
            fail_with_screenshot("Меню фильтра должно было исчезнуть после выбора пункта", page)
        if not filter_block.is_visible():
            fail_with_screenshot("Блок фильтра по дате не появился", page)
        # Шаг 4: Проверяем наличие подписей "с" и "по"
        labels = filter_block.locator('.cdm-datetime-interval__label')
        if labels.nth(0).inner_text() != "с":
            fail_with_screenshot("Подпись 'с' не найдена в блоке фильтра", page)
        if labels.nth(1).inner_text() != "по":
            fail_with_screenshot("Подпись 'по' не найдена в блоке фильтра", page)
    finally:
        # Шаг 5: Если фильтр уже применён — удаляем его
        if filter_block.is_visible():
            delete_icon = filter_block.locator('span[title="Удалить"]')
            if delete_icon.is_visible():
                delete_icon.click(force=True)
            if filter_block.is_visible():
                fail_with_screenshot("Фильтр не был удален", page)

def filter_date_time_set_and_remove(authenticated_page: Page, credentials):
    """
    Проверяет установку фильтра по дате и времени, корректность отображения выбранных значений и удаление фильтра.
    """
    # Шаг 1: Открываем меню фильтра
    page = authenticated_page
    filter_menu = open_filter_menu(page)
    try:
        # Шаг 2: Находим и кликаем по пункту "Дата и время"
        date_item = filter_menu.locator('li').filter(has_text="Дата и время")
        is_visible = date_item.is_visible()
        if not is_visible:
            fail_with_screenshot("Ожидалось, что пункт 'Дата и время' будет видим в меню фильтров, но он не найден или не виден.", page)
        date_item.click()
        page.wait_for_timeout(500)
        # Шаг 3: Устанавливаем дату "С"
        date_from_btn = page.locator('.cdm-datetime-interval__date button[aria-label="change date"]')
        is_visible = date_from_btn.is_visible()
        if not is_visible:
            fail_with_screenshot("Ожидалось, что кнопка выбора даты 'С' будет видимой, но она не найдена или не видна.", page)
        date_from_btn.click()
        page.locator('.MuiPickersDay-day:not([class*="MuiPickersDay-hidden"])', has_text="1").first.click()
        page.locator('.MuiPickersClock-container span:text-is("1")').click(force=True)
        page.wait_for_timeout(500)
        page.locator('.MuiPickersClock-container span:text-is("05")').click(force=True)
        size = page.viewport_size or page.context.viewport_size
        if size:
            page.mouse.click(size['width'] / 4, size['height'] / 4)
        # Шаг 4: Устанавливаем дату "По"
        date_to_btn = page.locator('.cdm-datetime-interval__time button[aria-label="change date"]')
        is_visible = date_to_btn.is_visible()
        if not is_visible:
            fail_with_screenshot("Ожидалось, что кнопка выбора даты 'По' будет видимой, но она не найдена или не видна.", page)
        date_to_btn.click()
        page.locator('.MuiPickersDay-day:not([class*="MuiPickersDay-hidden"])', has_text="2").first.click()
        page.locator('.MuiPickersClock-container span:text-is("23")').click(force=True)
        page.wait_for_timeout(500)
        page.locator('.MuiPickersClock-container span:text-is("55")').click(force=True)
        if size:
            page.mouse.click(size['width'] / 4, size['height'] / 4)
        page.wait_for_timeout(500)
        # Шаг 5: Проверяем значения в инпутах
        now = datetime.now()
        month = now.month
        year = now.year
        inputs = page.locator('.cdm-datetime-interval input')
        actual_from = inputs.nth(0).input_value()
        actual_to = inputs.nth(1).input_value()
        from_dt = datetime.strptime(actual_from, "%d.%m.%Y %H:%M:%S")
        to_dt = datetime.strptime(actual_to, "%d.%m.%Y %H:%M:%S")
        if from_dt.day != 1:
            fail_with_screenshot(f"Ожидался день '1' в поле 'с', получено: {from_dt.day}", page)
        if from_dt.month != month:
            fail_with_screenshot(f"Ожидался месяц '{month}', получено: {from_dt.month}", page)
        if from_dt.year != year:
            fail_with_screenshot(f"Ожидался год '{year}', получено: {from_dt.year}", page)
        if from_dt.hour != 1 or from_dt.minute != 5:
            fail_with_screenshot(f"Ожидалось время 01:05:00, получено: {from_dt.time()}", page)
        if to_dt.day != 2:
            fail_with_screenshot(f"Ожидался день '2' в поле 'по', получено: {to_dt.day}", page)
        if to_dt.month != month:
            fail_with_screenshot(f"Ожидался месяц '{month}', получено: {to_dt.month}", page)
        if to_dt.year != year:
            fail_with_screenshot(f"Ожидался год '{year}', получено: {to_dt.year}", page)
        if to_dt.hour != 23 or to_dt.minute != 55:
            fail_with_screenshot(f"Ожидалось время 23:55:00, получено: {to_dt.time()}", page)
    finally:
        # Шаг 6: Если фильтр уже применён — удаляем его
        filter_block = page.locator('.cdm-list-filter__filter-item')
        if filter_block.is_visible():
            delete_icon = filter_block.locator('span[title="Удалить"]')
            if delete_icon.is_visible():
                delete_icon.click(force=True)
            if filter_block.is_visible():
                fail_with_screenshot("Фильтр не был удален", page)

def filter_date_time_positive_range(authenticated_page: Page, credentials, skip_if_no_data):
    """
    Проверяет фильтрацию по корректному диапазону дат: отображаются только строки, попадающие в указанный интервал, после удаления фильтра — возвращаются все строки.
    """
    # Шаг 1: Получаем все даты из таблицы
    page = authenticated_page
    date_cells = page.locator('tbody tr td:nth-child(1) div')
    dates = [cell.inner_text() for cell in date_cells.all()]
    if len(dates) == 0:
        fail_with_screenshot("Нет данных для теста.", page)
    # Шаг 2: Преобразуем строки в datetime и выбираем максимальную дату
    dates_dt = [datetime.strptime(d, "%d.%m.%Y %H:%M:%S") for d in dates]
    target_dt = sorted(dates_dt, reverse=True)[0]
    # Шаг 3: Формируем диапазон дат для фильтра
    date_from = target_dt.replace(minute=floor_to_5(target_dt.minute), second=0)
    m = ceil_to_5(target_dt.minute)
    if m == 60:
        date_to = (target_dt + timedelta(hours=1)).replace(minute=0, second=0)
    else:
        date_to = target_dt.replace(minute=m, second=0)
    try:
        # Шаг 4: Открываем меню фильтра и применяем фильтр по диапазону дат
        filter_menu = open_filter_menu(page)
        date_item = filter_menu.locator('li').filter(has_text="Дата и время")
        if not date_item.is_visible():
            fail_with_screenshot("Пункт 'Дата и время' не найден в меню фильтра", page)
        date_item.click()
        page.wait_for_timeout(500)
        # Шаг 5: Устанавливаем дату "С"
        date_from_btn = page.locator('.cdm-datetime-interval__date button[aria-label="change date"]')
        if not date_from_btn.is_visible():
            fail_with_screenshot("Кнопка выбора даты 'С' не найдена", page)
        date_from_btn.click()
        page.locator(f'.MuiPickersDay-day:not([class*="MuiPickersDay-hidden"])', has_text=str(date_from.day)).first.click()
        page.wait_for_timeout(500)
        hour_str = f"{date_from.hour:02d}" if date_from.hour == 0 else str(date_from.hour)
        page.locator(f'.MuiPickersClock-container span:text-is("{hour_str}")').click(force=True)
        page.wait_for_timeout(500)
        page.locator(f'.MuiPickersClock-container span:text-is("{date_from.minute:02d}")').click(force=True)
        size = page.viewport_size or page.context.viewport_size
        if size:
            page.mouse.click(size['width'] / 4, size['height'] / 4)
        # Шаг 6: Устанавливаем дату "По"
        date_to_btn = page.locator('.cdm-datetime-interval__time button[aria-label="change date"]')
        if not date_to_btn.is_visible():
            fail_with_screenshot("Кнопка выбора даты 'По' не найдена", page)
        date_to_btn.click()
        page.locator(f'.MuiPickersDay-day:not([class*="MuiPickersDay-hidden"])', has_text=str(date_to.day)).first.click()
        page.wait_for_timeout(500)
        hour_str = f"{date_to.hour:02d}" if date_to.hour == 0 else str(date_to.hour)
        page.locator(f'.MuiPickersClock-container span:text-is("{hour_str}")').click(force=True)
        page.wait_for_timeout(500)
        page.locator(f'.MuiPickersClock-container span:text-is("{date_to.minute:02d}")').click(force=True)
        if size:
            page.mouse.click(size['width'] / 4, size['height'] / 4)
        page.wait_for_timeout(500)
        # Шаг 7: Проверяем, что все отфильтрованные даты попадают в диапазон
        filtered_date_cells = page.locator('tbody tr td:nth-child(1) div')
        filtered_dates = [cell.inner_text() for cell in filtered_date_cells.all()]
        filtered_dt = [datetime.strptime(d, "%d.%m.%Y %H:%M:%S") for d in filtered_dates]
        for dt in filtered_dt:
            if not (date_from <= dt <= date_to):
                fail_with_screenshot(f"Дата {dt} вне диапазона фильтра {date_from} - {date_to}", page)
            if not (floor_to_5(dt.minute) == floor_to_5(target_dt.minute) and dt.hour == target_dt.hour and dt.day == target_dt.day and dt.month == target_dt.month and dt.year == target_dt.year):
                fail_with_screenshot(f"Дата {dt} не совпадает с выбранной датой {target_dt} (по интервалу 5 минут)", page)
    finally:
        # Шаг 8: Удаляем фильтр и проверяем, что появились строки вне диапазона
        filter_block = page.locator('.cdm-list-filter__filter-item')
        if filter_block.is_visible():
            delete_icon = filter_block.locator('span[title="Удалить"]')
            if delete_icon.is_visible():
                delete_icon.click(force=True)
            if filter_block.is_visible():
                fail_with_screenshot("Фильтр не был удален", page)
        page.wait_for_timeout(500)
        restored_date_cells = page.locator('tbody tr td:nth-child(1) div')
        restored_dates = [cell.inner_text() for cell in restored_date_cells.all()]
        if len(restored_dates) != len(dates):
            fail_with_screenshot("После удаления фильтра должны снова отображаться все строки из таблицы", page)

def filter_date_time_future_empty(authenticated_page: Page, credentials, skip_if_no_data):
    """
    Проверяет, что при фильтрации по будущему диапазону дат таблица становится пустой, а после удаления фильтра данные возвращаются.
    """
    # Шаг 1: Получаем все даты из таблицы
    page = authenticated_page
    date_cells = page.locator('tbody tr td:nth-child(1) div')
    dates = [cell.inner_text() for cell in date_cells.all()]
    if len(dates) == 0:
        fail_with_screenshot("Нет данных для теста.", page, "filter_date_time_future_empty")
    # Шаг 2: Преобразуем строки в datetime и находим максимальную дату
    dates_dt = [datetime.strptime(d, "%d.%m.%Y %H:%M:%S") for d in dates]
    max_dt = max(dates_dt)
    # Шаг 3: Получаем будущий диапазон дат (гарантированно в будущем)
    future_from = max_dt + timedelta(hours=1)
    future_to = future_from + timedelta(minutes=5)
    date_from = future_from.replace(second=0, microsecond=0)
    date_to = future_to.replace(second=0, microsecond=0)
    try:
        # Шаг 4: Открываем меню фильтра и применяем фильтр по будущему диапазону
        filter_menu = open_filter_menu(page)
        date_item = filter_menu.locator('li').filter(has_text="Дата и время")
        if not date_item.is_visible():
            fail_with_screenshot("Пункт 'Дата и время' не найден в меню фильтра", page, "filter_date_time_future_empty")
        date_item.click()
        page.wait_for_timeout(500)
        # Шаг 5: Устанавливаем дату "С" (будущее)
        date_from_btn = page.locator('.cdm-datetime-interval__date button[aria-label="change date"]')
        date_from_btn.click()
        page.locator(f'.MuiPickersDay-day:not([class*="MuiPickersDay-hidden"]):has-text("{date_from.day}")').first.click()
        page.wait_for_timeout(500)
        hour_str = f"{date_from.hour:02d}" if date_from.hour == 0 else str(date_from.hour)
        page.locator(f'.MuiPickersClock-container span:text-is("{hour_str}")').click(force=True)
        page.wait_for_timeout(500)
        safe_pick_minute(page, date_from.minute)
        size = page.viewport_size or page.context.viewport_size
        if size:
            page.mouse.click(size['width'] / 4, size['height'] / 4)
        # Шаг 6: Устанавливаем дату "По" (будущее)
        date_to_btn = page.locator('.cdm-datetime-interval__time button[aria-label="change date"]')
        date_to_btn.click()
        page.locator(f'.MuiPickersDay-day:not([class*="MuiPickersDay-hidden"]):has-text("{date_to.day}")').first.click()
        page.wait_for_timeout(500)
        hour_str = f"{date_to.hour:02d}" if date_to.hour == 0 else str(date_to.hour)
        page.locator(f'.MuiPickersClock-container span:text-is("{hour_str}")').click(force=True)
        page.wait_for_timeout(500)
        safe_pick_minute(page, date_to.minute)
        if size:
            page.mouse.click(size['width'] / 4, size['height'] / 4)
        page.wait_for_timeout(500)
        # Шаг 7: Проверяем, что таблица пуста
        rows = page.locator('tbody tr')
        if not (rows.count() == 0 or page.locator('.cdm-data-grid__empty-message').is_visible()):
            fail_with_screenshot("Ожидалось, что при фильтрации по будущей дате таблица будет пуста", page, "filter_date_time_future_empty")
    finally:
        # Шаг 8: Удаляем фильтр и проверяем восстановление данных
        filter_block = page.locator('.cdm-list-filter__filter-item')
        if filter_block.is_visible():
            delete_icon = filter_block.locator('span[title="Удалить"]')
            if delete_icon.is_visible():
                delete_icon.click(force=True)
            if filter_block.is_visible():
                fail_with_screenshot("Фильтр не был удален", page)
        page.wait_for_timeout(500)  # Ждём появления строк после удаления фильтра
        restored_date_cells = page.locator('tbody tr td:nth-child(1) div')
        restored_dates = [cell.inner_text() for cell in restored_date_cells.all()]
        if len(restored_dates) == 0:
            fail_with_screenshot("После удаления фильтра должны снова отображаться строки из таблицы", page)

def filter_date_time_inverted_range_empty(authenticated_page: Page, credentials, skip_if_no_data):
    """
    Проверяет, что при перепутанных границах фильтра (дата "с" больше даты "по") таблица пуста, а после удаления фильтра данные возвращаются.
    """
    # Шаг 1: Открываем меню фильтра
    page = authenticated_page
    from datetime import datetime
    filter_menu = open_filter_menu(page)
    try:
        # Шаг 2: Находим и кликаем по пункту "Дата и время"
        date_item = filter_menu.locator('li').filter(has_text="Дата и время")
        if not date_item.is_visible():
            fail_with_screenshot("Пункт 'Дата и время' не найден в меню фильтра", page)
        date_item.click()
        page.wait_for_timeout(500)
        # Шаг 3: Формируем перепутанный диапазон дат (от больше до)
        now = datetime.now()
        date_from = now.replace(hour=23, minute=59, second=0)
        date_to = now.replace(hour=0, minute=0, second=0)
        # Шаг 4: Устанавливаем дату "С"
        date_from_btn = page.locator('.cdm-datetime-interval__date button[aria-label="change date"]')
        date_from_btn.click()
        page.locator(f'.MuiPickersDay-day:not([class*="MuiPickersDay-hidden"])', has_text=str(date_from.day)).first.click()
        page.wait_for_timeout(500)
        hour_str = f"{date_from.hour:02d}" if date_from.hour == 0 else str(date_from.hour)
        page.locator(f'.MuiPickersClock-container span:text-is("{hour_str}")').click(force=True)
        size = page.viewport_size or page.context.viewport_size
        if size:
            page.mouse.click(size['width'] / 4, size['height'] / 4)
        # Шаг 5: Устанавливаем дату "По"
        date_to_btn = page.locator('.cdm-datetime-interval__time button[aria-label="change date"]')
        date_to_btn.click()
        page.locator(f'.MuiPickersDay-day:not([class*="MuiPickersDay-hidden"])', has_text=str(date_to.day)).first.click()
        page.wait_for_timeout(500)
        hour_str = f"{date_to.hour:02d}" if date_to.hour == 0 else str(date_to.hour)
        page.locator(f'.MuiPickersClock-container span:text-is("{hour_str}")').click(force=True)
        if size:
            page.mouse.click(size['width'] / 4, size['height'] / 4)
        page.wait_for_timeout(500)
        # Шаг 6: Проверяем, что таблица пуста
        rows = page.locator('tbody tr')
        if not (rows.count() == 0 or page.locator('.cdm-data-grid__empty-message').is_visible()):
            fail_with_screenshot("Ожидалось, что при перепутанных границах фильтра таблица будет пуста", page)
    finally:
        # Шаг 7: Удаляем фильтр и проверяем восстановление данных
        filter_block = page.locator('.cdm-list-filter__filter-item')
        if filter_block.is_visible():
            delete_icon = filter_block.locator('span[title="Удалить"]')
            if delete_icon.is_visible():
                delete_icon.click(force=True)
            if filter_block.is_visible():
                fail_with_screenshot("Фильтр не был удален", page)
        page.wait_for_timeout(500)  # Ждём появления строк после удаления фильтра
        restored_date_cells = page.locator('tbody tr td:nth-child(1) div')
        restored_dates = [cell.inner_text() for cell in restored_date_cells.all()]
        if len(restored_dates) == 0:
            fail_with_screenshot("После удаления фильтра должны снова отображаться строки из таблицы", page)

def filter_date_time_exact_no_match(authenticated_page: Page, credentials, skip_if_no_data):
    """
    Проверяет, что при фильтрации по дате, которой нет в данных (10 лет назад), таблица пуста, а после удаления фильтра данные возвращаются.
    """
    # Шаг 1: Открываем меню фильтра
    page = authenticated_page
    from datetime import datetime, timedelta
    filter_menu = open_filter_menu(page)
    try:
        # Шаг 2: Находим и кликаем по пункту "Дата и время"
        date_item = filter_menu.locator('li').filter(has_text="Дата и время")
        if not date_item.is_visible():
            fail_with_screenshot("Пункт 'Дата и время' не найден в меню фильтра", page)
        date_item.click()
        page.wait_for_timeout(500)
        # Шаг 3: Формируем диапазон дат, по которым нет данных (10 лет назад)
        no_data_date = datetime.now() - timedelta(days=365*10)
        date_from = no_data_date.replace(hour=12, minute=0, second=0)
        date_to = no_data_date.replace(hour=12, minute=0, second=0)
        # Шаг 4: Устанавливаем дату "С"
        date_from_btn = page.locator('.cdm-datetime-interval__date button[aria-label="change date"]')
        date_from_btn.click()
        page.locator(f'.MuiPickersDay-day:not([class*="MuiPickersDay-hidden"])', has_text=str(date_from.day)).first.click()
        page.wait_for_timeout(500)
        hour_str = f"{date_from.hour:02d}" if date_from.hour == 0 else str(date_from.hour)
        page.locator(f'.MuiPickersClock-container span:text-is("{hour_str}")').click(force=True)
        page.wait_for_timeout(500)
        page.locator(f'.MuiPickersClock-container span:text-is("{date_from.minute:02d}")').click(force=True)
        size = page.viewport_size or page.context.viewport_size
        if size:
            page.mouse.click(size['width'] / 4, size['height'] / 4)
        # Шаг 5: Устанавливаем дату "По"
        date_to_btn = page.locator('.cdm-datetime-interval__time button[aria-label="change date"]')
        date_to_btn.click()
        page.locator(f'.MuiPickersDay-day:not([class*="MuiPickersDay-hidden"])', has_text=str(date_to.day)).first.click()
        page.wait_for_timeout(500)
        hour_str = f"{date_to.hour:02d}" if date_to.hour == 0 else str(date_to.hour)
        page.locator(f'.MuiPickersClock-container span:text-is("{hour_str}")').click(force=True)
        page.wait_for_timeout(500)
        page.locator(f'.MuiPickersClock-container span:text-is("{date_to.minute:02d}")').click(force=True)
        if size:
            page.mouse.click(size['width'] / 4, size['height'] / 4)
        page.wait_for_timeout(500)
        # Шаг 6: Проверяем, что таблица пуста
        rows = page.locator('tbody tr')
        if not (rows.count() == 0 or page.locator('.cdm-data-grid__empty-message').is_visible()):
            fail_with_screenshot("Ожидалось, что при фильтре по несуществующей дате таблица будет пуста", page)
    finally:
        # Шаг 7: Удаляем фильтр и проверяем восстановление данных
        filter_block = page.locator('.cdm-list-filter__filter-item')
        if filter_block.is_visible():
            delete_icon = filter_block.locator('span[title="Удалить"]')
            if delete_icon.is_visible():
                delete_icon.click(force=True)
            if filter_block.is_visible():
                fail_with_screenshot("Фильтр не был удален", page)
        page.wait_for_timeout(500)  # Ждём появления строк после удаления фильтра
        restored_date_cells = page.locator('tbody tr td:nth-child(1) div')
        restored_dates = [cell.inner_text() for cell in restored_date_cells.all()]
        if len(restored_dates) == 0:
            fail_with_screenshot("После удаления фильтра должны снова отображаться строки из таблицы", page)

def filter_date_time_only_from(authenticated_page: Page, credentials, skip_if_no_data):
    """
    Проверяет фильтрацию только по дате "с": отображаются только строки с датой больше или равной выбранной, после удаления фильтра данные возвращаются.
    """
    # Шаг 1: Получаем все даты из таблицы
    page = authenticated_page
    date_cells = page.locator('tbody tr td:nth-child(1) div')
    dates = [cell.inner_text() for cell in date_cells.all()]
    if len(dates) == 0:
        fail_with_screenshot("Нет данных для теста.", page)
    # Шаг 2: Преобразуем строки в datetime и находим min/max дату
    dates_dt = [datetime.strptime(d, "%d.%m.%Y %H:%M:%S") for d in dates]
    min_dt = min(dates_dt)
    max_dt = max(dates_dt)
    try:
        # Шаг 3: Открываем меню фильтра
        filter_menu = open_filter_menu(page)
        date_item = filter_menu.locator('li').filter(has_text="Дата и время")
        if not date_item.is_visible():
            fail_with_screenshot("Пункт 'Дата и время' не найден в меню фильтра", page)
        date_item.click()
        page.wait_for_timeout(500)
        # Шаг 4: Вычисляем середину диапазона и округляем вниз до 5 минут
        from_dt = min_dt + (max_dt - min_dt) / 2
        from_dt = from_dt.replace(minute=floor_to_5(from_dt.minute), second=0, microsecond=0)
        # Шаг 5: Устанавливаем только дату "С"
        date_from_btn = page.locator('.cdm-datetime-interval__date button[aria-label="change date"]')
        date_from_btn.click()
        page.locator(f'.MuiPickersDay-day:not([class*="MuiPickersDay-hidden"])', has_text=str(from_dt.day)).first.click()
        page.wait_for_timeout(500)
        hour_str = f"{from_dt.hour:02d}" if from_dt.hour == 0 else str(from_dt.hour)
        page.locator(f'.MuiPickersClock-container span:text-is("{hour_str}")').click(force=True)
        page.wait_for_timeout(500)
        page.locator(f'.MuiPickersClock-container span:text-is("{from_dt.minute:02d}")').click(force=True)
        size = page.viewport_size or page.context.viewport_size
        if size:
            page.mouse.click(size['width'] / 4, size['height'] / 4)
        page.wait_for_timeout(500)
        # Шаг 6: Проверяем, что все отфильтрованные даты >= from_dt
        filtered_date_cells = page.locator('tbody tr td:nth-child(1) div')
        filtered_dates = [cell.inner_text() for cell in filtered_date_cells.all()]
        filtered_dt = [datetime.strptime(d, "%d.%m.%Y %H:%M:%S") for d in filtered_dates]
        for dt in filtered_dt:
            if dt < from_dt:
                fail_with_screenshot(f"Дата {dt} меньше фильтра 'С' {from_dt}", page)
    finally:
        # Шаг 7: Удаляем фильтр и проверяем восстановление данных
        filter_block = page.locator('.cdm-list-filter__filter-item')
        if filter_block.is_visible():
            delete_icon = filter_block.locator('span[title="Удалить"]')
            if delete_icon.is_visible():
                delete_icon.click(force=True)
            if filter_block.is_visible():
                fail_with_screenshot("Фильтр не был удален", page)
        page.wait_for_timeout(500)  # Ждём появления строк после удаления фильтра
        restored_date_cells = page.locator('tbody tr td:nth-child(1) div')
        restored_dates = [cell.inner_text() for cell in restored_date_cells.all()]
        if len(restored_dates) == 0:
            fail_with_screenshot("После удаления фильтра должны снова отображаться строки из таблицы", page)

def filter_date_time_only_to(authenticated_page: Page, credentials, skip_if_no_data):
    """
    Проверяет фильтрацию только по дате "по": отображаются только строки с датой меньше или равной выбранной, после удаления фильтра данные возвращаются.
    """
    # Шаг 1: Получаем все даты из таблицы
    page = authenticated_page
    date_cells = page.locator('tbody tr td:nth-child(1) div')
    dates = [cell.inner_text() for cell in date_cells.all()]
    if len(dates) == 0:
        fail_with_screenshot("Нет данных для теста.", page)
    # Шаг 2: Преобразуем строки в datetime и находим min/max дату
    dates_dt = [datetime.strptime(d, "%d.%m.%Y %H:%M:%S") for d in dates]
    min_dt = min(dates_dt)
    max_dt = max(dates_dt)
    # Шаг 3: Открываем меню фильтра
    filter_menu = open_filter_menu(page)
    date_item = filter_menu.locator('li').filter(has_text="Дата и время")
    if not date_item.is_visible():
        fail_with_screenshot("Пункт 'Дата и время' не найден в меню фильтра", page)
    date_item.click()
    page.wait_for_timeout(500)
    try:
        # Шаг 4: Ставим фильтр 'по' чуть позже самой свежей даты
        to_dt = max_dt + timedelta(days=1)
        to_dt = to_dt.replace(minute=floor_to_5(to_dt.minute), second=0, microsecond=0)
        # Шаг 5: Устанавливаем только дату "По"
        date_to_btn = page.locator('.cdm-datetime-interval__time button[aria-label="change date"]')
        date_to_btn.click()
        # Выбираем конкретный день из to_dt
        page.locator(f'.MuiPickersDay-day:not([class*="MuiPickersDay-hidden"])', has_text=str(to_dt.day)).first.click()
        page.wait_for_timeout(500)
        hour_str = f"{to_dt.hour:02d}" if to_dt.hour == 0 else str(to_dt.hour)
        page.locator(f'.MuiPickersClock-container span:text-is("{hour_str}")').click(force=True)
        page.wait_for_timeout(500)
        page.locator(f'.MuiPickersClock-container span:text-is("{to_dt.minute:02d}")').click(force=True)
        size = page.viewport_size or page.context.viewport_size
        if size:
            page.mouse.click(size['width'] / 4, size['height'] / 4)
        page.wait_for_timeout(500)
        # Шаг 6: Проверяем, что все отфильтрованные даты <= to_dt
        filtered_date_cells = page.locator('tbody tr td:nth-child(1) div')
        filtered_dates = [cell.inner_text() for cell in filtered_date_cells.all()]
        filtered_dt = [datetime.strptime(d, "%d.%m.%Y %H:%M:%S") for d in filtered_dates]
        for dt in filtered_dt:
            if dt > to_dt:
                fail_with_screenshot(f"Дата {dt} больше фильтра 'По' {to_dt}", page)
    finally:
        # Шаг 7: Удаляем фильтр и проверяем восстановление данных
        filter_block = page.locator('.cdm-list-filter__filter-item')
        if filter_block.is_visible():
            delete_icon = filter_block.locator('span[title="Удалить"]')
            if delete_icon.is_visible():
                delete_icon.click(force=True)
            if filter_block.is_visible():
                fail_with_screenshot("Фильтр не был удален", page)
        page.wait_for_timeout(1000)  # Ждём появления строк после удаления фильтра
        restored_date_cells = page.locator('tbody tr td:nth-child(1) div')
        restored_dates = [cell.inner_text() for cell in restored_date_cells.all()]
        if len(restored_dates) == 0:
            fail_with_screenshot("После удаления фильтра должны снова отображаться строки из таблицы", page)

def check_filter_by_select(page, filter_name, severity_text, endpoint_substring="/api/service/remote/logger-analytics/analytics-server/call"):
    """
    Универсальный тест select-фильтра:
    1. Открывает меню фильтрации, выбирает нужный select-фильтр, выбирает значение, ждёт GET-запрос по endpoint_substring.
    2. Проверяет, что после фильтрации в таблице остались только строки, содержащие это значение в нужной колонке (частичное совпадение).
    Параметры:
        page: объект Playwright Page
        filter_name: название фильтра и колонки (например, 'Сервис')
        severity_text: значение для фильтрации
        endpoint_substring: подстрока эндпоинта для ожидания GET-запроса (по умолчанию старый эндпоинт)
    """
    skip_if_no_data(page)
    # Шаг №1: Определяем индекс колонки по названию фильтра
    ths = page.locator('thead tr th')
    header_texts = []
    for i in range(ths.count()):
        th = ths.nth(i)
        try:
            text = th.locator('span span').first.inner_text(timeout=2000)
        except Exception:
            try:
                text = th.locator('span').first.inner_text(timeout=2000)
            except Exception:
                text = ""
        header_texts.append(text.strip())
    try:
        col_idx = [h.lower() for h in header_texts].index(filter_name.lower())
    except ValueError:
        fail_with_screenshot(f"Колонка '{filter_name}' не найдена в таблице. Заголовки: {header_texts}", page)

    # Шаг №2: Проверяем наличие данных в этой колонке (хотя бы одна непустая ячейка)
    rows = page.locator('tbody tr')
    has_data = False
    for i in range(rows.count()):
        cell = rows.nth(i).locator(f'td:nth-child({col_idx+1})')
        if cell.inner_text().strip():
            has_data = True
            break
    if not has_data:
        pytest.skip("Нет данных для теста.")

    # Открываем меню фильтров
    filter_button = page.locator('button.cdm-icon-button__toolbar-primary span[title="Фильтр"]')
    filter_button.locator('xpath=ancestor::button').click()
    # Новый уникальный поиск меню фильтров (без userbar__menu)
    filter_menu = page.locator('.MuiMenu-paper:has(ul.MuiMenu-list[role="menu"]:not(.userbar__menu))')
    # Шаг 3: Ждём появления меню фильтра
    try:
        filter_menu.wait_for(state="visible", timeout=2000)
    except Exception:
        fail_with_screenshot(f"Меню фильтра по '{filter_name}' не появилось", page)

    # Шаг 4: Кликаем по фильтру с нужным названием
    filter_item = filter_menu.locator('li.MuiMenuItem-root[role="menuitem"]').filter(has_text=filter_name)
    try:
        filter_item.wait_for(state="visible", timeout=2000)
    except Exception:
        fail_with_screenshot(f"Пункт '{filter_name}' не найден в меню фильтра", page)
    filter_item.click()
    page.wait_for_timeout(500)
    try:
        # Проверяем, что появился select с лейблом
        filter_block = page.locator('.cdm-list-filter__filter-item')
        try:
            filter_block.wait_for(state="visible", timeout=2000)
        except Exception:
            fail_with_screenshot(f"Блок фильтра по '{filter_name}' не появился", page)
        select_label = filter_block.locator('label').filter(has_text=filter_name)
        try:
            select_label.wait_for(state="visible", timeout=2000)
        except Exception:
            fail_with_screenshot(f"Лейбл '{filter_name}' не найден в блоке фильтра", page)

        # Открываем select
        select_btn = filter_block.locator('.MuiSelect-root')
        select_btn.click()
        # Ждём появления меню с текстом из параметра
        menu = page.locator('.MuiMenu-paper', has_text=severity_text)
        try:
            menu.wait_for(state="visible", timeout=2000)
        except Exception:
            fail_with_screenshot(f"Меню выбора значения '{severity_text}' не появилось", page)
        # Выбираем фильтр
        menu.locator(f'li:has-text("{severity_text}")').click(force=True)
        page.wait_for_timeout(500)
        # После выбора фильтра
        try:
            page.wait_for_selector('tbody tr, .cdm-data-grid__empty-message', timeout=2000, state='visible')
            rows = page.locator('tbody tr')
            if rows.count() == 0:
                pytest.skip(f"Нет данных с фильтром '{filter_name}' и значением '{severity_text}' для проверки.")
            # --- основной блок проверки ---
            ths = page.locator('thead tr th')
            header_texts = []
            for i in range(ths.count()):
                th = ths.nth(i)
                try:
                    text = th.locator('span span').first.inner_text(timeout=2000)
                except Exception:
                    try:
                        text = th.locator('span').first.inner_text(timeout=2000)
                    except Exception:
                        text = ""
                header_texts.append(text.strip())
            try:
                severity_col_idx = [h.lower() for h in header_texts].index(filter_name.lower())
            except ValueError:
                fail_with_screenshot(f"Колонка '{filter_name}' не найдена в таблице. Заголовки: {header_texts}", page)
            # Получаем все строки из body и проверяем значения в колонке
            for i in range(rows.count()):
                cell = rows.nth(i).locator(f'td:nth-child({severity_col_idx+1})')
                cell_text = cell.inner_text().strip()
                if cell_text != severity_text:
                    fail_with_screenshot(f"В строке {i+1} ожидалось '{severity_text}', получено '{cell_text}'", page)
        except Exception as e:
            print(f"Ошибка при проверке фильтра '{filter_name}' по значению '{severity_text}': {e}")
            raise
    except Exception as e:
        print(f"Ошибка при проверке фильтра '{filter_name}' по значению '{severity_text}': {e}")
        raise
    finally:
        # Удаляем фильтр
        delete_icon = filter_block.locator('span[title="Удалить"]')
        if delete_icon.is_visible():
            delete_icon.click(force=True)
        try:
            filter_block.wait_for(state="hidden", timeout=2000)
        except Exception:
            fail_with_screenshot("Блок фильтра не исчез после удаления", page)
        page.wait_for_timeout(500)


def check_filter_by_select_negative_other_values(page, filter_name, severity_text, endpoint_substring="/api/service/remote/logger-analytics/analytics-server/call"):
    """
    Универсальный тест негативной select-фильтрации:
    1. Открывает меню фильтрации, выбирает нужный select-фильтр, выбирает значение, ждёт GET-запрос по endpoint_substring.
    2. Проверяет, что после фильтрации в таблице нет строк с этим значением (или таблица пуста).
    Параметры:
        page: объект Playwright Page
        filter_name: название фильтра и колонки (например, 'Сервис')
        severity_text: значение для фильтрации
        endpoint_substring: подстрока эндпоинта для ожидания GET-запроса (по умолчанию старый эндпоинт)
    """
    skip_if_no_data(page)
    # Шаг №0: Определяем индекс колонки по названию фильтра
    ths = page.locator('thead tr th')
    header_texts = []
    for i in range(ths.count()):
        th = ths.nth(i)
        try:
            text = th.locator('span span').first.inner_text(timeout=2000)
        except Exception:
            try:
                text = th.locator('span').first.inner_text(timeout=2000)
            except Exception:
                text = ""
        header_texts.append(text.strip())
    try:
        col_idx = [h.lower() for h in header_texts].index(filter_name.lower())
    except ValueError:
        fail_with_screenshot(f"Колонка '{filter_name}' не найдена в таблице. Заголовки: {header_texts}", page)

    # Шаг №2: Проверяем наличие данных в этой колонке (хотя бы одна непустая ячейка)
    rows = page.locator('tbody tr')
    has_data = False
    for i in range(rows.count()):
        cell = rows.nth(i).locator(f'td:nth-child({col_idx+1})')
        if cell.inner_text().strip():
            has_data = True
            break
    if not has_data:
        pytest.skip("Нет данных для теста.")

    # Шаг 2: Открываем меню фильтров
    filter_button = page.locator('button.cdm-icon-button__toolbar-primary span[title="Фильтр"]')
    filter_button.locator('xpath=ancestor::button').click()
    # Новый уникальный поиск меню фильтров (без userbar__menu)
    filter_menu = page.locator('.MuiMenu-paper:has(ul.MuiMenu-list[role="menu"]:not(.userbar__menu))')
    # Шаг 3: Ждём появления меню фильтра
    try:
        filter_menu.wait_for(state="visible", timeout=2000)
    except Exception:
        fail_with_screenshot(f"Меню фильтра по '{filter_name}' не появилось", page)

    # Шаг 4: Кликаем по фильтру с нужным названием
    filter_item = filter_menu.locator('li.MuiMenuItem-root[role="menuitem"]').filter(has_text=filter_name)
    try:
        filter_item.wait_for(state="visible", timeout=2000)
    except Exception:
        fail_with_screenshot(f"Пункт '{filter_name}' не найден в меню фильтра", page)
    filter_item.click()
    page.wait_for_timeout(500)

    try:
        # Шаг 5: Ждём появления блока фильтра
        filter_block = page.locator('.cdm-list-filter__filter-item')
        try:
            filter_block.wait_for(state="visible", timeout=2000)
        except Exception:
            fail_with_screenshot(f"Блок фильтра по '{filter_name}' не появился", page)
        select_label = filter_block.locator('label').filter(has_text=filter_name)
        try:
            select_label.wait_for(state="visible", timeout=2000)
        except Exception:
            fail_with_screenshot(f"Лейбл '{filter_name}' не найден в блоке фильтра", page)

        # Шаг 6: Открываем select и выбираем нужное значение
        select_btn = filter_block.locator('.MuiSelect-root')
        select_btn.click()
        menu = page.locator('.MuiMenu-paper', has_text=severity_text)
        try:
            menu.wait_for(state="visible", timeout=2000)
        except Exception:
            fail_with_screenshot(f"Меню выбора значения '{severity_text}' не появилось", page)
        menu.locator(f'li:has-text("{severity_text}")').click(force=True)
        page.wait_for_timeout(500)

        # Шаг 7: Ждём появления строк или сообщения о пустой таблице
        page.wait_for_selector('tbody tr, .cdm-data-grid__empty-message', timeout=2000, state='visible')
        rows = page.locator('tbody tr')
        if rows.count() == 0:
            # Нет данных с выбранным значением
            # Удаляем фильтр и skip
            delete_icon = filter_block.locator('span[title="Удалить"]')
            if delete_icon.is_visible():
                delete_icon.click(force=True)
            try:
                filter_block.wait_for(state="hidden", timeout=2000)
            except Exception:
                fail_with_screenshot("Блок фильтра не исчез после удаления", page)
            page.wait_for_timeout(500)
            pytest.skip(f"Нет данных с фильтром '{filter_name}' и значением '{severity_text}' для проверки.")

        # Шаг 8: Определяем индекс колонки по названию фильтра
        ths = page.locator('thead tr th')
        header_texts = []
        for i in range(ths.count()):
            th = ths.nth(i)
            try:
                text = th.locator('span span').first.inner_text(timeout=2000)
            except Exception:
                try:
                    text = th.locator('span').first.inner_text(timeout=2000)
                except Exception:
                    text = ""
            header_texts.append(text.strip())
        try:
            severity_col_idx = [h.lower() for h in header_texts].index(filter_name.lower())
        except ValueError:
            fail_with_screenshot(f"Колонка '{filter_name}' не найдена в таблице. Заголовки: {header_texts}", page)

        # Шаг 9: Проверяем, что в каждой строке таблицы значение совпадает с выбранным
        for i in range(rows.count()):
            cell = rows.nth(i).locator(f'td:nth-child({severity_col_idx+1})')
            cell_text = cell.inner_text().strip()
            if cell_text != severity_text:
                fail_with_screenshot(f"В таблице после фильтрации по '{filter_name}={severity_text}' найдена строка с '{cell_text}' (строка {i+1})", page)
    except Exception as e:
        print(f"Ошибка при проверке фильтра '{filter_name}' по значению '{severity_text}': {e}")
        raise
    # Шаг 10: Удаляем фильтр
    finally:
        delete_icon = filter_block.locator('span[title="Удалить"]')
        if delete_icon.is_visible():
            delete_icon.click(force=True)
        try:
            filter_block.wait_for(state="hidden", timeout=2000)
        except Exception:
            fail_with_screenshot("Блок фильтра не исчез после удаления", page)
        page.wait_for_timeout(500)

def check_filter_by_input(page, filter_name, severity_text, endpoint_substring="/api/service/remote/logger-analytics/analytics-server/call"):
    """
    Универсальный тест input-фильтра:
    1. Открывает меню фильтрации, выбирает нужный фильтр, вводит значение, ждёт GET-запрос по endpoint_substring.
    2. Проверяет, что после фильтрации в таблице остались только строки, содержащие это значение в нужной колонке (частичное совпадение).
    Параметры:
        page: объект Playwright Page
        filter_name: название фильтра и колонки (например, 'Сервис')
        severity_text: значение для фильтрации
        endpoint_substring: подстрока эндпоинта для ожидания GET-запроса (по умолчанию старый эндпоинт)
    """
    skip_if_no_data(page)
    # Шаг №0: Определяем индекс колонки по названию фильтра
    ths = page.locator('thead tr th')
    header_texts = []
    for i in range(ths.count()):
        th = ths.nth(i)
        try:
            text = th.locator('span span').first.inner_text(timeout=2000)
        except Exception:
            try:
                text = th.locator('span').first.inner_text(timeout=2000)
            except Exception:
                text = ""
        header_texts.append(text.strip())
    try:
        col_idx = [h.lower() for h in header_texts].index(filter_name.lower())
    except ValueError:
        fail_with_screenshot(f"Колонка '{filter_name}' не найдена в таблице. Заголовки: {header_texts}", page)

    # Шаг №2: Проверяем наличие данных в этой колонке (хотя бы одна непустая ячейка)
    rows = page.locator('tbody tr')
    has_data = False
    for i in range(rows.count()):
        cell = rows.nth(i).locator(f'td:nth-child({col_idx+1})')
        if cell.inner_text().strip():
            has_data = True
            break
    if not has_data:
        pytest.skip("Нет данных для теста.")

    # Шаг 2: Открываем меню фильтров
    filter_button = page.locator('button.cdm-icon-button__toolbar-primary span[title="Фильтр"]')
    filter_button.locator('xpath=ancestor::button').click()
    # Новый уникальный поиск меню фильтров (без userbar__menu)
    filter_menu = page.locator('.MuiMenu-paper:has(ul.MuiMenu-list[role="menu"]:not(.userbar__menu))')
    # Шаг 3: Ждём появления меню фильтра
    try:
        filter_menu.wait_for(state="visible", timeout=2000)
    except Exception:
        fail_with_screenshot(f"Меню фильтра по '{filter_name}' не появилось", page)

    # Шаг 4: Кликаем по фильтру с нужным названием
    filter_item = filter_menu.locator('li.MuiMenuItem-root[role="menuitem"]').filter(has_text=filter_name)
    try:
        filter_item.wait_for(state="visible", timeout=2000)
    except Exception:
        fail_with_screenshot(f"Пункт '{filter_name}' не найден в меню фильтра", page)
    filter_item.click()
    page.wait_for_timeout(500)

    try:
        # Шаг 5: Ждём появления блока фильтра с input
        filter_block = page.locator('.cdm-list-filter__filter-item')
        try:
            filter_block.wait_for(state="visible", timeout=2000)
        except Exception:
            fail_with_screenshot(f"Блок фильтра по '{filter_name}' не появился", page)
        select_label = filter_block.locator('label').filter(has_text=filter_name)
        try:
            select_label.wait_for(state="visible", timeout=2000)
        except Exception:
            fail_with_screenshot(f"Лейбл '{filter_name}' не найден в блоке фильтра", page)

        # Шаг 6: Находим input и вводим значение
        input_field = filter_block.locator('input[type="text"]')
        try:
            input_field.wait_for(state="visible", timeout=2000)
        except Exception:
            fail_with_screenshot(f"Input для фильтра '{filter_name}' не найден", page)

        # Шаг 7: Вводим текст и ждём ответ на запрос к API
        with page.expect_response(lambda resp: resp.request.method == "GET" and endpoint_substring in resp.url) as resp_info:
            input_field.fill(severity_text)
        response = resp_info.value
        # Проверяем код ответа и что ответ НЕ пустой
        if response.status not in (200, 304):
            fail_with_screenshot(f"API ответил кодом {response.status}, ожидалось 200 или 304", page)
        try:
            json_data = response.json()
        except Exception:
            json_data = None
        # Проверяем, что ответ не пустой
        if json_data in (None, [], {}):
            fail_with_screenshot(f"Ожидался НЕ пустой response, получено: {json_data}", page)

        page.wait_for_timeout(500)

        # Шаг 8: Ждём появления строк или сообщения о пустой таблице
        page.wait_for_selector('tbody tr, .cdm-data-grid__empty-message', timeout=2000, state='visible')
        rows = page.locator('tbody tr')
        if rows.count() == 0:
            pytest.skip(f"Нет данных с фильтром '{filter_name}' и значением '{severity_text}' для проверки.")

        # Шаг 9: Определяем индекс колонки по названию фильтра
        ths = page.locator('thead tr th')
        header_texts = []
        for i in range(ths.count()):
            th = ths.nth(i)
            try:
                text = th.locator('span span').first.inner_text(timeout=2000)
            except Exception:
                try:
                    text = th.locator('span').first.inner_text(timeout=2000)
                except Exception:
                    text = ""
            header_texts.append(text.strip())
        try:
            filter_col_idx = [h.lower() for h in header_texts].index(filter_name.lower())
        except ValueError:
            fail_with_screenshot(f"Колонка '{filter_name}' не найдена в таблице. Заголовки: {header_texts}", page)

        # Шаг 10: Проверяем, что в каждой строке таблицы значение содержит введённое
        for i in range(rows.count()):
            cell = rows.nth(i).locator(f'td:nth-child({filter_col_idx+1})')
            cell_text = cell.inner_text().strip()
            if severity_text.lower() not in cell_text.lower():
                fail_with_screenshot(f"В строке {i+1} ожидалось, что '{cell_text}' содержит '{severity_text}'", page)
    except Exception as e:
        print(f"Ошибка при проверке фильтра '{filter_name}' по значению '{severity_text}': {e}")
        raise
    finally:
        # Шаг 11: Удаляем фильтр
        delete_icon = filter_block.locator('span[title="Удалить"]')
        if delete_icon.is_visible():
            delete_icon.click(force=True)
        try:
            filter_block.wait_for(state="hidden", timeout=2000)
        except Exception:
            fail_with_screenshot("Блок фильтра не исчез после удаления", page)
        page.wait_for_timeout(500) 

def check_filter_by_input_negative_other_values(page, filter_name, severity_text, endpoint_substring="/api/service/remote/logger-analytics/analytics-server/call"):
    """
    Универсальный тест негативной input-фильтрации:
    1. Открывает меню фильтрации, выбирает нужный фильтр, вводит значение, ждёт GET-запрос по endpoint_substring.
    2. Проверяет, что после фильтрации в таблице нет строк с этим значением (или таблица пуста).
    Параметры:
        page: объект Playwright Page
        filter_name: название фильтра и колонки (например, 'Сервис')
        severity_text: значение для фильтрации
        endpoint_substring: подстрока эндпоинта для ожидания GET-запроса (по умолчанию старый эндпоинт)
    """
    skip_if_no_data(page)
    # Шаг №0: Определяем индекс колонки по названию фильтра
    ths = page.locator('thead tr th')
    header_texts = []
    for i in range(ths.count()):
        th = ths.nth(i)
        try:
            text = th.locator('span span').first.inner_text(timeout=2000)
        except Exception:
            try:
                text = th.locator('span').first.inner_text(timeout=2000)
            except Exception:
                text = ""
        header_texts.append(text.strip())
    try:
        col_idx = [h.lower() for h in header_texts].index(filter_name.lower())
    except ValueError:
        fail_with_screenshot(f"Колонка '{filter_name}' не найдена в таблице. Заголовки: {header_texts}", page)

    # Шаг №2: Проверяем наличие данных в этой колонке (хотя бы одна непустая ячейка)
    rows = page.locator('tbody tr')
    has_data = False
    for i in range(rows.count()):
        cell = rows.nth(i).locator(f'td:nth-child({col_idx+1})')
        if cell.inner_text().strip():
            has_data = True
            break
    if not has_data:
        pytest.skip("Нет данных для теста.")

    # Шаг 2: Открываем меню фильтров
    filter_button = page.locator('button.cdm-icon-button__toolbar-primary span[title="Фильтр"]')
    filter_button.locator('xpath=ancestor::button').click()
    # Новый уникальный поиск меню фильтров (без userbar__menu)
    filter_menu = page.locator('.MuiMenu-paper:has(ul.MuiMenu-list[role="menu"]:not(.userbar__menu))')
    # Шаг 3: Ждём появления меню фильтра
    try:
        filter_menu.wait_for(state="visible", timeout=2000)
    except Exception:
        fail_with_screenshot(f"Меню фильтра по '{filter_name}' не появилось", page)

    # Шаг 4: Кликаем по фильтру с нужным названием
    filter_item = filter_menu.locator('li.MuiMenuItem-root[role="menuitem"]').filter(has_text=filter_name)
    try:
        filter_item.wait_for(state="visible", timeout=2000)
    except Exception:
        fail_with_screenshot(f"Пункт '{filter_name}' не найден в меню фильтра", page)
    filter_item.click()
    page.wait_for_timeout(500)

    try:
        # Шаг 5: Ждём появления блока фильтра с input
        filter_block = page.locator('.cdm-list-filter__filter-item')
        try:
            filter_block.wait_for(state="visible", timeout=2000)
        except Exception:
            fail_with_screenshot(f"Блок фильтра по '{filter_name}' не появился", page)
        select_label = filter_block.locator('label').filter(has_text=filter_name)
        try:
            select_label.wait_for(state="visible", timeout=2000)
        except Exception:
            fail_with_screenshot(f"Лейбл '{filter_name}' не найден в блоке фильтра", page)

        # Шаг 6: Находим input поле
        input_field = filter_block.locator('input[type="text"]')
        try:
            input_field.wait_for(state="visible", timeout=2000)
        except Exception:
            fail_with_screenshot(f"Input для фильтра '{filter_name}' не найден", page)

        # Шаг 7: Вводим текст и ждём ответ на запрос к API
        endpoint_base = endpoint_substring
        if endpoint_substring == "/api/service/remote/logger-analytics/analytics-server/call":
            query_param = "filter="
        else:
            query_param = ""
        with page.expect_response(
            lambda resp: (
                resp.request.method == "GET"
                and endpoint_base in resp.url
                and query_param in resp.url
            )
        ) as resp_info:
            input_field.fill(severity_text)
        response = resp_info.value
        
        # Проверяем код ответа и пустой response
        if response.status not in (200, 304):
            fail_with_screenshot(f"API ответил кодом {response.status}, ожидалось 200 или 304", page)
        try:
            json_data = response.json()
        except Exception:
            json_data = None
        # Пустым считаем None, [], или {}
        if json_data not in (None, [], {}):
            fail_with_screenshot("Ожидался пустой response, однако", page)

        # Шаг 8: Проверяем, что таблица пуста и есть сообщение 'Нет данных'
        page.wait_for_selector('tbody tr, .cdm-data-grid__empty-message', timeout=2000, state='visible')
        rows = page.locator('tbody tr')
        empty_message = page.locator('.cdm-data-grid__empty-message')
        if rows.count() > 0:
            fail_with_screenshot(f"После фильтрации по невалидному значению '{severity_text}' таблица не пуста!", page)
        if not empty_message.is_visible():
            fail_with_screenshot("Сообщение 'Нет данных' не появилось при невалидном фильтре", page)
    except Exception as e:
        print(f"Ошибка при негативной проверке фильтра '{filter_name}' по невалидному значению '{severity_text}': {e}")
        raise
    finally:
        # Шаг 9: Удаляем фильтр
        delete_btn = filter_block.locator('button:has(span[title="Удалить"])')
        if delete_btn.is_visible():
            delete_btn.click(force=True)
        try:
            filter_block.wait_for(state="hidden", timeout=4000)  # увеличил таймаут
        except Exception:
            fail_with_screenshot("Блок фильтра не исчез после удаления", page)
        page.wait_for_timeout(500)

def check_filter_by_input_first_row_value(page, filter_name, endpoint_substring="/api/service/remote/logger-analytics/analytics-server/call"):
    """
    Универсальный тест input-фильтра:
    1. Берёт значение из первой строки колонки с именем filter_name.
    2. Применяет input-фильтр по этому значению, ждёт GET-запрос по endpoint_substring.
    3. Проверяет, что после фильтрации в таблице остались только строки, содержащие это значение в нужной колонке (частичное совпадение).
    Параметры:
        page: объект Playwright Page
        filter_name: название фильтра и колонки (например, 'Сервис')
        endpoint_substring: подстрока эндпоинта для ожидания GET-запроса (по умолчанию старый эндпоинт)
    """
    skip_if_no_data(page)
    column_name = filter_name
    # Шаг №0: Определяем индекс колонки по названию фильтра
    ths = page.locator('thead tr th')
    header_texts = []
    for i in range(ths.count()):
        th = ths.nth(i)
        try:
            text = th.locator('span span').first.inner_text(timeout=2000)
        except Exception:
            try:
                text = th.locator('span').first.inner_text(timeout=2000)
            except Exception:
                text = ""
        header_texts.append(text.strip())
    try:
        col_idx = [h.lower() for h in header_texts].index(filter_name.lower())
    except ValueError:
        fail_with_screenshot(f"Колонка '{filter_name}' не найдена в таблице. Заголовки: {header_texts}", page)

    # Шаг №2: Проверяем наличие данных в этой колонке (хотя бы одна непустая ячейка)
    rows = page.locator('tbody tr')
    has_data = False
    for i in range(rows.count()):
        cell = rows.nth(i).locator(f'td:nth-child({col_idx+1})')
        if cell.inner_text().strip():
            has_data = True
            break
    if not has_data:
        pytest.skip("Нет данных для теста.")

    # Шаг 2: Определяем индекс колонки по названию
    ths = page.locator('thead tr th')
    header_texts = []
    for i in range(ths.count()):
        th = ths.nth(i)
        try:
            text = th.locator('span span').first.inner_text(timeout=2000)
        except Exception:
            try:
                text = th.locator('span').first.inner_text(timeout=2000)
            except Exception:
                text = ""
        header_texts.append(text.strip())
    try:
        col_idx = [h.lower() for h in header_texts].index(column_name.lower())
    except ValueError:
        fail_with_screenshot(f"Колонка '{column_name}' не найдена в таблице. Заголовки: {header_texts}", page)

    # Шаг 3: Берём значение из первой строки этой колонки
    first_row = page.locator('tbody tr').first
    if not first_row.is_visible():
        pytest.skip("Нет строк в таблице для теста.")
    cell = first_row.locator(f'td:nth-child({col_idx+1})')
    value = cell.inner_text().strip()
    if not value:
        pytest.skip(f"В первой строке колонки '{column_name}' нет значения для фильтрации.")

    # Шаг 4: Вызываем универсальную функцию фильтрации по input
    check_filter_by_input(page, filter_name, value, endpoint_substring=endpoint_substring)