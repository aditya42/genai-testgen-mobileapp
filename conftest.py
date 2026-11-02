"""Pytest fixtures and retry-aware evidence for both mobile platforms."""

import json
import os
import re
from collections import defaultdict
from pathlib import Path

import pytest
from appium import webdriver

from mobileqa.config import HUB_URL, Settings

ATTEMPTS = defaultdict(list)
ERRORS = ("no such element", "timed out", "timeout", "connection", "appium",
          "device offline", "session not created", "unknown server error")


@pytest.fixture
def driver(request):
    platform = os.environ.get("MOBILE_PLATFORM", "android")
    settings = Settings.from_env(platform)
    session = webdriver.Remote(
        command_executor=HUB_URL, options=settings.options(request.node.name)
    )
    request.node._appium_driver = session
    yield session
    try:
        failed = getattr(request.node, "_appium_failed", False)
        verdict = "failed" if failed else "passed"
        reason = "Native Appium test failed" if failed else "Native Appium test passed"
        session.execute_script("browserstack_executor: " + json.dumps({
            "action": "setSessionStatus", "arguments": {"status": verdict, "reason": reason}
        }))
    except Exception:
        pass
    finally:
        session.quit()


def _case_id(item):
    for name, value in item.user_properties:
        if name == "case_id":
            return value
    case = getattr(item, "callspec", None)
    return case.params["case"]["id"] if case and "case" in case.params else None


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    if report.when not in ("setup", "call"):
        return
    if report.when == "setup" and not report.failed:
        return
    case_id = _case_id(item)
    if not case_id:
        return
    message = str(report.longrepr)[:3500] if report.failed else ""
    ATTTEMPT = {
        "status": "failed" if report.failed else "passed",
        "phase": report.when,
        "error": re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", message),
    }
    ATTEMPTS[case_id].append(ATTTEMPT)
    if report.failed:
        item._appium_failed = True
        session = getattr(item, "_appium_driver", None)
        if session is not None:
            try:
                folder = Path("screenshots") / os.environ.get("MOBILE_PLATFORM", "android")
                folder.mkdir(parents=True, exist_ok=True)
                filename = folder / f"{case_id}-{len(ATTEMPTS[case_id])}.png"
                session.save_screenshot(str(filename))
                ATTTEMPT["screenshot"] = str(filename)
            except Exception:
                pass


def pytest_sessionfinish(session, exitstatus):
    if not ATTEMPTS:
        return
    platform = os.environ.get("MOBILE_PLATFORM", "android")
    directory = Path("reports") / platform
    directory.mkdir(parents=True, exist_ok=True)
    cases = [
        {"id": case_id, "attempts": attempts, "status": attempts[-1]["status"]}
        for case_id, attempts in sorted(ATTEMPTS.items())
    ]
    (directory / "results.json").write_text(
        json.dumps({"platform": platform, "cases": cases}, indent=2) + "\n"
    )
