"""Credential-free tests of generation and safety."""

import pytest

from mobileqa.generator import base_cases, generate, load_plan, save_plan, validate


@pytest.mark.parametrize("platform", ["android", "ios"])
def test_bounded_generation(platform):
    cases = generate(platform, "mock")
    assert len(cases) == 3
    assert all(item["id"].startswith(platform.upper() + "-") for item in cases)
    assert cases == base_cases(platform)


@pytest.mark.parametrize("platform", ["android", "ios"])
def test_plan_round_trip(platform, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    cases = generate(platform)
    save_plan(platform, cases, "mock")
    assert load_plan(platform) == cases


def test_rejects_unapproved_model_action():
    cases = base_cases("android")
    cases[0]["actions"].append("run_arbitrary_python")
    with pytest.raises(ValueError, match="acceptance"):
        validate("android", cases)


def test_rejects_duplicate_scenarios():
    cases = base_cases("ios")
    cases[-1]["id"] = cases[0]["id"]
    with pytest.raises(ValueError, match="duplicate"):
        validate("ios", cases)


def test_no_openai_token_required_for_mock(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert len(generate("ios", "mock")) == 3


def test_openai_needs_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        generate("android", "openai")
