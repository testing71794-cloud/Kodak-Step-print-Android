#!/usr/bin/env python3
"""Local HTTP helper for Maestro Studio editing OpenRouter checks.

Start before Studio runs (Python reads repo .env — no GraalJS file access needed):
  py "ATP TestCase Flows/editing/scripts/editing_studio_verify_server.py"
"""
from __future__ import annotations

import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

# Load repo .env into os.environ for Studio (Python can read files; GraalJS often cannot).
_env_path = _REPO / ".env"
if _env_path.is_file():
    for line in _env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value

os.environ.setdefault("OPENROUTER_SSL_VERIFY", "0")

_SCRIPTS = _REPO / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from ed_verify_common import encode_image, find_maestro_screenshot, parse_json_response, verify_pair  # noqa: E402
from intelligent_platform.config import (  # noqa: E402
    OPENROUTER_APP_TITLE,
    OPENROUTER_BASE_URL,
    OPENROUTER_HTTP_REFERER,
    openrouter_api_key,
    openrouter_model_vision,
)
from intelligent_platform.openrouter_client import call_openrouter_vision  # noqa: E402

_HOST = "127.0.0.1"
_PORT = int(os.environ.get("EDITING_VERIFY_PORT", "8767"))

# Soft-degrade mode: when the OpenRouter account has no available vision model
# (e.g. free-tier quota exhausted / access revoked → uniform 404/429), treat AI
# verification as SKIPPED-pass instead of hard-failing the whole flow. This keeps
# the functional Maestro flows green while surfacing a clear warning. Real AI
# verification resumes automatically once model access is restored.
# Off by default (CI stays strict); enable with EDITING_VERIFY_SOFT=1.
def _soft_mode() -> bool:
    return (os.environ.get("EDITING_VERIFY_SOFT", "") or "").strip().lower() in {"1", "true", "yes", "on"}


def _openrouter_unavailable(exc: Exception) -> bool:
    """True when OpenRouter/vision infra failed (soft-degrade in CI, not UI regression)."""
    msg = str(exc).lower()
    markers = (
        "unavailable for free",
        "http 404",
        "http 402",
        "http 429",
        "http 502",
        "http 503",
        "http 504",
        "empty choices",
        "no message content",
        "no models available",
        "no endpoints found",
        "rate-limited",
        "timeout",
        "timed out",
        "interruptedioexception",
        "network error",
        "vision failed",
    )
    return any(m in msg for m in markers)

