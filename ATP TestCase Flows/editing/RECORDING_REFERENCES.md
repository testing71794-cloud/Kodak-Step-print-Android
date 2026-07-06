# Editing Module — Screen Recording References

Local reference videos used to derive Maestro flows (not committed to git — keep in Downloads or team share).

| Recording | Path | Flows derived |
|-----------|------|---------------|
| **Frames** | `C:\Users\HP\Downloads\framesvideo.mp4` | ED_03, ED_03B–ED_03H, `subflows/frames/*` |
| **Stickers** | `C:\Users\HP\Downloads\Stickers.mp4` | ED_04, ED_04B–ED_04H, `subflows/stickers/*` |

## Observed UI flow (both modules)

### Shared pattern
1. Tap **Frames** or **Stickers** on bottom toolbar
2. **Select Category** screen — horizontal category cards, yellow **Done**, back/X
3. Tap category → **in-category carousel** — thumbnails, download badges, orange **checkmark**
4. **Stickers only:** tap canvas to place overlay (`place_sticker_on_canvas.yaml`)
5. Confirm checkmark → **Done** → return to edit toolbar

### Frame-specific (framesvideo.mp4)
- Categories: Soccer, Graduation, Fathers Day, Summer, Easter, General, Mother Day…
- No-frame thumbnail at carousel index 0
- Frame decorates photo border (bokeh, floral, etc.)

### Sticker-specific (Stickers.mp4)
- Categories: Person, Object, Words, Mother Day, Graduation, Summer, Patriotic…
- Stickers: sunglasses, heart, "Love" script, floral "I ❤️ My Mom" wreath
- Download icon on assets not yet cached
- Sticker appears as overlay on photo center after thumbnail tap + canvas tap

## Copy to Jenkins agent (optional)

```bat
mkdir "C:\Jenkins\reference-videos" 2>nul
copy "C:\Users\HP\Downloads\framesvideo.mp4" "C:\Jenkins\reference-videos\"
copy "C:\Users\HP\Downloads\Stickers.mp4" "C:\Jenkins\reference-videos\"
```

Videos are **not required at runtime** — Maestro YAML flows are self-contained.
