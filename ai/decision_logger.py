"""Structured decision logging for AI recovery attempts."""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass
class DecisionRecord:
    timestamp: str
    module_name: str
    failed_step: str
    screen_classification: str
    confidence_score: float
    reasoning: str
    action_taken: str
    result: str  # Recovered | Failed | Skipped
    device_id: str = ""
    flow_path: str = ""
    attempt: int = 0
    extra: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        if d.get("extra") is None:
            d.pop("extra", None)
        return d


class DecisionLogger:
    def __init__(self, log_dir: Path) -> None:
        self.log_dir = log_dir
        self.log_dir.mkdir(parents=True, exist_ok=True)
        day = time.strftime("%Y%m%d")
        self._jsonl = self.log_dir / f"ai_decisions_{day}.jsonl"
        self._summary = self.log_dir / f"ai_decisions_{day}_summary.json"

    def log(self, record: DecisionRecord) -> None:
        line = json.dumps(record.to_dict(), ensure_ascii=False) + "\n"
        with self._jsonl.open("a", encoding="utf-8") as f:
            f.write(line)
        self._update_summary(record)

    def _update_summary(self, record: DecisionRecord) -> None:
        summary: dict[str, Any] = {"total": 0, "recovered": 0, "failed": 0, "skipped": 0}
        if self._summary.is_file():
            try:
                summary = json.loads(self._summary.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                pass
        summary["total"] = int(summary.get("total", 0)) + 1
        key = record.result.lower()
        if key in summary:
            summary[key] = int(summary.get(key, 0)) + 1
        self._summary.write_text(json.dumps(summary, indent=2), encoding="utf-8")
