"""Offline verification of TestRail/Jira side-effect boundaries."""

import pytest

from mobileqa import integrations


def fake_report(platform):
    return {"platform": platform, "cases": [
        {"id": f"{platform.upper()}-LOGIN-001",
         "status": "passed", "attempts": [{"status": "passed", "error": ""}]},
        {"id": f"{platform.upper()}-LOGIN-002",
         "status": "passed", "attempts": [{"status": "passed", "error": ""}]},
        {"id": f"{platform.upper()}-CATALOG-001",
         "status": "passed", "attempts": [{"status": "passed", "error": ""}]},
        {"id": f"{platform.upper()}-PRODUCT-001",
         "status": "passed", "attempts": [{"status": "passed", "error": ""}]},
        {"id": f"{platform.upper()}-CART-001",
         "status": "passed", "attempts": [{"status": "passed", "error": ""}]},
    ]}


@pytest.mark.parametrize("platform", ["android", "ios"])
def test_testrail_publishes_five_platform_cases(platform, monkeypatch):
    monkeypatch.setenv("TESTRAIL_PROJECT_ID", "1")
    monkeypatch.setenv("TESTRAIL_SECTION_ID", "1")
    monkeypatch.setenv("GITHUB_RUN_ID", "unit-run")
    calls = []
    current = 100

    def fake_testrail(path, method="GET", payload=None):
        nonlocal current
        calls.append((path, method, payload))
        if path.startswith("get_cases/"):
            return {"cases": [], "_links": {"next": None}}
        if path.startswith("get_runs/"):
            return {"runs": [], "_links": {"next": None}}
        if path.startswith("add_case/"):
            current += 1
            return {"id": current}
        if path.startswith("add_run/"):
            return {"id": 42}
        if path.startswith("add_result_for_case/"):
            return {"id": 200}
        raise AssertionError(path)

    monkeypatch.setattr(integrations, "testrail", fake_testrail)
    monkeypatch.setattr(integrations, "load_plan",
                        lambda value: __import__("mobileqa.generator", fromlist=["base_cases"])
                        .base_cases(value))
    run_id, mapping = integrations.publish_testrail(platform, fake_report(platform))
    assert run_id == 42
    assert len(mapping) == 5
    assert len([call for call in calls if call[0].startswith("add_case/")]) == 5
    assert len([call for call in calls if call[0].startswith("add_result_for_case/")]) == 5
    posted = next(call[2] for call in calls if call[0] == "add_run/1")
    assert "GitHub" not in posted["name"]
    assert "unit-run" in posted["description"]


def test_partial_report_is_not_published(monkeypatch):
    monkeypatch.setenv("TESTRAIL_PROJECT_ID", "1")
    monkeypatch.setenv("TESTRAIL_SECTION_ID", "1")
    monkeypatch.setattr(integrations, "load_plan",
                        lambda platform: __import__("mobileqa.generator", fromlist=["base_cases"])
                        .base_cases(platform))
    monkeypatch.setattr(integrations, "testrail",
                        lambda *args, **kwargs: {"cases": [], "_links": {"next": None}})
    with pytest.raises(RuntimeError, match="Incomplete test results"):
        integrations.publish_testrail("android", {"cases": []})


def test_flaky_test_never_creates_jira_issue(monkeypatch):
    monkeypatch.setenv("JIRA_PROJECT_KEY", "KAN")
    monkeypatch.setattr(integrations, "jira",
                        lambda *args, **kwargs: pytest.fail("Jira should not be called"))
    failed = {"status": "failed", "error": "AssertionError: cart quantity"}
    passed = {"status": "passed", "error": ""}
    report = {"cases": [{"id": "ANDROID-CART-001", "status": "passed",
                         "attempts": [failed, passed]}]}
    assert integrations.publish_jira_candidates("android", report) == []


def test_repeated_assertion_creates_review_candidate(monkeypatch):
    monkeypatch.setenv("JIRA_PROJECT_KEY", "KAN")
    failed = {"status": "failed", "error": "AssertionError: cart quantity is incorrect"}
    report = {"cases": [{"id": "IOS-CART-001", "status": "failed",
                         "attempts": [failed, failed]}]}
    posted = []

    def fake_jira(path, method="GET", payload=None, params=None):
        if path == "search/jql":
            return {"issues": []}
        if path == "project/KAN":
            return {"issueTypes": [{"id": "101", "name": "Bug"}]}
        if path == "issue" and method == "POST":
            posted.append(payload)
            return {"key": "KAN-22"}
        raise AssertionError(path)

    monkeypatch.setattr(integrations, "jira", fake_jira)
    assert integrations.publish_jira_candidates("ios", report, 44, {}) == ["KAN-22"]
    assert "needs-triage" in posted[0]["fields"]["labels"]
    assert "IOS-CART-001" in posted[0]["fields"]["summary"]



def test_jira_preview_is_read_only(monkeypatch):
    monkeypatch.delenv("JIRA_PROJECT_KEY", raising=False)
    monkeypatch.setattr(integrations, "jira",
                        lambda *args, **kwargs: pytest.fail("Preview contacted Jira"))
    failed = {"status": "failed", "error": "AssertionError: wrong cart quantity"}
    report = {"cases": [
        {"id": "ANDROID-CART-001", "status": "failed",
         "attempts": [failed, failed]},
        {"id": "ANDROID-PRODUCT-001", "status": "passed",
         "attempts": [{"status": "passed", "error": ""}]},
    ]}
    assert integrations.preview_jira_candidates("android", report) == [
        "ANDROID-CART-001"
    ]


