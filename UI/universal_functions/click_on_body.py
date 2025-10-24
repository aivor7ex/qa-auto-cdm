from playwright.sync_api import Page
import pytest
from UI.conftest import fail_with_screenshot
from contextlib import contextmanager
import re

def _norm(s: str) -> str:
    """
    Нормализует текст из ячейки:
    - убирает все переводы строк и табы
    - сводит множественные пробелы к одному
    - удаляет пробелы после/перед запятыми
    - приводит к однородному виду "10.0.0.1-10.0.0.3,10.0.0.10"
    """

    if not s:
        return ""

    s = s.replace("\n", " ").replace("\r", " ").replace("\t", " ")
    s = re.sub(r"\s+", " ", s)                # схлопываем все множественные пробелы
    s = re.sub(r"\s*,\s*", ",", s)            # убираем пробелы вокруг запятых
    s = s.strip()
    return s


def click_info_and_check_modal(page: Page, row_index: int = 0):
	"""
	Кликает по иконке информации в строке таблицы, проверяет появление модального окна с текстом "Описание события",
	затем закрывает модалку по крестику (закрытие всегда в finally).
	:param page: Playwright Page
	:param row_index: индекс строки (по умолчанию 0 — первая строка)
	"""
	# Шаг 1: Кликаем по иконке информации в нужной строке
	rows = page.locator('tbody tr')
	row = rows.nth(row_index)
	# Кнопка с иконкой информации: ищем по вложенному span[title="Информация"]
	info_button = row.locator('button:has(span[title="Информация"])')
	info_button.wait_for(state="visible", timeout=3000)
	info_button.scroll_into_view_if_needed()
	info_button.hover()
	try:
		info_button.click(force=True)
		# Шаг 2: Проверяем появление модального окна с текстом "Описание события"
		modal = page.locator('div.MuiPaper-root.cdm-card._without-margin:has(span.MuiCardHeader-title:text("Описание события"))')
		modal.wait_for(state="visible", timeout=2000)
	
		# Проверяем заголовок только внутри модального окна
		header = modal.locator('span.MuiCardHeader-title')
		if header.inner_text(timeout=2000).strip() != "Описание события":
			fail_with_screenshot("В модальном окне не найден заголовок 'Описание события'", page)
	# Шаг 3: Закрываем модалку по крестику
	finally:
		close_btn = modal.locator('button:has(span[title="Закрыть"])')
		close_btn.wait_for(state="visible", timeout=2000)
		close_btn.scroll_into_view_if_needed()
		close_btn.hover()
		close_btn.click(force=True)

# Универсальная функция: наведение на иконку "?" в заголовке колонки и проверка текста тултипа
def hover_column_help_icon_and_assert_title(page: Page, column_name: str, expected_tooltip: str, timeout: int = 5000) -> None:
	"""
	Наводит курсор на иконку подсказки ("?") внутри заголовка колонки с именем column_name и
	проверяет, что текст подсказки соответствует expected_tooltip. Проверка выполняется по атрибуту title,
	так как нативные браузерные тултипы не являются частью DOM.
	"""
	# Шаг №1: Ищем индекс нужной колонки по тексту заголовков
	ths = page.locator('thead tr th')
	header_texts = []
	for i in range(ths.count()):
		th = ths.nth(i)
		text = ""
		try:
			text = th.locator('span span').first.inner_text(timeout=1000)
		except Exception:
			try:
				text = th.locator('span').first.inner_text(timeout=1000)
			except Exception:
				text = ""
		header_texts.append(text.strip())
	try:
		col_idx = [h.lower() for h in header_texts].index(column_name.lower())
	except ValueError:
		fail_with_screenshot(f"Колонка '{column_name}' не найдена в таблице. Заголовки: {header_texts}", page)
		return

	# Шаг №2: Внутри найденного TH находим контейнер и иконку "?"
	target_th = ths.nth(col_idx)
	label_div = target_th.locator('div.cdm-data-grid__body__row__head-cell__label')
	if label_div.count() == 0:
		fail_with_screenshot(f"Контейнер заголовка для колонки '{column_name}' не найден", page)
		return

	# Пытаемся найти иконку по нескольким стратегиям
	icon = label_div.locator('svg[style*="cursor: pointer"]').first
	if icon.count() == 0:
		icon = label_div.locator('svg:not(.MuiTableSortLabel-icon)').last
	if icon.count() == 0:
		icon = label_div.locator('svg').last
	if icon.count() == 0:
		fail_with_screenshot(f"Иконка подсказки не найдена в заголовке колонки '{column_name}'", page)
		return

	icon.scroll_into_view_if_needed()
	icon.hover()

	# Шаг №3: Проверяем текст подсказки через атрибут title на контейнере/иконке
	title_attr = label_div.get_attribute("title")
	if title_attr is None:
		title_attr = icon.get_attribute("title")
	if title_attr is None:
		fail_with_screenshot("Атрибут title для тултипа не найден ни на контейнере, ни на иконке", page)
		return
	if expected_tooltip not in title_attr:
		fail_with_screenshot(f"Ожидали текст тултипа '{expected_tooltip}', получено: '{title_attr}'", page)
	# Успех — ничего не возвращаем

# Универсальная функция для удаления строки по значению первой колонки
def delete_row_by_first_cell(page: Page, first_cell_text: str | None, endpoint_contains: str):
    """Удаляет строку в таблице
    Args:
        page: объект Playwright Page.
        first_cell_text: текст первой ячейки. Если None — берётся первая строка.
        endpoint_contains: подстрока, которая должна содержаться в DELETE-запросе.
    """
    table = page.locator('table.cdm-data-grid')
    if not table.is_visible():
        fail_with_screenshot('Таблица не видна для удаления строки', page)
        return

    # Находим нужную строку
    target_row = None
    rows = table.locator('tbody tr')
    for i in range(rows.count()):
        row = rows.nth(i)
        cell_text = row.locator('td').nth(0).inner_text().strip()
        if first_cell_text is None and i == 0:
            target_row = row
            break
        if first_cell_text is not None and cell_text == first_cell_text:
            target_row = row
            break
    if target_row is None:
        fail_with_screenshot(f"Строка с текстом '{first_cell_text}' не найдена", page)
        return

    # Кнопка удаления
    delete_btn = target_row.locator('button:has(span[title="Удалить"])')
    delete_btn.wait_for(state="visible")

    # Ожидаем DELETE запрос и подтверждаем диалог
    with page.expect_response(lambda resp: resp.request.method == "DELETE" and endpoint_contains in resp.url) as resp_info:
        delete_btn.click()
        # В диалоге нажимаем кнопку "Удалить"
        confirm_btn = page.get_by_role("button", name="Удалить")
        confirm_btn.wait_for(state="visible")
        confirm_btn.click()
    response = resp_info.value
    if response.status != 200:
        fail_with_screenshot(f"DELETE запрос вернул статус {response.status}, ожидалось 200", page)

    # Проверяем, что строка исчезла
    if first_cell_text is None:
        target_row.wait_for(state="detached")
    else:
        hidden = table.locator('tbody tr', has_text=first_cell_text)
        hidden.wait_for(state="hidden")


