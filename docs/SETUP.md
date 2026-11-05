# First BrowserStack cloud execution — Android and iOS

## Upload test app binaries

Use the Swag Labs Mobile Sample **2.7.1** Android APK and **2.7.1** real-device IPA uploaded for this project. The binary inspection confirmed the iOS bundle name `SwagLabsMobileApp` and version `2.7.1`. The application starts on the Login screen; all catalog/cart cases must authenticate first.

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

## Swag Labs Mobile Sample 2.7.1 selector provenance

The uploaded iOS `.ipa` contains `Payload/SwagLabsMobileApp.app/main.jsbundle`. Its embedded English localization declares `Username`, `Password`, `LOGIN`, `PRODUCTS`, `Item`, `Description`, `ADD TO CART`, `Cart Content` and `Cart`. Its `testProperties()` helper prefixes accessibility IDs/labels with `test-` for iOS/Android. The selector configuration therefore uses these evidence-backed candidates, **not** the previous fictitious `test-Cart Item` identifier. Neither archive inspection nor unit tests can establish a particular element's live hierarchy or whether it is interactable: confirm on BrowserStack and update platform-specific JSON as needed.

## Jira defect review milestone

Use **Actions → BrowserStack Android and iOS Appium → Run workflow**.

1. Set `platform=both`, `provider=mock`, `publish_testrail=true`,
   `publish_jira=true`, and `jira_mode=preview`. Preview checks
   eligibility **without calling Jira or creating issues**. Review the
   `Jira preview` section of each job's GitHub Actions summary.
2. Only after reviewing a repeated, identical application assertion, set
   `jira_mode=create` on a subsequent run. Both `JIRA_URL` and
   `JIRA_PROJECT_KEY` must be configured as Actions variables or secrets,
   together with `JIRA_EMAIL` and `JIRA_API_TOKEN` as secrets.
3. Jira tickets are deliberately **review candidates**, labeled
   `needs-triage`. Existing tickets are looked up using the stable
   `genai-mobile-<platform>-<case-id>` label and reused instead of creating
   a duplicate. A human must verify the application defect before assigning
   it to an engineering team.

Controls: a test must fail on at least two attempts with the same assertion.
Passing-on-retry, setup failures, locator/timeout errors, and differing
assertions are not eligible. A green run creates no Jira tickets. Enabling
`publish_jira` alone never creates tickets because the default Jira mode is
`preview`.

The workflow refuses creation when required Jira configuration is missing.
Publishing to TestRail is independent of Jira mode. Never add API tokens to
the repository or log them. The initial Jira API integration is tested
offline with mocked endpoints; a real Jira creation test remains a separate
explicitly authorized step.
