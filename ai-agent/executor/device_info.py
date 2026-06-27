"""Collect device/app metadata for AI Agent reports."""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass


@dataclass
class DeviceInfo:
    device_id: str
    device_name: str
    android_version: str
    app_version: str
    printer_name: str
    firmware_version: str


def collect_device_info(device_id: str, app_package: str, timeout: int = 10) -> DeviceInfo:
    def adb(*args: str) -> str:
        try:
            r = subprocess.run(
                ["adb", "-s", device_id, *args],
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
            return (r.stdout or "") + (r.stderr or "")
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return ""

    android = ""
    m = re.search(r"\[ro\.build\.version\.release\]:?\s*\[([^\]]+)\]", adb("shell", "getprop"))
    if not m:
        m = re.search(r"release=(\S+)", adb("shell", "getprop", "ro.build.version.release"))
    if m:
        android = m.group(1).strip()

    app_ver = ""
    dump = adb("shell", "dumpsys", "package", app_package)
    vm = re.search(r"versionName=(\S+)", dump)
    if vm:
        app_ver = vm.group(1).strip()

    model = adb("shell", "getprop", "ro.product.model").strip()

    return DeviceInfo(
        device_id=device_id,
        device_name=model or device_id,
        android_version=android or "unknown",
        app_version=app_ver or "unknown",
        printer_name="",
        firmware_version="",
    )
