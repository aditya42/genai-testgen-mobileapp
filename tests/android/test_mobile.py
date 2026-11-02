"""Android native tests running on BrowserStack App Automate."""

import pytest

from mobileqa.generator import load_plan
from mobileqa.runner import execute


@pytest.mark.android
@pytest.mark.parametrize("case", load_plan("android"), ids=lambda case: case["id"])
def test_mobile_scenario(driver, case, request):
    request.node.user_properties.append(("case_id", case["id"]))
    execute(driver, "android", case)
