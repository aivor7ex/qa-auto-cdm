import pytest
from playwright.sync_api import expect, Page
from datetime import datetime
from typing import Callable, List, Any
from UI.conftest import fail_with_screenshot


"""------------------------------Сортировка по дате--------------------------------------- """

def check_sorting_by_date_column(page: Page, column_name: str, endpoint_substring: str):
    """
    Проверяет сортировку по дате в колонке. Ожидает API-запрос, кликает по колонке, проверяет сортировку.
    """
    # Шаг 1: Ожидаем загрузки данных и проверяем, что есть данные для теста
    try:
        page.wait_for_selector('tbody tr, .cdm-data-grid__empty-message', timeout=10000, state='visible')
    except Exception:
        pytest.skip("Таблица не загрузилась за отведённое время")
    
    rows = page.locator('tbody tr')
    if not rows.count():
        pytest.skip("Нет данных для теста.")

    # Шаг 2: Получаем индекс колонки
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

    # Шаг 3: Ожидаем API-запрос и кликаем по колонке
    sort_button = ths.nth(col_idx).locator('span[role="button"]')
    sort_button.scroll_into_view_if_needed()
    sort_button.hover()
    page.wait_for_timeout(300)
    with page.expect_response(lambda resp: resp.request.method == "GET", timeout=10000) as resp_info:
        sort_button.click(force=True)
    response = resp_info.value
    if not response.status in (200, 304):
        fail_with_screenshot(f"API ответил кодом {response.status}, ожидалось 200 или 304", page)

    # Шаг 4: Получаем значения из body
    rows = page.locator('tbody tr')
    values = []
    for i in range(rows.count()):
        cell = rows.nth(i).locator(f'td:nth-child({col_idx+1})')
        cell_text = cell.inner_text().strip()
        values.append(cell_text)

    # Шаг 5: Проверяем сортировку по возрастанию (после клика)
    def try_parse_datetime(s: str):
        for fmt in ("%d.%m.%Y %H:%M:%S", "%d.%m.%Y %H:%M"):
            try:
                return datetime.strptime(s, fmt)
            except Exception:
                continue
        return None
    parsed = [try_parse_datetime(v) for v in values]
    if not parsed == sorted(parsed):
        # Найти первую нарушающую пару
        context_msg = ""
        for i in range(len(parsed) - 1):
            if parsed[i] is not None and parsed[i+1] is not None and parsed[i] > parsed[i+1]:
                start = max(0, i - 5)
                end = min(len(values), i + 7)
                context_msg += f"\n--- Нарушение сортировки по возрастанию! ---\n"
                context_msg += f"Позиция: {i} и {i+1}\n"
                context_msg += f"Значения: {values[i]} > {values[i+1]}\n"
                context_msg += "Контекст (5 до и 5 после):\n"
                for idx in range(start, end):
                    mark = " <--" if idx == i or idx == i+1 else ""
                    context_msg += f"{idx}: {values[idx]}{mark}\n"
                context_msg += "--- Конец вывода ---\n"
                break
        fail_with_screenshot(f"Ожидалось, что значения в колонке '{column_name}' отсортированы по возрастанию (дата). {context_msg}", page)