@contextmanager
def wait_for_api_response(page: Page, endpoint_contains: str, expected_status: int = 200, method: str | None = None, timeout: int = 10000):
    """Контекст-менеджер ожидания ответа от API и проверки его статуса.

    Пример использования::

        with wait_for_api_response(page, "/security-report-cron-jobs/", 200, method="DELETE"):
            button.click()

    Args:
        page: Playwright Page.
        endpoint_contains: подстрока, которая должна присутствовать в URL запроса.
        expected_status: ожидаемый HTTP-код ответа (по умолчанию 200).
        method: HTTP-метод (GET/POST/DELETE/PUT/...) или None, чтобы игнорировать метод.
        timeout: тайм-аут ожидания ответа в мс (по умолчанию 10000).
    """
    with page.expect_response(
        lambda resp: endpoint_contains in resp.url and (method is None or resp.request.method.upper() == method.upper()),
        timeout=timeout,
    ) as resp_info:
        # передаём управление вызывающему коду (клик и т.д.)
        yield
    response = resp_info.value
    if response is None:
        print(f"No response received for endpoint '{endpoint_contains}'")
    else:
        try:
            print(f"Response body for '{endpoint_contains}': {response.text()}")
        except Exception as e:
            print(f"Could not read response body: {e}")
        print(f"Received response with status {response.status} for endpoint '{endpoint_contains}'")
    if response.status != expected_status:
        fail_with_screenshot(
            f"Ожидался статус {expected_status} для '{endpoint_contains}', получен {response.status}",
            page,
        )

@contextmanager
def wait_for_api_response_with_response(page: Page, endpoint_contains: str, expected_status: int = 200, method: str | None = None, timeout: int = 30000):
    """
    Контекст-менеджер: ждёт ответ от API и возвращает объект resp_info наружу для доступа к response.
    """
    with page.expect_response(
        lambda resp: endpoint_contains in resp.url and (method is None or resp.request.method.upper() == method.upper()),
        timeout=timeout,
    ) as resp_info:
        yield resp_info
    response = resp_info.value
    if response is not None:
        try:
            print(f"API RESPONSE: url={response.url}, method={response.request.method}, status={response.status}, body={response.text()}")
        except Exception as e:
            print(f"API RESPONSE: url={response.url}, method={response.request.method}, status={response.status}, body=<unreadable>: {e}")
    if response is None or response.status != expected_status:
        fail_with_screenshot(
            f"Ожидался статус {expected_status} для '{endpoint_contains}', получен {response.status if response else 'no response'}",
            page,
        )


def get_or_open_form_row(page: Page):
    """
    Возвращает открытую форм-строку таблицы (строку создания нового правила).
    Если форм-строки нет — нажимает кнопку «Создать» и дожидается её появления.
    После этого валидирует, что строка действительно редактируемая.

    Вход:
        page (Page): текущая страница Playwright, на которой отображается таблица
        (например, "Белые правила" или "Статические правила").

    Возвращает:
        Locator: локатор форм-строки (<tr class="cdm-data-grid__body__form-row">).

    Особенности и устойчивость:
        • Работает корректно даже в «пустом» состоянии списка, когда таблица ещё не смонтирована,
          а на странице отображается только сообщение «Нет данных».
        • Ищет кнопку «Создать» несколькими надёжными способами:
              – по ARIA-имени (get_by_role("button", name="Создать"))
              – по тексту (button:has-text("Создать"))
              – по .MuiButton-label → ancestor::button
          и делает повторную попытку после прокрутки вверх (на случай перекрытия тулбара).
        • После клика по «Создать» ждёт появления строки <tr.cdm-data-grid__body__form-row>
          без привязки к <table> (т.к. в пустом состоянии таблицы может ещё не быть).
        • Проверяет, что в найденной строке действительно есть:
              – кнопки «Сохранить» и «Отмена»
              – хотя бы одно редактируемое поле (<input> или <textarea>)
          Если условия не выполняются — делает скриншот и вызывает fail_with_screenshot.
        • Используется как вспомогательная функция для get_cell_by_header(...),
          когда create_row=True (т.е. тест работает с форм-строкой).

    Пример использования:
        # Получить форм-строку (создать, если отсутствует)
        form_row = get_or_open_form_row(page)

        # Найти поле "Комментарий" внутри этой строки
        comment_cell = form_row.locator('td').nth(8)

        # Проверить, что инпут виден
        assert comment_cell.locator('input').is_visible()
    """
    # 1) Проверяем, есть ли уже открытая форм-строка
    form_row = page.locator('tbody.cdm-data-grid__body tr.cdm-data-grid__body__form-row').first
    if form_row.count() > 0 and form_row.is_visible():
        pass
    else:
        # 2) Если нет — пробуем открыть через кнопку «Создать»
        list_card = page.locator('.cdm-list').first
        try:
            list_card.wait_for(state="visible", timeout=8000)
        except Exception:
            # иногда .cdm-list отсутствует — не критично
            pass

        candidates = []
        candidates.append(page.get_by_role("button", name="Создать"))
        candidates.append(page.locator('button:has-text("Создать")'))
        candidates.append(page.locator('.MuiButton-label >> text=Создать').locator('xpath=ancestor::button'))
        candidates.append(page.locator('text=Создать').locator('xpath=ancestor::button'))

        create_btn = None
        for cand in candidates:
            try:
                cand.first.wait_for(state="visible", timeout=2500)
                create_btn = cand.first
                break
            except Exception:
                continue

        if create_btn is None or create_btn.count() == 0 or not create_btn.is_visible():
            # Пробуем прокрутить вверх — возможно, тулбар скрыт
            page.evaluate("window.scrollTo(0, 0)")
            try:
                page.get_by_role("button", name="Создать").first.wait_for(state="visible", timeout=2000)
                create_btn = page.get_by_role("button", name="Создать").first
            except Exception:
                pass

        if create_btn is None or create_btn.count() == 0 or not create_btn.is_visible():
            fail_with_screenshot("Кнопка 'Создать' не найдена или не видна", page)

        create_btn.scroll_into_view_if_needed()
        create_btn.click()

        # 3) После клика ждём форм-строку
        form_row = page.locator('tr.cdm-data-grid__body__form-row').first
        try:
            form_row.wait_for(state="visible", timeout=8000)
        except Exception:
            fail_with_screenshot("Форм-строка не появилась после нажатия 'Создать'", page)

    # 4) Проверки структуры строки
    save_btn = form_row.locator('.cdm-data-grid__body__row__actions-cell .cdm-icon-wrapper[title="Сохранить"]')
    cancel_btn = form_row.locator('.cdm-data-grid__body__row__actions-cell .cdm-icon-wrapper[title="Отмена"]')
    if save_btn.count() == 0 or cancel_btn.count() == 0:
        fail_with_screenshot("Найдена строка без кнопок 'Сохранить'/'Отмена' — это не форм-строка.", page)

    editable_fields = form_row.locator('input, textarea')
    if editable_fields.count() == 0:
        fail_with_screenshot("Форм-строка не содержит редактируемых полей (input/textarea).", page)

    return form_row


