import pytest
from playwright.sync_api import Browser, expect, Page
from UI.conftest import CURRENT_CLUSTER_STATE

print(f"CURRENT_CLUSTER_STATE во время сбора тестов: {CURRENT_CLUSTER_STATE}")

def _check_cluster_indicator(page: Page, fill_color: str, cursor_style: str, aria_label: str, test_name: str):
    """
    Проверяет свойства SVG-индикатора кластера.
    """
    expected_svg_locator = page.locator(f'div.MuiBox-root svg[fill="{fill_color}"][aria-label="{aria_label}"]')
    expect(expected_svg_locator).to_be_visible()
    expect(expected_svg_locator).to_have_attribute('style', f'cursor: {cursor_style};')

@pytest.mark.skipif(CURRENT_CLUSTER_STATE != "standalone", reason="Тест запускается только для состояния standalone")
def test_cluster_state_standalone(authenticated_page: Page, request, credentials):
    """
    Проверяет, что при состоянии кластера 'standalone' отображается корректный SVG-индикатор
    и он некликабелен.
    """
    try:
        _check_cluster_indicator(authenticated_page, "gray", "not-allowed", "", "standalone")
    except Exception as e:
        authenticated_page.screenshot(path="UI/error_screenshots/cluster_state_standalone_error.png")
        raise e

@pytest.mark.skipif(CURRENT_CLUSTER_STATE != "master", reason="Тест запускается только для состояния master")
def test_cluster_state_master(authenticated_page: Page, request, credentials):
    """
    Проверяет, что при состоянии кластера 'master' отображается корректный SVG-индикатор
    и он кликабелен.
    """
    try:
        _check_cluster_indicator(authenticated_page, "green", "pointer", "Master", "master")
    except Exception as e:
        authenticated_page.screenshot(path="UI/error_screenshots/cluster_state_master_error.png")
        raise e

@pytest.mark.skipif(CURRENT_CLUSTER_STATE != "slave", reason="Тест запускается только для состояния slave")
def test_cluster_state_slave(authenticated_page: Page, request, credentials):
    """
    Проверяет, что при состоянии кластера 'slave' отображается корректный SVG-индикатор
    и он кликабелен.
    """
    try:
        _check_cluster_indicator(authenticated_page, "green", "pointer", "Slave", "slave")
    except Exception as e:
        authenticated_page.screenshot(path="UI/error_screenshots/cluster_state_slave_error.png")
        raise e

@pytest.mark.skipif(CURRENT_CLUSTER_STATE != "master", reason="Тест запускается только для состояния master")
def test_cluster_info_popup_master(authenticated_page: Page, request, credentials):
    """
    Проверяет, что при клике на индикатор Master появляется корректное информационное окно.
    """
    try:
        # Локатор для SVG-индикатора Master
        master_svg_locator = authenticated_page.locator('div.MuiBox-root svg[fill="green"][aria-label="Master"]')
        
        # Убеждаемся, что индикатор виден и кликабелен
        expect(master_svg_locator).to_be_visible()
        expect(master_svg_locator).to_have_attribute('style', 'cursor: pointer;')

        # Убеждаемся, что всплывающее окно из предыдущего состояния закрыто
        expect(authenticated_page.locator('.MuiBackdrop-root')).not_to_be_visible()

        # Кликаем на индикатор
        master_svg_locator.click()

        # Проверяем видимость всплывающего окна
        cluster_info_popup = authenticated_page.locator('.MuiPaper-root.MuiPopover-paper:has-text("Информация о кластере")')
        expect(cluster_info_popup).to_be_visible()

        # Проверяем текст режима в окне
        mode_text_locator = cluster_info_popup.locator('p.MuiTypography-root:has-text("Режим:")')
        expect(mode_text_locator).to_be_visible()
        expect(mode_text_locator).to_have_text("Режим: Master")

        # Закрываем всплывающее окно кликом по центру экрана
        authenticated_page.mouse.click(authenticated_page.viewport_size['width'] / 2, authenticated_page.viewport_size['height'] / 2)

    except Exception as e:
        authenticated_page.screenshot(path="UI/error_screenshots/cluster_info_popup_master_error.png")
        raise e

