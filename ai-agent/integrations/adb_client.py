"""ADB client — isolated from existing orchestrator."""

from __future__ import annotations

import subprocess
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class UIElement:
    text: str
    resource_id: str
    class_name: str
    bounds: str
    clickable: bool
    enabled: bool


class ADBClient:
    def __init__(self, device_id: str, app_package: str, timeout: int = 15) -> None:
        self.device_id = device_id
        self.app_package = app_package
        self.timeout = timeout

    def _adb(self, *args: str) -> subprocess.CompletedProcess[str]:
        cmd = ["adb", "-s", self.device_id, *args]
        return subprocess.run(cmd, capture_output=True, text=True, timeout=self.timeout, check=False)

    def screenshot(self, dest: Path) -> bool:
        dest.parent.mkdir(parents=True, exist_ok=True)
        remote = "/sdcard/ai_agent_screen.png"
        r1 = self._adb("shell", "screencap", "-p", remote)
        if r1.returncode != 0:
            return False
        r2 = self._adb("pull", remote, str(dest))
        self._adb("shell", "rm", remote)
        return r2.returncode == 0 and dest.is_file()

    def dump_ui(self, dest: Path) -> bool:
        dest.parent.mkdir(parents=True, exist_ok=True)
        remote = "/sdcard/ai_agent_ui.xml"
        r1 = self._adb("shell", "uiautomator", "dump", remote)
        if r1.returncode != 0:
            r1 = self._adb("shell", "uiautomator", "dump", "/sdcard/window_dump.xml")
            remote = "/sdcard/window_dump.xml"
        r2 = self._adb("pull", remote, str(dest))
        return r2.returncode == 0 and dest.is_file()

    def tap(self, x: int, y: int) -> bool:
        return self._adb("shell", "input", "tap", str(x), str(y)).returncode == 0

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300) -> bool:
        return self._adb(
            "shell", "input", "swipe", str(x1), str(y1), str(x2), str(y2), str(duration_ms)
        ).returncode == 0

    def press_back(self) -> bool:
        return self._adb("shell", "input", "keyevent", "KEYCODE_BACK").returncode == 0

    def current_focus(self) -> str:
        r = self._adb("shell", "dumpsys", "window", "windows")
        for line in r.stdout.splitlines():
            if "mCurrentFocus" in line or "mFocusedApp" in line:
                return line.strip()
        return ""

    def launch_app(self) -> bool:
        return self._adb(
            "shell", "monkey", "-p", self.app_package, "-c", "android.intent.category.LAUNCHER", "1"
        ).returncode == 0
