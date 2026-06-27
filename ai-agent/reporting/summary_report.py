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
    *,
    session_metrics: Any = None,
) -> None:
    summary_txt.parent.mkdir(parents=True, exist_ok=True)
    sm = session_metrics or getattr(outcome, "session_metrics", None)
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
        ]
    )
    if sm:
        lines.extend(
            [
                f"Application Launches  : {getattr(sm, 'launch_count', 0)}",
                f"Application Restarts  : {getattr(sm, 'restart_count', 0)}",
                f"Adaptive Wait Saved   : {getattr(sm, 'adaptive_wait_saved_sec', 0):.1f} sec",
                f"Navigation Optimised  : {getattr(sm, 'navigation_optimisations', 0)}",
                f"Checkpoint Resumes    : {getattr(sm, 'checkpoint_resumes', 0)}",
                f"Artifacts Learned     : {getattr(sm, 'artifacts_learned', 0)}",
            ]
        )
        prev = getattr(sm, "performance_vs_previous_pct", 0)
        if prev:
            lines.append(f"Performance vs Prev   : {prev:+.1f}%")

    lines.extend(
        [
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
    if sm:
        payload["session"] = {
            "launch_count": sm.launch_count,
            "restart_count": sm.restart_count,
            "adaptive_wait_saved_sec": sm.adaptive_wait_saved_sec,
            "navigation_optimisations": sm.navigation_optimisations,
        }
    summary_json.write_text(
        __import__("json").dumps(payload, indent=2),
        encoding="utf-8",
    )
