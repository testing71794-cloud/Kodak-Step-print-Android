# Editing Module — Enterprise Automation Report

Generated: 2026-07-05

## Summary

| Status | Count |
|--------|-------|
| Comprehensive module tests (AI-verified) | 13 |
| Reusable subflows (editing/) | 64+ |
| In-flow OpenRouter scripts | 3 |

The edit module now uses **one comprehensive test per tool category**, each with **before/after OpenRouter vision validation** and shared warm-start entry.

## Architecture

```
prepare_editor_warm_start.yaml
    └── enter_edit_mode.yaml
    └── verify_edit_screen_with_ai.yaml → verify_edit_screen_openrouter.js

Module test (ED_03–ED_12)
    └── takeScreenshot (before)
    └── tool subflow (apply_frame, adjust_brightness, …)
    └── takeScreenshot (after)
    └── verify_visual_pair_with_ai.yaml → verify_visual_pair_openrouter.js

ED_12 / ED_99 save path
    └── save_and_verify_gallery_with_ai.yaml
    └── verify_edit_screen_with_ai.yaml (gallery profile)
```

## Test Inventory

| TC_ID | Module | AI profiles used |
|-------|--------|------------------|
| ED_01 | Enter edit mode | edit_screen |
| ED_02 | Filters (6 filters) | edit_screen, filter |
| ED_03 | Frames / borders | edit_screen, frame |
| ED_04 | Stickers | edit_screen, sticker |
| ED_05 | Crop / fit | edit_screen, crop |
| ED_06 | Rotate | edit_screen, rotate |
| ED_07 | Flip | edit_screen, flip |
| ED_08 | Adjust (6 sliders) | edit_screen, adjust |
| ED_09 | Text | edit_screen, text |
| ED_10 | Draw / paint | edit_screen, draw |
| ED_11 | Blur / effects | edit_screen, blur |
| ED_12 | Save + gallery | filter, save, gallery |
| ED_99 | Master E2E | all profiles |

## AI Implementation (in-flow, editing-local)

| Script | Purpose |
|--------|---------|
| `scripts/verify_visual_pair_openrouter.js` | Generic before/after OpenRouter verify (profiles: filter, frame, sticker, crop, rotate, flip, adjust, text, draw, blur, save, generic) |
| `scripts/verify_edit_screen_openrouter.js` | Single-screen verify (edit_screen, gallery profiles) |
| `scripts/verify_filter_pair_openrouter.js` | Legacy filter script (superseded by generic pair script; kept for reference) |

**Required env for AI flows:**

```
OpenRouterAPI or OPENROUTER_API_KEY
MAESTRO_CLI_DANGEROUS_GRAALJS_ALLOW_HOST_ACCESS=1
MAESTRO_CLI_DANGEROUS_GRAALJS_ALLOW_HOST_CLASS_LOOKUP=1
```

## Execution

```bat
automation\appium-gestures\scripts\run_editing_verify_suite.bat ZA222RFQ75
```

Single test:

```bat
set MAESTRO_CLI_DANGEROUS_GRAALJS_ALLOW_HOST_ACCESS=1
set MAESTRO_CLI_DANGEROUS_GRAALJS_ALLOW_HOST_CLASS_LOOKUP=1
maestro --device ZA222RFQ75 test "ATP TestCase Flows/editing/ED_01 - Enter edit photo mode.yaml"
```

## Reused Components (unchanged outside editing/)

- `signup-login/subflows/reach_gallery_after_onboarding_skip.yaml` (ED_01 cold start only)
- All existing editing tool subflows (`apply_frame`, `adjust_*`, `apply_rotate`, etc.)
- Post-flow Python verify scripts (`scripts/verify_ed_visual_pair.py`) remain available for split-flow CI

## Remaining Limitations

1. **Flip controls** — no stable resource IDs documented; flip subflows use optional ID/label fallbacks.
2. **Crop aspect ratios** (1:1, 3:4, etc.) — not exposed as stable selectors; crop test uses pinch/pan paths.
3. **Adjust sliders** — only brightness/contrast/warmth/saturation/highlights/shadows exist in subflows; exposure/tint/sharpness not in current app toolbar mapping.
4. **ED_99 runtime** — full master E2E is long (~15+ OpenRouter calls); run selectively in CI.
5. **Jenkins Editing stage** — still needs OpenRouter credential binding (same as Gallery stage) for in-flow AI in CI.

## Regression Scope

Only files under `ATP TestCase Flows/editing/` and `automation/appium-gestures/scripts/run_editing_verify_suite.bat` were modified. No login, signup, gallery, settings, or shared signup-login subflows were changed.
