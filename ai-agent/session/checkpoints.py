"""Session checkpoints for resume-without-full-restart."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any


class CheckpointLevel(IntEnum):
    APP_LAUNCHED = 1
    PERMISSIONS_GRANTED = 2
    LOGGED_IN = 3
    PRINTER_CONNECTED = 4
    GALLERY_READY = 5
    MODULE_READY = 6


@dataclass
class SessionCheckpoint:
    level: CheckpointLevel
    name: str
    module: str
    screen_hint: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class CheckpointRegistry:
    checkpoints: list[SessionCheckpoint] = field(default_factory=list)

    def save(self, cp: SessionCheckpoint) -> None:
        self.checkpoints = [c for c in self.checkpoints if c.level != cp.level]
        self.checkpoints.append(cp)
        self.checkpoints.sort(key=lambda c: c.level)

    def latest(self) -> SessionCheckpoint | None:
        return self.checkpoints[-1] if self.checkpoints else None

    def nearest_for_module(self, module_name: str) -> SessionCheckpoint | None:
        for cp in reversed(self.checkpoints):
            if cp.module == module_name:
                return cp
        return self.latest()


MODULE_CHECKPOINT_MAP = {
    "Onboarding": CheckpointLevel.PERMISSIONS_GRANTED,
    "SignIn": CheckpointLevel.LOGGED_IN,
    "Connection": CheckpointLevel.PRINTER_CONNECTED,
    "Camera": CheckpointLevel.MODULE_READY,
    "Collage": CheckpointLevel.GALLERY_READY,
    "Gallery": CheckpointLevel.GALLERY_READY,
    "PreCut": CheckpointLevel.GALLERY_READY,
    "Editing": CheckpointLevel.GALLERY_READY,
    "Printing": CheckpointLevel.PRINTER_CONNECTED,
    "Settings": CheckpointLevel.GALLERY_READY,
}
