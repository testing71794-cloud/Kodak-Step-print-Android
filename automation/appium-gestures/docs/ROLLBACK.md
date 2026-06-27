# Rollback Guide

This module is **fully isolated**. Rollback = remove the folder.

## Steps

1. **Stop using optional Jenkins stage** (if you pasted `JENKINS_OPTIONAL_STAGE.md` into Jenkinsfile — remove that block).
2. **Remove any copies** you made of `examples/scripts/run_pinch_zoom.*` or `examples/maestro/pinchZoom.yaml` from ATP folders.
3. **Delete the module:**

   ```bat
   rmdir /s /q automation\appium-gestures
   ```

4. **Uninstall Appium** (optional, only if installed solely for this module):

   ```bat
   npm uninstall -g appium
   ```

## Verification after rollback

- Run any existing ATP flow (e.g. `ED_03`) — behavior must match pre-module baseline.
- Jenkins `RUN_ATP_EDITING` stage — unchanged.
- Reports / Excel / OpenRouter analysis — unchanged.

No registry, env vars, or global Jenkins config are modified by this module by default.
