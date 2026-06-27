"""Recovery engine — bounded intelligent retries."""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from pathlib import Path

from decision_engine.decision_engine import Decision
from integrations.adb_client import ADBClient
from ui_parser.hierarchy_parser import parse_ui_dump


@dataclass
class RecoveryResult:
    success: bool
    attempts: int
    last_action: str
    duration_ms: int
    message: str


class RecoveryEngine:
    def __init__(self, adb: ADBClient, max_attempts: int = 3) -> None:
        self.adb = adb
        self.max_attempts = max_attempts

    def execute(self, decision: Decision, ui_dump: Path | None) -> RecoveryResult:
        start = time.time()
        attempts = 0
        last = decision.chosen_action
        for _ in range(self.max_attempts):
            attempts += 1
            ok = self._apply_action(last, ui_dump)
            if ok:
                return RecoveryResult(
                    success=True,
                    attempts=attempts,
                    last_action=last,
                    duration_ms=int((time.time() - start) * 1000),
                    message="Recovery action applied",
                )
            time.sleep(1.5)
        return RecoveryResult(
            success=False,
            attempts=attempts,
            last_action=last,
            duration_ms=int((time.time() - start) * 1000),
            message="Recovery exhausted",
        )

    def _apply_action(self, action: str, ui_dump: Path | None) -> bool:
        if action.startswith("tap:"):
            label = action.split(":", 1)[1]
            return self._tap_label(label, ui_dump)
        if "allow" in action.lower():
            return self._tap_label("Allow", ui_dump) or self._tap_label("While using", ui_dump)
        if "dismiss" in action.lower() or action.startswith("app_rule:dismiss"):
            return self._tap_label("OK", ui_dump) or self._tap_label("Got it", ui_dump)
        if "rescan" in action.lower() or "bluetooth" in action.lower():
            self.adb.press_back()
            time.sleep(0.5)
            return self._tap_label("Scan", ui_dump) or self._tap_label("Search", ui_dump)
        if action == "wait_and_retry":
            time.sleep(2.0)
            return True
        if action == "navigate_back":
            return self.adb.press_back()
        return False

    def _tap_label(self, label: str, ui_dump: Path | None) -> bool:
        if not ui_dump or not ui_dump.is_file():
            return False
        elements = parse_ui_dump(ui_dump)
        for el in elements:
            hay = f"{el.text} {el.content_desc}"
            if label.lower() in hay.lower() and el.clickable:
                center = el.center
                if center:
                    return self.adb.tap(center[0], center[1])
        return False
