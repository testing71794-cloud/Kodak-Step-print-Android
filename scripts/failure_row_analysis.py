"""
Excel-oriented failure analysis: OpenRouter + rule fallback; never leave failed rows blank.
Respects build-summary/ai_status.txt: AI_STATUS=UNAVAILABLE skips OpenRouter; otherwise
uses key from OpenRouterAPI (primary) when not blocked.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
if str(REPO / "scripts") not in sys.path:
    sys.path.insert(0, str(REPO / "scripts"))


def _read_openrouter_key() -> str:
    return (
        (os.environ.get("OpenRouterAPI", "") or "").strip()
        or (os.environ.get("OPENROUTER_API_KEY", "") or "").strip()
        or (os.environ.get("OPENROUTER_KEY", "") or "").strip()
    )


def _read_build_ai_status_block() -> dict[str, str]:
    """Values from build-summary/ai_status.txt; never includes secrets."""
    p = REPO / "build-summary" / "ai_status.txt"
    d: dict[str, str] = {
        "ai_status": "NOT_CHECKED",
        "model_used_health": "",
        "key_present": "no",
    }
    d["key_present"] = "yes" if _read_openrouter_key() else "no"
    if not p.is_file():
        return d
    try:
        for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
            s = line.strip()
            if s.upper().startswith("AI_STATUS="):
                d["ai_status"] = s.split("=", 1)[1].strip() or d["ai_status"]
            elif s.upper().startswith("MODEL_USED="):
                d["model_used_health"] = s.split("=", 1)[1].strip() or d["model_used_health"]
            elif s.upper().startswith("MODEL=") and not d.get("model_used_health"):
                d["model_used_health"] = s.split("=", 1)[1].strip() or d["model_used_health"]
            elif s.upper().startswith("KEY_PRESENT="):
                d["key_present"] = s.split("=", 1)[1].strip() or d["key_present"]
    except OSError:
        pass
    if _read_openrouter_key() and d.get("key_present") == "no":
        d["key_present"] = "yes"
    return d


def _read_ai_status_unavailable() -> bool:
    p = REPO / "build-summary" / "ai_status.txt"
    if not p.is_file():
        return False
    try:
        return "AI_STATUS=UNAVAILABLE" in p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False


def _read_log_tail(p: Path, max_bytes: int = 120_000) -> str:
    if not p.is_file():
        return ""
    try:
        raw = p.read_bytes()
        if len(raw) > max_bytes:
            raw = raw[-max_bytes:]
        return raw.decode("utf-8", errors="replace")
    except OSError:
        return ""


def _build_failure_dict(log_text: str) -> dict[str, Any]:
    try:
        from intelligent_platform.failure_parser import parse_failures

        rows = parse_failures(log_text)
        if rows:
            r = dict(rows[-1])
            r.setdefault("error_message", r.get("error_message", ""))
            r.setdefault("step_failed", r.get("step_failed", ""))
            return r
    except Exception:
        pass
    line = (log_text or "").strip().splitlines()
    last = line[-1] if line else ""
    return {
        "error_message": (log_text or "")[-4000:],
        "step_failed": last[:500],
    }


def _camera_analysis_for_row(
    flow_name: str,
    suite: str,
    device_id: str,
    status: str,
) -> dict[str, Any] | None:
    try:
        from camera_vision_analysis import analyze_camera_for_excel_row, is_camera_automation_flow

        if not is_camera_automation_flow(flow_name, suite):
            return None
        return analyze_camera_for_excel_row(
            flow_name=flow_name,
            suite=suite,
            device_id=device_id,
            status=status,
        )
    except Exception:
        return None


def _merge_camera_into_result(base: dict[str, Any], cam: dict[str, Any] | None) -> dict[str, Any]:
    if not cam:
        return base
    out = dict(base)
    cam_summary = str(cam.get("ai_failure_summary") or cam.get("camera_summary") or "")
    if cam_summary:
        prev = str(out.get("ai_failure_summary") or "").strip()
        if prev and prev not in ("—", "-"):
            out["ai_failure_summary"] = f"{cam_summary} | Maestro: {prev}"[:2000]
        else:
            out["ai_failure_summary"] = cam_summary[:2000]
    if cam.get("root_cause_category") and out.get("root_cause_category") in ("Unknown", "—", ""):
        out["root_cause_category"] = cam["root_cause_category"]
    if cam.get("suggested_fix") and str(out.get("suggested_fix") or "—") in ("—", ""):
        out["suggested_fix"] = cam["suggested_fix"]
    if cam.get("screenshot_path"):
        out["screenshot_path"] = cam["screenshot_path"]
    if out.get("analysis_source") in ("Rule-based fallback", "N/A", "Heuristic (FLAKY)"):
        out["analysis_source"] = cam.get("analysis_source", out.get("analysis_source"))
    return out


def analyze_failure_for_row(
    log_path: str | None,
    *,
    status: str = "",
    use_openrouter: bool = True,
    flow_name: str = "",
    suite: str = "",
    device_id: str = "",
) -> dict[str, Any]:
    """
    Return keys: failure_step, error_message, ai_failure_summary, root_cause_category,
    suggested_fix, ai_confidence, analysis_source, ai_status, model_used, key_present
    """
    meta = _read_build_ai_status_block()
    p = Path(log_path or "")
    log_text = _read_log_tail(p) if p else ""
    st = (status or "").upper()
    cam = _camera_analysis_for_row(flow_name, suite, device_id, st)

    if st in ("PASS", "SKIPPED"):
        if cam:
            return {
                "failure_step": "",
                "error_message": "",
                "ai_failure_summary": cam["ai_failure_summary"],
                "root_cause_category": cam["root_cause_category"],
                "suggested_fix": cam["suggested_fix"],
                "ai_confidence": cam["ai_confidence"],
                "analysis_source": cam["analysis_source"],
                "ai_status": meta.get("ai_status", "NOT_CHECKED"),
                "model_used": cam["model_used"],
                "key_present": meta.get("key_present", "no"),
                "screenshot_path": cam.get("screenshot_path", ""),
            }
        return {
            "failure_step": "",
            "error_message": "",
            "ai_failure_summary": "—",
            "root_cause_category": "—",
            "suggested_fix": "—",
            "ai_confidence": 1.0,
            "analysis_source": "N/A",
            "ai_status": meta.get("ai_status", "NOT_CHECKED"),
            "model_used": "—",
            "key_present": meta.get("key_present", "no"),
        }
    if st == "FLAKY":
        base = {
            "failure_step": "—",
            "error_message": "—",
            "ai_failure_summary": "Flaky run — see log for first failure and retry context.",
            "root_cause_category": "Timing/Flaky Issue",
            "suggested_fix": "Stabilize waits; check device load and animation timing.",
            "ai_confidence": 0.55,
            "analysis_source": "Heuristic (FLAKY)",
            "ai_status": meta.get("ai_status", "NOT_CHECKED"),
            "model_used": "—",
            "key_present": meta.get("key_present", "no"),
        }
        return _merge_camera_into_result(base, cam)

    fd = _build_failure_dict(log_text)
    if cam:
        fd["flow"] = flow_name
        fd["suite"] = suite
        fd["device"] = device_id
        fd["camera_view_summary"] = cam.get("camera_summary", "")
    err = (fd.get("error_message") or "")[:2000]
    step = (fd.get("step_failed") or err[:240] or "Unknown step")[:2000]

    has_key = bool(_read_openrouter_key())
    want_ai = use_openrouter and has_key and not _read_ai_status_unavailable()

    if want_ai:
        try:
            from intelligent_platform.ai_failure_analyzer import analyze_failure
            from intelligent_platform import config as _cfg

            if not _cfg.openrouter_configured():
                want_ai = False
            else:
                r = analyze_failure(fd)
                if r and str(r.get("root_cause", "")).strip():
                    asrc = str(
                        r.get("analysis_source")
                        or r.get("source_label")
                        or "OpenRouter"
                    )[:60]
                    base = {
                        "failure_step": step,
                        "error_message": err
                        or str(r.get("root_cause", ""))[:2000],
                        "ai_failure_summary": str(r.get("root_cause", ""))[:2000],
                        "root_cause_category": str(
                            r.get("category", "assertion")
                        )[:120],
                        "suggested_fix": str(r.get("suggestion", ""))[:2000],
                        "ai_confidence": float(r.get("confidence", 0.7) or 0.7),
                        "analysis_source": asrc,
                        "ai_status": str(r.get("ai_status", meta.get("ai_status", "")) or "")
                        or meta.get("ai_status", "NOT_CHECKED")
                        or "",
                        "model_used": str(
                            r.get("model_used")
                            or meta.get("model_used_health", "")
                            or ""
                        )
                        or "—",
                        "key_present": "yes",
                    }
                    return _merge_camera_into_result(base, cam)
        except Exception as e:
            err = f"{err} [AI error: {e}]"[:2000] if err else f"AI error: {e}"

    r2 = _rule_fallback(err, step, log_text, meta=meta)
    r2["error_message"] = (err or r2.get("error_message", "See log."))[:2000]
    if cam and not want_ai:
        return {
            **r2,
            "ai_failure_summary": cam["ai_failure_summary"],
            "root_cause_category": cam.get("root_cause_category", r2.get("root_cause_category")),
            "suggested_fix": cam.get("suggested_fix", r2.get("suggested_fix")),
            "ai_confidence": cam.get("ai_confidence", r2.get("ai_confidence")),
            "analysis_source": cam.get("analysis_source", r2.get("analysis_source")),
            "model_used": cam.get("model_used", r2.get("model_used")),
            "screenshot_path": cam.get("screenshot_path", ""),
        }
    return _merge_camera_into_result(r2, cam)


def _rule_fallback(
    err: str, step: str, log_text: str, *, meta: dict[str, str] | None = None
) -> dict[str, Any]:
    m = meta or _read_build_ai_status_block()
    text = f"{err} {log_text}"[-8000:]
    low = text.lower()
    base = {
        "key_present": m.get("key_present", "no"),
        "ai_status": m.get("ai_status", "NOT_CHECKED"),
    }
    if "device" in low and (
        "offline" in low or "unauthorized" in low or "not found" in low
    ):
        return {
            **base,
            "failure_step": step,
            "error_message": err or "Device / ADB issue",
            "ai_failure_summary": "ADB reports device not ready, offline, or unauthorized.",
            "root_cause_category": "Config/Setup Issue",
            "suggested_fix": "Check USB, authorize RSA, adb devices, and single concurrent user of adb.",
            "ai_confidence": 0.75,
            "analysis_source": "Rule-based fallback",
            "model_used": "rules",
        }
    if "element not found" in low or "id matching" in low:
        return {
            **base,
            "failure_step": step,
            "error_message": err or "Element not found",
            "ai_failure_summary": "Maestro could not find the target element (locator).",
            "root_cause_category": "locator",
            "suggested_fix": "Update selectors from hierarchy; add waits; check screen state.",
            "ai_confidence": 0.72,
            "analysis_source": "Rule-based fallback",
            "model_used": "rules",
        }
    if "assertion" in low:
        return {
            **base,
            "failure_step": step,
            "error_message": err or "Assertion failed",
            "ai_failure_summary": "Assertion did not pass within the test flow.",
            "root_cause_category": "assertion",
            "suggested_fix": "Compare expected vs app state; adjust timing and preconditions.",
            "ai_confidence": 0.6,
            "analysis_source": "Rule-based fallback",
            "model_used": "rules",
        }
    return {
        **base,
        "failure_step": step,
        "error_message": err or "Test failed — see log path.",
        "ai_failure_summary": (err or "Failure recorded; inspect log for the exact Maestro line.")[:2000],
        "root_cause_category": "Unknown",
        "suggested_fix": "Open the log file; reproduce locally with same device and data.",
        "ai_confidence": 0.45,
        "analysis_source": "Rule-based fallback",
        "model_used": "rules",
    }