@pytest.mark.skipif(CURRENT_CLUSTER_STATE != "slave", reason="Тест запускается только для состояния slave")
def test_cluster_info_popup_slave(authenticated_page: Page, request, credentials):
    """
    Проверяет, что при клике на индикатор Slave появляется корректное информационное окно.
    """
    try:
        # Локатор для SVG-индикатора Slave
        slave_svg_locator = authenticated_page.locator('div.MuiBox-root svg[fill="green"][aria-label="Slave"]')
        
        # Убеждаемся, что индикатор виден и кликабелен
        expect(slave_svg_locator).to_be_visible()
        expect(slave_svg_locator).to_have_attribute('style', 'cursor: pointer;')

        # Убеждаемся, что всплывающее окно из предыдущего состояния закрыто
        expect(authenticated_page.locator('.MuiBackdrop-root')).not_to_be_visible()

        # Кликаем на индикатор
        slave_svg_locator.click()

        # Проверяем видимость всплывающего окна
        cluster_info_popup = authenticated_page.locator('.MuiPaper-root.MuiPopover-paper:has-text("Информация о кластере")')
        expect(cluster_info_popup).to_be_visible()

        # Проверяем текст режима в окне
        mode_text_locator = cluster_info_popup.locator('p.MuiTypography-root:has-text("Режим:")')
        expect(mode_text_locator).to_be_visible()
        expect(mode_text_locator).to_have_text("Режим: Slave")

        # Закрываем всплывающее окно кликом по центру экрана
        authenticated_page.mouse.click(authenticated_page.viewport_size['width'] / 2, authenticated_page.viewport_size['height'] / 2)

    except Exception as e:
        authenticated_page.screenshot(path="UI/error_screenshots/cluster_info_popup_slave_error.png")
        raise e

@pytest.mark.skipif(CURRENT_CLUSTER_STATE != "standalone", reason="Тест запускается только для состояния standalone")
def test_cluster_state_standalone_negative_indicators(authenticated_page: Page, request, credentials):
    """
    Проверяет, что при состоянии кластера 'standalone' индикаторы Master и Slave не видны.
    """
    try:
        # Проверяем, что индикатор Master не виден
        master_svg_locator = authenticated_page.locator('div.MuiBox-root svg[fill="green"][aria-label="Master"]')
        expect(master_svg_locator).not_to_be_visible()

        # Проверяем, что индикатор Slave не виден
        slave_svg_locator = authenticated_page.locator('div.MuiBox-root svg[fill="green"][aria-label="Slave"]')
        expect(slave_svg_locator).not_to_be_visible()

    except Exception as e:
        authenticated_page.screenshot(path="UI/error_screenshots/cluster_state_standalone_negative_error.png")
        raise e

@pytest.mark.skipif(CURRENT_CLUSTER_STATE != "master", reason="Тест запускается только для состояния master")
def test_cluster_state_master_negative_indicators(authenticated_page: Page, request, credentials):
    """
    Проверяет, что при состоянии кластера 'master' индикатор Standalone не виден.
    """
    try:
        # Проверяем, что индикатор Standalone не виден
        standalone_svg_locator = authenticated_page.locator('div.MuiBox-root svg[fill="gray"][aria-label=""]')
        expect(standalone_svg_locator).not_to_be_visible()

    except Exception as e:
        authenticated_page.screenshot(path="UI/error_screenshots/cluster_state_master_negative_error.png")
        raise e

@pytest.mark.skipif(CURRENT_CLUSTER_STATE != "slave", reason="Тест запускается только для состояния slave")
def test_cluster_state_slave_negative_indicators(authenticated_page: Page, request, credentials):
    """
    Проверяет, что при состоянии кластера 'slave' индикатор Standalone не виден.
    """
    try:
        # Проверяем, что индикатор Standalone не виден
        standalone_svg_locator = authenticated_page.locator('div.MuiBox-root svg[fill="gray"][aria-label=""]')
        expect(standalone_svg_locator).not_to_be_visible()

    except Exception as e:
        authenticated_page.screenshot(path="UI/error_screenshots/cluster_state_slave_negative_error.png")
        raise e