def check_sorting_by_date_column_desc(page: Page, column_name: str, endpoint_substring: str):
    """
    Проверяет сортировку по дате в колонке по убыванию. Ожидает API-запрос, кликает по колонке, проверяет сортировку.
    Предполагается, что функция вызывается после сортировки по возрастанию.
    После проверки повторно кликает по колонке (3-е состояние), без ожидания API и без проверки.
    """
    try:
        # Шаг 1: Ожидаем загрузки данных и проверяем, что есть данные для теста
        try:
            page.wait_for_selector('tbody tr, .cdm-data-grid__empty-message', timeout=10000, state='visible')
        except Exception:
            pytest.skip("Таблица не загрузилась за отведённое время")
        
        rows = page.locator('tbody tr')
        if not rows.count():
            pytest.skip("Нет данных для теста.")

        # Шаг 2: Получаем индекс колонки
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

        # Шаг 3: Ожидаем API-запрос и кликаем по колонке
        sort_button = ths.nth(col_idx).locator('span[role="button"]')
        sort_button.scroll_into_view_if_needed()
        sort_button.hover()
        page.wait_for_timeout(300)
        with page.expect_response(lambda resp: resp.request.method == "GET", timeout=10000) as resp_info:
            sort_button.click(force=True)
        response = resp_info.value
        if not response.status in (200, 304):
            fail_with_screenshot(f"API ответил кодом {response.status}, ожидалось 200 или 304", page)

        # Шаг 4: Получаем значения из body
        rows = page.locator('tbody tr')
        values = []
        for i in range(rows.count()):
            cell = rows.nth(i).locator(f'td:nth-child({col_idx+1})')
            cell_text = cell.inner_text().strip()
            values.append(cell_text)

        # Шаг 5: Проверяем сортировку по убыванию (после второго клика)
        def try_parse_datetime(s: str):
            for fmt in ("%d.%m.%Y %H:%M:%S", "%d.%m.%Y %H:%M"):
                try:
                    return datetime.strptime(s, fmt)
                except Exception:
                    continue
            return None
        parsed = [try_parse_datetime(v) for v in values]
        if not parsed == sorted(parsed, reverse=True):
            # Найти первую нарушающую пару
            context_msg = ""
            for i in range(len(parsed) - 1):
                if parsed[i] is not None and parsed[i+1] is not None and parsed[i] < parsed[i+1]:
                    start = max(0, i - 5)
                    end = min(len(values), i + 7)
                    context_msg += f"\n--- Нарушение сортировки по убыванию! ---\n"
                    context_msg += f"Позиция: {i} и {i+1}\n"
                    context_msg += f"Значения: {values[i]} < {values[i+1]}\n"
                    context_msg += "Контекст (5 до и 5 после):\n"
                    for idx in range(start, end):
                        mark = " <--" if idx == i or idx == i+1 else ""
                        context_msg += f"{idx}: {values[idx]}{mark}\n"
                    context_msg += "--- Конец вывода ---\n"
                    break
            fail_with_screenshot(f"Ожидалось, что значения в колонке '{column_name}' отсортированы по убыванию (дата). {context_msg}", page)
    finally:
        # Просто кликаем по sort-кнопке (3-е состояние)
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
            return
        sort_button = ths.nth(col_idx).locator('span[role="button"]')
        sort_button.scroll_into_view_if_needed()
        sort_button.hover()
        sort_button.click(force=True)


"""------------------------------Сортировка по числам--------------------------------------- """


def check_sorting_by_number_column(page: Page, column_name: str, endpoint_substring: str):
    """
    Проверяет сортировку по числу в колонке. Ожидает API-запрос, кликает по колонке, проверяет сортировку.
    """
    # Шаг 1: Ожидаем загрузки данных и проверяем, что есть данные для теста
    try:
        page.wait_for_selector('tbody tr, .cdm-data-grid__empty-message', timeout=10000, state='visible')
    except Exception:
        pytest.skip("Таблица не загрузилась за отведённое время")
    
    rows = page.locator('tbody tr')
    if not rows.count():
        pytest.skip("Нет данных для теста.")

    # Шаг 2: Получаем индекс колонки
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

    # Шаг 3: Ожидаем API-запрос и кликаем по колонке
    sort_button = ths.nth(col_idx).locator('span[role="button"]')
    sort_button.scroll_into_view_if_needed()
    sort_button.hover()
    page.wait_for_timeout(300)
    with page.expect_response(lambda resp: resp.request.method == "GET", timeout=10000) as resp_info:
        sort_button.click(force=True)
    response = resp_info.value
    if not response.status in (200, 304):
        fail_with_screenshot(f"API ответил кодом {response.status}, ожидалось 200 или 304", page)

    # Шаг 4: Получаем значения из body
    rows = page.locator('tbody tr')
    values = []
    for i in range(rows.count()):
        cell = rows.nth(i).locator(f'td:nth-child({col_idx+1})')
        cell_text = cell.inner_text().strip()
        values.append(cell_text)

    # Шаг 5: Парсим числа, IP, дроби
    def try_parse_number(s: str):
        try:
            # IP-адрес: разбиваем на кортеж чисел
            if all(part.isdigit() for part in s.split('.')) and s.count('.') == 3:
                return tuple(int(part) for part in s.split('.'))
            # Дробь вида 4/4 — берём первое число
            if '/' in s:
                s = s.split('/')[0]
            return float(s.replace(' ', '').replace(',', '.'))
        except Exception:
            return s  # если не число — оставляем строкой
    parsed = [try_parse_number(v) for v in values]
    if not parsed == sorted(parsed):
        fail_with_screenshot(f"Ожидалось, что значения в колонке '{column_name}' отсортированы по возрастанию (числа/IP): {values}", page)

