"""Strict and conservative classification of Appium UI failures."""

INFRA = ("connection", "timed out", "timeout", "appium", "device offline",
         "no such element", "session not created", "unknown server error",
         "webdriverexception", "stale element", "network error")
ASSERTION = ("assertionerror", "assert ", "assertion failed")


def jira_eligible(attempts):
    """Return true only for twice-reproduced application assertions.

    This only qualifies a candidate; it is not proof of a real product defect.
    """
    if len(attempts) < 2:
        return False
    for attempt in attempts:
        message = str(attempt.get("error", "")).lower()
        if attempt.get("status") != "failed" or not any(x in message for x in ASSERTION):
            return False
        if any(x in message for x in INFRA):
            return False
    return True