def get_cell_by_header(
    page: Page,
    header_text: str,
    create_row: bool = False,
    first_cell_text: str | None = None,
    nth_row: int | None = None,
):
    """
    Универсальная функция: вернуть ячейку (td) по названию колонки.

    Вход:
        page (Page): Playwright Page текущей страницы с таблицей.
        header_text (str): Текст заголовка колонки (например: "Вес", "Действие",
            "Тип", "Сеть/адрес-источника", "Сеть/адрес назначения",
            "Порт получателя", "Статус", "Комментарий", "Ошибка", "Счетчик", "Создано").
        create_row (bool, по умолчанию False):
            True  — работаем с форм-строкой; при её отсутствии функция откроет форм-строку (get_or_open_form_row).
            False — работаем с обычной строкой таблицы.
        first_cell_text (str | None): если create_row=False — выбрать обычную строку,
            у которой «первая содержательная ячейка» (второй td после чекбокса) строго равна этому тексту.
            Если не указан — используется nth_row.
        nth_row (int | None): если create_row=False и first_cell_text не задан — индекс обычной строки (0-based).

    Возвращает:
        Locator: локатор <td> искомой колонки в выбранной строке.

    Особенности/устойчивость:
        • Если create_row=True — сначала гарантируем появление форм-строки даже на «пустом» списке (где есть лишь
          <div class="cdm-data-grid__empty-message">Нет данных</div>), затем берём таблицу как предка форм-строки.
        • Если create_row=False — ищем таблицу каскадом фолбэков: внутри .cdm-list__grid-box, по упрощённым селекторам,
          по структурным признакам (thead/tbody с нужными классами) и глобально (вплоть до role="table").
        • Проверяем наличие thead/tbody и видимость заголовков.
        • Поиск колонки — по вхождению текста (case-insensitive) в заголовке.
        • Для обычных строк исключается форм-строка (':not(.cdm-data-grid__body__form-row)').
        • Для «первой ячейки» учитывается, что первый видимый столбец — чекбокс, значит реальная «первая значимая» — td:nth-child(2).
        • При несоответствиях вызывает fail_with_screenshot(...) с диагностикой.

    Пример использования:
        # Ячейка «Вес» в форм-строке (создать при необходимости)
        cell = get_cell_by_header(page, "Вес", create_row=True)

        # Ячейка «Комментарий» у строки, где 1-я ячейка равна "10530"
        cell = get_cell_by_header(page, "Комментарий", create_row=False, first_cell_text="10530")

        # Ячейка «Статус» у 3-й обычной строки (индекс 2)
        cell = get_cell_by_header(page, "Статус", create_row=False, nth_row=2)
    """
    # ===== Шаг №1. Находим таблицу (логика зависит от create_row) =====
    table = None

    if create_row:
        # В «пустом» состоянии таблицы как <table> может не быть — сначала создаём форм-строку.
        row = get_or_open_form_row(page)  # эта функция кликает «Создать» при необходимости и валидирует форм-строку
        # Берём ближайший <table> как предка найденной строки
        table = row.locator("xpath=ancestor::table").first
        try:
            table.wait_for(state="visible", timeout=10000)
        except Exception:
            # На всякий случай — фолбэки (редко нужны, но не мешают)
            table = page.locator("table.MuiTable-root.cdm-data-grid._sortable._selectable").first
            if table.count() == 0 or not table.is_visible():
                table = page.locator("table.cdm-data-grid").first
                try:
                    table.wait_for(state="visible", timeout=6000)
                except Exception:
                    fail_with_screenshot(
                        "Не удалось определить таблицу-предок форм-строки (после клика 'Создать').", page
                    )
    else:
        # Ищем таблицу каскадом фолбэков (на странице уже должны быть обычные строки)
        grid_box = page.locator(".cdm-list__grid-box").first
        try:
            grid_box.wait_for(state="visible", timeout=10000)
        except Exception:
            # контейнера может не быть / появиться позже — не фейлимся, пойдём по глобальным фолбэкам
            pass

        candidates = []
        # a) «правильная» таблица внутри контейнера
        candidates.append(grid_box.locator("table.MuiTable-root.cdm-data-grid._sortable._selectable").first)
        candidates.append(grid_box.locator("table.cdm-data-grid").first)
        # b) таблица по структурным признакам (thead/tbody) — внутри контейнера
        candidates.append(
            grid_box.locator("table")
                .filter(has=page.locator("thead.cdm-data-grid__head"))
                .filter(has=page.locator("tbody.cdm-data-grid__body"))
                .first
        )
        # c) глобальные фолбэки по странице
        candidates.append(page.locator("table.MuiTable-root.cdm-data-grid._sortable._selectable").first)
        candidates.append(page.locator("table.cdm-data-grid").first)
        candidates.append(
            page.locator("table")
                .filter(has=page.locator("thead.cdm-data-grid__head"))
                .filter(has=page.locator("tbody.cdm-data-grid__body"))
                .first
        )
        # d) самый общий структурный фолбэк по роли
        candidates.append(
            page.get_by_role("table")
                .filter(has=page.locator("thead.cdm-data-grid__head"))
                .filter(has=page.locator("tbody.cdm-data-grid__body"))
                .first
        )

        for cand in candidates:
            try:
                if cand and cand.count() > 0:
                    cand.wait_for(state="visible", timeout=15000)
                    table = cand
                    break
            except Exception:
                continue

        if table is None:
            # Если у страницы «пустой» список (нет <table>, а есть только .cdm-data-grid__empty-message),
            # то для работы с обычной строкой это действительно ошибка.
            empty_msg = page.locator(".cdm-data-grid__empty-message")
            if empty_msg.count() > 0 and empty_msg.first.is_visible():
                fail_with_screenshot("Список пуст — нет обычных строк для выбора (видно 'Нет данных').", page)
            fail_with_screenshot(
                "Таблица .cdm-data-grid не видна: не нашли ни по точным, ни по структурным селекторам (thead/tbody).", page
            )

    # ===== Шаг №2. Проверяем структуру таблицы =====
    if table.locator("thead.MuiTableHead-root.cdm-data-grid__head").count() == 0:
        fail_with_screenshot("У таблицы нет thead.cdm-data-grid__head", page)
    if table.locator("tbody.MuiTableBody-root.cdm-data-grid__body").count() == 0:
        fail_with_screenshot("У таблицы нет tbody.cdm-data-grid__body", page)

    # ===== Шаг №3. Находим индекс колонки по заголовку =====
    ths = table.locator("thead tr th")
    try:
        ths.first.wait_for(state="visible", timeout=6000)
    except Exception:
        fail_with_screenshot("Заголовки таблицы (th) не видны", page)

    header_count = ths.count()
    found_col = None
    snapshot = []
    for i in range(header_count):
        th = ths.nth(i)
        # типовая разметка заголовка
        label = th.locator(".cdm-data-grid__body__row__head-cell__label span span").first
        txt = ""
        try:
            if label.count() > 0:
                txt = label.inner_text().strip()
            else:
                txt = th.inner_text().strip()
        except Exception:
            txt = ""
        snapshot.append(txt)
        if txt and header_text.lower() in txt.lower():
            found_col = i
            break

    if found_col is None:
        fail_with_screenshot(
            f"Колонка '{header_text}' не найдена. Заголовки: {snapshot}",
            page,
        )

    # ===== Шаг №4. Выбираем строку: форм-строка ИЛИ обычная =====
    if create_row:
        row = get_or_open_form_row(page)
        # sanity-check: это именно форм-строка
        row_classes = (row.get_attribute("class") or "")
        if "cdm-data-grid__body__form-row" not in row_classes:
            fail_with_screenshot("Ожидалась форм-строка, но выбрана другая строка", page)
    else:
        tbody = table.locator("tbody.MuiTableBody-root.cdm-data-grid__body").first
        try:
            tbody.wait_for(state="visible", timeout=6000)
        except Exception:
            fail_with_screenshot("tbody таблицы не виден", page)

        # исключаем форм-строку
        rows = tbody.locator("tr.cdm-data-grid__body__row:not(.cdm-data-grid__body__form-row)")
        if rows.count() == 0:
            fail_with_screenshot("Нет обычных строк в таблице", page)

        if first_cell_text is not None:
            target = None
            for i in range(rows.count()):
                r = rows.nth(i)
                # первый визуальный столбец — чекбокс; «первая содержательная ячейка» — td:nth-child(2)
                first_td_text = (r.locator("td").nth(1).inner_text() or "").strip() \
                    if r.locator("td").count() > 1 else ""
                if first_td_text == first_cell_text:
                    target = r
                    break
            if target is None:
                fail_with_screenshot(f"Строка с первым значением '{first_cell_text}' не найдена", page)
            row = target
        else:
            idx = 0 if nth_row is None else nth_row
            if idx < 0 or idx >= rows.count():
                fail_with_screenshot(f"nth_row={idx} вне диапазона [0..{rows.count()-1}]", page)
            row = rows.nth(idx)

        if not row.is_visible():
            row.scroll_into_view_if_needed()
            row.wait_for(state="visible", timeout=3000)

    # ===== Шаг №5. Возвращаем ячейку найденной колонки =====
    cell = row.locator("td").nth(found_col)
    if cell.count() == 0:
        total_tds = row.locator("td").count()
        fail_with_screenshot(
            f"Ячейка для колонки '{header_text}' (index={found_col}) не найдена. В строке td={total_tds}",
            page,
        )

    if not cell.first.is_visible():
        cell.first.scroll_into_view_if_needed()
        cell.first.wait_for(state="visible", timeout=3000)

    return cell.first