def check_sorting_by_number_column_desc(page: Page, column_name: str, endpoint_substring: str):
    """
    Проверяет сортировку по числам (в том числе IP, дроби) в колонке по убыванию. Ожидает API-запрос, кликает по колонке, проверяет сортировку.
    Предполагается, что функция вызывается после сортировки по возрастанию.
    После проверки повторно кликает по колонке (3-е состояние), без ожидания API и без проверки.
    """
    try:
        # Шаг 1: Ожидаем загрузки данных и проверяем, что есть данные для теста
        try:
            page.wait_for_selector('tbody tr, .cdm-data-grid__empty-message', timeout=10000, state='visible')
        except Exception:
            pytest.skip("Таблица не загрузилась за отведённое время")
        
        rows = page.locator('tbody tr')
        if not rows.count():
            pytest.skip("Нет данных для теста.")

        # Шаг 2: Получаем индекс колонки
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
        # Шаг 3: Ожидаем API-запрос и кликаем по колонке
        sort_button = ths.nth(col_idx).locator('span[role="button"]')
        sort_button.scroll_into_view_if_needed()
        sort_button.hover()
        page.wait_for_timeout(300)
        with page.expect_response(lambda resp: resp.request.method == "GET", timeout=10000) as resp_info:
            sort_button.click(force=True)
        response = resp_info.value
        if not response.status in (200, 304):
            fail_with_screenshot(f"API ответил кодом {response.status}, ожидалось 200 или 304", page)

        # Шаг 4: Получаем значения из body
        rows = page.locator('tbody tr')
        values = []
        for i in range(rows.count()):
            cell = rows.nth(i).locator(f'td:nth-child({col_idx+1})')
            cell_text = cell.inner_text().strip()
            values.append(cell_text)

        # Шаг 5: Парсим числа, IP, дроби
        def try_parse_number(s: str):
            try:
                if all(part.isdigit() for part in s.split('.')) and s.count('.') == 3:
                    return tuple(int(part) for part in s.split('.'))
                if '/' in s:
                    s = s.split('/')[0]
                return float(s.replace(' ', '').replace(',', '.'))
            except Exception:
                return s
        parsed = [try_parse_number(v) for v in values]
        if not parsed == sorted(parsed, reverse=True):
            fail_with_screenshot(f"Ожидалось, что значения в колонке '{column_name}' отсортированы по убыванию (числа/IP): {values}", page)
    finally:
        # Просто кликаем по колонке (3-е состояние)
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
            return
        sort_button = ths.nth(col_idx).locator('span[role="button"]')
        sort_button.scroll_into_view_if_needed()
        sort_button.hover()
        sort_button.click(force=True)


"""------------------------------Сортировка по тексту--------------------------------------- """


