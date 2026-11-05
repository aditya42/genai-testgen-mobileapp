"""Conservative, deterministic eligibility checks for Jira review candidates."""

import re

INFRA = (
    "connection", "timed out", "timeout", "device offline", "no such element",
    "session not created", "unknown server error", "webdriverexception",
    "stale element", "network error", "element not found", "socket",
    "connection refused", "failed to create session",
)
ASSERTION = ("assertionerror", "assertion failed", "assert ")


def _assertion_detail(error):
    """Extract the same application assertion across retry stack traces."""
    lines = str(error).splitlines()
    for line in reversed(lines):
        content = line.strip()
        match = re.search(r"(?:AssertionError:|AssertionError\b)(.*)", content, re.I)
        if match:
            return re.sub(r"\s+", " ", match.group(1)).strip().lower()
    return ""


def jira_eligible(attempts):
    """Only repeated, identical application assertions qualify for review.

    This is not proof of an app defect; failures from infrastructure and
    element location remain in CI/TestRail rather than opening Jira tickets.
    """
    if len(attempts) < 2:
        return False
    details = []
    for attempt in attempts:
        if attempt.get("status") != "failed" or attempt.get("phase") == "setup":
            return False
        message = str(attempt.get("error", "")).lower()
        if not any(marker in message for marker in ASSERTION):
            return False
        if any(marker in message for marker in INFRA):
            return False
        detail = _assertion_detail(message)
        if not detail:
            return False
        details.append(detail)
    return len(set(details)) == 1
