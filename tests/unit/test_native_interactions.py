"""Regression coverage for the two Android failures from BrowserStack run 41812021962."""

from unittest.mock import Mock, patch

import pytest

from mobileqa.pages import LoginScreen, ProductScreen


def test_login_error_uses_native_content_description_when_text_is_empty():
    element = Mock()
    element.text = ""
    element.get_attribute.side_effect = lambda key: (
        "Username and password do not match any user in this service."
        if key == "content-desc" else None
    )
    element.find_elements.return_value = []
    driver = Mock()
    screen = LoginScreen(driver, {"login_error": {
        "by": "accessibility id", "value": "test-Error message"
    }})
    with patch.object(screen, "visible", return_value=element):
        screen.assert_invalid_password()


def test_cart_action_clicks_immediately_when_visible():
    driver = Mock()
    screen = ProductScreen(driver, {"add_to_cart": {
        "by": "accessibility id", "value": "test-ADD TO CART"
    }})
    button = Mock()
    with patch("mobileqa.pages.WebDriverWait") as waiter:
        waiter.return_value.until.return_value = button
        screen.add_to_cart()
    button.click.assert_called_once()
    driver.execute_script.assert_not_called()


@pytest.mark.parametrize("platform,direction", [
    ("Android", "scrollGesture"), ("iOS", "swipe")
])
def test_cart_action_scrolls_once_when_initially_offscreen(platform, direction):
    from selenium.common.exceptions import TimeoutException

    driver = Mock()
    driver.capabilities = {"platformName": platform}
    driver.get_window_size.return_value = {"width": 400, "height": 800}
    screen = ProductScreen(driver, {"add_to_cart": {
        "by": "accessibility id", "value": "test-ADD TO CART"
    }})
    button = Mock()
    with patch("mobileqa.pages.WebDriverWait") as waiter:
        waiter.return_value.until.side_effect = [TimeoutException(), button]
        screen.add_to_cart()
    assert driver.execute_script.call_count == 1
    assert direction in driver.execute_script.call_args.args[0]
    button.click.assert_called_once()
