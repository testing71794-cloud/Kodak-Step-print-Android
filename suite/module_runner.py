"""Run one ATP module via existing jenkins_atp_stage — never aborts the suite."""

from __future__ import annotations

import os
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

from execution.atp_folder_paths import discover_atp_yaml_files, resolve_atp_subfolder

from suite.config_loader import ModuleSpec


@dataclass
class ModuleResult:
    name: str
    folder: str
    suite_id: str
    status: str  # PASS | FAIL | SKIP
    exit_code: int
    duration_sec: float
    message: str = ""
    log_hint: str = ""
    retry_attempt: int = 0
    artifacts: list[str] = field(default_factory=list)


def folder_to_suite_id(folder: str) -> str:
    import re

    t = re.sub(r"[^a-zA-Z0-9]+", "_", folder.strip())
    t = t.strip("_").lower()
    return f"atp_{t or 'unknown'}"


def _module_folder_exists(repo: Path, folder: str) -> bool:
    resolved = resolve_atp_subfolder(repo, folder)
    path = repo / "ATP TestCase Flows" / resolved
    return path.is_dir()


def run_module(
    repo: Path,
    spec: ModuleSpec,
    *,
    app_package: str,
    maestro_cmd: str,
    clear_state: bool,
    skip_yaml_preflight: bool,
    refresh_devices: bool,
    retry_attempt: int = 0,
) -> ModuleResult:
    t0 = time.time()
    resolved = resolve_atp_subfolder(repo, spec.folder)
    sid = folder_to_suite_id(resolved or spec.folder)

    if not _module_folder_exists(repo, spec.folder):
        if spec.skip_if_folder_missing:
            return ModuleResult(
                name=spec.name,
                folder=spec.folder,
                suite_id=sid,
                status="SKIP",
                exit_code=0,
                duration_sec=time.time() - t0,
                message="Module folder not present — skipped",
            )
        return ModuleResult(
            name=spec.name,
            folder=spec.folder,
            suite_id=sid,
            status="FAIL",
            exit_code=1,
            duration_sec=time.time() - t0,
            message=f"ATP folder missing: {spec.folder}",
        )

    flows = discover_atp_yaml_files(repo, resolved or spec.folder, exclude_subflows=True)
    if not flows:
        return ModuleResult(
            name=spec.name,
            folder=spec.folder,
            suite_id=sid,
            status="SKIP",
            exit_code=0,
            duration_sec=time.time() - t0,
            message="No top-level YAML flows in module",
        )

    env = os.environ.copy()
    if skip_yaml_preflight:
        env["ATP_VALIDATE_MAESTRO_YAML"] = "0"
    if not refresh_devices:
        env["ATP_REFRESH_DEVICES_BEFORE_RUN"] = "0"
    env["ATP_SUITE_MODULE"] = spec.name

    clear_str = "true" if clear_state else "false"
    stage_py = repo / "scripts" / "jenkins_atp_stage.py"
    argv = [
        sys.executable,
        str(stage_py),
        "all",
        spec.folder,
        app_package,
        clear_str,
        maestro_cmd,
    ]
    print(
        f"[suite.module_runner] START module={spec.name!r} folder={spec.folder!r} "
        f"clear_state={clear_str} retry={retry_attempt}",
        flush=True,
    )
    proc = subprocess.run(argv, cwd=str(repo), env=env, check=False)
    duration = time.time() - t0
    log_dir = repo / "reports" / sid / "logs"
    log_hint = str(log_dir) if log_dir.is_dir() else ""

    if proc.returncode == 0:
        return ModuleResult(
            name=spec.name,
            folder=spec.folder,
            suite_id=sid,
            status="PASS",
            exit_code=0,
            duration_sec=duration,
            message="Module completed",
            log_hint=log_hint,
            retry_attempt=retry_attempt,
        )

    return ModuleResult(
        name=spec.name,
        folder=spec.folder,
        suite_id=sid,
        status="FAIL",
        exit_code=proc.returncode,
        duration_sec=duration,
        message=f"Module failed exit={proc.returncode}",
        log_hint=log_hint,
        retry_attempt=retry_attempt,
    )
