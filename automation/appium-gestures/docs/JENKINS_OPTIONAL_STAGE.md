# Optional Jenkins Stage (disabled by default)

**Do not add unless you want pinch gestures in CI.**

Paste into `Jenkinsfile` / `Jenkinsfile.hybrid.gcp-windows` **manually** — not applied by this module.

## 1. Add parameter

```groovy
booleanParam(
    name: 'RUN_PINCH_ZOOM',
    defaultValue: false,
    description: 'Optional: run isolated Appium pinch module (automation/appium-gestures). Does not replace Maestro ATP.'
)
```

## 2. Add stage (Windows agent with device + Appium)

```groovy
stage('PinchZoom (optional)') {
    when {
        expression { return params.RUN_PINCH_ZOOM == true }
    }
    steps {
        script {
            // Appium must be running on the Windows executor (127.0.0.1:4723)
            bat '''
                cd /d "%WORKSPACE%\\automation\\appium-gestures"
                call mvn -q exec:java -Dexec.args="both --udid %DEVICE_SERIAL%"
            '''
        }
    }
}
```

Set `DEVICE_SERIAL` from your existing device discovery (`detected_devices.txt` / `ATP` env) in the same `script` block if needed.

## 3. Ordering

| Pattern | When to run PinchZoom stage |
|---------|----------------------------|
| Standalone smoke | Any time app is on edit canvas |
| With ATP | **After** a Maestro flow reaches edit screen — requires split pipeline or manual param |

**Default:** `RUN_PINCH_ZOOM=false` — stage skipped; identical to today.

## 4. OpenRouter

Unchanged. This stage does not call OpenRouter.

## 5. Ubuntu GCP trigger

GCP job only triggers Jenkins; run this stage on the **Windows node** label that has USB devices (same as Maestro).
