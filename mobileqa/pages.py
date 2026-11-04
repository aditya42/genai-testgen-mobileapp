"""Native Swag Labs 2.7.1 screen objects; platform locators are in config/*.json."""

import json
from pathlib import Path

from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException

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
        # Native Android accessibility wrappers may have empty .text while the
        # meaningful message is exposed as a content description or child label.
        def error_message(_driver):
            element = self.visible("login_error")
            platform = str(
                self.driver.capabilities.get("platformName", "")
            ).lower()
            # Avoid requesting 'label' on UiAutomator2: Android rejects that
            # iOS-only attribute with UnknownMethodException.
            attributes = (
                ("label", "name", "value") if platform == "ios"
                else ("content-desc", "text", "name")
            )
            candidates = [element.text]
            candidates.extend(element.get_attribute(key) for key in attributes)
            if platform == "android":
                candidates.extend(
                    child.text for child in element.find_elements(
                        AppiumBy.CLASS_NAME, "android.widget.TextView"
                    )
                )
            return next(
                (value for value in candidates if value and
                 "Username and password do not match" in value), False
            )

        message = WebDriverWait(self.driver, self.timeout).until(
            error_message, "Expected invalid-login error was not exposed to Appium"
        )
        assert "Username and password do not match" in message


class CatalogScreen(BaseScreen):
    def assert_catalog(self):
        assert self.visible("catalog").is_displayed(), "Product inventory not displayed"

    def open_first_product(self):
        self.tap("first_product")


class ProductScreen(BaseScreen):
    def assert_details(self):
        assert self.visible("product_detail").is_displayed(), "Product details not displayed"

    def add_to_cart(self):
        # Product details place the purchase controls below the initial viewport
        # on some Android devices; use a bounded native scroll before failing.
        for attempt in range(3):
            try:
                WebDriverWait(self.driver, 4).until(
                    ec.element_to_be_clickable(self.locator("add_to_cart"))
                ).click()
                return
            except TimeoutException:
                if attempt == 2:
                    raise TimeoutException(
                        "Add to cart not found after two scroll gestures: "
                        f"{self.locator('add_to_cart')}"
                    ) from None
                size = self.driver.get_window_size()
                if str(self.driver.capabilities.get("platformName", "")).lower() == "ios":
                    self.driver.execute_script("mobile: swipe", {"direction": "up"})
                else:
                    self.driver.execute_script("mobile: scrollGesture", {
                        "left": int(size["width"] * 0.1),
                        "top": int(size["height"] * 0.25),
                        "width": int(size["width"] * 0.8),
                        "height": int(size["height"] * 0.6),
                        "direction": "down",
                        "percent": 0.75,
                    })

    def open_cart(self):
        self.tap("cart_button")


class CartScreen(BaseScreen):
    def assert_item(self):
        # The cart header is not consistently exposed in the iOS accessibility
        # hierarchy; verify the user-facing result instead of a screen wrapper.
        assert self.visible("cart_item").is_displayed(), "Product missing from cart"