def check_sorting_by_text_column(page: Page, column_name: str, endpoint_substring: str):
    """
    Проверяет сортировку по тексту в колонке. Ожидает API-запрос, кликает по колонке, проверяет сортировку по стандарту Python (Unicode).
    """
    # Шаг 1: Ожидаем загрузки данных и проверяем, что есть данные для теста
    try:
        page.wait_for_selector('tbody tr, .cdm-data-grid__empty-message', timeout=10000, state='visible')
    except Exception:
        pytest.skip("Таблица не загрузилась за отведённое время")
    
    rows = page.locator('tbody tr')
    if not rows.count():
        pytest.skip("Нет данных для теста.")

    # Шаг 2: Получаем индекс колонки
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

    # Шаг 3: Ожидаем API-запрос и кликаем по колонке
    sort_button = ths.nth(col_idx).locator('span[role="button"]')
    sort_button.scroll_into_view_if_needed()
    sort_button.hover()
    page.wait_for_timeout(300)
    with page.expect_response(lambda resp: resp.request.method == "GET", timeout=10000) as resp_info:
        sort_button.click(force=True)
    response = resp_info.value
    if not response.status in (200, 304):
        fail_with_screenshot(f"API ответил кодом {response.status}, ожидалось 200 или 304", page)

    # Шаг 4: Получаем значения из body
    rows = page.locator('tbody tr')
    values = []
    for i in range(rows.count()):
        cell = rows.nth(i).locator(f'td:nth-child({col_idx+1})')
        cell_text = cell.inner_text().strip()
        values.append(cell_text)

    # Шаг 5: Проверяем сортировку по возрастанию (стандарт Python)
    if values != sorted(values):
        # print("Отсортированные значения: ", values)
        # print("Проверочные значения: ", sorted(values))
        fail_with_screenshot(f"Ожидалось, что значения в колонке '{column_name}' отсортированы по возрастанию (Python)", page)


def check_sorting_by_text_column_desc(page: Page, column_name: str, endpoint_substring: str):
    """
    Проверяет сортировку по тексту в колонке по убыванию. Ожидает API-запрос, кликает по колонке, проверяет сортировку по стандарту Python (Unicode).
    Предполагается, что функция вызывается после сортировки по возрастанию.
    После проверки повторно кликает по колонке (3-е состояние), без ожидания API и без проверки.
    """
    try:
        # Шаг 1: Ожидаем загрузки данных и проверяем, что есть данные для теста
        try:
            page.wait_for_selector('tbody tr, .cdm-data-grid__empty-message', timeout=10000, state='visible')
        except Exception:
            pytest.skip("Таблица не загрузилась за отведённое время")
        
        rows = page.locator('tbody tr')
        if not rows.count():
            pytest.skip("Нет данных для теста.")

        # Шаг 2: Получаем индекс колонки
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
        # Шаг 3: Ожидаем API-запрос и кликаем по колонке (ещё раз)
        sort_button = ths.nth(col_idx).locator('span[role="button"]')
        sort_button.scroll_into_view_if_needed()
        sort_button.hover()
        page.wait_for_timeout(300)
        with page.expect_response(lambda resp: resp.request.method == "GET", timeout=10000) as resp_info:
            sort_button.click(force=True)
        response = resp_info.value
        if not response.status in (200, 304):
            fail_with_screenshot(f"API ответил кодом {response.status}, ожидалось 200 или 304", page)

        # Шаг 4: Получаем значения из body
        rows = page.locator('tbody tr')
        values = []
        for i in range(rows.count()):
            cell = rows.nth(i).locator(f'td:nth-child({col_idx+1})')
            cell_text = cell.inner_text().strip()
            values.append(cell_text)

        # Шаг 5: Проверяем сортировку по убыванию (стандарт Python)
        if not values == sorted(values, reverse=True):
            fail_with_screenshot(f"Ожидалось, что значения в колонке '{column_name}' отсортированы по убыванию (Python)", page) 
        # print("Отсортированные значения: ", values) # для отладки
        # print("Проверочные значения: ", sorted(values, reverse=True))
    finally:
        # Просто кликаем по колонке (3-е состояние)
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
            return
        sort_button = ths.nth(col_idx).locator('span[role="button"]')
        sort_button.scroll_into_view_if_needed()
        sort_button.hover()
        sort_button.click(force=True) 