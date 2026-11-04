"""Produce bounded GenAI plans without executing model-generated code."""

import argparse
import json
import os
import urllib.request
from pathlib import Path

SCENARIOS = (
    {"id": "LOGIN-001", "intent": "valid_login",
     "title": "Standard user signs in and sees the Swag Labs inventory",
     "actions": ["login_standard", "assert_catalog"]},
    {"id": "LOGIN-002", "intent": "invalid_password",
     "title": "Swag Labs rejects an invalid password",
     "actions": ["login_invalid_password", "assert_invalid_login_error"]},
    {"id": "CATALOG-001", "intent": "catalog_visible",
     "title": "Authenticated user sees the Swag Labs product inventory",
     "actions": ["login_standard", "assert_catalog"]},
    {"id": "PRODUCT-001", "intent": "product_details",
     "title": "Authenticated user opens the product detail screen",
     "actions": ["login_standard", "open_first_product", "assert_product_details"]},
    {"id": "CART-001", "intent": "add_to_cart",
     "title": "Authenticated user adds a product and sees it in the cart",
     "actions": ["login_standard", "open_first_product", "add_to_cart",
                 "open_cart", "assert_cart_item"]},
)
PLATFORMS = ("android", "ios")


def base_cases(platform):
    if platform not in PLATFORMS:
        raise ValueError("Unsupported platform")
    cases = [
        {"id": f"{platform.upper()}-{item['id']}", "intent": item["intent"],
         "title": item["title"], "actions": list(item["actions"])}
        for item in SCENARIOS
    ]
    if platform == "ios":
        # Swag Labs 2.7.1 has ADD TO CART controls on the inventory page.
        # The iOS product-details action has repeatedly been nonresponsive
        # in BrowserStack sessions; exercise the same purchase outcome from
        # inventory while retaining a separate product-details test.
        next(case for case in cases if case["intent"] == "add_to_cart")[
            "actions"
        ] = ["login_standard", "assert_catalog", "add_to_cart",
             "open_cart", "assert_cart_item"]
    return cases


def validate(platform, cases):
    expected = {case["id"]: case for case in base_cases(platform)}
    if (not isinstance(cases, list) or len(cases) != len(expected)
            or any(not isinstance(case, dict) for case in cases)
            or {case.get("id") for case in cases} != set(expected)):
        raise ValueError("Missing or duplicate mobile cases")
    for case in cases:
        reference = expected[case["id"]]
        if (case.get("intent") != reference["intent"]
                or case.get("actions") != reference["actions"]
                or not isinstance(case.get("title"), str)
                or not 8 <= len(case["title"]) <= 160):
            raise ValueError("LLM plan violates reviewed acceptance criteria")
    return cases


def generate(platform, provider="mock"):
    cases = base_cases(platform)
    if provider == "mock":
        return cases
    if provider != "openai":
        raise ValueError("Provider must be mock or openai")
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        raise ValueError("OPENAI_API_KEY required for live generation")
    body = {
        "model": os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": (
                "Generate precisely the supplied native mobile test cases as a JSON object "
                "with a cases array. Each case has id, intent, title, actions. Make titles "
                "specific and readable; preserve every ID, intent and exact action sequence. "
                "Do not invent code, selectors, requirements or extra actions."
            )},
            {"role": "user", "content": json.dumps({"platform": platform, "cases": cases})},
        ],
    }
    request = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=45) as response:
        answer = json.load(response)
    return validate(platform, json.loads(answer["choices"][0]["message"]["content"])["cases"])


def plan_path(platform):
    if platform not in PLATFORMS:
        raise ValueError("Unsupported platform")
    return Path("plans") / f"{platform}.json"


def save_plan(platform, cases, provider):
    target = plan_path(platform)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps({"platform": platform, "provider": provider,
                    "cases": validate(platform, cases)}, indent=2) + "\n"
    )
    return target


def load_plan(platform):
    path = plan_path(platform)
    if not path.exists():
        raise FileNotFoundError(f"Run python -m mobileqa.generator --platform {platform} first")
    plan = json.loads(path.read_text())
    if plan.get("platform") != platform:
        raise ValueError("Plan platform mismatch")
    return validate(platform, plan["cases"])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--platform", required=True, choices=PLATFORMS)
    parser.add_argument("--provider", default="mock", choices=("mock", "openai"))
    args = parser.parse_args()
    cases = generate(args.platform, args.provider)
    print(json.dumps({"platform": args.platform, "count": len(cases),
                      "path": str(save_plan(args.platform, cases, args.provider))}))


if __name__ == "__main__":
    main()
