"""Learn from historical Jenkins/Maestro artifacts incrementally."""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from memory.sqlite_store import MemoryRecord, SQLiteMemoryStore


class ArtifactLearner:
    """Scan logs, status, reports, screenshots — only new/changed files."""

    SCAN_DIRS = (
        "status",
        "reports",
        "build-summary",
        "ai-agent/logs",
    )
    GLOBS = ("*.txt", "*.json", "*.jsonl", "*.log", "*.csv", "*.xlsx")

    def __init__(self, repo: Path, memory: SQLiteMemoryStore) -> None:
        self.repo = repo
        self.memory = memory

    def ingest(self) -> tuple[int, bool]:
        manifest = self.memory.get("artifact_scan", "manifest") or {}
        known: dict[str, str] = manifest.get("files", {})
        updated: dict[str, str] = dict(known)
        new_count = 0

        for rel in self.SCAN_DIRS:
            base = self.repo / rel
            if not base.is_dir():
                continue
            for pattern in self.GLOBS:
                for path in base.rglob(pattern):
                    if not path.is_file():
                        continue
                    try:
                        stat = path.stat()
                    except OSError:
                        continue
                    sig = f"{stat.st_size}:{int(stat.st_mtime)}"
                    key = str(path.relative_to(self.repo))
                    if known.get(key) == sig:
                        continue
                    updated[key] = sig
                    insight = self._extract_insight(path)
                    if insight:
                        self.memory.upsert(
                            MemoryRecord(
                                "artifact",
                                key,
                                insight,
                                confidence=0.7,
                            )
                        )
                        new_count += 1

        changed = updated != known
        if changed:
            self.memory.upsert(
                MemoryRecord(
                    "artifact_scan",
                    "manifest",
                    {
                        "files": updated,
                        "scanned_at": datetime.now(timezone.utc).isoformat(),
                        "file_count": len(updated),
                    },
                )
            )
        return new_count, changed

    def _extract_insight(self, path: Path) -> dict[str, Any] | None:
        suffix = path.suffix.lower()
        if suffix == ".txt" and "status" in path.parts:
            return self._parse_status(path)
        if suffix in {".log", ".jsonl"}:
            return self._parse_log_tail(path)
        if suffix == ".csv":
            return {"type": "csv", "path": str(path), "note": "historical results"}
        return {"type": suffix.lstrip("."), "path": str(path)}

    @staticmethod
    def _parse_status(path: Path) -> dict[str, Any]:
        fields: dict[str, str] = {}
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines()[:30]:
            if "=" in line:
                k, _, v = line.partition("=")
                fields[k.strip().lower()] = v.strip()
        return {
            "type": "status",
            "status": fields.get("status", ""),
            "reason": fields.get("reason", ""),
            "flow": fields.get("flow", path.stem),
            "duration_ms": fields.get("duration_ms", ""),
        }

    @staticmethod
    def _parse_log_tail(path: Path) -> dict[str, Any] | None:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")[-4000:]
        except OSError:
            return None
        failures = [
            ln.strip()
            for ln in text.splitlines()
            if any(x in ln.lower() for x in ("fail", "error", "timeout", "not found"))
        ]
        if not failures:
            return None
        return {
            "type": "log",
            "path": str(path),
            "failure_lines": failures[-5:],
            "hash": hashlib.sha256(text.encode()).hexdigest()[:16],
        }
