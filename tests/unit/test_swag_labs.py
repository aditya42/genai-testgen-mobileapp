"""Validate that the acceptance flows match the uploaded Swag Labs Sample 2.7.1."""

import pytest

from mobileqa.generator import base_cases
from mobileqa.pages import REQUIRED, load_selectors
from mobileqa.runner import ALLOWED


@pytest.mark.parametrize("platform", ["android", "ios"])
def test_requires_login_before_authenticated_product_operations(platform):
    cases = base_cases(platform)
    for case in cases:
        assert set(case["actions"]).issubset(ALLOWED)
        if case["intent"] in ("catalog_visible", "product_details", "add_to_cart"):
            assert case["actions"][0] == "login_standard"
    assert next(c for c in cases if c["intent"] == "invalid_password")["actions"] == [
        "login_invalid_password", "assert_invalid_login_error"
    ]


@pytest.mark.parametrize("platform", ["android", "ios"])
def test_all_native_selector_names_present(platform):
    selectors = load_selectors(platform)
    assert REQUIRED.issubset(selectors)
    assert selectors["cart_item"]["value"] == "test-Item"
    assert selectors["cart_screen"]["value"] == "test-Cart Content"
    assert selectors["login_button"]["value"] == "test-LOGIN"
