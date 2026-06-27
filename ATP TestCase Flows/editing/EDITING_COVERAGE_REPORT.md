# Editing Module — ED_01 through ED_27 Coverage Report

Generated: 2026-06-10

## Summary

| Status | Count |
|--------|-------|
| Implemented (automated) | 22 |
| Partial (UI action only, no pixel/visual proof) | 7 |
| Hardware / manual | 3 |
| Assumption (labels/fixtures inferred) | 5 |

**All 27 ATP cases now have YAML implementations** under `ATP TestCase Flows/editing/`. Cases ED_18–ED_27 were **not present in the repo** prior to this refactor; they were created from the requirements in the editing alignment task.

## Architecture

- **ATP wrappers**: `ATP TestCase Flows/editing/ED_XX*.yaml` — cold start, gallery entry, subflow orchestration, final assertions.
- **Reusable subflows**: `ATP TestCase Flows/editing/subflows/` — shared edit actions.
- **Legacy delegates**: `flows/editing/*.yaml` — thin `runFlow` pointers to subflows (Jenkins/generator compatibility).

## Defects Fixed (legacy automation)

1. **Missing ED_01 entry** — ED_03–ED_15 previously ran tool actions without entering edit mode.
2. **Coordinate taps** — Replaced `point: "15%,30%"` gallery selection with `imageViewPhoto` / `relativeLayoutItem` / `linearlayout_edit_photo`.
3. **No post-edit assertions** — Added `confirm_tool_done_returns_toolbar.yaml` and final `filterEditingOptionsImageView` checks.
4. **ED_14 missing prerequisite** — Now runs `apply_doodle` before `erase_doodle`.
5. **ED_E01 incomplete** — Added cancel + discard validation path.
6. **Brittle hardcoded indices** — Kept as optional fallbacks with text/ID alternatives where possible.
7. **editing_suite.yaml** — Deprecated unsafe sequential chain of all tools without re-entry.

## Remaining Defects / Gaps

| ID | Issue |
|----|-------|
| D1 | Sticker/text resize, rotate, delete not validated (no stable Maestro selectors for canvas transforms). |
| D2 | Blur flows (ED_20–22) use inferred labels; **no blur strings found in repo** — must verify on device. |
| D3 | Undo (ED_23) taps undo control but cannot assert pixel-level revert. |
| D4 | ED_17 / ED_26 / ED_27 require printer hardware; print completion not fully automatable. |
| D5 | ED_E03 has no dedicated large-image test fixture. |
| D6 | `ATP_TestCase_Maestro_Mapping.csv` still points to stale `TC_ED_*.yaml` paths under `Editing/` (capital E). |

## Assumptions (cannot fully validate automatically)

1. **ED_18–ED_27 step text** — ATP step documents for these cases were not in the repository; flows follow task requirements (save, discard, blur, undo, print).
2. **Blur UI** — Expects popup with YES/NO and a "NO BLUR" removal control; exact strings may vary by OS/build.
3. **Visual edit proof** — Filter/brightness/frame application is validated by UI state (toolbar/Done), not image comparison.
4. **ED_17 AR scan** — Physical print + camera scan cannot be asserted in CI without hardware.
5. **Gallery photo content** — Tests use first available gallery photo; empty gallery will fail at photo selection.

## Subflow Library

| Subflow | Purpose |
|---------|---------|
| `enter_edit_mode.yaml` | ED_01 — open photo + edit toolbar |
| `open_gallery_photo_for_edit.yaml` | Gallery photo selection |
| `dismiss_edit_overlay_if_visible.yaml` | Coachmark dismissal |
| `confirm_tool_done_returns_toolbar.yaml` | Done/checkmark + toolbar assert |
| `open_adjust_menu.yaml` | Optional Adjust cluster |
| `adjust_brightness.yaml` / `contrast` / `warmth` / `saturation` / `highlights` / `shadows` | Slider tools |
| `apply_filter.yaml` / `fit_crop` / `rotate` / `sticker` / `text` / `doodle` / `frame` / `ar_video` | Creative tools |
| `erase_doodle.yaml` | Erase after doodle |
| `save_changes.yaml` / `discard_changes.yaml` | Save/discard exit paths |
| `cancel_tool_edit.yaml` | In-tool cancel |
| `apply_blur_yes.yaml` / `apply_blur_no.yaml` / `remove_blur_no_blur.yaml` | Blur scenarios |
| `undo_last_edit.yaml` | Undo |
| `print_edited_image.yaml` / `print_auto_saves_image.yaml` | Print paths |

## Coverage Matrix

See `atp_editing_mapping.csv` for ATP Case → YAML File → Validation mapping.

## Execution

Run a single case:

```bat
maestro --device ZA222RFQ75 test "ATP TestCase Flows/editing/ED_01 - Enter edit photo mode.yaml"
```

Device must have at least one photo in gallery for edit flows.

## Next Steps

1. Run full editing suite on target device and tune blur/undo/save dialog strings.
2. Update `ATP_TestCase_Maestro_Mapping.csv` paths to new `editing/` folder.
3. Add large-image fixture for ED_E03 if ATP specifies file size/resolution.
4. Add sticker/text transform subflows when stable resource IDs are documented.
