"""Orchestrate camera view/capture AI analysis (ai-agent optional helpers)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from analysis.camera_analyzer import (
    CameraAnalyzer,
    analyze_flow_from_workspace,
)
from integrations.llm_client import LLMClient


def analyze_camera_failure_workspace(
    repo_root: Path,
    failure: dict[str, Any],
    *,
    llm: LLMClient | None = None,
) -> dict[str, Any]:
    """Enrich a failure dict with camera view/capture analysis."""
    flow = str(failure.get("flow") or failure.get("test_name") or "")
    if not CameraAnalyzer.is_camera_flow(flow):
        return failure

    suite = str(failure.get("suite") or "atp_camera")
    device = str(failure.get("device") or "")
    analyzer = CameraAnalyzer(repo_root, llm=llm)
    view, capture = analyze_flow_from_workspace(
        analyzer,
        repo_root,
        suite_id=suite,
        flow_name=flow,
        device_id=device,
    )
    out = dict(failure)
    out["camera_view_status"] = view.status
    out["camera_view_confidence"] = view.confidence
    out["camera_view_summary"] = view.summary
    out["capture_status"] = capture.status
    out["capture_confidence"] = capture.confidence
    out["capture_summary"] = capture.summary
    out["screen"] = "camera"
    if view.screenshot:
        out["screenshot_path"] = view.screenshot
    out["camera_analysis"] = {
        "view": view.as_dict(),
        "capture": capture.as_dict(),
    }
    return out
