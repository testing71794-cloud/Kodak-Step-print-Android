"""Read connected devices from repo detected_devices.txt or adb."""

from __future__ import annotations

import subprocess
from pathlib import Path


def list_devices(repo_root: Path) -> list[str]:
    detected = repo_root / "detected_devices.txt"
    if detected.is_file():
        lines = [
            ln.strip()
            for ln in detected.read_text(encoding="utf-8", errors="replace").splitlines()
            if ln.strip() and not ln.strip().startswith("#")
        ]
        if lines:
            return lines
    try:
        out = subprocess.run(
            ["adb", "devices"],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        ids: list[str] = []
        for line in out.stdout.splitlines()[1:]:
            parts = line.split()
            if len(parts) >= 2 and parts[1] == "device":
                ids.append(parts[0])
        return ids
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return []
