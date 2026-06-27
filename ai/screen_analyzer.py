"""Capture and analyze current device screen (screenshot + UI dump + OCR)."""

from __future__ import annotations

import os
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ai.ocr_engine import extract_text
from ai.ui_parser import UIElement, parse_ui_dump, screen_context_summary


def _adb_exe() -> str:
    for env in ("ADB_HOME",):
        root = os.environ.get(env, "").strip().strip('"')
        if root:
            exe = Path(root) / ("adb.exe" if os.name == "nt" else "adb")
            if exe.is_file():
                return str(exe)
    for env in ("ANDROID_HOME", "ANDROID_SDK_ROOT"):
        root = os.environ.get(env, "").strip().strip('"')
        if root:
            exe = Path(root) / "platform-tools" / ("adb.exe" if os.name == "nt" else "adb")
            if exe.is_file():
                return str(exe)
    return "adb"


@dataclass
class ScreenSnapshot:
    screenshot_path: Path
    ui_dump_path: Path
    ui_tree: UIElement | None
    ocr_lines: list[str]
    context: dict[str, Any]
    captured_at: float


class ScreenAnalyzer:
    def __init__(self, device_id: str, artifact_dir: Path) -> None:
        self.device_id = device_id
        self.artifact_dir = artifact_dir
        self.artifact_dir.mkdir(parents=True, exist_ok=True)
        self._adb = _adb_exe()

    def _run(self, *args: str, timeout: int = 60) -> subprocess.CompletedProcess[str]:
        cmd = [self._adb, "-s", self.device_id, *args]
        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8",
            errors="replace",
        )

    def capture(self, tag: str = "recovery") -> ScreenSnapshot:
        ts = time.strftime("%Y%m%d_%H%M%S")
        base = self.artifact_dir / f"{tag}_{self.device_id}_{ts}"
        png = base.with_suffix(".png")
        xml_device = "/sdcard/ai_ui_dump.xml"
        xml_local = base.with_suffix(".xml")

        self._run("shell", "screencap", "-p", f"/sdcard/ai_screen_{ts}.png")
        self._run("pull", f"/sdcard/ai_screen_{ts}.png", str(png))
        self._run("shell", "uiautomator", "dump", xml_device)
        self._run("pull", xml_device, str(xml_local))

        tree = parse_ui_dump(xml_local)
        ocr_lines = extract_text(png)
        ctx = screen_context_summary(tree, ocr_lines)
        return ScreenSnapshot(
            screenshot_path=png,
            ui_dump_path=xml_local,
            ui_tree=tree,
            ocr_lines=ocr_lines,
            context=ctx,
            captured_at=time.time(),
        )

    def classify_screen(self, snapshot: ScreenSnapshot) -> tuple[str, float, str]:
        """
        Rule-based screen classification.
        Returns (classification, confidence, brief_reason).
        """
        text_blob = " ".join(snapshot.context.get("all_visible_text", [])).lower()
        clickable = " ".join(snapshot.context.get("clickable_labels", [])).lower()
        combined = f"{text_blob} {clickable}"

        rules: list[tuple[str, float, str, tuple[str, ...]]] = [
            (
                "bluetooth_disabled",
                0.85,
                "System prompt to turn on Bluetooth",
                ("turn on bluetooth", "bluetooth is off", "enable bluetooth"),
            ),
            (
                "permission_dialog",
                0.9,
                "Android runtime permission sheet",
                (
                    "while using the app",
                    "only this time",
                    "don't allow",
                    "allow kodak",
                    "take pictures",
                    "nearby devices",
                    "send you notifications",
                ),
            ),
            (
                "printer_not_found",
                0.88,
                "No printer discovered after scan",
                ("no printer", "printer not found", "couldn't find", "no devices found", "search again"),
            ),
            (
                "multiple_printers",
                0.82,
                "Multiple printer candidates visible",
                ("select a printer", "choose printer", "available printers"),
            ),
            (
                "printer_busy_popup",
                0.8,
                "Printer busy or unavailable popup",
                ("printer busy", "try again later", "printer unavailable"),
            ),
            (
                "firmware_update_popup",
                0.78,
                "Firmware update prompt",
                ("firmware update", "update available", "software update"),
            ),
            (
                "paper_low_popup",
                0.75,
                "Paper or media warning",
                ("paper low", "out of paper", "load paper", "replace cartridge"),
            ),
            (
                "battery_low_popup",
                0.75,
                "Battery warning on printer or device",
                ("battery low", "charge your", "low battery"),
            ),
            (
                "unexpected_popup",
                0.6,
                "Generic dismissible dialog",
                ("ok", "cancel", "dismiss", "got it", "not now", "later"),
            ),
            (
                "connection_scanning",
                0.7,
                "Printer search in progress",
                ("searching", "scanning", "looking for"),
            ),
        ]

        best = ("unknown_state", 0.3, "No rule matched confidently")
        for name, conf, reason, needles in rules:
            if any(n in combined for n in needles):
                if conf > best[1]:
                    best = (name, conf, reason)

        # Heuristic: list-like printer rows (Step / Kodak names) without explicit multi-printer copy
        if best[0] == "unknown_state":
            printer_hits = [
                w
                for w in snapshot.context.get("all_visible_text", [])
                if re_printer_name(w)
            ]
            if len(printer_hits) >= 2:
                best = ("multiple_printers", 0.75, f"Detected {len(printer_hits)} printer-like labels")

        return best


def re_printer_name(label: str) -> bool:
    s = label.lower()
    return any(k in s for k in ("kodak", "step", "barbie", "printer")) and len(label) > 3
