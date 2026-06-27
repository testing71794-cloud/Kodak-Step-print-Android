"""Continuous UI monitoring for adaptive execution."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from integrations.adb_client import ADBClient
from ocr.ocr_engine import extract_text
from ui_parser.hierarchy_parser import parse_ui_dump
from vision.screen_capture import VisionEngine


@dataclass
class ScreenObservation:
    labels: list[str]
    has_loading: bool
    has_progress: bool
    ocr_sample: str
    focus_line: str


class ScreenMonitor:
    LOADING_PATTERNS = re.compile(
        r"loading|please wait|connecting|searching|pairing|spinner|progress",
        re.I,
    )

    def __init__(self, adb: ADBClient, vision: VisionEngine) -> None:
        self.adb = adb
        self.vision = vision

    def observe(self, tag: str) -> tuple[ScreenObservation, Path | None, Path | None]:
        cap = self.vision.capture(tag)
        labels: list[str] = []
        ocr = ""
        if cap.ui_dump_path:
            elements = parse_ui_dump(cap.ui_dump_path)
            labels = [e.text for e in elements if e.text][:25]
        if cap.screenshot_path:
            ocr = extract_text(cap.screenshot_path)[:500]
        combined = " ".join(labels + [ocr])
        obs = ScreenObservation(
            labels=labels,
            has_loading=bool(self.LOADING_PATTERNS.search(combined)),
            has_progress="ProgressBar" in (cap.focus_line or ""),
            ocr_sample=ocr[:200],
            focus_line=cap.focus_line,
        )
        return obs, cap.screenshot_path, cap.ui_dump_path

    def wait_until_idle(self, waiter, tag: str, timeout: float | None = None) -> bool:
        def _idle() -> bool:
            obs, _, _ = self.observe(tag)
            return not obs.has_loading and not obs.has_progress

        result = waiter.until(f"{tag}_idle", _idle, timeout=timeout)
        return result.success

    def wait_for_text(self, waiter, tag: str, pattern: str) -> bool:
        rx = re.compile(pattern, re.I)

        def _found() -> bool:
            obs, _, _ = self.observe(tag)
            hay = " ".join(obs.labels) + " " + obs.ocr_sample
            return bool(rx.search(hay))

        return waiter.until(f"{tag}_text_{pattern[:20]}", _found).success
