# GenAI Mobile Test Generation — Android + iOS

A dual-platform **Appium + Python + pytest** quality-engineering framework for native mobile apps running on **BrowserStack real devices**, with structured **GenAI test-case generation**, **TestRail** result synchronization, and guarded **Jira Bug** creation.

## Architecture

```text
Reviewed mobile acceptance criteria
  -> OpenAI (or offline mock)
  -> validated JSON plans per platform
  -> Android tests/ | iOS tests/
  -> Appium Page Object Model -> BrowserStack App Automate (real devices)
  -> pytest JSON/JUnit + screenshots
  -> TestRail case/run/result (one per platform)
  -> Jira candidate only for repeatable, assertion-based failures
```

## Platform layout

```text
mobileqa/
  config.py            BrowserStack and platform capability engine
  generator.py         OpenAI and mock test-case generation, validation
  pages.py             Native Page Object Model
  runner.py            Executes a validated plan through the page objects
  integrations.py      TestRail and Jira publishing with retry-safe case IDs
  triage.py            Conservative failure classification
  reporting.py         Pytest hook and evidence capture
tests/
  android/test_mobile.py     Android-only suite
  ios/test_mobile.py         iOS-only suite
  unit/                 Credential-free unit tests
config/
  android.json          Configurable Android accessibility IDs
  ios.json              Configurable iOS accessibility IDs
.github/workflows/
  quality.yml           Fast offline tests, no BrowserStack charges
  mobile-app-automate.yml Manual BrowserStack workflow; platform both/android/ios
```

## App under test

Use the uploaded **Android.SauceLabs.Mobile.Sample.app.2.7.1.apk** and **iOS.RealDevice.SauceLabs.Mobile.Sample.app.2.7.1.ipa** binaries (Swag Labs Mobile Sample v2.7.1) as the target applications. Upload its **Android APK** and a **real-device-compatible iOS IPA** to [BrowserStack App Automate](https://app-automate.browserstack.com/); use the two resulting `bs://` identifiers. The app builds are **not** committed.

The initial tests cover **valid login, invalid password, authenticated catalog visibility, product details, and add-to-cart** on each OS. Both uploaded files are **Swag Labs Mobile Sample 2.7.1**, which starts on a login screen. Locator candidates are grounded in the bundled iOS JavaScript localization/test-property definitions but still require verification using an actual device UI hierarchy. Selector IDs in `config/android.json` and `config/ios.json` are *starting points*; confirm them using Appium Inspector against the exact uploaded app versions. The repo does not claim cloud test passes until this is done.

## Required GitHub Actions secrets

| Secret | Purpose |
| --- | --- |
| `BROWSERSTACK_USERNAME` | BrowserStack credentials |
| `BROWSERSTACK_ACCESS_KEY` | BrowserStack credentials |
| `BROWSERSTACK_ANDROID_APP_ID` | Uploaded APK identifier (`bs://...`) |
| `BROWSERSTACK_IOS_APP_ID` | Uploaded real-device IPA identifier (`bs://...`) |
| `OPENAI_API_KEY` | Only required for `provider=openai` |
| `TESTRAIL_EMAIL`, `TESTRAIL_API_KEY` | Optional TestRail live publishing |
| `JIRA_EMAIL`, `JIRA_API_TOKEN` | Optional eligible Jira candidate publishing |

Repository **Actions variables** (or defaults in workflow): `TESTRAIL_URL`, `TESTRAIL_PROJECT_ID`, `TESTRAIL_SECTION_ID`, `JIRA_URL`, `JIRA_PROJECT_KEY`. TestRail/Jira publish steps are controlled by workflow inputs; there is **no destructive run retention** in this new repository.

## Run offline

```bash
python -m pip install -r requirements.txt
python -m mobileqa.generator --platform android --provider mock
python -m mobileqa.generator --platform ios --provider mock
python -m pytest tests/unit -q
```

## Run on BrowserStack

Choose **Actions → Mobile App Automate → Run workflow**, select `android`, `ios`, or `both` and provider `mock` or `openai`. The workflow validates secrets before opening any device session. An Appium session is created **per test** for isolation, and one retry is used to classify flaky failures. Remote execution has BrowserStack device/video logs plus failure screenshots and pytest reports.

You can also execute a single platform locally (with BrowserStack env vars configured):

```bash
python -m mobileqa.generator --platform android --provider mock
MOBILE_PLATFORM=android python -m pytest tests/android -q --reruns 1
```

## Defect policy

A failed automation step is **not automatically a genuine product defect**. The framework creates a Jira issue *candidate* only when both attempts fail due to a recognized application assertion, not an Appium, device, setup, network, or timeout error. Jira records carry `needs-triage` and the platform/case ID; human confirmation is required to establish root cause.

The generator never executes code produced by an LLM. It accepts only reviewed case IDs, scenarios and action sequences. LLM generation proposes descriptive titles; the allowlisted runner executes native interactions.

## Scope and status

This is a runnable repository scaffold with offline tests and CI. **Cloud integration is credential- and app-upload-dependent**. Real iOS/Android selector validation and live TestRail/Jira publication must be confirmed by your first BrowserStack runs.

See [BrowserStack's Python Appium documentation](https://www.browserstack.com/docs/app-automate/appium/getting-started/python/pytest) for device and application prerequisites.
