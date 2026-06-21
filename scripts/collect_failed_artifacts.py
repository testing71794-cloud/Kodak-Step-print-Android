#!/usr/bin/env python3
"""
Collect logs and screen recordings for failed Maestro flows only.

Reads status/*.txt (newest row per suite+flow+device), copies matching logs/videos into
build-summary/failed-artifacts/, writes failed_tests_summary.json, and optionally
build-summary/failed_tests_artifacts.zip.

Exit 0 always (Jenkins catchError-friendly); prints a one-line summary to stdout.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import zipfile
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
if str(REPO / "scripts") not in sys.path:
    sys.path.insert(0, str(REPO / "scripts"))

from generate_excel_report import parse_status_file  # noqa: E402

FAILED_STATUSES = frozenset({"FAIL", "FLAKY", "PARSE_ERROR", "ERROR"})
SKIP_STATUSES = frozenset({"PASS", "RUNNING", "UNKNOWN"})


@dataclass
class FailedTestRow:
    test_name: str
    suite: str
    device_id: str
    status: str
    failure_reason: str
    log_source: str
    video_source: str
    log_artifact: str
    video_artifact: str


def _safe_stem(text: str) -> str:
    s = re.sub(r"[^\w\-]+", "_", (text or "").strip())
    return s.strip("_") or "test"


def _resolve_log_path(repo: Path, row: dict) -> Path | None:
    for key in ("log_file", "log_path", "first_log_path", "log"):
        raw = (row.get(key) or "").strip()
        if not raw:
            continue
        p = Path(raw)
        if not p.is_absolute():
            p = (repo / p).resolve()
        if p.is_file():
            return p
    suite = (row.get("suite") or "").strip()
    flow = (row.get("flow") or "").strip()
    dev = (row.get("device_id") or row.get("device") or "").strip()
    if suite and flow and dev:
        safe_flow = flow.replace(" ", "_")
        safe_dev = dev.replace(" ", "_")
        candidate = repo / "reports" / suite / "logs" / f"{safe_flow}_{safe_dev}.log"
        if candidate.is_file():
            return candidate
    return None


VIDEO_EXTENSIONS = (".mp4", ".webm", ".mkv", ".mov")


def _resolve_path_or_dir_under_repo(repo: Path, raw: str) -> Path | None:
    """Resolve a file or directory from status (may be an absolute Windows path) under repo."""
    if not raw:
        return None
    p = Path(raw.strip())
    if p.exists():
        return p.resolve()
    if not p.is_absolute():
        candidate = (repo / p).resolve()
        if candidate.exists():
            return candidate
    parts = p.parts
    for anchor in ("reports", "status", "build-summary", "collected-artifacts"):
        if anchor in parts:
            idx = parts.index(anchor)
            candidate = repo.joinpath(*parts[idx:]).resolve()
            if candidate.exists():
                return candidate
    return None


def _resolve_path_under_repo(repo: Path, raw: str) -> Path | None:
    """Resolve a file path from status (may be absolute Windows) to a file under repo."""
    hit = _resolve_path_or_dir_under_repo(repo, raw)
    return hit if hit is not None and hit.is_file() else None


def _newest_video_in_dir(directory: Path) -> Path | None:
    if not directory.is_dir():
        return None
    found: list[Path] = []
    for ext in VIDEO_EXTENSIONS:
        found.extend(directory.rglob(f"*{ext}"))
    if not found:
        return None
    return max(found, key=lambda p: p.stat().st_mtime)


def _resolve_video_path(repo: Path, row: dict) -> Path | None:
    for key in ("video_file", "video_path", "recording_file"):
        raw = (row.get(key) or "").strip()
        if raw:
            resolved = _resolve_path_under_repo(repo, raw)
            if resolved is not None:
                return resolved

    suite = (row.get("suite") or "").strip()
    flow = (row.get("flow") or "").strip()
    dev = (row.get("device_id") or row.get("device") or "").strip()

    test_out_raw = (row.get("test_output_dir") or "").strip()
    if test_out_raw:
        test_out = _resolve_path_or_dir_under_repo(repo, test_out_raw)
        if test_out is not None:
            if test_out.is_file():
                return test_out
            preferred = test_out / "recording.mp4"
            if preferred.is_file():
                return preferred
            hit = _newest_video_in_dir(test_out)
            if hit is not None:
                return hit

    if not flow:
        return None

    safe_flow = flow.replace(" ", "_")
    safe_dev = dev.replace(" ", "_")
    if suite:
        recordings_roots = [repo / "reports" / suite / "recordings"]
    else:
        recordings_roots = [
            p for p in (repo / "reports").glob("*/recordings") if p.is_dir()
        ]
    for recordings_root in recordings_roots:
        if not recordings_root.is_dir():
            continue

        slug = f"{flow}__{safe_dev}"
        candidates = [
            recordings_root / slug,
            recordings_root / f"{safe_flow}__{safe_dev}",
            recordings_root / safe_flow,
        ]
        for base in candidates:
            if base.is_dir():
                for name in ("recording.mp4", "recording.webm", f"{safe_flow}.mp4"):
                    p = base / name
                    if p.is_file():
                        return p
                hit = _newest_video_in_dir(base)
                if hit is not None:
                    return hit
            elif base.with_suffix(".mp4").is_file():
                return base.with_suffix(".mp4")

        flow_key = flow.casefold()
        all_videos: list[Path] = []
        for ext in VIDEO_EXTENSIONS:
            all_videos.extend(recordings_root.rglob(f"*{ext}"))
        matched = [p for p in all_videos if flow_key in p.as_posix().casefold()]
        if matched:
            return max(matched, key=lambda p: p.stat().st_mtime)
    return None


def load_failed_rows(repo: Path) -> list[dict]:
    status_dir = repo / "status"
    if not status_dir.is_dir():
        return []

    by_key: dict[tuple[str, str, str], tuple[float, dict]] = {}
    for file_path in status_dir.glob("*.txt"):
        row = parse_status_file(file_path)
        st = (row.get("status") or "").upper()
        if st in SKIP_STATUSES or st == "PASS":
            continue
        if st not in FAILED_STATUSES and st:
            continue
        flow = (row.get("flow") or "").strip()
        if not flow:
            continue
        suite = (row.get("suite") or "").strip().lower()
        dev = (row.get("device_id") or row.get("device") or "").strip()
        key = (suite, flow, dev)
        mtime = file_path.stat().st_mtime
        prev = by_key.get(key)
        if prev is None or mtime >= prev[0]:
            by_key[key] = (mtime, row)

    out: list[dict] = []
    for _, row in sorted(by_key.values(), key=lambda x: (x[1].get("suite", ""), x[1].get("flow", ""))):
        st = (row.get("status") or "FAIL").upper()
        if st == "PASS":
            continue
        out.append(row)
    return out


def _artifact_stem(flow: str, device_id: str, *, multi_device: bool) -> str:
    stem = _safe_stem(flow)
    if multi_device and device_id:
        stem = f"{stem}_{_safe_stem(device_id)}"
    return stem


def collect_failed_artifacts(repo: Path) -> dict:
    repo = repo.resolve()
    failed_rows = load_failed_rows(repo)
    out_dir = repo / "build-summary" / "failed-artifacts"
    summary_path = repo / "build-summary" / "failed_tests_summary.json"
    zip_path = repo / "build-summary" / "failed_tests_artifacts.zip"

    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    device_sets: dict[str, set[str]] = {}
    for row in failed_rows:
        flow = (row.get("flow") or "").strip()
        dev = (row.get("device_id") or row.get("device") or "").strip()
        device_sets.setdefault(flow, set()).add(dev)

    collected: list[FailedTestRow] = []
    for row in failed_rows:
        flow = (row.get("flow") or "").strip()
        suite = (row.get("suite") or "").strip()
        dev = (row.get("device_id") or row.get("device") or "").strip()
        st = (row.get("status") or "FAIL").upper()
        reason = (row.get("reason") or row.get("log") or "—").strip() or "—"
        multi = len(device_sets.get(flow, set())) > 1
        stem = _artifact_stem(flow, dev, multi_device=multi)

        log_src = _resolve_log_path(repo, row)
        vid_src = _resolve_video_path(repo, row)

        log_art = ""
        vid_art = ""
        if log_src is not None:
            dest = out_dir / f"{stem}.log"
            shutil.copy2(log_src, dest)
            log_art = dest.name
        if vid_src is not None:
            dest = out_dir / f"{stem}{vid_src.suffix.lower() or '.mp4'}"
            shutil.copy2(vid_src, dest)
            vid_art = dest.name

        collected.append(
            FailedTestRow(
                test_name=flow,
                suite=suite,
                device_id=dev,
                status=st,
                failure_reason=reason,
                log_source=str(log_src) if log_src else "",
                video_source=str(vid_src) if vid_src else "",
                log_artifact=log_art,
                video_artifact=vid_art,
            )
        )

    summary = {
        "failed_count": len(collected),
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "failures": [asdict(r) for r in collected],
    }
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    if zip_path.is_file():
        zip_path.unlink()

    if collected:
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for p in sorted(out_dir.iterdir()):
                if p.is_file():
                    zf.write(p, arcname=p.name)
        print(
            f"[collect_failed_artifacts] failed={len(collected)} "
            f"videos={sum(1 for r in collected if r.video_artifact)} "
            f"dir={out_dir} zip={zip_path}",
            flush=True,
        )
    else:
        print("[collect_failed_artifacts] no failed tests — skipped zip", flush=True)

    return {
        "failed_count": len(collected),
        "summary_path": str(summary_path),
        "artifacts_dir": str(out_dir),
        "zip_path": str(zip_path) if collected else "",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect failed Maestro logs and videos.")
    parser.add_argument(
        "workspace",
        nargs="?",
        default=str(Path(os.environ.get("WORKSPACE", REPO))),
        help="Repo root (default: WORKSPACE or script parent)",
    )
    args = parser.parse_args()
    collect_failed_artifacts(Path(args.workspace))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
