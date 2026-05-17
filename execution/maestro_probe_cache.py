#!/usr/bin/env python3
"""Disk cache for Maestro capability / isolated-runtime probes (Jenkins agent)."""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any


def _cache_path(repo: Path | None) -> Path | None:
    if repo is not None:
        return (repo / ".atp-cache" / "maestro_capability.json").resolve()
    raw = (os.environ.get("ATP_PROBE_CACHE_DIR") or "").strip().strip('"')
    if raw:
        return Path(raw) / "maestro_capability.json"
    return None


def _ttl_sec() -> float:
    try:
        return float((os.environ.get("ATP_PROBE_CACHE_TTL_SEC") or str(7 * 86400)).strip())
    except ValueError:
        return 7 * 86400.0


def _load(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return None
        ts = float(data.get("ts", 0))
        if time.time() - ts > _ttl_sec():
            return None
        return data
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return None


def _save(path: Path, data: dict[str, Any]) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        data["ts"] = time.time()
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except OSError:
        pass


def load_isolated_probe(
    *,
    repo: Path | None,
    app_home: Path,
    devices: list[str],
) -> tuple[bool, str] | None:
    path = _cache_path(repo)
    if path is None:
        return None
    data = _load(path)
    if not data:
        return None
    lib_mtime = data.get("lib_mtime")
    try:
        current_mtime = max(p.stat().st_mtime for p in (app_home / "lib").glob("*.jar"))
    except OSError:
        current_mtime = None
    if lib_mtime is not None and current_mtime is not None and abs(lib_mtime - current_mtime) > 1.0:
        return None
    cached_devs = sorted(str(d) for d in (data.get("devices") or []))
    if cached_devs != sorted(devices):
        return None
    if str(data.get("app_home", "")).lower() != str(app_home.resolve()).lower():
        return None
    if "isolated_supported" not in data:
        return None
    supported = bool(data["isolated_supported"])
    detail = str(data.get("isolated_detail") or "disk_cache")
    return supported, f"disk_cache:{detail}"


def save_isolated_probe(
    *,
    repo: Path | None,
    app_home: Path,
    devices: list[str],
    supported: bool,
    detail: str,
) -> None:
    path = _cache_path(repo)
    if path is None:
        return
    lib_mtime: float | None = None
    try:
        jars = list((app_home / "lib").glob("*.jar"))
        if jars:
            lib_mtime = max(p.stat().st_mtime for p in jars)
    except OSError:
        pass
    existing = _load(path) or {}
    existing.update(
        {
            "app_home": str(app_home.resolve()),
            "lib_mtime": lib_mtime,
            "devices": devices,
            "isolated_supported": supported,
            "isolated_detail": detail,
        }
    )
    _save(path, existing)
