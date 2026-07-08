"""Write visual_validation.json artifacts (separate from existing reports)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from models import VisualValidationResult


def default_output_path(screenshot_path: Path, testcase_id: str = "") -> Path:
    """
    Place visual_validation.json beside the screenshot (or in testcase folder).
    Does not move or rename screenshots.
    """
    parent = screenshot_path.parent
    if testcase_id:
        tc_dir = parent / testcase_id
        if tc_dir.is_dir():
            return tc_dir / "visual_validation.json"
    return parent / "visual_validation.json"


def write_validation_json(result: VisualValidationResult, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = result.to_json_dict()
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return output_path


def write_validation_report(result: VisualValidationResult, output_path: Path) -> Path:
    """Extended report with _meta for debugging/merge tooling."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = result.to_report_dict()
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return output_path


def merge_index_entry(result: VisualValidationResult, screenshot_path: Path) -> dict[str, Any]:
    """Lightweight row for optional downstream merge into Excel/Jenkins."""
    entry: dict[str, Any] = {
        "testcaseId": result.testcase_id,
        "screenshot": str(screenshot_path),
        "validationJson": str(default_output_path(screenshot_path, result.testcase_id)),
        "status": result.status,
    }
    if result.status != "AI_SKIPPED":
        entry["screenMatched"] = result.screen_matched
        entry["confidence"] = result.confidence
        entry["modelUsed"] = result.model_used
    else:
        entry["error"] = result.error
    return entry