def validate_cell_input_error_negative(
    page: Page,
    *,
    header_text: str,
    value_to_fill: str,
    expected_error: str | list[str],
    create_row: bool = True,
    require_aria_invalid: bool = True,
    match_mode: str = "auto",  # "exact" | "contains" | "auto"
    blur_action: str = "tab"   # "tab" | "click_outside"
) -> str:
    """
    Универсальная проверка валидации для текстового инпута в ячейке таблицы по заголовку колонки.

    Параметры:
        page               : Playwright Page.
        header_text        : Текст заголовка колонки (например, "Вес").
        value_to_fill      : Значение, которое нужно ввести в текстовое поле (например, "-1", "120001", "abc" или "").
        expected_error     : Ожидаемое сообщение об ошибке (строка) или список допустимых вариантов сообщений.
        create_row         : Если True — гарантируем наличие форм-строки через `get_cell_by_header(..., create_row=True)`.
                             Если False — берём существующую строку (например, когда форма уже открыта другим тестом).
        require_aria_invalid: Если True — дополнительно проверяем, что у инпута `aria-invalid="true"`.
        match_mode         : Режим сравнения текста ошибки:
                                - "exact"    — точное совпадение строки.
                                - "contains" — ошибка должна содержать подстроку.
                                - "auto"     — если ожидаемое значение одно — точное сравнение,
                                               если список — допускаем точное совпадение с любым из списка
                                               или частичное совпадение, если элемент списка длиннее 0.
        blur_action        : Как «увести фокус» для триггера валидации:
                                - "tab"         — отправить Tab на инпуте.
                                - "click_outside" — кликнуть вне ячейки (в тело таблицы).

    Возвращает:
        Строку фактически найденного текста ошибки (для возможной дополнительной проверки в вызывающем коде).

    Важные нюансы использования:
        1) Функция ориентирована на текстовые поля. В ячейке сперва ищется `input[type="text"]`,
           если не найден — пробуем `textarea`. Если ни одно не найдено — тест завершается с ошибкой.
        2) Ошибки читаются внутри текущего FormControl: `.MuiFormHelperText-root.Mui-error`.
           Если платформенный CSS изменится, при необходимости скорректируйте локатор `helper_text`.
        3) Чтобы не плодить форм-строки между тестами, регулируйте `create_row`:
           - Для независимых тестов UI формы — оставляйте `create_row=True`.
           - Если вы строго управляете состоянием между тестами — можно `create_row=False`.
        4) При нестабильном фокусе используйте `blur_action="click_outside"`.
    """

    # Шаг №1. Находим ячейку по заголовку (и при необходимости открываем форм-строку)
    cell = get_cell_by_header(page, header_text=header_text, create_row=create_row)
    if cell.count() == 0 or not cell.first.is_visible():
        fail_with_screenshot(f"Ячейка колонки '{header_text}' не найдена или не видна", page)

    # Шаг №2. Определяем поле ввода (input[type='text'] или textarea)
    text_input = cell.locator('input[type="text"]').first
    if text_input.count() == 0 or not text_input.is_visible():
        # пробуем textarea как запасной вариант
        text_input = cell.locator("textarea").first
        if text_input.count() == 0 or not text_input.is_visible():
            fail_with_screenshot(f"Текстовое поле в колонке '{header_text}' не найдено", page)

    # Шаг №3. Вводим значение
    text_input.fill(value_to_fill)

    # Шаг №4. Тригерим валидацию (уводим фокус)
    if blur_action == "tab":
        text_input.press("Tab")
    else:
        # кликнем в область пагинации (точно вне ячейки)
        page.locator(".cdm-pagination, .cdm-list__grid-box").first.click(position={"x": 2, "y": 2}, force=True)

    # Шаг №5. Ищем блок ошибки в пределах текущего FormControl
    form_control = cell.locator(".MuiFormControl-root").first
    helper_text = form_control.locator(".MuiFormHelperText-root.Mui-error").first

    # Небольшая подстраховка на случай отложенного рендера helper
    page.wait_for_timeout(100)  # короткая задержка, чтобы не гоняться за race condition

    if helper_text.count() == 0 or not helper_text.is_visible():
        fail_with_screenshot(
            f"Текст ошибки в колонке '{header_text}' не отображается при вводе '{value_to_fill}'",
            page
        )

    actual_error = helper_text.inner_text().strip()

    # Шаг №6. Дополнительная проверка aria-invalid (если включено)
    if require_aria_invalid:
        aria_invalid = text_input.get_attribute("aria-invalid")
        if aria_invalid != "true":
            fail_with_screenshot(
                f"aria-invalid!='true' у инпута колонки '{header_text}' при значении '{value_to_fill}'",
                page
            )

    # Шаг №7. Сверяем текст ошибки по выбранной стратегии
    def _match(expected: str, actual: str) -> bool:
        if match_mode == "exact":
            return actual == expected
        if match_mode == "contains":
            return expected in actual
        # auto
        return actual == expected or (len(expected) > 0 and expected in actual)

    if isinstance(expected_error, list):
        if not any(_match(e, actual_error) for e in expected_error):
            fail_with_screenshot(
                f"Ошибка не соответствует ожиданию при вводе '{value_to_fill}'. "
                f"Ожидалось одно из: {expected_error}. Получено: '{actual_error}'",
                page,
            )
    else:
        if not _match(expected_error, actual_error):
            fail_with_screenshot(
                f"Ошибка не соответствует ожиданию при вводе '{value_to_fill}'. "
                f"Ожидалось: '{expected_error}'. Получено: '{actual_error}'",
                page,
            )

    return actual_error


