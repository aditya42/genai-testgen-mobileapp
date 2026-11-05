"""Isolated real-device Appium assertion failure for Jira integration validation.

This is a deliberately inverted expected result, NOT a Swag Labs defect.
It is never included in normal mobile regression execution.
"""

from mobileqa.pages import CatalogScreen, LoginScreen, load_selectors


def test_inverted_catalog_assertion_creates_repeatable_failure(driver, request):
    request.node.user_properties.append(("case_id", "IOS-JIRA-ASSERT-001"))
    selectors = load_selectors("ios")
    LoginScreen(driver, selectors).sign_in("standard_user", "secret_sauce")
    catalog = CatalogScreen(driver, selectors)
    catalog.assert_catalog()
    observed = catalog.visible("catalog").is_displayed()
    # Real Appium screen observation; the deliberately incorrect oracle
    # guarantees a repeatable assertion failure after catalog is visible.
    assert not observed, (
        "Intentional Jira E2E validation: catalog was visible, "
        "but the deliberately inverted expectation required it hidden"
    )
