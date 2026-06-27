"""Execute recovery actions on device via adb (tap, swipe, key, settings)."""

from __future__ import annotations

import os
import re
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from ai.ui_parser import UIElement


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
class ActionResult:
    success: bool
    action: str
    detail: str = ""


class ActionExecutor:
    def __init__(self, device_id: str, app_package: str = "com.kodak.steptouch") -> None:
        self.device_id = device_id
        self.app_package = app_package
        self._adb = _adb_exe()

    def _run(self, *args: str, timeout: int = 30) -> subprocess.CompletedProcess[str]:
        cmd = [self._adb, "-s", self.device_id, *args]
        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8",
            errors="replace",
        )

    def tap_element(self, element: UIElement) -> ActionResult:
        center = element.center
        if not center:
            return ActionResult(False, "tap_element", "No bounds on element")
        x, y = center
        p = self._run("shell", "input", "tap", str(x), str(y))
        ok = p.returncode == 0
        return ActionResult(ok, "tap_element", f"tap ({x},{y}) label={element.label!r}")

    def tap_text(self, tree: UIElement | None, pattern: str) -> ActionResult:
        if tree is None:
            return ActionResult(False, "tap_text", "No UI tree")
        hits = tree.find_clickable_with_text(pattern)
        if not hits:
            for node in tree.flatten():
                if node.label and re.search(pattern, node.label, re.I):
                    if node.center:
                        return self.tap_element(node)
            return ActionResult(False, "tap_text", f"No match for {pattern!r}")
        return self.tap_element(hits[0])

    def tap_label_exact(self, tree: UIElement | None, label: str) -> ActionResult:
        if tree is None:
            return ActionResult(False, "tap_label_exact", "No UI tree")
        target = label.strip().lower()
        for node in tree.flatten():
            if node.clickable and node.label.lower() == target:
                return self.tap_element(node)
        return ActionResult(False, "tap_label_exact", f"Label not found: {label!r}")

    def swipe_refresh(self) -> ActionResult:
        p = self._run("shell", "input", "swipe", "540", "400", "540", "1200", "350")
        return ActionResult(p.returncode == 0, "swipe_refresh", "pull-to-refresh gesture")

    def press_back(self) -> ActionResult:
        p = self._run("shell", "input", "keyevent", "KEYCODE_BACK")
        return ActionResult(p.returncode == 0, "press_back", "KEYCODE_BACK")

    def wait_ms(self, ms: int) -> None:
        time.sleep(max(0, ms) / 1000.0)

    def enable_bluetooth(self) -> ActionResult:
        p = self._run("shell", "cmd", "bluetooth_manager", "enable")
        if p.returncode != 0:
            p = self._run("shell", "svc", "bluetooth", "enable")
        return ActionResult(p.returncode == 0, "enable_bluetooth", (p.stderr or p.stdout or "").strip())

    def launch_app(self) -> ActionResult:
        p = self._run(
            "shell",
            "monkey",
            "-p",
            self.app_package,
            "-c",
            "android.intent.category.LAUNCHER",
            "1",
        )
        return ActionResult(p.returncode == 0, "launch_app", self.app_package)

    def open_app_settings(self) -> ActionResult:
        p = self._run(
            "shell",
            "am",
            "start",
            "-a",
            "android.settings.APPLICATION_DETAILS_SETTINGS",
            "-d",
            f"package:{self.app_package}",
        )
        return ActionResult(p.returncode == 0, "open_app_settings", self.app_package)