def validate_cell_input_error_positive(
    page: Page,
    *,
    header_text: str,
    value_to_fill: str,
    create_row: bool = True,
    require_aria_invalid_absent: bool = True,
    blur_action: str = "tab"  # "tab" | "click_outside"
):
    """
    Универсальная проверка валидации для позитивного сценария —
    убеждаемся, что после ввода корректного значения в ячейку таблицы
    **не отображается сообщение об ошибке** и у поля нет признака ошибки.

    Параметры:
        page : Playwright Page
        header_text : Заголовок колонки (например, "Вес")
        value_to_fill : Значение, которое нужно ввести (валидное)
        create_row : Если True — создаёт форм-строку при необходимости
        require_aria_invalid_absent : Если True — проверяем, что aria-invalid отсутствует или не "true"
        blur_action : Как увести фокус, чтобы сработала валидация:
                      - "tab" (по умолчанию)
                      - "click_outside" — кликнуть вне ячейки

    Возвращает:
        None (валидация успешна), иначе вызывает fail_with_screenshot.
    """

    # Шаг №1. Находим ячейку и поле по заголовку
    cell = get_cell_by_header(page, header_text=header_text, create_row=create_row)
    if cell.count() == 0 or not cell.first.is_visible():
        fail_with_screenshot(f"Ячейка колонки '{header_text}' не найдена или не видна", page)

    # Шаг №2. Определяем поле ввода (input или textarea)
    text_input = cell.locator('input[type="text"]').first
    if text_input.count() == 0 or not text_input.is_visible():
        text_input = cell.locator("textarea").first
        if text_input.count() == 0 or not text_input.is_visible():
            fail_with_screenshot(f"Текстовое поле в колонке '{header_text}' не найдено", page)

    # Шаг №3. Вводим значение
    text_input.fill(value_to_fill)

    # Шаг №4. Тригерим валидацию
    if blur_action == "tab":
        text_input.press("Tab")
    else:
        page.locator(".cdm-pagination, .cdm-list__grid-box").first.click(position={"x": 2, "y": 2}, force=True)

    # Небольшая задержка, чтобы UI успел обновиться
    page.wait_for_timeout(150)

    # Шаг №5. Проверяем отсутствие aria-invalid="true"
    if require_aria_invalid_absent:
        aria_invalid = text_input.get_attribute("aria-invalid")
        if aria_invalid == "true":
            fail_with_screenshot(
                f"Поле '{header_text}' помечено как невалидное (aria-invalid=true) при вводе '{value_to_fill}'",
                page
            )

    # Шаг №6. Проверяем отсутствие сообщения об ошибке
    form_control = cell.locator(".MuiFormControl-root").first
    helper_text = form_control.locator(".MuiFormHelperText-root.Mui-error").first

    # Если helper текст всё-таки есть и виден — это ошибка
    if helper_text.count() > 0 and helper_text.is_visible():
        actual_error = helper_text.inner_text().strip()
        fail_with_screenshot(
            f"Для поля '{header_text}' отображается ошибка при валидном значении '{value_to_fill}': '{actual_error}'",
            page
        )


def select_option_in_cell_and_verify(
    page: Page,
    *,
    header_text: str,
    option_to_select: str,
    create_row: bool = True,
):
    """
    Универсальная позитивная проверка select в ячейке таблицы:
    - Открывает селект в колонке `header_text`
    - Выбирает пункт `option_to_select`
    - Проверяет, что выбранный текст отобразился в самом селекте
      (внутренний div и его title равны `option_to_select`, если title присутствует)

    Параметры:
        page             : Playwright Page
        header_text      : Заголовок колонки (например, "Действие" или "Тип")
        option_to_select : Текст пункта в меню (например, "ICMP (1)", "TCP+UDP (6,17)")
        create_row       : Если True — гарантирует наличие форм-строки

    Возвращает:
        None. В случае несоответствия вызывает fail_with_screenshot.
    """
    # Шаг №1. Берём ячейку нужной колонки
    cell = get_cell_by_header(page, header_text=header_text, create_row=create_row)
    if cell.count() == 0 or not cell.first.is_visible():
        fail_with_screenshot(f"Ячейка колонки '{header_text}' не найдена или не видна", page)

    # Шаг №2. Открываем селект
    select_button = cell.locator('div.MuiSelect-root[role="button"]').first
    if select_button.count() == 0 or not select_button.is_visible():
        fail_with_screenshot(f"Селект в колонке '{header_text}' не найден", page)
    select_button.click()

    # Шаг №3. Ждём меню и кликаем нужный пункт
    menu = page.locator('.MuiMenu-paper ul[role="listbox"]').first
    try:
        menu.wait_for(state="visible", timeout=4000)
    except Exception:
        fail_with_screenshot(f"Меню селекта для '{header_text}' не появилось", page)

    option = menu.locator('li.MuiMenuItem-root').filter(has_text=option_to_select).first
    if option.count() == 0 or not option.is_visible():
        fail_with_screenshot(f"Пункт '{option_to_select}' не найден в меню селекта '{header_text}'", page)
    option.click()

    # Дадим меню скрыться и UI обновиться (0.3 сек, как просили)
    page.wait_for_timeout(300)
    try:
        menu.wait_for(state="hidden", timeout=2000)
    except Exception:
        # не критично, если не успело анимироваться, продолжаем проверку отображения
        pass

    # Шаг №4. Проверяем, что выбранный текст отобразился в селекте
    # Обычно лейбл лежит в div внутри .MuiSelect-root и дублируется в атрибуте title
    label_div = select_button.locator('div[title]').first
    if label_div.count() == 0:
        # fallback: первый внутренний div
        label_div = select_button.locator('div').first
    if label_div.count() == 0 or not label_div.is_visible():
        fail_with_screenshot(f"Текст выбранной опции в селекте '{header_text}' не отображается", page)

    displayed_text = (label_div.inner_text() or "").strip()
    if displayed_text != option_to_select:
        fail_with_screenshot(
            f"Отображаемое значение селекта '{header_text}' != '{option_to_select}'. "
            f"Получено: '{displayed_text}'",
            page
        )

    title_attr = label_div.get_attribute("title")
    if title_attr is not None and title_attr.strip() != option_to_select:
        fail_with_screenshot(
            f"title выбранной опции в селекте '{header_text}' != '{option_to_select}'. "
            f"Получено: '{title_attr}'",
            page
        )


def toggle_cell_switch_state(
    page: Page,
    *,
    header_text: str,
    create_row: bool = True,
) -> None:
    """
    Универсальная функция: изменяет состояние переключателя (MUI Switch) в ячейке таблицы по заголовку колонки.

    Поведение:
        - Находит ячейку по заголовку.
        - Определяет текущее состояние switch (checked / unchecked).
        - Кликает по переключателю.
        - Проверяет, что состояние действительно изменилось.
        - При неудаче делает скриншот и падает с fail_with_screenshot.

    Параметры:
        page        : Playwright Page
        header_text : Текст заголовка колонки, где находится переключатель (например, "Активен")
        create_row  : Если True — создаёт форм-строку при необходимости через get_cell_by_header(...)

    Возвращает:
        None
    """

    # Шаг №1. Находим ячейку с нужным заголовком
    cell = get_cell_by_header(page, header_text=header_text, create_row=create_row)
    if cell.count() == 0 or not cell.first.is_visible():
        fail_with_screenshot(f"Ячейка колонки '{header_text}' не найдена или не видна", page)

    # Шаг №2. Ищем переключатель
    switch_root = cell.locator(".MuiSwitch-root").first
    if switch_root.count() == 0 or not switch_root.is_visible():
        fail_with_screenshot(f"Переключатель ('.MuiSwitch-root') в колонке '{header_text}' не найден", page)

    # Шаг №3. Получаем сам checkbox (реальный input)
    checkbox = switch_root.locator('input[type="checkbox"]').first
    if checkbox.count() == 0 or not checkbox.is_visible():
        # запасной вариант — вдруг input не внутри .MuiSwitch-root
        checkbox = cell.locator('input[type="checkbox"]').first
        if checkbox.count() == 0 or not checkbox.is_visible():
            fail_with_screenshot(f"Checkbox переключателя в колонке '{header_text}' не найден", page)

    # Шаг №4. Проверяем доступность
    try:
        if checkbox.is_disabled():
            fail_with_screenshot(f"Переключатель в колонке '{header_text}' недоступен (disabled)", page)
    except Exception:
        pass

    # Шаг №5. Определяем текущее состояние
    try:
        initial_state = checkbox.is_checked()
    except Exception:
        page.wait_for_timeout(100)
        initial_state = checkbox.is_checked()

    # Шаг №6. Кликаем по свитчу
    switch_root.click()
    page.wait_for_timeout(200)

    # Шаг №7. Проверяем новое состояние
    try:
        new_state = checkbox.is_checked()
    except Exception:
        page.wait_for_timeout(100)
        new_state = checkbox.is_checked()

    # Шаг №8. Проверяем, что состояние изменилось
    if initial_state == new_state:
        fail_with_screenshot(
            f"Состояние переключателя в колонке '{header_text}' не изменилось после клика "
            f"(осталось {'включено' if initial_state else 'выключено'})",
            page
        )


