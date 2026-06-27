"""Stateful session — single app journey across all modules."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from session.checkpoints import CheckpointLevel, CheckpointRegistry, SessionCheckpoint


@dataclass
class SessionMetrics:
    launch_count: int = 0
    restart_count: int = 0
    adaptive_wait_saved_sec: float = 0.0
    navigation_optimisations: int = 0
    artifacts_learned: int = 0
    knowledge_updated: bool = False
    checkpoint_resumes: int = 0
    avg_screen_load_sec: float = 0.0
    performance_vs_previous_pct: float = 0.0


@dataclass
class ExecutionSession:
    session_id: str
    device_id: str
    started_at: str
    mode: str
    warm: bool = False
    logged_in: bool = False
    printer_connected: bool = False
    permissions_granted: bool = False
    current_module: str = ""
    current_screen: str = "unknown"
    checkpoints: CheckpointRegistry = field(default_factory=CheckpointRegistry)
    metrics: SessionMetrics = field(default_factory=SessionMetrics)
    decisions: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def create(cls, device_id: str, mode: str) -> ExecutionSession:
        return cls(
            session_id=str(uuid.uuid4())[:10],
            device_id=device_id,
            started_at=datetime.now(timezone.utc).isoformat(),
            mode=mode,
        )

    def mark_launch(self) -> None:
        self.metrics.launch_count += 1
        self.warm = True
        self.checkpoints.save(
            SessionCheckpoint(
                level=CheckpointLevel.APP_LAUNCHED,
                name="app_launched",
                module=self.current_module or "bootstrap",
                screen_hint="app_focus",
            )
        )

    def mark_restart(self, reason: str) -> None:
        self.metrics.restart_count += 1
        self.metrics.launch_count += 1
        self.decisions.append({"action": "relaunch", "reason": reason})

    def mark_module_checkpoint(self, module_name: str, passed: bool) -> None:
        from session.checkpoints import MODULE_CHECKPOINT_MAP

        level = MODULE_CHECKPOINT_MAP.get(module_name, CheckpointLevel.MODULE_READY)
        if not passed:
            return
        self.current_module = module_name
        self.checkpoints.save(
            SessionCheckpoint(
                level=level,
                name=level.name.lower(),
                module=module_name,
                screen_hint=self.current_screen,
            )
        )
        if module_name == "SignIn":
            self.logged_in = True
        if module_name == "Connection":
            self.printer_connected = True
        if module_name in ("Onboarding",):
            self.permissions_granted = True

    def should_clear_state(self) -> bool:
        """Only clear on cold session start (first launch)."""
        return self.metrics.launch_count == 0 and not self.warm
