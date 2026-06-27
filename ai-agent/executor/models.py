"""Shared dataclasses for hybrid execution."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ModuleSummary:
    name: str
    status: str
    duration_sec: float
    recovered: bool = False


@dataclass
class RunOutcome:
    rows: list[dict[str, Any]] = field(default_factory=list)
    module_summaries: list[ModuleSummary] = field(default_factory=list)
    recovered_count: int = 0
    unrecoverable_count: int = 0
    knowledge_updated: bool = False
    knowledge_load_sec: float = 0.0
    total_sec: float = 0.0
    exit_code: int = 0
    session_metrics: Any = None
