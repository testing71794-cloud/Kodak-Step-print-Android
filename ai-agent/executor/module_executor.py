"""Fast path — run ATP module via existing jenkins_atp_stage (no Maestro YAML changes)."""

from __future__ import annotations

import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ModuleRunResult:
    name: str
    folder: str
    suite_id: str
    passed: bool
    exit_code: int
    duration_sec: float
    message: str = ""


def folder_to_suite_id(folder: str) -> str:
    t = re.sub(r"[^a-zA-Z0-9]+", "_", folder.strip())
    t = t.strip("_").lower()
    return f"atp_{t or 'unknown'}"


def _folder_exists(repo: Path, folder: str) -> bool:
    base = repo / "ATP TestCase Flows" / folder
    if base.is_dir():
        return True
    atp = repo / "ATP TestCase Flows"
    if not atp.is_dir():
        return False
    target = folder.lower().replace("_", "-")
    for d in atp.iterdir():
        if d.is_dir() and d.name.lower().replace("_", "-") == target:
            return True
    return False


def run_module_fast(
    repo: Path,
    *,
    folder: str,
    module_name: str,
    app_package: str,
    maestro_cmd: str,
    device_id: str,
    clear_state: bool,
    skip_device_refresh: bool = True,
    warm_session: bool = False,
) -> ModuleRunResult:
    t0 = time.time()
    sid = folder_to_suite_id(folder)

    if not _folder_exists(repo, folder):
        return ModuleRunResult(
            name=module_name,
            folder=folder,
            suite_id=sid,
            passed=True,
            exit_code=0,
            duration_sec=time.time() - t0,
            message="Module folder missing — skipped",
        )

    env = os.environ.copy()
    env["AI_AGENT_MODULE"] = module_name
    env["AI_AGENT_STATEFUL_SESSION"] = "1"
    env["AI_AGENT_WARM_START"] = "1" if warm_session else "0"
    if skip_device_refresh:
        env["ATP_REFRESH_DEVICES_BEFORE_RUN"] = "0"
    env["ATP_VALIDATE_MAESTRO_YAML"] = "0"

    stage_py = repo / "scripts" / "jenkins_atp_stage.py"
    clear_str = "true" if clear_state else "false"
    argv = [
        sys.executable,
        str(stage_py),
        "all",
        folder,
        app_package,
        clear_str,
        maestro_cmd,
    ]
    print(
        f"[ai-agent.fast] START module={module_name!r} folder={folder!r} "
        f"clear={clear_str} warm={warm_session}",
        flush=True,
    )
    proc = subprocess.run(argv, cwd=str(repo), env=env, check=False)
    duration = time.time() - t0
    passed = proc.returncode == 0
    return ModuleRunResult(
        name=module_name,
        folder=folder,
        suite_id=sid,
        passed=passed,
        exit_code=proc.returncode,
        duration_sec=duration,
        message="PASS" if passed else f"FAIL exit={proc.returncode}",
    )
