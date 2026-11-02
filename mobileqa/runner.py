"""Execute allowlisted native actions only (never model-generated code)."""

from mobileqa.pages import CartScreen, CatalogScreen, ProductScreen, load_selectors

ALLOWED = {"assert_catalog", "open_first_product", "assert_product_details",
           "add_to_cart", "open_cart", "assert_cart_item"}


def execute(driver, platform, case):
    selectors = load_selectors(platform)
    catalog = CatalogScreen(driver, selectors)
    product = ProductScreen(driver, selectors)
    cart = CartScreen(driver, selectors)
    actions = {
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