def test_existing_jira_issue_reused_without_creating_duplicate(monkeypatch):
    monkeypatch.setenv("JIRA_PROJECT_KEY", "KAN")
    failed = {"status": "failed", "error": "AssertionError: quantity mismatch"}
    report = {"cases": [{"id": "IOS-CART-001", "status": "failed",
                          "attempts": [failed, failed]}]}
    requested = []

    def fake_jira(path, method="GET", payload=None, params=None):
        requested.append((path, method, params))
        if path == "search/jql":
            assert 'genai-mobile-ios-cart-001' in params["jql"]
            return {"issues": [{"key": "KAN-22"}]}
        pytest.fail(f"Unexpected Jira request: {method} {path}")

    monkeypatch.setattr(integrations, "jira", fake_jira)
    assert integrations.publish_jira_candidates("ios", report) == ["KAN-22"]
    assert len(requested) == 1


def test_infrastructure_failure_never_queries_jira(monkeypatch):
    monkeypatch.setenv("JIRA_PROJECT_KEY", "KAN")
    monkeypatch.setattr(integrations, "jira",
                        lambda *args, **kwargs: pytest.fail("Jira must not be called"))
    failed = {"status": "failed",
              "error": "TimeoutException: No such element on Android"}
    report = {"cases": [{"id": "ANDROID-CART-001", "status": "failed",
                          "attempts": [failed, failed]}]}
    assert integrations.publish_jira_candidates("android", report) == []


def test_live_jira_smoke_rejects_unconfirmed_execution(monkeypatch):
    monkeypatch.delenv("JIRA_LIVE_SMOKE_CONFIRM", raising=False)
    monkeypatch.setattr(integrations, "jira",
                        lambda *args, **kwargs: pytest.fail("Unexpected Jira call"))
    with pytest.raises(ValueError, match="explicit confirmation"):
        integrations.verify_jira_live("ios")


def test_live_jira_smoke_creates_and_reuses_one_issue(monkeypatch):
    monkeypatch.setenv("JIRA_LIVE_SMOKE_CONFIRM", "YES")
    monkeypatch.setenv("JIRA_URL", "https://example.atlassian.net")
    monkeypatch.setenv("JIRA_PROJECT_KEY", "KAN")
    monkeypatch.setenv("JIRA_EMAIL", "fake@example.com")
    monkeypatch.setenv("JIRA_API_TOKEN", "dummy")
    created = []
    lookups = []

    def fake_jira(path, method="GET", payload=None, params=None):
        if path == "search/jql":
            lookups.append(params["jql"])
            return {"issues": [{"key": "KAN-100"}] if created else []}
        if path == "project/KAN":
            return {"issueTypes": [{"id": "10001", "name": "Bug"}]}
        if path == "issue" and method == "POST":
            assert "[INTEGRATION TEST - NOT A DEFECT]" in payload["fields"]["summary"]
            assert "integration-test" in payload["fields"]["labels"]
            assert "needs-triage" not in payload["fields"]["labels"]
            created.append(payload)
            return {"key": "KAN-100"}
        if path == "issue/KAN-100":
            return {"fields": {
                "summary": "[INTEGRATION TEST - NOT A DEFECT][IOS] IOS-JIRA-SMOKE-001",
                "labels": ["integration-test", "genai-mobile-ios-jira-smoke-001"],
            }}
        pytest.fail(f"Unexpected Jira call: {method} {path}")

    monkeypatch.setattr(integrations, "jira", fake_jira)
    result = integrations.verify_jira_live("ios")
    assert result["issue"] == "KAN-100"
    assert result["duplicate_count"] == 0
    assert len(created) == 1
    assert len(lookups) >= 3
    assert all('genai-mobile-ios-jira-smoke-001' in query for query in lookups)


def test_live_jira_smoke_reuses_prior_ticket(monkeypatch):
    monkeypatch.setenv("JIRA_LIVE_SMOKE_CONFIRM", "YES")
    for key, value in {
        "JIRA_URL": "https://example.atlassian.net",
        "JIRA_PROJECT_KEY": "KAN",
        "JIRA_EMAIL": "fake@example.com",
        "JIRA_API_TOKEN": "dummy",
    }.items():
        monkeypatch.setenv(key, value)

    def fake_jira(path, method="GET", payload=None, params=None):
        if path == "search/jql":
            return {"issues": [{"key": "KAN-100"}]}
        if path == "issue/KAN-100":
            return {"fields": {
                "summary": "[INTEGRATION TEST - NOT A DEFECT][IOS] IOS-JIRA-SMOKE-001",
                "labels": ["integration-test", "genai-mobile-ios-jira-smoke-001"],
            }}
        pytest.fail(f"Unexpected request: {method} {path}")

    monkeypatch.setattr(integrations, "jira", fake_jira)
    outcome = integrations.verify_jira_live("ios")
    assert outcome["first_pass"] == "reused existing smoke issue"
    assert outcome["second_pass"] == "reused same issue"
