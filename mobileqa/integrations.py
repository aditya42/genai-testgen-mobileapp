"""Publish native mobile results to TestRail; create triaged Jira candidates."""

import argparse
import json
import os
import re
from pathlib import Path

import requests
from requests.auth import HTTPBasicAuth

from mobileqa.generator import load_plan
from mobileqa.triage import jira_eligible


def api(base, path, user, token, method="GET", payload=None, params=None):
    if not base.startswith("https://"):
        raise ValueError("External integration URLs must use HTTPS")
    response = requests.request(
        method, base.rstrip("/") + path,
        auth=HTTPBasicAuth(user, token), json=payload,
        params=params, timeout=30,
        headers={"Accept": "application/json"},
    )
    if not response.ok:
        raise RuntimeError(f"{method} {path.split('?')[0]} failed: HTTP {response.status_code}")
    return response.json() if response.content else {}


def testrail(path, method="GET", payload=None):
    return api(os.environ["TESTRAIL_URL"], "/index.php?/api/v2/" + path,
               os.environ["TESTRAIL_EMAIL"], os.environ["TESTRAIL_API_KEY"],
               method, payload)


def jira(path, method="GET", payload=None, params=None):
    return api(os.environ["JIRA_URL"], "/rest/api/3/" + path,
               os.environ["JIRA_EMAIL"], os.environ["JIRA_API_TOKEN"],
               method, payload, params)


def load_results(platform):
    path = Path("reports") / platform / "results.json"
    if not path.exists():
        raise FileNotFoundError(f"No Appium results at {path}; refusing to publish")
    report = json.loads(path.read_text())
    if report.get("platform") != platform or not report.get("cases"):
        raise ValueError("Unexpected or empty result report")
    return report


def _paginated_cases(project):
    offset = 0
    while True:
        response = testrail(f"get_cases/{project}&limit=250&offset={offset}")
        items = response if isinstance(response, list) else response.get("cases", [])
        yield from items
        next_page = response.get("_links", {}).get("next") if isinstance(response, dict) else None
        if not next_page:
            break
        if not items or offset > 10_000:
            raise RuntimeError("TestRail pagination safety limit reached")
        offset += len(items)


def _run_for_execution(project, platform, case_ids):
    github_run = os.getenv("GITHUB_RUN_ID", "local")
    title = f"Mobile App | {platform.upper()} Regression | BrowserStack App Automate"
    description = f"GitHub Actions run: {github_run}; platform: {platform}"
    offset = 0
    existing = None
    while True:
        response = testrail(f"get_runs/{project}&limit=250&offset={offset}")
        runs = response if isinstance(response, list) else response.get("runs", [])
        for item in runs:
            if item.get("name") != title:
                continue
            detail = testrail(f"get_run/{item['id']}")
            if detail.get("description") == description:
                existing = item
                break
        if existing:
            break
        if not isinstance(response, dict) or not response.get("_links", {}).get("next"):
            break
        if not runs or offset > 10_000:
            raise RuntimeError("TestRail run pagination safety limit reached")
        offset += len(runs)
    if existing:
        return int(existing["id"])
    body = {"name": title, "description": description, "include_all": False,
            "case_ids": case_ids}
    if os.getenv("TESTRAIL_SUITE_ID"):
        body["suite_id"] = int(os.environ["TESTRAIL_SUITE_ID"])
    return int(testrail(f"add_run/{project}", "POST", body)["id"])


def publish_testrail(platform, report):
    project = os.environ["TESTRAIL_PROJECT_ID"]
    section = int(os.environ["TESTRAIL_SECTION_ID"])
    plans = {case["id"]: case for case in load_plan(platform)}
    results = {case["id"]: case for case in report["cases"]}
    if set(results) != set(plans):
        raise RuntimeError("Incomplete test results: refusing to publish a partial run")
    existing = {}
    for case in _paginated_cases(project):
        if int(case.get("section_id", 0)) != section:
            continue
        match = re.match(r"^\[([A-Z]+-[A-Z]+-\d+)\]", case.get("title", ""))
        if match:
            existing[match.group(1)] = int(case["id"])
    mapping = {}
    for requirement_id, spec in plans.items():
        if requirement_id in existing:
            mapping[requirement_id] = existing[requirement_id]
            continue
        created = testrail(f"add_case/{section}", "POST", {
            "title": f"[{requirement_id}] {spec['title']}",
            "custom_preconds": f"Native {platform.upper()} build uploaded to BrowserStack",
        })
        mapping[requirement_id] = int(created["id"])
    run_id = _run_for_execution(project, platform, sorted(mapping.values()))
    for case_id, record in results.items():
        attempts = record["attempts"]
        status = (1 if record["status"] == "passed" and len(attempts) == 1
                  else 4 if record["status"] == "passed" else 5)
        testrail(f"add_result_for_case/{run_id}/{mapping[case_id]}", "POST", {
            "status_id": status,
            "comment": (f"BrowserStack {platform} Appium. "
                        f"Attempts={len(attempts)}. "
                        f"Last outcome={record['status']}. "
                        f"GitHub run={os.getenv('GITHUB_RUN_ID', 'local')}")[:2500],
        })
    return run_id, mapping


