"""Adaptive polling — no static long waits; learn timing per screen."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass
class WaitResult:
    success: bool
    elapsed_sec: float
    saved_sec: float
    used_timeout_sec: float


class AdaptiveWait:
    def __init__(
        self,
        timing_store: Any,
        *,
        default_timeout: float = 12.0,
        poll_interval: float = 0.35,
        safety_multiplier: float = 1.4,
    ) -> None:
        self.timing = timing_store
        self.default_timeout = default_timeout
        self.poll_interval = poll_interval
        self.safety_multiplier = safety_multiplier
        self.total_saved_sec = 0.0

    def timeout_for(self, screen_key: str) -> float:
        stats = self.timing.get_stats(screen_key)
        if stats and stats.get("p90_sec"):
            learned = float(stats["p90_sec"]) * self.safety_multiplier
            return min(max(learned, 2.0), self.default_timeout * 2)
        return self.default_timeout

    def until(
        self,
        screen_key: str,
        condition: Callable[[], bool],
        *,
        timeout: float | None = None,
    ) -> WaitResult:
        limit = timeout if timeout is not None else self.timeout_for(screen_key)
        t0 = time.time()
        while time.time() - t0 < limit:
            if condition():
                elapsed = time.time() - t0
                self.timing.record(screen_key, elapsed)
                saved = max(0.0, limit - elapsed)
                self.total_saved_sec += saved
                return WaitResult(True, elapsed, saved, limit)
            time.sleep(self.poll_interval)
        elapsed = time.time() - t0
        return WaitResult(False, elapsed, 0.0, limit)
