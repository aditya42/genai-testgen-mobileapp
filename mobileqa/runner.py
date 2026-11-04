"""Compile reviewed Swag Labs actions into native screen methods, never arbitrary LLM code."""

from mobileqa.pages import (
    CartScreen, CatalogScreen, LoginScreen, ProductScreen, load_selectors,
)

STANDARD_USERNAME = "standard_user"
STANDARD_PASSWORD = "secret_sauce"

ALLOWED = {
    "login_standard", "login_invalid_password", "assert_invalid_login_error",
    "assert_catalog", "open_first_product", "assert_product_details",
    "add_to_cart", "open_cart", "assert_cart_item",
}


def execute(driver, platform, case):
    selectors = load_selectors(platform)
    login = LoginScreen(driver, selectors)
    catalog = CatalogScreen(driver, selectors)
    product = ProductScreen(driver, selectors)
    cart = CartScreen(driver, selectors)
    actions = {
        "login_standard": lambda: login.sign_in(STANDARD_USERNAME, STANDARD_PASSWORD),
        "login_invalid_password": lambda: login.sign_in(
            STANDARD_USERNAME, "invalid_password"
        ),
        "assert_invalid_login_error": login.assert_invalid_password,
        "assert_catalog": catalog.assert_catalog,
        "open_first_product": catalog.open_first_product,
        "assert_product_details": product.assert_details,
        "add_to_cart": product.add_to_cart,
        "open_cart": product.open_cart,
        "assert_cart_item": cart.assert_item,
    }
    for step in case["actions"]:
        if step not in ALLOWED:
            raise ValueError(f"Unapproved action: {step}")
        actions[step]()