def _adf(text):
    return {"type": "doc", "version": 1, "content": [{
        "type": "paragraph",
        "content": [{"type": "text", "text": text[:12000]}],
    }]}


def preview_jira_candidates(platform, report):
    """Offline preview: never contact Jira or create a ticket."""
    return [
        case["id"] for case in report["cases"]
        if case["status"] == "failed" and jira_eligible(case["attempts"])
    ]


def publish_jira_candidates(platform, report, run_id=None, mapping=None):
    project = os.environ["JIRA_PROJECT_KEY"]
    candidates = []
    for case in report["cases"]:
        if case["status"] != "failed" or not jira_eligible(case["attempts"]):
            continue
        case_id = case["id"]
        label = "genai-mobile-" + case_id.lower()
        existing = jira("search/jql", params={
            "jql": f'project = "{project}" AND labels = "{label}"',
            "maxResults": 1, "fields": "key",
        }).get("issues", [])
        if existing:
            candidates.append(existing[0]["key"])
            continue
        project_detail = jira("project/" + project)
        bug = next((t for t in project_detail.get("issueTypes", [])
                    if t.get("name", "").lower() == "bug"), None)
        if bug is None:
            raise RuntimeError("Jira project has no Bug issue type")
        last_error = case["attempts"][-1]["error"][:2500]
        message = (f"Repeated Appium assertion failure on {platform.upper()}."
                   f"\nRequirement: {case_id}"
                   f"\nTestRail run: {run_id or 'not published'}"
                   f"\nTestRail case: {(mapping or {}).get(case_id, 'unknown')}"
                   f"\nGitHub run: {os.getenv('GITHUB_RUN_ID', 'local')}"
                   f"\nBrowserStack App Automate logs are in cloud build."
                   f"\nFailure evidence:\n{last_error}"
                   f"\nClassification: candidate product defect; requires human verification.")
        body = {"fields": {
            "project": {"key": project}, "issuetype": {"id": str(bug["id"])},
            "summary": f"[Mobile QA][{platform.upper()}] {case_id} repeated assertion failure",
            "description": _adf(message),
            "labels": ["automated-qa", "mobile", "browserstack", "needs-triage", label],
        }}
        candidates.append(jira("issue", "POST", body)["key"])
    return candidates


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--platform", choices=("android", "ios"), required=True)
    parser.add_argument("--testrail", action="store_true")
    parser.add_argument("--jira", action="store_true",
                        help="Create/reuse Jira review issues")
    parser.add_argument("--jira-preview", action="store_true",
                        help="Preview eligible cases without contacting Jira")
    args = parser.parse_args()
    report = load_results(args.platform)
    run_id, mapping = (None, {})
    if args.testrail:
        run_id, mapping = publish_testrail(args.platform, report)
    if args.jira and args.jira_preview:
        parser.error("--jira and --jira-preview cannot be used together")
    preview = preview_jira_candidates(args.platform, report) if args.jira_preview else []
    jira_keys = publish_jira_candidates(args.platform, report, run_id, mapping) if args.jira else []
    outcome = {"platform": args.platform, "testrail_run": run_id,
               "jira_candidates": jira_keys, "jira_preview": preview,
               "passed": sum(r["status"] == "passed" for r in report["cases"]),
               "failed": sum(r["status"] == "failed" for r in report["cases"])}
    print(json.dumps(outcome))
    summary = os.getenv("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as handle:
            handle.write(
                f"### {args.platform.upper()} Appium execution\n"
                f"- Passed: {outcome['passed']}\n- Failed: {outcome['failed']}\n"
                f"- TestRail run: {run_id or 'not published'}\n"
                f"- Jira candidates: {', '.join(jira_keys) or 'none'}\n"
                f"- Jira preview (no issues created): {', '.join(preview) or 'none'}\n"
            )


if __name__ == "__main__":
    main()
