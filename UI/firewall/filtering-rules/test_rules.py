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
    wait_for_api_response_with_response
)
import time


@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_rules_navigate_and_check_url_with_tab(authenticated_page: Page, credentials):
    """
    Проверяет переход на вкладку "Динамические правила" в разделе "Правила фильтрации" и корректность URL для "Динамические правила".
    """
    tab_button_1 = "Межсетевое экранирование"
    tab_button_2 = "Правила фильтрации"
    tab_name = "Динамические правила"
    url = "firewall/filtering/rules"
    navigate_and_check_url_with_tab(authenticated_page, tab_button_1, tab_button_2, tab_name, url, credentials)

@pytest.mark.parametrize("credentials", [("admin", "password")], indirect=True)
def test_page_rules_check_tabs_selected_state(authenticated_page: Page, credentials):
    """
    Проверяет, что вкладка "Динамические правила" выбраны.
    """
    tab_names = ["Динамические правила", "Статические правила"]
    active_tab = "Динамические правила"
    expected_path = "firewall/filtering/rules"
    check_tabs_selected_state(authenticated_page, tab_names, active_tab, expected_path, credentials)
