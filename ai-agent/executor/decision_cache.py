"""In-run decision cache — avoid re-analyzing the same screen state."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any


@dataclass
class CachedDecision:
    chosen_action: str
    confidence: float
    root_cause: str
    suggested_fix: str
    used_llm: bool = False


class DecisionCache:
    def __init__(self) -> None:
        self._cache: dict[str, CachedDecision] = {}
        self.hits = 0
        self.misses = 0

    @staticmethod
    def key(module: str, error: str, ui_signature: str = "") -> str:
        raw = f"{module}|{error[:200]}|{ui_signature[:300]}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]

    def get(self, key: str) -> CachedDecision | None:
        hit = self._cache.get(key)
        if hit:
            self.hits += 1
        else:
            self.misses += 1
        return hit

    def put(self, key: str, decision: CachedDecision) -> None:
        self._cache[key] = decision