@pytest.mark.skipif(CURRENT_CLUSTER_STATE != "standalone", reason="Тест запускается только для состояния standalone")
def test_cluster_state_standalone_no_popup(authenticated_page: Page, request, credentials):
    """
    Проверяет, что при состоянии кластера 'standalone' и клике на индикатор всплывающее окно не появляется.
    """
    try:
        # Локатор для SVG-индикатора Standalone
        standalone_svg_locator = authenticated_page.locator('div.MuiBox-root svg[fill="gray"][aria-label=""]')
        
        # Убеждаемся, что индикатор виден (позитивная проверка, что элемент вообще существует)
        expect(standalone_svg_locator).to_be_visible()

        # Кликаем на индикатор
        standalone_svg_locator.click()

        # Проверяем, что всплывающее окно не видимо
        cluster_info_popup = authenticated_page.locator('.MuiPaper-root.MuiPopover-paper:has-text("Информация о кластере")')
        expect(cluster_info_popup).not_to_be_visible()

    except Exception as e:
        authenticated_page.screenshot(path="UI/error_screenshots/cluster_state_standalone_no_popup_error.png")
        raise e

@pytest.mark.skipif(CURRENT_CLUSTER_STATE != "master", reason="Тест запускается только для состояния master")
def test_cluster_info_popup_master_incorrect_mode_content(authenticated_page: Page, request, credentials):
    """
    Проверяет, что при клике на индикатор Master, во всплывающем окне НЕ отображается текст "Режим: Slave".
    """
    try:
        master_svg_locator = authenticated_page.locator('div.MuiBox-root svg[fill="green"][aria-label="Master"]')
        expect(master_svg_locator).to_be_visible()
        expect(master_svg_locator).to_have_attribute('style', 'cursor: pointer;')

        # Убеждаемся, что всплывающее окно из предыдущего состояния закрыто
        expect(authenticated_page.locator('.MuiBackdrop-root')).not_to_be_visible()

        # Кликаем на индикатор
        master_svg_locator.click()

        # Проверяем видимость всплывающего окна
        cluster_info_popup = authenticated_page.locator('.MuiPaper-root.MuiPopover-paper:has-text("Информация о кластере")')
        expect(cluster_info_popup).to_be_visible()

        # Проверяем текст режима в окне
        mode_text_locator = cluster_info_popup.locator('p.MuiTypography-root:has-text("Режим:")')
        expect(mode_text_locator).to_be_visible()
        expect(mode_text_locator).not_to_have_text("Режим: Slave")

        # Закрываем всплывающее окно кликом по центру экрана
        authenticated_page.mouse.click(authenticated_page.viewport_size['width'] / 2, authenticated_page.viewport_size['height'] / 2)

    except Exception as e:
        authenticated_page.screenshot(path="UI/error_screenshots/cluster_info_popup_master_incorrect_mode_error.png")
        raise e

@pytest.mark.skipif(CURRENT_CLUSTER_STATE != "slave", reason="Тест запускается только для состояния slave")
def test_cluster_info_popup_slave_incorrect_mode_content(authenticated_page: Page, request, credentials):
    """
    Проверяет, что при клике на индикатор Slave, во всплывающем окне НЕ отображается текст "Режим: Master".
    """
    try:
        slave_svg_locator = authenticated_page.locator('div.MuiBox-root svg[fill="green"][aria-label="Slave"]')
        expect(slave_svg_locator).to_be_visible()
        expect(slave_svg_locator).to_have_attribute('style', 'cursor: pointer;')

        # Убеждаемся, что всплывающее окно из предыдущего состояния закрыто
        expect(authenticated_page.locator('.MuiBackdrop-root')).not_to_be_visible()

        # Кликаем на индикатор
        slave_svg_locator.click()
        
        # Проверяем видимость всплывающего окна
        cluster_info_popup = authenticated_page.locator('.MuiPaper-root.MuiPopover-paper:has-text("Информация о кластере")')
        expect(cluster_info_popup).to_be_visible()

        # Проверяем текст режима в окне
        mode_text_locator = cluster_info_popup.locator('p.MuiTypography-root:has-text("Режим:")')
        expect(mode_text_locator).to_be_visible()
        expect(mode_text_locator).not_to_have_text("Режим: Master")

        # Закрываем всплывающее окно кликом по центру экрана
        authenticated_page.mouse.click(authenticated_page.viewport_size['width'] / 2, authenticated_page.viewport_size['height'] / 2)

    except Exception as e:
        authenticated_page.screenshot(path="UI/error_screenshots/cluster_info_popup_slave_incorrect_mode_error.png")
        raise e 