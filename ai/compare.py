"""Parse and normalize model JSON responses."""

from __future__ import annotations

import json
import re
from typing import Any

from models import ValidationMode, VisualValidationResult


_BOOL_TRUE = {"true", "yes", "1"}
_BOOL_FALSE = {"false", "no", "0"}


def _coerce_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        low = value.strip().lower()
        if low in _BOOL_TRUE:
            return True
        if low in _BOOL_FALSE:
            return False
    return False


def _coerce_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _coerce_str_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value] if value.strip() else []
    if isinstance(value, list):
        return [str(x) for x in value if str(x).strip()]
    return []


def extract_json_object(raw: str) -> dict[str, Any]:
    text = (raw or "").strip()
    if not text:
        raise ValueError("empty model response")

    if "```" in text:
        for part in text.split("```"):
            chunk = part.strip()
            if chunk.lower().startswith("json"):
                chunk = chunk[4:].strip()
            if chunk.startswith("{"):
                text = chunk
                break

    if not text.startswith("{"):
        start, end = text.find("{"), text.rfind("}")
        if start >= 0 and end > start:
            text = text[start : end + 1]

    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    # key=value fallback (some VL models ignore JSON-only instruction)
    kv = _parse_key_value_response(text)
    if kv:
        return kv

    raise ValueError(f"invalid JSON from model: {text[:200]}")


def _parse_key_value_response(text: str) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for m in re.finditer(
        r"([A-Za-z_][A-Za-z0-9_]*)\s*[=:]\s*(\"[^\"]*\"|'[^']*'|[^,\n}]+)",
        text,
    ):
        key = m.group(1).strip()
        val_raw = m.group(2).strip().strip('"').strip("'").strip()
        low = val_raw.lower()
        if low in _BOOL_TRUE:
            result[key] = True
        elif low in _BOOL_FALSE:
            result[key] = False
        else:
            result[key] = val_raw
    decision_fields = {
        "screenMatched",
        "screen_matched",
        "confidence",
        "popupDetected",
        "popup_detected",
        "similarityScore",
        "similarity_score",
    }
    if any(f in result for f in decision_fields):
        return result
    return {}


def parse_validation_response(
    raw: str,
    *,
    mode: ValidationMode,
) -> VisualValidationResult:
    data = extract_json_object(raw)
    result = VisualValidationResult(
        status="OK",
        screen=str(data.get("screen") or data.get("screenName") or ""),
        screen_matched=_coerce_bool(data.get("screenMatched", data.get("screen_matched"))),
        confidence=max(0, min(100, _coerce_int(data.get("confidence"), 0))),
        missing_elements=_coerce_str_list(data.get("missingElements", data.get("missing_elements"))),
        unexpected_elements=_coerce_str_list(
            data.get("unexpectedElements", data.get("unexpected_elements"))
        ),
        ocr_issues=_coerce_str_list(data.get("ocrIssues", data.get("ocr_issues"))),
        layout_issues=_coerce_str_list(data.get("layoutIssues", data.get("layout_issues"))),
        popup_detected=_coerce_bool(data.get("popupDetected", data.get("popup_detected"))),
        recommendation=str(data.get("recommendation") or ""),
        mode=mode.value,
    )
    if mode == ValidationMode.COMPARE:
        result.similarity_score = max(
            0, min(100, _coerce_int(data.get("similarityScore", data.get("similarity_score")), 0))
        )
        result.differences = _coerce_str_list(data.get("differences"))
    return result
