# Frame Editing — Automation Coverage Report

Generated: 2026-07-06

## Executive summary

| Metric | Value |
|--------|-------|
| **Frame scenarios identified** | 35 |
| **Automated (Maestro + AI)** | 22 |
| **Partially automated** | 4 |
| **Manual / not feasible** | 9 |
| **Automation feasibility** | **~78%** |
| **Estimated frame regression coverage** | **~85%** (P0+P1 in CI) |
| **Near-100% path** | Add network mocks, redo flow, multi-aspect photo fixtures |

## Covered scenarios (automated)

- Category screen open, scroll, and navigation (ED_03B)
- In-category carousel open, scroll, cancel (ED_03B, ED_03D)
- Frame apply, replace, remove (ED_03, ED_03C)
- AI verification: category, carousel, before/after frame (ED_03B, ED_03C, ED_03E)
- Undo after frame (ED_03E)
- Cross-category switching (ED_03F)
- Frame + filter + save + reopen (ED_03G)
- Rapid thumbnail switching stress (ED_03H)
- Master E2E frame step (ED_99)
- Checkmark vs Done navigation (frames/* subflows)

## Partially covered

| Area | Gap | Mitigation |
|------|-----|------------|
| Frame asset download | `handle_frame_asset_download.yaml` uses text fallbacks | Add download icon `id` when dev exposes it |
| Cross-tool (Frames↔Stickers) | Only in ED_99 | Add ED_03I dedicated hop |
| Redo | No stable redo selector | Map `imageViewRedo` when available |
| Error toasts | Text varies | AI single-screen or logcat hook |

## Missing / manual scenarios

1. **No internet** during frame download — requires network shim or adb shell svc wifi.
2. **Slow 3G** download timeout — needs proxy (Charles) or Firebase Test Lab network profiles.
3. **Cached frames offline** — second run without network; agent-dependent.
4. **Portrait vs landscape / extreme resolutions** — needs fixture photos in gallery seed.
5. **Orientation change** — Android config change may kill Maestro session.
6. **Empty category** — rare catalog state; needs backend fixture.
7. **Unsupported image size errors** — app-specific message not yet mapped.
8. **Long-press / pinch on frame screen** — not exposed in UI per screenshots.
9. **Exact selection border (red highlight)** — drawable; use AI carousel profile.

## Risk areas

| Risk | Severity | Notes |
|------|----------|-------|
| Seasonal category rename | Medium | Use `flFrameCategory` index + optional text |
| Download-required frames | Medium | ED_03H may fail if asset missing; use cached category |
| Parallel device runs + AI cost | Low | 7 new flows × OpenRouter calls |
| Done vs checkmark confusion | High | Documented in subflows; ED_03B validates |
| Index drift when catalog grows | Medium | Prefer scrollUntilVisible by partial text |

## Test inventory (frame-focused)

| TC_ID | Priority | Description |
|-------|----------|-------------|
| ED_03 | P0 | Frames comprehensive (apply ×2, undo, AI) |
| ED_03B | P0 | Category navigation + AI screen verify |
| ED_03C | P0 | Apply, replace, remove |
| ED_03D | P1 | Cancel / discard |
| ED_03E | P1 | Undo |
| ED_03F | P1 | Cross-category switch |
| ED_03G | P1 | Cross-tool + save persistence |
| ED_03H | P2 | Rapid switch regression |
| ED_99 | P0 | Master E2E includes frame step |

## Recommendations for ~100% coverage

1. **Expose test IDs** — `frameCategoryRecycler`, `frameThumbnailRecycler`, `btnFrameDownload`, `btnFrameRedo`.
2. **Gallery seed job** — push portrait, landscape, 12MP, and invalid-size fixtures before editing suite.
3. **Network stub stage** — Jenkins pre-step to toggle `adb shell svc wifi disable` for FR-19 only.
4. **AI profile tuning** — add `frame_removed` profile for no-frame after removal.
5. **Visual baseline library** — store golden screenshots per device DPI for non-AI fallback.
6. **Run order** — P0 nightly (ED_03, ED_03B, ED_03C); P1 weekly; P2 on release candidate.

## Folder structure

```
ATP TestCase Flows/editing/
├── ED_03*.yaml              # Frame test suite
├── FRAMES_AUTOMATION_MATRIX.md
├── FRAMES_COVERAGE_REPORT.md
├── subflows/
│   ├── apply_frame.yaml     # Delegates to frames/
│   └── frames/              # Page-object-style frame components
│       ├── open_frames_tool.yaml
│       ├── apply_frame_full.yaml
│       └── ...
└── scripts/
    ├── verify_visual_pair_openrouter.js  # profile: frame
    └── verify_edit_screen_openrouter.js  # profiles: frame_category, frame_carousel
```
