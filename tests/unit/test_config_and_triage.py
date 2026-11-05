"""Safety and capability settings without remote device sessions."""

import pytest

from mobileqa.config import Settings
from mobileqa.triage import jira_eligible


@pytest.mark.parametrize("platform", ["android", "ios"])
def test_capability_generation(platform):
    values = {
        "BROWSERSTACK_USERNAME": "fake",
        "BROWSERSTACK_ACCESS_KEY": "fake",
        f"BROWSERSTACK_{platform.upper()}_APP_ID": "bs://example",
    }
    settings = Settings.from_env(platform, values)
    result = settings.options("smoke test").to_capabilities()
    assert result["appium:app"] == "bs://example"
    assert result["bstack:options"]["sessionName"] == "smoke test"


def test_no_cloud_session_without_app_id():
    with pytest.raises(ValueError, match="Missing BrowserStack"):
        Settings.from_env("ios", {})


def test_rejects_non_uploaded_app_id():
    values = {"BROWSERSTACK_USERNAME": "fake", "BROWSERSTACK_ACCESS_KEY": "fake",
              "BROWSERSTACK_ANDROID_APP_ID": "/tmp/app.apk"}
    with pytest.raises(ValueError, match="bs://"):
        Settings.from_env("android", values)


def test_jira_eligible_only_for_repeated_assertions():
    failed = {"status": "failed", "error": "AssertionError: expected cart item visible"}
    assert jira_eligible([failed, failed])
    assert not jira_eligible([failed])
    assert not jira_eligible([failed, {"status": "passed", "error": ""}])
    assert not jira_eligible([
        {"status": "failed", "error": "Appium connection timed out"},
        {"status": "failed", "error": "Appium connection timed out"},
    ])



def test_different_assertions_across_retries_are_not_eligible():
    first = {"status": "failed", "error": "AssertionError: cart quantity 0"}
    second = {"status": "failed", "error": "AssertionError: checkout error"}
    assert not jira_eligible([first, second])


def test_locator_failure_with_assertion_is_not_product_defect():
    failed = {"status": "failed",
              "error": "AssertionError: cart missing\\nNoSuchElementException: element not found"}
    assert not jira_eligible([failed, failed])


def test_setup_failures_are_not_jira_eligible():
    failed = {"status": "failed", "phase": "setup",
              "error": "AssertionError: app was not launched"}
    assert not jira_eligible([failed, failed])
