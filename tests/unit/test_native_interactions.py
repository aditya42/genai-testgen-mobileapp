"""Regression coverage for the two Android failures from BrowserStack run 41812021962."""

from unittest.mock import Mock, patch

import pytest

from mobileqa.pages import LoginScreen, ProductScreen
from appium.webdriver.common.appiumby import AppiumBy


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
    button.rect = {"x": 25, "y": 267, "width": 340, "height": 41}
    with patch("mobileqa.pages.WebDriverWait") as waiter:
        waiter.return_value.until.side_effect = (
            [TimeoutException(), button, Mock()] if platform == "iOS"
            else [TimeoutException(), button]
        )
        screen.add_to_cart()
    commands = [call.args[0] for call in driver.execute_script.call_args_list]
    assert any(direction in command for command in commands)
    assert commands.count("mobile: tap") == (1 if platform == "iOS" else 0)
    if platform == "iOS":
        button.click.assert_not_called()
        assert any(
            call.args[0] == "mobile: tap"
            for call in driver.execute_script.call_args_list
        )
    else:
        button.click.assert_called_once()


@pytest.mark.parametrize("platform,expected_attributes", [
    ("Android", {"content-desc", "text", "name"}),
    ("iOS", {"label", "name", "value"}),
])
def test_login_error_reads_only_supported_platform_attributes(platform, expected_attributes):
    element = Mock()
    element.text = ""
    message = "Username and password do not match any user in this service."
    element.get_attribute.side_effect = lambda key: (
        message if key == ("label" if platform == "iOS" else "content-desc")
        else None
    )
    element.find_elements.return_value = []
    driver = Mock()
    driver.capabilities = {"platformName": platform}
    screen = LoginScreen(driver, {"login_error": {
        "by": "accessibility id", "value": "test-Error message"
    }})
    with patch.object(screen, "visible", return_value=element):
        screen.assert_invalid_password()
    attributes_used = {call.args[0] for call in element.get_attribute.call_args_list}
    assert attributes_used == expected_attributes


def test_cart_asserts_product_without_relying_on_screen_header():
    from mobileqa.pages import CartScreen

    driver = Mock()
    screen = CartScreen(driver, {"cart_item": {
        "by": "accessibility id", "value": "test-Item"
    }})
    item = Mock()
    item.is_displayed.return_value = True
    with patch.object(screen, "visible", return_value=item) as visible:
        screen.assert_item()
    visible.assert_called_once_with("cart_item")


def test_ios_cart_clicks_nested_actionable_child():
    driver = Mock()
    driver.capabilities = {"platformName": "iOS"}
    parent = Mock()
    child = Mock()
    parent.find_element.return_value = child
    screen = ProductScreen(driver, {"cart_button": {
        "by": "accessibility id", "value": "test-Cart"
    }})
    with patch.object(screen, "visible", return_value=parent):
        screen.open_cart()
    parent.find_element.assert_called_once_with(AppiumBy.XPATH, "./*")
    child.click.assert_called_once()
    driver.execute_script.assert_not_called()


def test_android_cart_keeps_element_click():
    driver = Mock()
    driver.capabilities = {"platformName": "Android"}
    screen = ProductScreen(driver, {})
    with patch.object(screen, "tap") as tap:
        screen.open_cart()
    tap.assert_called_once_with("cart_button")
    driver.execute_script.assert_not_called()


def test_android_add_to_cart_uses_element_click():
    driver = Mock()
    driver.capabilities = {"platformName": "Android"}
    screen = ProductScreen(driver, {"add_to_cart": {
        "by": "accessibility id", "value": "test-ADD TO CART"
    }})
    button = Mock()
    with patch("mobileqa.pages.WebDriverWait") as waiter:
        waiter.return_value.until.return_value = button
        screen.add_to_cart()
    button.click.assert_called_once()
    driver.execute_script.assert_not_called()


def test_ios_requires_remove_state_after_add_to_cart():
    driver = Mock()
    driver.capabilities = {"platformName": "iOS"}
    screen = ProductScreen(driver, {"add_to_cart": {
        "by": "accessibility id", "value": "test-ADD TO CART"
    }})
    button = Mock()
    button.rect = {"x": 25, "y": 267, "width": 340, "height": 41}
    with patch("mobileqa.pages.WebDriverWait") as waiter:
        waiter.return_value.until.side_effect = [button, Mock()]
        screen.add_to_cart()
    button.click.assert_not_called()
    driver.execute_script.assert_called_once_with(
        "mobile: tap", {"x": 195, "y": 287}
    )
    assert waiter.return_value.until.call_count == 2
    assert "Add to cart click did not produce REMOVE state" in (
        waiter.return_value.until.call_args.args[1]
    )
