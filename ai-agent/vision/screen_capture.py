"""Screen capture and lightweight CV analysis."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from integrations.adb_client import ADBClient


@dataclass
class ScreenState:
    screenshot_path: Path | None
    ui_dump_path: Path | None
    focus_line: str
    metadata: dict[str, Any]


class VisionEngine:
    def __init__(self, adb: ADBClient, screenshot_dir: Path, ui_dump_dir: Path) -> None:
        self.adb = adb
        self.screenshot_dir = screenshot_dir
        self.ui_dump_dir = ui_dump_dir
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)
        self.ui_dump_dir.mkdir(parents=True, exist_ok=True)

    def capture(self, tag: str) -> ScreenState:
        from datetime import datetime

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        shot = self.screenshot_dir / f"{tag}_{ts}.png"
        dump = self.ui_dump_dir / f"{tag}_{ts}.xml"
        ok_shot = self.adb.screenshot(shot)
        ok_dump = self.adb.dump_ui(dump)
        return ScreenState(
            screenshot_path=shot if ok_shot else None,
            ui_dump_path=dump if ok_dump else None,
            focus_line=self.adb.current_focus(),
            metadata={"tag": tag, "screenshot_ok": ok_shot, "ui_dump_ok": ok_dump},
        )

    def analyze_brightness(self, image_path: Path) -> float:
        try:
            import cv2  # type: ignore
            import numpy as np  # type: ignore

            img = cv2.imread(str(image_path))
            if img is None:
                return 0.0
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            return float(np.mean(gray))
        except Exception:
            return 0.0
