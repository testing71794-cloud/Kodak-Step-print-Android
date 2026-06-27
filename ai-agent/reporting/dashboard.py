"""HTML dashboard for AI Step Print Agent."""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def render_dashboard(html_path: Path, rows: list[dict[str, Any]], summary_json: Path) -> None:
    html_path.parent.mkdir(parents=True, exist_ok=True)
    statuses = Counter(str(r.get("Status", "")) for r in rows)
    recoveries = Counter(str(r.get("Recovery Result", "")) for r in rows)
    root_causes = Counter(str(r.get("Root Cause", ""))[:80] for r in rows if r.get("Root Cause"))
    avg_conf = (
        sum(float(r.get("Confidence", 0) or 0) for r in rows) / len(rows) if rows else 0.0
    )
    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_runs": len(rows),
        "status_breakdown": dict(statuses),
        "recovery_breakdown": dict(recoveries),
        "avg_confidence": round(avg_conf, 3),
        "top_root_causes": root_causes.most_common(10),
        "knowledge_growth": len(rows),
    }
    summary_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>AI Step Print Agent Dashboard</title>
<style>
body {{ font-family: Segoe UI, sans-serif; margin: 24px; background: #0f1419; color: #e7ecf1; }}
h1 {{ color: #ffd200; }}
.card {{ background: #1a2332; border-radius: 8px; padding: 16px; margin: 12px 0; }}
.grid {{ display: grid; grid-template-columns: repeat(auto-fit,minmax(220px,1fr)); gap: 12px; }}
.metric {{ font-size: 28px; font-weight: 700; }}
table {{ width: 100%; border-collapse: collapse; }}
th, td {{ border-bottom: 1px solid #2d3a4d; padding: 8px; text-align: left; }}
th {{ color: #ffd200; }}
</style></head><body>
<h1>AI Step Print Agent Dashboard</h1>
<p>Generated: {summary['generated_at']}</p>
<div class="grid">
  <div class="card"><div>Total Runs</div><div class="metric">{summary['total_runs']}</div></div>
  <div class="card"><div>Avg Confidence</div><div class="metric">{summary['avg_confidence']:.0%}</div></div>
  <div class="card"><div>Passed</div><div class="metric">{statuses.get('passed', 0)}</div></div>
  <div class="card"><div>Recovered</div><div class="metric">{recoveries.get('PASS', 0)}</div></div>
</div>
<div class="card"><h2>Recent Runs</h2>
<table><tr><th>Module</th><th>Case</th><th>Status</th><th>Root Cause</th><th>Fix</th><th>Conf</th></tr>
"""
    for r in rows[-20:]:
        html += (
            f"<tr><td>{r.get('Module','')}</td><td>{r.get('Test Case','')}</td>"
            f"<td>{r.get('Status','')}</td><td>{str(r.get('Root Cause',''))[:60]}</td>"
            f"<td>{str(r.get('Suggested Fix',''))[:60]}</td>"
            f"<td>{r.get('Confidence','')}</td></tr>"
        )
    html += "</table></div></body></html>"
    html_path.write_text(html, encoding="utf-8")
