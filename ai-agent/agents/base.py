"""Shared agent context passed through LangGraph workflow."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class AgentState:
    session_id: str
    mode: str
    device_id: str
    repo_root: Path
    app_package: str
    status: str = "running"
    current_module: str = ""
    current_flow: str = ""
    maestro_error: str = ""
    maestro_output: str = ""
    screenshot: Path | None = None
    ui_dump: Path | None = None
    decision: dict[str, Any] = field(default_factory=dict)
    recovery: dict[str, Any] = field(default_factory=dict)
    failure_analysis: dict[str, Any] = field(default_factory=dict)
    recommendation: dict[str, Any] = field(default_factory=dict)
    rows: list[dict[str, Any]] = field(default_factory=list)
    steps: int = 0
    messages: list[str] = field(default_factory=list)
    knowledge_hits: list[dict[str, Any]] = field(default_factory=list)

    def log(self, msg: str) -> None:
        self.messages.append(msg)
