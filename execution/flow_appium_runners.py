"""Route selected Maestro ATP flows to Appium W3C pinch runners (Jenkins / run_one_flow)."""
from __future__ import annotations

import re
from pathlib import Path

# Split Maestro steps used only by Appium orchestrators — not top-level Jenkins tests.
_APPium_HELPER_STEM_RE = re.compile(r"^GA_0[56][ab] -", re.IGNORECASE)

# Top-level ATP yaml stem -> repo-relative runner .bat (device serial passed as %1).
_FLOW_RUNNER_BAT: dict[str, str] = {
    "GA_05 - Pinch to zoom out": "scripts/run_ga05_real_pinch.bat",
    "GA_06 - Pinch to zoom in": "scripts/run_ga06_real_pinch.bat",
}


def is_appium_helper_flow(path: Path) -> bool:
    """GA_05a/b and GA_06a/b are invoked by run_ga*_real_pinch.bat, not Jenkins discovery."""
    return bool(_APPium_HELPER_STEM_RE.match((path.stem or "").strip()))


def resolve_appium_runner_bat(flow_path: Path, repo: Path) -> Path | None:
    """Return absolute .bat path when flow should use Appium W3C pinch instead of Maestro-only yaml."""
    rel = _FLOW_RUNNER_BAT.get((flow_path.stem or "").strip())
    if not rel:
        return None
    bat = (repo / rel).resolve()
    return bat if bat.is_file() else None
