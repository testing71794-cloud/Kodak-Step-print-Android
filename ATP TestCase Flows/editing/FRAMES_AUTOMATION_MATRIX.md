# Frame Editing — Automation Test Matrix

Generated: 2026-07-06 | Based on Frame Editing UI screenshots (category picker + in-category carousel)

## UI inventory (from screenshots)

| Zone | Elements | Interaction |
|------|-----------|-------------|
| **Header (category)** | Back `<`, title "Select Frame Category", yellow **Done** pill | Tap back/Done |
| **Header (carousel)** | Orange **X**, category title (e.g. Graduation, Mother Day), orange **checkmark** | Cancel / confirm frame |
| **Preview** | Photo in white border, frame overlay on edges | Visual-only (pinch not exposed on frame screen) |
| **Category row** | Cards: Soccer, Graduation, Fathers Day, Summer, Easter, General, Mother Day… | Tap, horizontal swipe |
| **Frame carousel** | Thumbnails, red selection border, download badge on some | Tap, horizontal swipe |
| **No-frame slot** | Circle-with-slash thumbnail (index 0) | Tap to remove frame |
| **Bottom toolbar** | Filter, **Frames** (active=white), Stickers, Brightness, Temperature, Adjust | Tap to switch tools |

## Test matrix

| ID | Scenario | Type | Priority | Flow | Status |
|----|----------|------|----------|------|--------|
| FR-01 | Open Frames from edit toolbar | Functional | P0 | ED_03B | Automated |
| FR-02 | Category screen UI visible | UI | P0 | ED_03B | Automated |
| FR-03 | Scroll category row | Interaction | P0 | ED_03B | Automated |
| FR-04 | Open category → carousel | Navigation | P0 | ED_03B | Automated |
| FR-05 | Carousel UI + scroll thumbnails | UI | P0 | ED_03B | Automated |
| FR-06 | AI verify category screen | AI | P0 | ED_03B | Automated |
| FR-07 | AI verify carousel screen | AI | P0 | ED_03B | Automated |
| FR-08 | Apply frame (Graduation) | Functional | P0 | ED_03, ED_03C | Automated |
| FR-09 | Replace frame (another category) | Functional | P0 | ED_03C | Automated |
| FR-10 | Remove frame (no-frame thumbnail) | Functional | P0 | ED_03C | Automated |
| FR-11 | AI before/after frame apply | Regression | P0 | ED_03, ED_03C | Automated |
| FR-12 | Cancel frame (X/back) — no persist | Negative | P1 | ED_03D | Automated |
| FR-13 | Undo after frame apply | State | P1 | ED_03E | Automated |
| FR-14 | Switch categories without Done | Navigation | P1 | ED_03F | Automated |
| FR-15 | Frame + filter combined | Cross-tool | P1 | ED_03G | Automated |
| FR-16 | Save + reopen persistence | Persistence | P1 | ED_03G | Automated |
| FR-17 | Rapid thumbnail switching | Performance | P2 | ED_03H | Automated |
| FR-18 | Download badge on frame asset | Network | P2 | handle_frame_asset_download | Partial |
| FR-19 | No internet during download | Negative | P2 | — | Manual / mock |
| FR-20 | Slow network download | Boundary | P2 | — | Manual |
| FR-21 | Cached frame (offline replay) | Edge | P2 | — | Manual |
| FR-22 | Portrait vs landscape photo | Boundary | P2 | — | Data-driven (future) |
| FR-23 | Very high-res image | Performance | P2 | — | Manual |
| FR-24 | Orientation change in editor | Edge | P2 | — | Not reliable |
| FR-25 | Long-press on thumbnail | Interaction | P2 | — | N/A (no action in UI) |
| FR-26 | Pinch/zoom on frame preview | Gesture | P2 | — | Not on frame screen |
| FR-27 | Drag & drop frame | Gesture | P2 | — | N/A |
| FR-28 | Double-tap preview | Gesture | P2 | — | N/A |
| FR-29 | Toast/snackbar on download fail | Error | P1 | — | Needs stable text |
| FR-30 | Redo after undo | State | P1 | — | Future (redo ID TBD) |
| FR-31 | Frames → Stickers → back to Frames | Cross-tool | P1 | ED_99 | Partial (master E2E) |
| FR-32 | Done vs checkmark semantics | Regression | P0 | frames/* | Automated |
| FR-33 | Toolbar Frames highlighted | UI state | P0 | assert_frame_* | Automated |
| FR-34 | Empty category (no assets) | Edge | P2 | — | Needs test account |
| FR-35 | Master E2E includes frames | Regression | P0 | ED_99 | Automated |

## Reusable subflows (`subflows/frames/`)

| Subflow | Role (page-object style) |
|---------|--------------------------|
| `open_frames_tool.yaml` | Navigate to Frames module |
| `assert_frame_category_screen.yaml` | Category screen assertions |
| `scroll_frame_categories.yaml` | Horizontal category scroll |
| `select_frame_category.yaml` | Pick category by text/index |
| `assert_frame_carousel_screen.yaml` | In-category picker assertions |
| `scroll_frame_carousel.yaml` | Thumbnail strip scroll |
| `select_frame_thumbnail.yaml` | Pick frame by index |
| `select_no_frame.yaml` | Remove applied frame |
| `confirm_frame_checkmark.yaml` | Apply within carousel |
| `confirm_frame_category_done.yaml` | Exit via Done pill |
| `cancel_frame_edit.yaml` | Discard frame changes |
| `handle_frame_asset_download.yaml` | Download badge handling |
| `return_to_edit_toolbar.yaml` | Return to main edit toolbar |
| `apply_frame_full.yaml` | End-to-end apply composition |

## Stability recommendations

1. Prefer **resource IDs** (`flFrameCategory`, `imageViewFilter`, `saveRecentEditImageView`) over coordinates.
2. Use **`extendedWaitUntil`** for category/carousel transitions; avoid fixed sleeps except `waitForAnimationToEnd`.
3. Pass **data via env** (`FRAME_CATEGORY`, `FRAME_CATEGORY_INDEX`, `FRAME_THUMB_INDEX`) for data-driven variants.
4. Use **OpenRouter AI** for preview pixels (frame border, confetti, floral) where selectors cannot assert decoration.
5. Category labels vary by **seasonal catalog** — keep index fallbacks (`flFrameCategory` index) when text labels rotate.
6. Run frame suite **sequential per device** when debugging; parallel OK in Jenkins with isolated Maestro homes.
7. Start `start_editing_studio_verify.bat` before Studio runs with AI profiles.

## Non-automatable / high-risk scenarios

| Scenario | Why | Alternative |
|----------|-----|-------------|
| Exact pixel match of frame artwork | Bitmap comparison flaky across devices | OpenRouter `frame` profile |
| Offline / airplane mode | OS-level; Maestro cannot toggle reliably on all agents | Dedicated manual + Charles proxy |
| Download progress % timing | No stable progress ID documented | Assert download icon disappears + AI |
| Device rotation mid-edit | Activity recreate race | Skip or run on single device lab |
| Red border selection state | May be drawable-only | AI carousel profile or screenshot diff |
| Seasonal category catalog drift | Labels change (Mother Day, Easter) | Index-based selection + optional text |