def click_form_row_save_and_wait(
    page: Page,
    *,
    endpoint_part: str,
    method: str = "POST",
    expected_status: int = 200,
    timeout: int = 15000,
) -> None:
    """
    Универсальная функция: нажимает кнопку «Сохранить» в форм-строке и ждёт сетевой запрос.

    Поведение:
        - Находит текущую форм-строку (создаёт через get_or_open_form_row при необходимости).
        - Находит и нажимает кнопку с иконкой title="Сохранить".
        - Ждёт сетевой ответ, URL которого содержит endpoint_part и метод равен method.
        - Проверяет, что статус ответа равен expected_status.
        - При неудаче делает скриншот и падает через fail_with_screenshot.

    Параметры:
        page           : Playwright Page.
        endpoint_part  : Подстрока для матчинга URL запроса (например, "/api/firewall/white-rules").
        method         : Ожидаемый HTTP-метод (например, "POST", "PUT", "PATCH").
        expected_status: Ожидаемый HTTP-статус ответа (например, 200, 201, 204).
        timeout        : Таймаут ожидания ответа, мс.

    Возвращает:
        None.
    """
    # Шаг №1. Гарантируем наличие форм-строки
    form_row = get_or_open_form_row(page)
    if form_row.count() == 0 or not form_row.is_visible():
        fail_with_screenshot("Форм-строка не обнаружена/не видна перед нажатием 'Сохранить'", page)

    # Шаг №2. Находим кнопку «Сохранить»
    # Иконка с title="Сохранить" находится внутри кнопки, по клику по иконке событие пройдёт на кнопку.
    save_icon = form_row.locator('.cdm-icon-wrapper[title="Сохранить"]').first
    if save_icon.count() == 0 or not save_icon.is_visible():
        fail_with_screenshot("Кнопка 'Сохранить' в форм-строке не найдена или не видна", page)

    # Шаг №3. Ожидаем ответ на запрос с нужным URL/методом
    def _predicate(resp) -> bool:
        try:
            return (
                endpoint_part in resp.url
                and resp.request is not None
                and (resp.request.method or "").upper() == method.upper()
            )
        except Exception:
            return False

    try:
        with page.expect_response(_predicate, timeout=timeout) as resp_info:
            save_icon.click()
        resp = resp_info.value
    except Exception:
        fail_with_screenshot(
            f"Не дождались ответа на запрос с методом '{method}' и URL, содержащим '{endpoint_part}', "
            f"после нажатия 'Сохранить' (таймаут {timeout} мс).",
            page,
        )
        return  # для читаемости; фактически не достигнется

    # Шаг №4. Проверяем статус ответа
    status = None
    try:
        status = resp.status
    except Exception:
        fail_with_screenshot("Не удалось получить статус ответа после нажатия 'Сохранить'", page)

    if status != expected_status:
        fail_with_screenshot(
            f"Ожидался статус {expected_status} на '{method} {endpoint_part}', получено: {status}",
            page,
        )


def find_row_by_columns(
    page: Page,
    expectations: dict[str, str],
    *,
    match_mode: str = "exact",   # "exact" | "contains"
    timeout: int = 10000,
):
    """
    Универсальный поиск строки таблицы по подмножеству колонок.

    Поведение:
        - Ищет обычные строки таблицы (без форм-строки).
        - Сравнивает значения только по переданным колонкам (dict: "колонка" → "ожидаемое значение").
        - Сопоставляет значения в ячейках и возвращает строку, где все указанные совпадают.
        - Если строка не найдена — вызывает fail_with_screenshot с диагностикой и примером содержимого таблицы.

    Параметры:
        page (Page): Текущая страница Playwright.
        expectations (dict[str, str]): Пары "заголовок колонки" → "ожидаемое значение".
                                       Можно передавать любое подмножество колонок (необязательно все).
        match_mode (str): Режим сравнения текста:
            - "exact" — точное совпадение (по нормализованным пробелам).
            - "contains" — допускает вхождение (подстроку).
        timeout (int): Таймаут ожидания появления tbody таблицы, мс.

    Возвращает:
        Locator: найденную строку таблицы (<tr.cdm-data-grid__body__row>), где все указанные значения совпали.

    Особенности:
        • Ищет только обычные строки (исключает форм-строку).
        • Нормализует пробелы в значениях перед сравнением.
        • Если таблица пуста — выводит содержимое ".cdm-data-grid__empty-message".
        • Выводит подробную диагностику при несовпадении (показывает первые строки таблицы с данными).
    """

    # Шаг №1. Находим тело таблицы и убеждаемся, что оно отображается
    tbody = page.locator("tbody.MuiTableBody-root.cdm-data-grid__body").first
    try:
        tbody.wait_for(state="visible", timeout=timeout)
    except Exception:
        empty_msg = page.locator(".cdm-data-grid__empty-message")
        if empty_msg.count() > 0 and empty_msg.first.is_visible():
            fail_with_screenshot("Список пуст — отображается '.cdm-data-grid__empty-message'.", page)
        fail_with_screenshot("tbody таблицы не найден или не отображается.", page)

    # Шаг №2. Получаем все обычные строки (исключаем форм-строку)
    rows = tbody.locator("tr.cdm-data-grid__body__row:not(.cdm-data-grid__body__form-row)")
    total = rows.count()
    if total == 0:
        fail_with_screenshot("Обычные строки таблицы отсутствуют (возможно, таблица пуста).", page)

    # Шаг №3. Перебираем строки и ищем, где все указанные колонки совпадают по значению
    for i in range(total):
        row_ok = True
        for header_text, expected_value in expectations.items():
            # Берём ячейку по заголовку в текущей строке
            cell = get_cell_by_header(page, header_text=header_text, create_row=False, nth_row=i)
            actual_text = _norm(cell.inner_text())

            # Проверяем совпадение по выбранному режиму
            if match_mode == "exact":
                if actual_text != _norm(expected_value):
                    row_ok = False
                    break
            else:  # contains
                if _norm(expected_value) not in actual_text:
                    row_ok = False
                    break

        if row_ok:
            # Совпали все указанные колонки — возвращаем найденную строку
            return rows.nth(i)

    # Шаг №4. Если строка не найдена — собираем диагностическую информацию (первые 5 строк)
    sample = []
    max_probe = min(total, 5)
    for i in range(max_probe):
        probe = {}
        for header_text in expectations.keys():
            try:
                cell = get_cell_by_header(page, header_text=header_text, create_row=False, nth_row=i)
                probe[header_text] = _norm(cell.inner_text())
            except Exception:
                probe[header_text] = "<недоступно>"
        sample.append(f"row[{i}]: {probe}")

    # Шаг №5. Формируем сообщение об ошибке и делаем скриншот
    fail_with_screenshot(
        "Строка по переданным колонкам не найдена.\n"
        f"Ожидалось (match_mode={match_mode}): {expectations}\n"
        f"Проверено строк: {total}. Примеры первых {max_probe}:\n" + "\n".join(sample),
        page,
    )

    # unreachable, но добавлен для IDE/типизации
    return rows.first


