"""Text execution summary for AI Step Print Agent."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from executor.decision_cache import DecisionCache
from executor.models import RunOutcome


def write_execution_summary(
    summary_json: Path,
    summary_txt: Path,
    excel_path: Path,
    outcome: RunOutcome,
    health: float,
    mode: str,
    cache: DecisionCache,
) -> None:
    summary_txt.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "Execution Summary",
        "=================",
        "",
    ]
    for mod in outcome.module_summaries:
        dots = "." * max(1, 18 - len(mod.name))
        lines.append(f"{mod.name} {dots} {mod.status}")

    lines.extend(
        [
            "",
            f"Recovered Failures      : {outcome.recovered_count}",
            f"Unrecoverable Failures  : {outcome.unrecoverable_count}",
            f"Overall Health          : {health:.0f}%",
            f"Total Execution Time    : {outcome.total_sec / 60:.1f} minutes",
            f"Knowledge Load Time     : {outcome.knowledge_load_sec:.1f} seconds",
            f"Decision Cache Hits     : {cache.hits}",
            f"Excel Report            : {excel_path.name}",
            f"Knowledge Base Updated  : {'Yes' if outcome.knowledge_updated else 'No'}",
            f"Mode                    : {mode}",
            f"Generated               : {datetime.now(timezone.utc).isoformat()}",
        ]
    )
    summary_txt.write_text("\n".join(lines) + "\n", encoding="utf-8")

    payload: dict[str, Any] = {
        "execution_summary_text": str(summary_txt),
        "health_percent": health,
        "recovered_failures": outcome.recovered_count,
        "unrecoverable_failures": outcome.unrecoverable_count,
        "total_execution_sec": outcome.total_sec,
        "knowledge_updated": outcome.knowledge_updated,
        "modules": [{"name": m.name, "status": m.status} for m in outcome.module_summaries],
    }
    summary_json.write_text(
        __import__("json").dumps(payload, indent=2),
        encoding="utf-8",
    )
