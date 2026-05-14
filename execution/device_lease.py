#!/usr/bin/env python3
"""
Per-device coarse lease for Maestro runs (filesystem-based, stdlib only).

Avoids overlapping Maestro sessions on the same ADB serial from concurrent
Jenkins jobs or stray processes. Stale locks expire by wall-clock age.
"""
from __future__ import annotations

import json
import os
import shutil
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass
class DeviceLease:
    serial: str
    lock_dir: Path

    @staticmethod
    def lock_root(repo: Path) -> Path:
        return (repo / ".maestro-locks").resolve()

    @classmethod
    def for_serial(cls, repo: Path, serial: str) -> DeviceLease:
        safe = "".join(c if c.isalnum() or c in "._-" else "_" for c in serial.strip())
        return cls(serial=serial.strip(), lock_dir=cls.lock_root(repo) / safe)

    def _meta(self) -> Path:
        return self.lock_dir / "lease.json"

    def _stale_age_sec(self) -> float:
        raw = os.environ.get("ATP_DEVICE_LEASE_STALE_SEC", "7200").strip()
        try:
            return max(60.0, float(raw))
        except ValueError:
            return 7200.0

    def is_stale(self) -> bool:
        if not self.lock_dir.is_dir():
            return False
        meta = self._meta()
        if not meta.is_file():
            return True
        try:
            age = time.time() - meta.stat().st_mtime
            return age > self._stale_age_sec()
        except OSError:
            return True

    def force_release(self) -> None:
        if self.lock_dir.is_dir():
            shutil.rmtree(self.lock_dir, ignore_errors=True)

    def acquire(self, *, owner_pid: int | None = None) -> None:
        owner_pid = owner_pid or os.getpid()
        deadline = time.monotonic() + float(os.environ.get("ATP_DEVICE_LEASE_WAIT_SEC", "300"))
        while True:
            try:
                self.lock_dir.mkdir(parents=True, exist_ok=False)
                self._meta().write_text(
                    json.dumps({"pid": owner_pid, "ts": time.time(), "serial": self.serial}, indent=0),
                    encoding="utf-8",
                )
                return
            except FileExistsError:
                if self.is_stale():
                    self.force_release()
                    continue
                if time.monotonic() > deadline:
                    raise TimeoutError(f"Device lease busy: {self.serial} ({self.lock_dir})")
                time.sleep(1.0)

    def release(self) -> None:
        self.force_release()
