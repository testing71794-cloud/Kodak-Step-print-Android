#!/usr/bin/env python3
"""Print per-suite timing rollup from reports/<suite>/flow_timing.jsonl (post-run)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("suite_id", help="e.g. atp_collage")
    ap.add_argument("--repo", default=str(REPO))
    ap.add_argument("--top", type=int, default=15, help="Show slowest N flows")
    args = ap.parse_args()
    path = Path(args.repo) / "reports" / args.suite_id / "flow_timing.jsonl"
    if not path.is_file():
        print(f"No timing file: {path}", file=sys.stderr)
        return 2
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    if not rows:
        print("No timing records.")
        return 0
    total_ms = sum(int(r.get("duration_ms") or 0) for r in rows)
    passed = [r for r in rows if str(r.get("status", "")).upper() in ("PASS", "FLAKY")]
    failed = [r for r in rows if r not in passed]
    print(f"Suite: {args.suite_id}")
    print(f"Flows recorded: {len(rows)}  total_wall_ms: {total_ms}  (~{total_ms/60000:.1f} min)")
    print(f"PASS/FLAKY: {len(passed)}  FAIL/other: {len(failed)}")
    slow = sorted(rows, key=lambda r: int(r.get("duration_ms") or 0), reverse=True)[: args.top]
    print(f"\nSlowest {len(slow)} flows:")
    for r in slow:
        ms = int(r.get("duration_ms") or 0)
        print(
            f"  {ms/1000:7.1f}s  {r.get('status','?'):6}  {r.get('flow','')}  device={r.get('device','')}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
