# Execution Guide

## ED_03 fit/crop with **real** two-finger pinch (recommended)

Maestro has **no native pinch**. Parallel `adb input swipe` is **not** multitouch.

```bat
REM One-shot: ED_03a (Maestro) -> W3C pinch (Appium) -> ED_03b (Maestro)
automation\appium-gestures\scripts\run_ed03_verify.bat ZA222RFQ75
```

## GA_05 / GA_06 gallery pinch (real W3C multitouch)

**Jenkins Gallery stage** (`RUN_ATP_GALLERY=true`) routes `GA_05` / `GA_06` through Appium automatically via `scripts/run_one_flow_on_device.bat` → `run_ga05_real_pinch.bat` / `run_ga06_real_pinch.bat`. Split flows `GA_05a/b` and `GA_06a/b` are excluded from discovery (invoked by those runners).

```bat
REM GA_05 zoom out (pinch-in after double-tap zoom-in setup)
scripts\run_ga05_real_pinch.bat ZA222RFQ75

REM GA_06 zoom in (pinch-out / spread)
scripts\run_ga06_real_pinch.bat ZA222RFQ75
```

Flow: `GA_06a` or `GA_05a` (Maestro → photo detail) → Appium `pinch_w3c.mjs` → `GA_06b` / `GA_05b` (assert Edit/Print/Collage).

**One-time setup (Windows agent):**

```bat
npm install -g appium@2.11.5
set APPIUM_SKIP_CHROMEDRIVER_INSTALL=1
appium driver install uiautomator2@3.5.7
set ANDROID_HOME=%LOCALAPPDATA%\Android\Sdk
cd automation\appium-gestures && npm install
```

Start Appium before the script (or let the script start it): `appium --address 127.0.0.1 --port 4723`

Screenshots: `automation/appium-gestures/target/screenshots/w3c/before_pinch_*.png` vs `after_pinch_*.png`

If Maestro fails with `tcp:7001` after pinch: `adb kill-server`, `adb start-server`, rerun with `--reinstall-driver` (the verify script already does).

## CLI (Maven / Java module — optional)

```bat
cd automation\appium-gestures

REM Pinch out only (zoom in / tighter crop)
mvn -q exec:java -Dexec.args="pinch-out --udid ZA222RFQ75"

REM Pinch in only (zoom out)
mvn -q exec:java -Dexec.args="pinch-in --udid ZA222RFQ75"

REM Both (matches ED_03 fit/crop pattern)
mvn -q exec:java -Dexec.args="both --udid ZA222RFQ75"
```

Jar (after `mvn package`):

```bat
java -jar target\appium-gestures-1.0.0.jar both --udid ZA222RFQ75
```

## With Maestro (manual coordination)

1. Run Maestro until the **edit canvas** is visible (`borderIV` / fit-crop screen).
2. **Do not** close the app.
3. Run Appium pinch in a second shell (same device).
4. Resume Maestro (pan, back, assert).

Maestro and Appium share the device — never run both drivers simultaneously on the same UI action without closing one session first. `PinchGestureRunner` quits the Appium session when done.

## JUnit

```bat
mvn clean test -Dandroid.device.udid=ZA222RFQ75
```

## Wrapper scripts

```bat
REM Real W3C pinch (Node + WebdriverIO, no Maven)
automation\appium-gestures\examples\scripts\run_pinch_zoom_w3c.bat pinch-out ZA222RFQ75

REM Legacy Java (requires mvn package)
automation\appium-gestures\examples\scripts\run_pinch_zoom.bat both ZA222RFQ75
```

**Do not use** `run_pinch_zoom_adb.bat` for pinch — parallel ADB swipes are not real multitouch on Android.

## Exit codes (Jenkins)

| Code | Meaning |
|------|---------|
| 0 | Gestures completed |
| 1 | Bad args / missing config |
| 2 | Appium / driver / gesture error |

## Screenshots

Before/after PNGs under `target/screenshots/`:

- `pinch_out_before_*.png`
- `pinch_out_after_*.png`
- `pinch_in_before_*.png`
- `pinch_in_after_*.png`

## Logs

SLF4J + Logback to stdout (`src/main/resources/logback.xml`).
