"""Select printer from multiple candidates using configurable priority rules."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from ai.config_loader import _load_file
from ai.ui_parser import UIElement


@dataclass
class PrinterCandidate:
    label: str
    score: float
    reason: str
    element: UIElement | None = None


@dataclass
class PrinterRules:
    preferred_names: list[str]
    preferred_serials: list[str]
    priority_list: list[str]
    name_patterns: list[str]
    exclude_patterns: list[str]

    @classmethod
    def from_file(cls, path: Path) -> "PrinterRules":
        data = _load_file(path)
        sel = data.get("printer_selection") or data
        return cls(
            preferred_names=list(sel.get("preferred_names") or []),
            preferred_serials=list(sel.get("preferred_serials") or []),
            priority_list=list(sel.get("priority_list") or []),
            name_patterns=list(sel.get("name_patterns") or [r"(?i)kodak.*step"]),
            exclude_patterns=list(sel.get("exclude_patterns") or []),
        )


class PrinterSelector:
    def __init__(self, rules: PrinterRules) -> None:
        self.rules = rules

    def _score_label(self, label: str) -> tuple[float, str]:
        s = label.strip()
        lower = s.lower()
        for ex in self.rules.exclude_patterns:
            if re.search(ex, s):
                return 0.0, f"Excluded by pattern {ex!r}"

        for serial in self.rules.preferred_serials:
            if serial.lower() in lower:
                return 1.0, f"Exact serial match {serial!r}"

        for i, pref in enumerate(self.rules.priority_list):
            if pref.lower() in lower or lower in pref.lower():
                return 0.95 - i * 0.01, f"Priority list rank {i}: {pref!r}"

        for name in self.rules.preferred_names:
            if name.lower() in lower or lower in name.lower():
                return 0.9, f"Preferred name {name!r}"

        for pat in self.rules.name_patterns:
            if re.search(pat, s):
                return 0.7, f"Matched pattern {pat!r}"

        if "kodak" in lower or "step" in lower:
            return 0.5, "Generic Kodak/Step heuristic"

        return 0.2, "Low-confidence printer-like label"

    def candidates_from_tree(self, tree: UIElement | None) -> list[PrinterCandidate]:
        if tree is None:
            return []
        seen: set[str] = set()
        out: list[PrinterCandidate] = []
        for node in tree.flatten():
            if not node.clickable:
                continue
            label = node.label
            if not label or label in seen:
                continue
            score, reason = self._score_label(label)
            if score < 0.25:
                continue
            seen.add(label)
            out.append(PrinterCandidate(label=label, score=score, reason=reason, element=node))
        out.sort(key=lambda c: c.score, reverse=True)
        return out

    def select_best(self, tree: UIElement | None) -> PrinterCandidate | None:
        cands = self.candidates_from_tree(tree)
        return cands[0] if cands else None

    def explain_selection(self, candidate: PrinterCandidate | None) -> str:
        if candidate is None:
            return "No selectable printer candidate found"
        return json.dumps(
            {"label": candidate.label, "score": candidate.score, "reason": candidate.reason},
            ensure_ascii=False,
        )