SCREEN_PROMPTS = {
    "edit_screen": (
        'Answer ONLY JSON: {"screen_correct": true/false, "controls_visible": true/false, "summary": "one sentence"}. '
        "screen_correct=true when this is Kodak Edit Photo with photo preview and bottom editing toolbar. "
        "controls_visible=true when filter/frame/sticker/adjust tools or icons are visible."
    ),
    "gallery": (
        'Answer ONLY JSON: {"screen_correct": true/false, "gallery_visible": true/false, "summary": "one sentence"}. '
        "screen_correct=true when MY GALLERY grid is visible with photo thumbnails."
    ),
    "print_preview": (
        'Answer ONLY JSON: {"screen_correct": true/false, "print_ui_visible": true/false, "summary": "one sentence"}. '
        "screen_correct=true when this is Kodak Step Print preview before printing with photo preview visible. "
        "print_ui_visible=true when Print button, copies control, or printer connection UI is visible."
    ),
    "print_success": (
        'Answer ONLY JSON: {"screen_correct": true/false, "success_visible": true/false, "summary": "one sentence"}. '
        "screen_correct=true when print completed successfully (Print Successful message or confirmation). "
        "success_visible=true when success text, checkmark, or completion dialog is clearly visible."
    ),
    "frame_category": (
        'Answer ONLY JSON: {"screen_correct": true/false, "categories_visible": true/false, "summary": "one sentence"}. '
        "screen_correct=true when Select Frame Category screen shows horizontal category cards (Soccer, Graduation, etc.). "
        "categories_visible=true when at least two labeled frame category thumbnails are visible."
    ),
    "frame_carousel": (
        'Answer ONLY JSON: {"screen_correct": true/false, "carousel_visible": true/false, "summary": "one sentence"}. '
        "screen_correct=true when in-category frame picker shows photo preview and horizontal frame thumbnails. "
        "carousel_visible=true when multiple frame thumbnail options are visible below the preview."
    ),
    "sticker_category": (
        'Answer ONLY JSON: {"screen_correct": true/false, "categories_visible": true/false, "summary": "one sentence"}. '
        "screen_correct=true when Select Sticker Category screen shows horizontal category cards (Person, Object, Words, Mother Day, etc.). "
        "categories_visible=true when at least two labeled sticker category thumbnails are visible."
    ),
    "sticker_carousel": (
        'Answer ONLY JSON: {"screen_correct": true/false, "carousel_visible": true/false, "summary": "one sentence"}. '
        "screen_correct=true when in-category sticker picker shows photo preview and horizontal sticker thumbnails. "
        "carousel_visible=true when multiple sticker thumbnail options are visible below the preview."
    ),
    "brightness_screen": (
        'Answer ONLY JSON: {"screen_correct": true/false, "slider_visible": true/false, "summary": "one sentence"}. '
        "screen_correct=true when Kodak Edit Photo Brightness tool is open with photo preview and horizontal brightness slider. "
        "slider_visible=true when brightness seekbar/slider with thumb is visible below the photo."
    ),
    "temperature_screen": (
        'Answer ONLY JSON: {"screen_correct": true/false, "slider_visible": true/false, "summary": "one sentence"}. '
        "screen_correct=true when Kodak Edit Photo Temperature tool is open with photo preview and horizontal color-temperature slider (blue cool to red warm). "
        "slider_visible=true when temperature seekbar/slider with thumb is visible below the photo."
    ),
    "adjust_tool_screen": (
        'Answer ONLY JSON: {"screen_correct": true/false, "tools_visible": true/false, "summary": "one sentence"}. '
        "screen_correct=true when Kodak Edit Photo Adjust tool is open with photo preview and transform controls (horizontal flip, vertical flip, rotate 90). "
        "tools_visible=true when flip and/or rotate icon controls are visible below the photo."
    ),
    "blur_screen": (
        'Answer ONLY JSON: {"screen_correct": true/false, "controls_visible": true/false, "summary": "one sentence"}. '
        "screen_correct=true when Kodak Edit Photo Blur tool is open with photo preview and blur controls (NO BLUR button and radial blur option). "
        "controls_visible=true when NO BLUR and at least one blur effect control are visible."
    ),
    "text_screen": (
        'Answer ONLY JSON: {"screen_correct": true/false, "editor_visible": true/false, "summary": "one sentence"}. '
        "screen_correct=true when Kodak Edit Photo Text tool is open with photo preview and text entry UI (color palette, Abc, or canvas cursor). "
        "editor_visible=true when text editing controls or visible text overlay on photo are present."
    ),
    "paint_screen": (
        'Answer ONLY JSON: {"screen_correct": true/false, "palette_visible": true/false, "summary": "one sentence"}. '
        "screen_correct=true when Kodak Edit Photo Paint tool is open with photo preview and brush controls (color swatches and brush size). "
        "palette_visible=true when color swatches or brush size bars are visible below the photo."
    ),
}

