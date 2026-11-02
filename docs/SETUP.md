# First BrowserStack cloud execution — Android and iOS

## Upload test app binaries

Use an Android APK and a real-device-compatible iOS IPA from the **same
revision** of the [Sauce Labs My Demo App React Native project](https://github.com/saucelabs/my-demo-app-rn/releases).
A simulator-only `.app` bundle is not a substitute for a real-device IPA.

Upload the APK and IPA separately to BrowserStack App Automate. Save the
returned `bs://` identifiers under the names:

- `BROWSERSTACK_ANDROID_APP_ID`
- `BROWSERSTACK_IOS_APP_ID`

Do **not** commit binaries or credentials to the repository.

## GitHub secrets

In this repository go to **Settings → Secrets and variables → Actions**.

Configure the four BrowserStack secrets:
`BROWSERSTACK_USERNAME`, `BROWSERSTACK_ACCESS_KEY`,
`BROWSERSTACK_ANDROID_APP_ID`, and `BROWSERSTACK_IOS_APP_ID`.

To generate cases with a real model, also set `OPENAI_API_KEY`.
`provider=mock` needs no OpenAI key.

## Verify actual accessibility identifiers

The starting selector values in `config/android.json` and `config/ios.json`
are provisional. Inspect the uploaded binaries with Appium Inspector
against actual BrowserStack real-device sessions. Replace selectors only
where the native UI tree proves a mismatch.

Do not treat a selector mismatch as a real application defect.

## Run a controlled cloud test

Select **Actions → BrowserStack Android and iOS Appium → Run workflow**.

For the first run choose:
- platform: `android` (then `ios` after the first platform passes)
- provider: `mock`
- publish_testrail: **false**
- publish_jira: **false**

Once both platform suites are green, create TestRail project/section and
Jira project credentials as needed, enable publishing, and repeat.

The initial suite contains three cases per platform:
catalog visibility, product details and add to cart.

## Optional TestRail and Jira integration

Set repo **Actions variables**: `TESTRAIL_URL`,
`TESTRAIL_PROJECT_ID`, `TESTRAIL_SECTION_ID`, `JIRA_URL`, and
`JIRA_PROJECT_KEY`. Set **Actions secrets**:
`TESTRAIL_EMAIL`, `TESTRAIL_API_KEY`, `JIRA_EMAIL`, `JIRA_API_TOKEN`.

TestRail uses unique requirement IDs prefixed by platform
(`ANDROID-CART-001` vs `IOS-CART-001`) and creates separate execution
runs. The GitHub run ID is in each TestRail **description**, not run title.
There is no automatic deletion of historical TestRail runs.

Jira tickets are eligible only for two failed application assertions with
no detected infrastructure problem. Tickets are labeled
`needs-triage`; they are **candidates**, not established product defects.
