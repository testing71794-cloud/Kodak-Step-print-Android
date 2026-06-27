"""Classify and handle unexpected popups using rule configuration."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from ai.action_executor import ActionExecutor, ActionResult
from ai.config_loader import _load_file
from ai.ui_parser import UIElement


@dataclass
class PopupRule:
    name: str
    patterns: list[str]
    action: str  # dismiss | continue | retry | fail
    tap_label: str | None = None
    tap_pattern: str | None = None
    confidence: float = 0.8


@dataclass
class PopupDecision:
    matched_rule: str
    action: str
    confidence: float
    reasoning: str
    tap_label: str | None = None
    tap_pattern: str | None = None


class PopupHandler:
    def __init__(self, rules_path: Path) -> None:
        data = _load_file(rules_path)
        block = data.get("popup_handling") or data
        raw_rules = block.get("rules") or []
        self.default_action = str(block.get("default_action", "dismiss"))
        self.rules: list[PopupRule] = []
        for r in raw_rules:
            self.rules.append(
                PopupRule(
                    name=str(r.get("name", "unnamed")),
                    patterns=list(r.get("match_text") or r.get("patterns") or []),
                    action=str(r.get("action", "dismiss")),
                    tap_label=r.get("tap_label"),
                    tap_pattern=r.get("tap_pattern"),
                    confidence=float(r.get("confidence", 0.8)),
                )
            )

    def classify(self, text_blob: str) -> PopupDecision | None:
        lower = text_blob.lower()
        best: PopupDecision | None = None
        for rule in self.rules:
            for pat in rule.patterns:
                if pat.lower() in lower or re.search(pat, text_blob, re.I):
                    dec = PopupDecision(
                        matched_rule=rule.name,
                        action=rule.action,
                        confidence=rule.confidence,
                        reasoning=f"Matched popup rule {rule.name!r} via {pat!r}",
                        tap_label=rule.tap_label,
                        tap_pattern=rule.tap_pattern,
                    )
                    if best is None or dec.confidence > best.confidence:
                        best = dec
        return best

    def execute(
        self,
        decision: PopupDecision,
        executor: ActionExecutor,
        tree: UIElement | None,
    ) -> ActionResult:
        if decision.action == "fail":
            return ActionResult(False, "popup_fail", decision.reasoning)
        if decision.action == "continue":
            return ActionResult(True, "popup_continue", "No tap — continue flow")
        if decision.action == "retry":
            return ActionResult(True, "popup_retry", "Signal caller to retry scan")

        if decision.tap_label:
            return executor.tap_label_exact(tree, decision.tap_label)
        if decision.tap_pattern:
            return executor.tap_text(tree, decision.tap_pattern)
        for label in ("OK", "Got it", "Not now", "Later", "Cancel", "Dismiss"):
            r = executor.tap_label_exact(tree, label)
            if r.success:
                return r
        return executor.press_back()
