# Appium Multi-Touch Gestures (Isolated Module)

**Additive only.** Nothing in Maestro ATP, Jenkins, Python orchestration, or reporting is changed unless you explicitly copy examples from this folder.

Pinch-in / pinch-out via **Appium 2.x + W3C Actions API** for Android physical devices.

---

## Folder structure

```
automation/appium-gestures/
├── pom.xml
├── config.properties
├── src/main/java/com/kodak/gestures/
│   ├── DriverManager.java
│   ├── GestureConfig.java
│   ├── GestureUtils.java      # pinchIn(), pinchOut()
│   └── PinchGestureRunner.java # CLI, Jenkins exit codes
├── src/test/java/com/kodak/gestures/
│   ├── BaseTest.java
│   └── PinchZoomTest.java
├── examples/
│   ├── maestro/pinchZoom.yaml          # integration template (not active)
│   └── scripts/run_pinch_zoom.bat|.sh  # optional hooks (copy if needed)
└── docs/
    ├── INSTALL.md
    ├── EXECUTION.md
    ├── ROLLBACK.md
    └── JENKINS_OPTIONAL_STAGE.md
```

---

## Quick start (Windows agent — same as Maestro nodes)

### 1. Prerequisites

| Tool | Version |
|------|---------|
| JDK | 17+ |
| Maven | 3.9+ |
| Node.js | 18+ (for Appium) |
| Appium | 2.x (`npm i -g appium`) |
| UiAutomator2 driver | `appium driver install uiautomator2` |
| adb | Android SDK platform-tools |

### 2. Start Appium (separate terminal)

```bat
appium --address 127.0.0.1 --port 4723
```

### 3. Configure device

Edit `config.properties`:

```properties
android.device.udid=ZA222RFQ75
app.package=com.kodak.steptouch
gesture.center.y.percent=42
```

Or pass at runtime:

```bat
mvn -q exec:java -Dexec.args="both --udid ZA222RFQ75"
```

### 4. Run gestures (app must be on screen — e.g. edit canvas)

```bat
cd automation\appium-gestures
mvn -q exec:java -Dexec.args="pinch-out"
mvn -q exec:java -Dexec.args="pinch-in"
mvn -q exec:java -Dexec.args="both"
```

**Exit codes:** `0` success · `1` usage/config · `2` gesture/driver failure

Screenshots: `target/screenshots/*_before.png`, `*_after.png`

### 5. JUnit smoke (optional)

```bat
mvn clean test
```

---

## Maestro integration (optional — you opt in)

Maestro **does not** support native pinch. This module is **not** called automatically.

**Recommended:** run Appium pinch **between** Maestro steps from Jenkins or a local terminal while the edit screen is open:

```bat
REM Terminal 1: maestro test (pauses manually or split flows)
REM Terminal 2:
cd automation\appium-gestures
mvn -q exec:java -Dexec.args="both --udid %DEVICE_SERIAL%"
```

**Option A — shell hook (copy, do not modify repo ATP flows):**

Copy `examples/scripts/run_pinch_zoom.bat` and invoke from your own wrapper — **not** from Maestro `runScript` (Maestro runScript is JavaScript-only).

**Option B — example flow template:**

See `examples/maestro/pinchZoom.yaml` (documentation only).

---

## Jenkins (optional stage — disabled by default)

See `docs/JENKINS_OPTIONAL_STAGE.md`. Paste into Jenkinsfile **only if** you want `RUN_PINCH_ZOOM=true`.

OpenRouter and existing ATP stages are unaffected.

---

## Rollback

Delete `automation/appium-gestures/`. No other files were modified.

---

## Design notes

- **W3C Actions:** two `PointerInput` sequences performed in parallel (`driver.perform`).
- **Session:** attaches to running `com.kodak.steptouch` (`noReset`, `dontStopAppOnReset`).
- **Isolation:** zero Maven dependency from Maestro project; zero changes to `execution/`, `scripts/`, `ATP TestCase Flows/`.
