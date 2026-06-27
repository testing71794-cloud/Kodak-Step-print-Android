# Installation Guide

## 1. Java & Maven

```bat
java -version
mvn -version
```

JDK **17+** required (matches `pom.xml`).

## 2. Appium 2.x

```bat
npm install -g appium
appium driver install uiautomator2
appium -v
```

## 3. Build module (no install to Maestro project)

```bat
cd automation\appium-gestures
mvn clean package -DskipTests
```

Artifact: `target/appium-gestures-1.0.0.jar`

## 4. config.properties

| Key | Purpose |
|-----|---------|
| `appium.server.url` | Appium server (default `http://127.0.0.1:4723`) |
| `android.device.udid` | `adb devices` serial |
| `app.package` | `com.kodak.steptouch` |
| `gesture.center.x.percent` / `y.percent` | Pinch focal point |
| `gesture.inner.offset.pixels` | Start finger spread |
| `gesture.outer.offset.pixels` | End finger spread |
| `gesture.duration.ms` | W3C move duration |
| `gesture.mode` | `pinch-in` \| `pinch-out` \| `both` |
| `screenshots.dir` | Default `target/screenshots` |

CLI overrides: `-Dandroid.device.udid=SERIAL` or `--udid SERIAL` on `PinchGestureRunner`.

## 5. Verify adb

```bat
adb devices
adb -s SERIAL shell wm size
```

## 6. Start Appium before gestures

```bat
appium --address 127.0.0.1 --port 4723
```

## 7. Jenkins agent

Install the same stack on **Windows Maestro nodes**. Ubuntu GCP trigger only starts Jenkins — Appium runs on the Windows executor where the device is plugged in.

No changes to Jenkins credentials or OpenRouter setup.