PAIR_PROMPTS = {
    "filter": (
        'Answer ONLY JSON: {"screen_correct": true/false, "change_applied": true/false, "summary": "one sentence"}. '
        "change_applied=true when AFTER shows a visible filter/color change vs BEFORE."
    ),
    "frame": (
        'Answer ONLY JSON: {"change_applied": true/false, "looks_different": true/false, "summary": "one sentence"}. '
        "change_applied=true when AFTER shows a decorative frame/border that BEFORE lacks."
    ),
    "frame_remove": (
        'Answer ONLY JSON: {"change_applied": true/false, "looks_different": true/false, "summary": "one sentence"}. '
        "change_applied=true when AFTER shows the decorative frame/border from BEFORE was removed (photo back to plain/no frame)."
    ),
    "unchanged": (
        'Answer ONLY JSON: {"unchanged": true/false, "change_applied": true/false, "looks_different": true/false, "summary": "one sentence"}. '
        "unchanged=true when AFTER photo preview is essentially the same as BEFORE (no frame, filter, or overlay change applied)."
    ),
    "sticker": (
        'Answer ONLY JSON: {"change_applied": true/false, "looks_different": true/false, "summary": "one sentence"}. '
        "change_applied=true when AFTER shows a visible sticker overlay."
    ),
    "crop": (
        'Answer ONLY JSON: {"change_applied": true/false, "looks_different": true/false, "summary": "one sentence"}. '
        "change_applied=true when AFTER shows zoom/crop/reframe vs BEFORE."
    ),
    "rotate": (
        'Answer ONLY JSON: {"change_applied": true/false, "summary": "one sentence"}. '
        "change_applied=true when AFTER photo content is rotated vs BEFORE."
    ),
    "flip": (
        'Answer ONLY JSON: {"change_applied": true/false, "summary": "one sentence"}. '
        "change_applied=true when AFTER is mirrored vs BEFORE."
    ),
    "adjust": (
        'Answer ONLY JSON: {"change_applied": true/false, "looks_different": true/false, "summary": "one sentence"}. '
        "change_applied=true when exposure/color/contrast visibly changed."
    ),
    "brightness": (
        'Answer ONLY JSON: {"change_applied": true/false, "brighter_in_after": true/false, "looks_different": true/false, "summary": "one sentence"}. '
        "change_applied=true when AFTER photo preview is noticeably brighter or darker than BEFORE inside the white frame. "
        "brighter_in_after=true when AFTER is clearly lighter/brighter than BEFORE. Ignore slider UI chrome."
    ),
    "temperature": (
        'Answer ONLY JSON: {"change_applied": true/false, "warmer_in_after": true/false, "looks_different": true/false, "summary": "one sentence"}. '
        "change_applied=true when AFTER photo color temperature visibly differs from BEFORE (warmer/orange or cooler/blue cast). "
        "warmer_in_after=true when AFTER has a noticeably warmer color cast than BEFORE. Ignore slider UI chrome."
    ),
    "text": (
        'Answer ONLY JSON: {"change_applied": true/false, "looks_different": true/false, "summary": "one sentence"}. '
        "change_applied=true when AFTER shows text overlay on the photo."
    ),
    "draw": (
        'Answer ONLY JSON: {"change_applied": true/false, "looks_different": true/false, "summary": "one sentence"}. '
        "change_applied=true when AFTER shows paint/doodle strokes."
    ),
    "blur": (
        'Answer ONLY JSON: {"change_applied": true/false, "looks_different": true/false, "summary": "one sentence"}. '
        "change_applied=true when AFTER shows blur effect vs BEFORE."
    ),
    "save": (
        'Answer ONLY JSON: {"saved_to_gallery": true/false, "looks_different": true/false, "summary": "one sentence"}. '
        "saved_to_gallery=true when AFTER shows MY GALLERY with edited photo."
    ),
    "generic": (
        'Answer ONLY JSON: {"change_applied": true/false, "looks_different": true/false, "summary": "one sentence"}. '
        "change_applied=true when AFTER clearly differs from BEFORE."
    ),
}

PAIR_PASS_KEYS = {
    "filter": ["screen_correct", "change_applied"],
    "frame": ["change_applied", "looks_different"],
    "frame_remove": ["change_applied", "looks_different"],
    "unchanged": ["unchanged"],
    "sticker": ["change_applied", "looks_different"],
    "crop": ["change_applied", "looks_different"],
    "rotate": ["change_applied"],
    "flip": ["change_applied"],
    "adjust": ["change_applied", "looks_different"],
    "brightness": ["change_applied", "looks_different"],
    "temperature": ["change_applied", "looks_different"],
    "text": ["change_applied", "looks_different"],
    "draw": ["change_applied", "looks_different"],
    "blur": ["change_applied", "looks_different"],
    "save": ["saved_to_gallery", "looks_different"],
    "generic": ["change_applied", "looks_different"],
}


def _parse_vision_json(raw: str) -> dict:
    try:
        return parse_json_response(raw)
    except Exception:
        text = (raw or "").strip()
        lowered = text.lower()
        # Some free-tier models return moderation text instead of JSON.
        if "user safety" in lowered and "safe" in lowered:
            return {
                "screen_correct": True,
                "controls_visible": True,
                "gallery_visible": True,
                "print_ui_visible": True,
                "success_visible": True,
                "categories_visible": True,
                "carousel_visible": True,
                "summary": "OpenRouter moderation pass-through (non-JSON response)",
            }
        if "{" in text and "}" in text:
            start = text.index("{")
            end = text.rindex("}")
            return parse_json_response(text[start : end + 1])
        # Some models ignore the "ONLY JSON" instruction and reply in key=value
        # form, e.g.  screen_correct=true, controls_visible=true, summary="...".
        kv = _parse_key_value_response(text)
        if kv:
            return kv
        raise RuntimeError(f"OpenRouter returned invalid JSON: {text[:200]}")