def assert_no_row_by_columns(
    page: Page,
    expectations: dict[str, str],
    *,
    match_mode: str = "exact",   # "exact" | "contains"
    timeout: int = 10000,
) -> None:
    """
    Универсальная проверка отсутствия строки таблицы по подмножеству колонок.

    Поведение:
        - Ищет обычные строки таблицы (без форм-строки).
        - Для каждой строки сравнивает значения только по переданным колонкам (dict: "колонка" → "ожидаемое значение").
        - Если находится строка, где ВСЕ указанные значения совпали — падаем с fail_with_screenshot.
        - Если ни одна строка не совпала — успешно выходим.

    Параметры:
        page (Page): Текущая страница Playwright.
        expectations (dict[str, str]): Пары "заголовок колонки" → "ожидаемое значение".
        match_mode (str): Режим сравнения текста:
            - "exact"     — точное совпадение (по нормализованным пробелам).
            - "contains"  — допускает вхождение (подстроку).
        timeout (int): Таймаут ожидания появления tbody таблицы, мс.

    Возвращает:
        None (если подходящей строки нет). Иначе — fail_with_screenshot.
    """

    # Шаг №1. Находим tbody и убеждаемся, что он отображается (или список пуст)
    tbody = page.locator("tbody.MuiTableBody-root.cdm-data-grid__body").first
    try:
        tbody.wait_for(state="visible", timeout=timeout)
    except Exception:
        # если таблица пуста — это ок для «отсутствия строки»
        empty_msg = page.locator(".cdm-data-grid__empty-message")
        if empty_msg.count() > 0 and empty_msg.first.is_visible():
            return
        fail_with_screenshot("tbody таблицы не найден или не отображается.", page)

    # Шаг №2. Берём только обычные строки (исключаем форм-строку)
    rows = tbody.locator("tr.cdm-data-grid__body__row:not(.cdm-data-grid__body__form-row)")
    total = rows.count()
    if total == 0:
        # пустая таблица — нужной строки точно нет
        return

    # Шаг №3. Ищем совпадение по всем переданным колонкам в КАЖДОЙ строке
    for i in range(total):
        matched_all = True
        for header_text, expected_value in expectations.items():
            # Берём ячейку нужной колонки в текущей строке
            cell = get_cell_by_header(page, header_text=header_text, create_row=False, nth_row=i)
            actual_text = _norm(cell.inner_text())

            if match_mode == "exact":
                if actual_text != _norm(expected_value):
                    matched_all = False
                    break
            else:  # contains
                if _norm(expected_value) not in actual_text:
                    matched_all = False
                    break

        if matched_all:
            # Шаг №4. Если нашли полное совпадение — формируем диагностику и падаем
            probe = {}
            for header_text in expectations.keys():
                try:
                    cell = get_cell_by_header(page, header_text=header_text, create_row=False, nth_row=i)
                    probe[header_text] = _norm(cell.inner_text())
                except Exception:
                    probe[header_text] = "<недоступно>"

            fail_with_screenshot(
                "Найдена строка, которой НЕ должно быть.\n"
                f"Ожидали отсутствие строки с (match_mode={match_mode}): {expectations}\n"
                f"Найдена строка row[{i}] со значениями: {probe}",
                page,
            )

    # Если сюда дошли — ни одной подходящей строки нет (успех)
    return


def click_row_edit_and_wait_editable(
    page: Page,
    *,
    header_text: str,
    expected_value: str,
    timeout: int = 10000,
):
    """
    Универсальная функция: находит ОДНУ обычную строку по значению в указанной колонке,
    нажимает в ней кнопку «Изменить» и проверяет, что строка стала редактируемой.

    Поведение:
        - Ищет таблицу и определяет индекс колонки `header_text`.
        - Находит обычную строку (не форм-строку), где значение в этой колонке равно `expected_value`
          (нормализация: схлопывание пробелов/переводов строк, удаление пробелов вокруг запятых).
        - Нажимает иконку с title="Изменить" в найденной строке.
        - Ждёт появления форм-строки (tr.cdm-data-grid__body__form-row).
        - Валидирует, что в форм-строке есть кнопки «Сохранить»/«Отмена» и хотя бы один input/textarea.

    Параметры:
        page          : Playwright Page.
        header_text   : Текст заголовка колонки, по которой ищем строку (например, "Комментарий", "Тип", ...).
        expected_value: Искомое значение в целевой колонке (с учётом нормализации).
        timeout       : Таймаут ожиданий (мс).

    Возвращает:
        Locator форм-строки (<tr.cdm-data-grid__body__form-row>).

    Шаг №1. Находим таблицу и tbody
    Шаг №2. Находим индекс колонки по заголовку
    Шаг №3. Находим нужную обычную строку по значению в колонке
    Шаг №4. Жмём «Изменить» в найденной строке
    Шаг №5. Ждём появления форм-строки
    Шаг №6. Валидируем, что строка стала редактируемой (Save/Cancel)
    """

    # Шаг №1. Находим таблицу и tbody
    table = None
    grid_box = page.locator(".cdm-list__grid-box").first
    try:
        grid_box.wait_for(state="visible", timeout=timeout)
    except Exception:
        pass

    candidates = [
        grid_box.locator("table.MuiTable-root.cdm-data-grid._sortable._selectable").first,
        grid_box.locator("table.cdm-data-grid").first,
        page.locator("table.MuiTable-root.cdm-data-grid._sortable._selectable").first,
        page.locator("table.cdm-data-grid").first,
        page.locator("table").filter(
            has=page.locator("thead.cdm-data-grid__head")
        ).filter(
            has=page.locator("tbody.cdm-data-grid__body")
        ).first,
    ]
    for cand in candidates:
        try:
            if cand and cand.count() > 0:
                cand.wait_for(state="visible", timeout=3000)
                table = cand
                break
        except Exception:
            continue

    if table is None:
        empty_msg = page.locator(".cdm-data-grid__empty-message")
        if empty_msg.count() > 0 and empty_msg.first.is_visible():
            fail_with_screenshot("Список пуст — нет строк для редактирования (видно 'Нет данных').", page)
        fail_with_screenshot("Таблица .cdm-data-grid не найдена/не видна.", page)

    if table.locator("thead.cdm-data-grid__head").count() == 0:
        fail_with_screenshot("У таблицы нет thead.cdm-data-grid__head", page)
    if table.locator("tbody.cdm-data-grid__body").count() == 0:
        fail_with_screenshot("У таблицы нет tbody.cdm-data-grid__body", page)

    tbody = table.locator("tbody.cdm-data-grid__body").first

    # Шаг №2. Находим индекс колонки по заголовку
    ths = table.locator("thead tr th")
    try:
        ths.first.wait_for(state="visible", timeout=4000)
    except Exception:
        fail_with_screenshot("Заголовки таблицы (th) не видны", page)

    header_count = ths.count()
    found_col = None
    snapshot = []
    for i in range(header_count):
        th = ths.nth(i)
        label = th.locator(".cdm-data-grid__body__row__head-cell__label span span").first
        try:
            txt = label.inner_text().strip() if label.count() > 0 else (th.inner_text() or "").strip()
        except Exception:
            txt = ""
        snapshot.append(txt)
        if txt and header_text.lower() in txt.lower():
            found_col = i
            break

    if found_col is None:
        fail_with_screenshot(f"Колонка '{header_text}' не найдена. Заголовки: {snapshot}", page)

    # Шаг №3. Находим нужную обычную строку по значению в колонке
    rows = tbody.locator("tr.cdm-data-grid__body__row:not(.cdm-data-grid__body__form-row)")
    if rows.count() == 0:
        fail_with_screenshot("Нет обычных строк в таблице", page)

    target_row = None
    expected_norm = _norm(expected_value)
    for i in range(rows.count()):
        r = rows.nth(i)
        td = r.locator("td").nth(found_col)
        if td.count() == 0:
            continue
        try:
            cell_text = (td.inner_text() or "").strip()
        except Exception:
            cell_text = ""
        if _norm(cell_text) == expected_norm:
            target_row = r
            break

    if target_row is None:
        fail_with_screenshot(
            f"Строка со значением '{expected_value}' в колонке '{header_text}' не найдена.",
            page,
        )

    # Шаг №4. Жмём «Изменить» в найденной строке
    edit_icon = target_row.locator('.cdm-icon-wrapper[title="Изменить"]').first
    if edit_icon.count() == 0 or not edit_icon.is_visible():
        fail_with_screenshot("Иконка 'Изменить' в найденной строке не найдена или не видна", page)
    edit_icon.click()

    # Шаг №5. Ждём появления форм-строки
    form_row = page.locator("tr.cdm-data-grid__body__form-row").first
    try:
        form_row.wait_for(state="visible", timeout=timeout)
    except Exception:
        fail_with_screenshot("Форм-строка не появилась после нажатия 'Изменить'", page)

    # Шаг №6. Валидируем, что строка стала редактируемой (есть Save/Cancel)
    save_btn = form_row.locator('.cdm-data-grid__body__row__actions-cell .cdm-icon-wrapper[title="Сохранить"]')
    cancel_btn = form_row.locator('.cdm-data-grid__body__row__actions-cell .cdm-icon-wrapper[title="Отмена"]')
    if save_btn.count() == 0 or cancel_btn.count() == 0:
        fail_with_screenshot("После 'Изменить' не появились кнопки 'Сохранить'/'Отмена' — строка не редактируемая.", page)

    return form_row


