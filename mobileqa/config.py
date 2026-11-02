"""Validated BrowserStack capabilities for Android and iOS real devices."""

import os
from dataclasses import dataclass

from appium.options.android import UiAutomator2Options
from appium.options.ios import XCUITestOptions

HUB_URL = "https://hub-cloud.browserstack.com/wd/hub"


@dataclass(frozen=True)
class Settings:
    platform: str
    username: str
    access_key: str
    app_id: str
    device: str
    os_version: str
    build: str

    @classmethod
    def from_env(cls, platform=None, env=None):
        values = os.environ if env is None else env
        platform = (platform or values.get("MOBILE_PLATFORM", "android")).lower()
        if platform not in ("android", "ios"):
            raise ValueError("Platform must be android or ios")
        prefix = platform.upper()
        required = ("BROWSERSTACK_USERNAME", "BROWSERSTACK_ACCESS_KEY",
                    f"BROWSERSTACK_{prefix}_APP_ID")
        missing = [name for name in required if not values.get(name)]
        if missing:
            raise ValueError("Missing BrowserStack configuration: " + ", ".join(missing))
        app_id = values[f"BROWSERSTACK_{prefix}_APP_ID"]
        if not app_id.startswith("bs://"):
            raise ValueError("The app ID must start with bs://")
        return cls(
            platform=platform,
            username=values["BROWSERSTACK_USERNAME"],
            access_key=values["BROWSERSTACK_ACCESS_KEY"],
            app_id=app_id,
            device=values.get(f"{prefix}_DEVICE") or
            ("Google Pixel 8" if platform == "android" else "iPhone 15"),
            os_version=values.get(f"{prefix}_OS_VERSION") or
            ("14.0" if platform == "android" else "17"),
            build=values.get("BROWSERSTACK_BUILD_NAME") or "GenAI Mobile Regression",
        )

    def options(self, test_name):
        options = UiAutomator2Options() if self.platform == "android" else XCUITestOptions()
        options.app = self.app_id
        options.set_capability("appium:deviceName", self.device)
        options.set_capability("appium:platformVersion", self.os_version)
        options.set_capability("bstack:options", {
            "userName": self.username, "accessKey": self.access_key,
            "deviceName": self.device, "osVersion": self.os_version,
            "projectName": "GenAI Mobile Test Generation",
            "buildName": self.build, "sessionName": test_name[:200],
            "debug": True, "video": True, "deviceLogs": True,
        })
        return options