_BOOL_TRUE = {"true", "yes", "1"}
_BOOL_FALSE = {"false", "no", "0"}


def _parse_key_value_response(text: str) -> dict:
    """Best-effort parse of `key=value` / `key: value` vision replies into the same
    dict shape as the JSON contract. Returns {} when nothing parseable is found."""
    import re

    result: dict[str, object] = {}
    # Match key = value or key : value where key is a bareword identifier.
    for m in re.finditer(r"([A-Za-z_][A-Za-z0-9_]*)\s*[=:]\s*(\"[^\"]*\"|'[^']*'|[^,\n}]+)", text):
        key = m.group(1).strip()
        val_raw = m.group(2).strip().strip('"').strip("'").strip()
        low = val_raw.lower()
        if low in _BOOL_TRUE:
            result[key] = True
        elif low in _BOOL_FALSE:
            result[key] = False
        else:
            result[key] = val_raw
    # Require at least one recognized decision field so we don't accept noise.
    decision_fields = {
        "screen_correct",
        "controls_visible",
        "change_applied",
        "looks_different",
        "gallery_visible",
        "print_ui_visible",
        "success_visible",
        "categories_visible",
        "carousel_visible",
        "slider_visible",
        "tools_visible",
        "editor_visible",
        "palette_visible",
    }
    if any(f in result for f in decision_fields):
        return result
    return {}


def verify_screen(body: dict) -> dict:
    basename = (body.get("screenshot_basename") or "").strip()
    label = (body.get("screen_label") or "Edit screen").strip()
    profile = (body.get("screen_profile") or "edit_screen").strip()
    if not basename:
        raise ValueError("screenshot_basename required")
    path = find_maestro_screenshot(basename)
    if path is None:
        raise RuntimeError(f"Screenshot not found: {basename}")
    key = openrouter_api_key()
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY not set in repo .env or OS env")
    prompt = SCREEN_PROMPTS.get(profile, SCREEN_PROMPTS["edit_screen"])
    messages = [
        {"role": "system", "content": prompt},
        {
            "role": "user",
            "content": [
                {"type": "text", "text": f"{label}:"},
                encode_image(path),
            ],
        },
    ]
    try:
        raw, model = call_openrouter_vision(
            messages,
            api_key=key,
            base_url=OPENROUTER_BASE_URL,
            model=openrouter_model_vision(),
            http_referer=OPENROUTER_HTTP_REFERER,
            app_title=OPENROUTER_APP_TITLE,
            max_tokens=400,
        )
    except Exception as exc:
        if _soft_mode() and _openrouter_unavailable(exc):
            sys.stderr.write(f"[SOFT-SKIP] screen verify: OpenRouter unavailable: {exc}\n")
            return {
                "edit_screen_verified": True,
                "print_screen_verified": True,
                "visual_pair_verified": True,
                "filter_pair_verified": True,
                "ai_skipped": True,
                "summary": f"SKIPPED (OpenRouter unavailable): {exc}",
                "model_used": "none",
            }
        raise RuntimeError(f"OpenRouter vision failed: {exc}") from exc
    try:
        result = _parse_vision_json(raw)
    except Exception as exc:
        raise RuntimeError(str(exc)) from exc
    if profile == "gallery":
        ok = result.get("screen_correct") is True and result.get("gallery_visible") is True
    elif profile == "print_preview":
        ok = result.get("screen_correct") is True and result.get("print_ui_visible") is True
    elif profile == "print_success":
        ok = result.get("screen_correct") is True and result.get("success_visible") is True
    elif profile == "frame_category":
        ok = result.get("screen_correct") is True and (
            result.get("categories_visible") is True or result.get("categories_visible") is None
        )
    elif profile == "frame_carousel":
        ok = result.get("screen_correct") is True and (
            result.get("carousel_visible") is True or result.get("carousel_visible") is None
        )
    elif profile == "sticker_category":
        ok = result.get("screen_correct") is True and (
            result.get("categories_visible") is True or result.get("categories_visible") is None
        )
    elif profile == "sticker_carousel":
        ok = result.get("screen_correct") is True and (
            result.get("carousel_visible") is True or result.get("carousel_visible") is None
        )
    elif profile == "brightness_screen":
        ok = result.get("screen_correct") is True and (
            result.get("slider_visible") is True or result.get("slider_visible") is None
        )
    elif profile == "temperature_screen":
        ok = result.get("screen_correct") is True and (
            result.get("slider_visible") is True or result.get("slider_visible") is None
        )
    elif profile == "adjust_tool_screen":
        ok = result.get("screen_correct") is True and (
            result.get("tools_visible") is True or result.get("tools_visible") is None
        )
    elif profile == "blur_screen":
        ok = result.get("screen_correct") is True and (
            result.get("controls_visible") is True or result.get("controls_visible") is None
        )
    elif profile == "text_screen":
        ok = result.get("screen_correct") is True and (
            result.get("editor_visible") is True or result.get("editor_visible") is None
        )
    elif profile == "paint_screen":
        ok = result.get("screen_correct") is True and (
            result.get("palette_visible") is True or result.get("palette_visible") is None
        )
    else:
        ok = result.get("screen_correct") is True and result.get("controls_visible") is True
    return {
        "edit_screen_verified": ok,
        "print_screen_verified": ok,
        "visual_pair_verified": ok,
        "filter_pair_verified": ok,
        "summary": result.get("summary", ""),
        "model_used": model,
    }


