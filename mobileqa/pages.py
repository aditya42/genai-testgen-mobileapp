"""Native Swag Labs 2.7.1 screen objects; platform locators are in config/*.json."""

import json
from pathlib import Path

from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait

ROOT = Path(__file__).resolve().parents[1]
SELECTOR_TYPES = {"accessibility id": AppiumBy.ACCESSIBILITY_ID,
                  "id": AppiumBy.ID, "xpath": AppiumBy.XPATH}
REQUIRED = {"username", "password", "login_button", "login_error",
            "catalog", "first_product", "product_detail", "add_to_cart",
            "cart_button", "cart_screen", "cart_item"}


def load_selectors(platform):
    if platform not in ("android", "ios"):
        raise ValueError("Unsupported platform")
    data = json.loads((ROOT / "config" / f"{platform}.json").read_text())
    if not REQUIRED.issubset(data):
        raise ValueError("Missing selectors: " + ", ".join(sorted(REQUIRED - set(data))))
    for key, locator in data.items():
        if key.startswith("_"):
            continue
        if locator.get("by") not in SELECTOR_TYPES or not locator.get("value"):
            raise ValueError(f"Unsupported or missing selector: {key}")
    return data


class BaseScreen:
    def __init__(self, driver, selectors, timeout=20):
        self.driver, self.selectors, self.timeout = driver, selectors, timeout

    def locator(self, name):
        entry = self.selectors[name]
        return SELECTOR_TYPES[entry["by"]], entry["value"]

    def visible(self, name):
        return WebDriverWait(self.driver, self.timeout).until(
            ec.visibility_of_element_located(self.locator(name))
        )

    def tap(self, name):
        WebDriverWait(self.driver, self.timeout).until(
            ec.element_to_be_clickable(self.locator(name))
        ).click()


class LoginScreen(BaseScreen):
    def sign_in(self, username, password):
        self.visible("username").send_keys(username)
        self.visible("password").send_keys(password)
        self.tap("login_button")

    def assert_invalid_password(self):
        message = self.visible("login_error").text
        assert "Username and password do not match" in message, (
            f"Incorrect login error: {message!r}"
        )


class CatalogScreen(BaseScreen):
    def assert_catalog(self):
        assert self.visible("catalog").is_displayed(), "Product inventory not displayed"

    def open_first_product(self):
        self.tap("first_product")


class ProductScreen(BaseScreen):
    def assert_details(self):
        assert self.visible("product_detail").is_displayed(), "Product details not displayed"

    def add_to_cart(self):
        self.tap("add_to_cart")

    def open_cart(self):
        self.tap("cart_button")


class CartScreen(BaseScreen):
    def assert_item(self):
        assert self.visible("cart_screen").is_displayed(), "Cart screen not displayed"
        assert self.visible("cart_item").is_displayed(), "Product missing from cart"
