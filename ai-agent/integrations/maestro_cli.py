"""Maestro CLI wrapper — subprocess only, no flow modification."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path


class MaestroCLI:
    def __init__(self, maestro_cmd: str, repo_root: Path) -> None:
        self.maestro_cmd = maestro_cmd
        self.repo_root = repo_root

    def run_flow(self, flow_path: Path, device_id: str, *, debug_output: Path | None = None) -> tuple[int, str]:
        flow = flow_path.resolve()
        if not flow.is_file():
            return 1, f"Flow not found: {flow}"
        cmd = [self.maestro_cmd, "test", str(flow), "--device", device_id]
        if debug_output:
            debug_output.mkdir(parents=True, exist_ok=True)
            cmd.extend(["--debug-output", str(debug_output)])
        env = os.environ.copy()
        mh = env.get("MAESTRO_HOME")
        if mh:
            env["PATH"] = f"{mh};{env.get('PATH', '')}"
        proc = subprocess.run(
            cmd,
            cwd=str(self.repo_root),
            capture_output=True,
            text=True,
            env=env,
            timeout=3600,
            check=False,
            shell=(os.name == "nt" and self.maestro_cmd.endswith(".bat")),
        )
        output = (proc.stdout or "") + (proc.stderr or "")
        return proc.returncode, output

    def observe_running(self, device_id: str) -> str:
        """Lightweight status — Maestro has no observe API; return device focus hint."""
        return f"device={device_id} maestro_cmd={self.maestro_cmd}"