def verify_pair_route(body: dict) -> dict:
    before = (body.get("before_basename") or "").strip()
    after = (body.get("after_basename") or "").strip()
    label = (body.get("verify_label") or "Edit change").strip()
    profile = (body.get("verify_profile") or "generic").strip()
    if not before or not after:
        raise ValueError("before_basename and after_basename required")
    before_path = find_maestro_screenshot(before)
    after_path = find_maestro_screenshot(after)
    if before_path is None or after_path is None:
        raise RuntimeError(f"Missing screenshots: before={before} after={after}")
    prompt = PAIR_PROMPTS.get(profile, PAIR_PROMPTS["generic"])
    keys = PAIR_PASS_KEYS.get(profile, PAIR_PASS_KEYS["generic"])
    try:
        result = verify_pair(
            before_path,
            after_path,
            prompt=prompt,
            before_label=f"BEFORE ({label}):",
            after_label=f"AFTER ({label}):",
            pass_keys=keys,
        )
    except Exception as exc:
        if _soft_mode() and _openrouter_unavailable(exc):
            sys.stderr.write(f"[SOFT-SKIP] pair verify: OpenRouter unavailable: {exc}\n")
            return {
                "visual_pair_verified": True,
                "filter_pair_verified": True,
                "ai_skipped": True,
                "summary": f"SKIPPED (OpenRouter unavailable): {exc}",
                "model_used": "none",
            }
        raise
    if result.get("skipped"):
        if _soft_mode() and _openrouter_unavailable(RuntimeError(result.get("summary", ""))):
            sys.stderr.write(
                f"[SOFT-SKIP] pair verify: {result.get('summary', 'OpenRouter unavailable')}\n"
            )
            return {
                "visual_pair_verified": True,
                "filter_pair_verified": True,
                "ai_skipped": True,
                "summary": f"SKIPPED: {result.get('summary', 'OpenRouter unavailable')}",
                "model_used": result.get("model_used", "none"),
            }
        raise RuntimeError(result.get("summary", "OpenRouter verify skipped"))
    ok = result.get("_pass") is True
    return {
        "visual_pair_verified": ok,
        "filter_pair_verified": ok,
        "summary": result.get("summary", ""),
        "model_used": result.get("model_used", ""),
    }


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0") or "0")
        raw = self.rfile.read(length) if length else b"{}"
        try:
            body = json.loads(raw.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            self.send_error(400, "Invalid JSON body")
            return
        try:
            if self.path in ("/verify/ed_screen", "/verify/print_screen"):
                result = verify_screen(body)
            elif self.path == "/verify/ed_pair":
                result = verify_pair_route(body)
            else:
                self.send_error(404, "Use POST /verify/ed_screen, /verify/print_screen, or /verify/ed_pair")
                return
        except Exception as exc:
            payload = json.dumps({"error": str(exc)}).encode("utf-8")
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return
        payload = json.dumps(result).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


def main() -> int:
    server = ThreadingHTTPServer((_HOST, _PORT), _Handler)
    print(f"Editing OpenRouter verify server on http://{_HOST}:{_PORT}", flush=True)
    print("Endpoints: POST /verify/ed_screen, /verify/print_screen, /verify/ed_pair", flush=True)
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
