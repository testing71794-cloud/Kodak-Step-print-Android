# Maestro integration examples (copy-only)

Maestro 2.x has **no native pinch**. This module is invoked **outside** Maestro YAML unless you add hooks yourself.

## What NOT to do

- Do not add Appium Maven deps to the Maestro repo root.
- Do not change existing `ATP TestCase Flows/**` files in the main repo (copy examples instead).

## Option A — shell between Maestro runs

1. Split fit/crop into two flows (copy in your branch):
   - `ED_03a_enter_edit.yaml` — stops on edit canvas
   - `ED_03b_after_pinch.yaml` — continues pan + exit

2. Jenkins or local:

   ```bat
   maestro --device SERIAL test ED_03a_enter_edit.yaml
   automation\appium-gestures\examples\scripts\run_pinch_zoom.bat both SERIAL
   maestro --device SERIAL test ED_03b_after_pinch.yaml
   ```

## Option B — example flow template

`examples/maestro/pinchZoom.yaml` shows intent. **Maestro `runScript` is JavaScript-only** — it cannot execute `.bat` files directly. Use Option A or the Jenkins optional stage.

## Suggested ED_03 pinch point

After `toBeEditedFilterImageViewTouch` is visible, before pan swipes:

| Step | Tool |
|------|------|
| Enter edit canvas | Maestro |
| Pinch out + in | Appium (`both`) |
| Pan + exit | Maestro |

Coordinates in `config.properties` default to **50%, 42%** (edit photo area, avoids bottom toolbar).