def click_row_delete_and_wait(
    page: Page,
    *,
    header_text: str,
    expected_value: str,
    endpoint_part: str,
    method: str = "DELETE",
    expected_status: int = 200,
    timeout: int = 15000,
):
    """
    Универсальная функция: находит ОДНУ обычную строку по значению в указанной колонке,
    нажимает в ней кнопку «Удалить», подтверждает действие в диалоге и ждёт сетевой ответ.

    Поведение:
        - Ищет таблицу и определяет индекс колонки `header_text`.
        - Находит обычную строку (не форм-строку), где значение в этой колонке равно `expected_value`.
        - Нажимает иконку с title="Удалить" в найденной строке.
        - Ждёт появления диалога подтверждения и кликает по кнопке «Удалить».
        - Ждёт сетевой ответ (через `wait_for_api_response`).
        - Проверяет, что статус ответа равен `expected_status`.

    Параметры:
        page           : Playwright Page.
        header_text    : Текст заголовка колонки (например, "Комментарий").
        expected_value : Значение, по которому ищем строку (с учётом нормализации).
        endpoint_part  : Подстрока для матчинга URL запроса (например, "/api/firewall/white-rules").
        method         : Ожидаемый HTTP-метод (по умолчанию "DELETE").
        expected_status: Ожидаемый статус ответа (по умолчанию 200).
        timeout        : Таймаут ожиданий (мс).

    Возвращает:
        None.

    Шаг №1. Находим таблицу и tbody  
    Шаг №2. Находим индекс колонки по заголовку  
    Шаг №3. Находим нужную обычную строку по значению в колонке  
    Шаг №4. Жмём «Удалить» в найденной строке  
    Шаг №5. Ждём появления диалога и подтверждаем удаление  
    Шаг №6. Ждём сетевой ответ и проверяем статус (через wait_for_api_response)
    """

    # --- Шаг №1. Находим таблицу и tbody ---
    table = None
    grid_box = page.locator(".cdm-list__grid-box").first
    try:
        grid_box.wait_for(state="visible", timeout=timeout)
    except Exception:
        pass

    candidates = [
        grid_box.locator("table.MuiTable-root.cdm-data-grid._sortable._selectable").first,
        grid_box.locator("table.cdm-data-grid").first,
        page.locator("table.MuiTable-root.cdm-data-grid._sortable._selectable").first,
        page.locator("table.cdm-data-grid").first,
        page.locator("table").filter(
            has=page.locator("thead.cdm-data-grid__head")
        ).filter(
            has=page.locator("tbody.cdm-data-grid__body")
        ).first,
    ]
    for cand in candidates:
        try:
            if cand and cand.count() > 0:
                cand.wait_for(state="visible", timeout=3000)
                table = cand
                break
        except Exception:
            continue

    if table is None:
        empty_msg = page.locator(".cdm-data-grid__empty-message")
        if empty_msg.count() > 0 and empty_msg.first.is_visible():
            fail_with_screenshot("Список пуст — нет строк для удаления (видно 'Нет данных').", page)
        fail_with_screenshot("Таблица .cdm-data-grid не найдена/не видна.", page)

    if table.locator("thead.cdm-data-grid__head").count() == 0:
        fail_with_screenshot("У таблицы нет thead.cdm-data-grid__head", page)
    if table.locator("tbody.cdm-data-grid__body").count() == 0:
        fail_with_screenshot("У таблицы нет tbody.cdm-data-grid__body", page)

    tbody = table.locator("tbody.cdm-data-grid__body").first

    # --- Шаг №2. Находим индекс колонки по заголовку ---
    ths = table.locator("thead tr th")
    try:
        ths.first.wait_for(state="visible", timeout=4000)
    except Exception:
        fail_with_screenshot("Заголовки таблицы (th) не видны", page)

    header_count = ths.count()
    found_col = None
    snapshot = []
    for i in range(header_count):
        th = ths.nth(i)
        label = th.locator(".cdm-data-grid__body__row__head-cell__label span span").first
        try:
            txt = label.inner_text().strip() if label.count() > 0 else (th.inner_text() or "").strip()
        except Exception:
            txt = ""
        snapshot.append(txt)
        if txt and header_text.lower() in txt.lower():
            found_col = i
            break

    if found_col is None:
        fail_with_screenshot(f"Колонка '{header_text}' не найдена. Заголовки: {snapshot}", page)

    # --- Шаг №3. Находим нужную обычную строку ---
    rows = tbody.locator("tr.cdm-data-grid__body__row:not(.cdm-data-grid__body__form-row)")
    if rows.count() == 0:
        fail_with_screenshot("Нет обычных строк в таблице", page)

    target_row = None
    expected_norm = _norm(expected_value)
    for i in range(rows.count()):
        r = rows.nth(i)
        td = r.locator("td").nth(found_col)
        if td.count() == 0:
            continue
        try:
            cell_text = (td.inner_text() or "").strip()
        except Exception:
            cell_text = ""
        if _norm(cell_text) == expected_norm:
            target_row = r
            break

    if target_row is None:
        fail_with_screenshot(
            f"Строка со значением '{expected_value}' в колонке '{header_text}' не найдена.",
            page,
        )

    # --- Шаг №4. Жмём «Удалить» ---
    delete_icon = target_row.locator('.cdm-icon-wrapper[title="Удалить"]').first
    if delete_icon.count() == 0 or not delete_icon.is_visible():
        fail_with_screenshot("Иконка 'Удалить' в найденной строке не найдена или не видна", page)
    delete_icon.click()

    # --- Шаг №5. Подтверждаем удаление ---
    dialog = page.locator('.MuiDialog-paper[role="dialog"]').first
    try:
        dialog.wait_for(state="visible", timeout=timeout)
    except Exception:
        fail_with_screenshot("Диалог подтверждения удаления не появился", page)

    confirm_btn = dialog.locator('button:has-text("Удалить")').first
    if confirm_btn.count() == 0 or not confirm_btn.is_visible():
        fail_with_screenshot("Кнопка подтверждения 'Удалить' не найдена или не видна", page)

    # --- Шаг №6. Ждём API-ответ и проверяем статус ---
    with wait_for_api_response(page, endpoint_part, expected_status, method=method, timeout=timeout):
        confirm_btn.click()