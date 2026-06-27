"""One-time suite setup: devices, optional precheck, MasterSetup Maestro flow."""

from __future__ import annotations

import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from execution.atp_folder_paths import resolve_atp_subfolder
from execution.subprocess_launch import log_subprocess_launch, windows_cmd_bat_argv

from suite.config_loader import SuiteConfig


@dataclass
class SetupResult:
    success: bool
    message: str
    duration_sec: float
    devices: list[str]


def read_detected_devices(repo: Path) -> list[str]:
    path = repo / "detected_devices.txt"
    if not path.is_file():
        return []
    lines = [
        ln.strip()
        for ln in path.read_text(encoding="utf-8", errors="replace").splitlines()
        if ln.strip() and not ln.strip().startswith("#")
    ]
    return lines


def refresh_devices(repo: Path) -> None:
    bat = repo / "scripts" / "windows_agent" / "list_devices.bat"
    if not bat.is_file():
        bat = repo / "scripts" / "list_devices.bat"
    if not bat.is_file():
        return
    cmd = windows_cmd_bat_argv(bat, str(repo.resolve()))
    log_subprocess_launch(cmd, cwd=repo, shell=False, label="suite_refresh_devices")
    subprocess.run(cmd, cwd=str(repo), check=False, shell=False)


def verify_app_on_devices(repo: Path, app_package: str, devices: list[str]) -> tuple[bool, str]:
    adb = _adb_exe()
    missing: list[str] = []
    for serial in devices:
        p = subprocess.run(
            [adb, "-s", serial, "shell", "pm", "path", app_package],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if p.returncode != 0 or "package:" not in (p.stdout or ""):
            missing.append(serial)
    if missing:
        return False, f"App {app_package} not installed on: {', '.join(missing)}"
    return True, "ok"


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


def run_master_setup_flow(
    repo: Path,
    *,
    device_id: str,
    setup_flow: Path,
    maestro_cmd: str,
) -> tuple[bool, str]:
    flow = setup_flow.resolve()
    if not flow.is_file():
        return False, f"MasterSetup flow missing: {flow}"

    maestro = maestro_cmd.strip() or os.environ.get("MAESTRO_CMD", "maestro.bat")
    if not Path(maestro).is_absolute():
        candidate = repo / maestro
        if candidate.is_file():
            maestro = str(candidate)

    argv = [maestro, "--device", device_id, "test", str(flow)]
    log_subprocess_launch(argv, cwd=repo, shell=False, label=f"suite_setup_{device_id}")
    p = subprocess.run(argv, cwd=str(repo), check=False)
    if p.returncode != 0:
        return False, f"MasterSetup failed on {device_id} exit={p.returncode}"
    return True, "ok"


def run_suite_setup(
    repo: Path,
    config: SuiteConfig,
    *,
    app_package: str,
    maestro_cmd: str,
) -> SetupResult:
    t0 = time.time()
    if not config.setup_enabled:
        return SetupResult(True, "setup skipped (disabled in config)", 0.0, [])

    refresh_devices(repo)
    devices = read_detected_devices(repo)
    if not devices:
        return SetupResult(False, "No devices in detected_devices.txt", time.time() - t0, [])

    if config.verify_app_installed:
        ok, msg = verify_app_on_devices(repo, app_package, devices)
        if not ok:
            return SetupResult(False, msg, time.time() - t0, devices)

    if config.run_precheck:
        pre = repo / "scripts" / "jenkins_ci_precheck.bat"
        if pre.is_file():
            cmd = windows_cmd_bat_argv(pre, str(repo.resolve()), maestro_cmd, app_package)
            subprocess.run(cmd, cwd=str(repo), check=False, shell=False)

    setup_path = Path(config.setup_flow)
    failures: list[str] = []
    for dev in devices:
        ok, msg = run_master_setup_flow(
            repo, device_id=dev, setup_flow=setup_path, maestro_cmd=maestro_cmd
        )
        if not ok:
            failures.append(f"{dev}: {msg}")

    if failures:
        return SetupResult(
            False,
            "; ".join(failures),
            time.time() - t0,
            devices,
        )

    # Resolve folder sanity (optional)
    _ = resolve_atp_subfolder(repo, "connection")
    return SetupResult(True, "MasterSetup completed on all devices", time.time() - t0, devices)
