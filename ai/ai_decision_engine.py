"""
AI Decision Engine — core state classification and recovery plan generation.

Invoked ONLY when Maestro cannot continue (timeout / element not found / unexpected UI).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ai.config_loader import EngineConfig, load_engine_config
from ai.llm_advisor import suggest_recovery_action
from ai.popup_handler import PopupDecision, PopupHandler
from ai.printer_selector import PrinterRules, PrinterSelector
from ai.screen_analyzer import ScreenAnalyzer, ScreenSnapshot
from ai.ui_parser import UIElement


@dataclass
class RecoveryPlan:
    classification: str
    confidence: float
    reasoning: str
    action_name: str
    tap_label: str | None = None
    tap_pattern: str | None = None
    target_element: UIElement | None = None
    permission_policy: str = "allow_while_using"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RecoveryOutcome:
    recovered: bool
    attempts: int
    classification: str
    last_reasoning: str
    skipped: bool = False
    skip_reason: str = ""


class AIDecisionEngine:
    """
    Rule-first decision engine with optional LLM fallback.
    Extension point: subclass and override generate_plan() for custom modules.
    """

    def __init__(
        self,
        config: EngineConfig | None = None,
        repo_root: Path | None = None,
        device_id: str = "",
        app_package: str = "com.kodak.steptouch",
    ) -> None:
        self.repo_root = repo_root or Path.cwd()
        self.config = config or load_engine_config(self.repo_root)
        self.device_id = device_id
        self.app_package = app_package
        self.popup_handler = PopupHandler(Path(self.config.popup_rules_path))
        self.printer_selector = PrinterSelector(
            PrinterRules.from_file(Path(self.config.printer_rules_path))
        )
        self.analyzer: ScreenAnalyzer | None = None
        if device_id:
            self.analyzer = ScreenAnalyzer(device_id, Path(self.config.screenshot_dir))

    def is_enabled(self) -> bool:
        return bool(self.config.enabled)

    def analyze_failure(
        self,
        *,
        module_name: str,
        failed_step: str,
        maestro_error: str = "",
        snapshot: ScreenSnapshot | None = None,
    ) -> RecoveryPlan:
        if snapshot is None:
            if self.analyzer is None:
                raise RuntimeError("device_id required when snapshot not provided")
            snapshot = self.analyzer.capture(tag="failure")
        classification, confidence, reason = self.analyzer.classify_screen(snapshot)
        if maestro_error:
            reason = f"{reason}; maestro: {maestro_error[:200]}"

        plan = self._plan_from_classification(
            classification,
            confidence,
            reason,
            snapshot,
            module_name,
            failed_step,
        )

        if (
            self.config.llm_enabled
            and plan.confidence < self.config.use_llm_when_rules_below_confidence
        ):
            llm = suggest_recovery_action(
                classification=classification,
                confidence=confidence,
                context=snapshot.context,
                failed_step=failed_step,
                module_name=module_name,
                allowed_actions=self._allowed_actions(classification),
            )
            if llm:
                plan = RecoveryPlan(
                    classification=classification,
                    confidence=float(llm.get("confidence", 0.5)),
                    reasoning=str(llm.get("reasoning", "LLM suggestion")),
                    action_name=str(llm["action"]),
                    metadata={"source": "llm"},
                )
        return plan

    def _allowed_actions(self, classification: str) -> list[str]:
        base = ["wait_and_retry", "dismiss_popup"]
        mapping = {
            "printer_not_found": ["retry_printer_scan", "wait_and_retry"],
            "multiple_printers": ["select_printer"],
            "bluetooth_disabled": ["enable_bluetooth"],
            "permission_dialog": ["grant_permission"],
            "connection_scanning": ["wait_and_retry"],
        }
        return mapping.get(classification, base) + ["dismiss_popup"]

    def _plan_from_classification(
        self,
        classification: str,
        confidence: float,
        reason: str,
        snapshot: ScreenSnapshot,
        module_name: str,
        failed_step: str,
    ) -> RecoveryPlan:
        tree = snapshot.ui_tree
        text_blob = " ".join(snapshot.context.get("all_visible_text", []))

        if classification == "permission_dialog":
            return RecoveryPlan(
                classification=classification,
                confidence=confidence,
                reasoning=reason,
                action_name="grant_permission",
                permission_policy=self.config.permission_policy,
            )

        if classification == "bluetooth_disabled":
            return RecoveryPlan(
                classification=classification,
                confidence=confidence,
                reasoning=reason,
                action_name="enable_bluetooth",
            )

        if classification == "printer_not_found":
            return RecoveryPlan(
                classification=classification,
                confidence=confidence,
                reasoning=reason,
                action_name="retry_printer_scan",
            )

        if classification == "multiple_printers":
            best = self.printer_selector.select_best(tree)
            if best and best.element:
                return RecoveryPlan(
                    classification=classification,
                    confidence=max(confidence, best.score),
                    reasoning=f"{reason}; {self.printer_selector.explain_selection(best)}",
                    action_name="select_printer",
                    tap_label=best.label,
                    target_element=best.element,
                )
            return RecoveryPlan(
                classification=classification,
                confidence=confidence,
                reasoning=reason,
                action_name="retry_printer_scan",
            )

        popup = self.popup_handler.classify(text_blob)
        if popup or classification.endswith("_popup") or classification == "unexpected_popup":
            p = popup or PopupDecision(
                matched_rule=classification,
                action="dismiss",
                confidence=confidence,
                reasoning=reason,
                tap_label="OK",
            )
            return RecoveryPlan(
                classification=classification,
                confidence=p.confidence,
                reasoning=p.reasoning,
                action_name="dismiss_popup" if p.action != "retry" else "retry_printer_scan",
                tap_label=p.tap_label,
                tap_pattern=p.tap_pattern,
            )

        if classification == "connection_scanning":
            return RecoveryPlan(
                classification=classification,
                confidence=confidence,
                reasoning=reason,
                action_name="wait_and_retry",
            )

        custom = self._module_hook(module_name, failed_step, snapshot)
        if custom:
            return custom

        return RecoveryPlan(
            classification=classification,
            confidence=confidence,
            reasoning=reason,
            action_name="dismiss_popup",
            tap_pattern="OK|Cancel|Not now",
        )

    def _module_hook(
        self,
        module_name: str,
        failed_step: str,
        snapshot: ScreenSnapshot,
    ) -> RecoveryPlan | None:
        """Override in subclasses for module-specific recovery."""
        _ = (module_name, failed_step, snapshot)
        return None

    @staticmethod
    def parse_maestro_failure(log_text: str) -> str:
        """Extract human-readable failure from maestro.log snippet."""
        for pat in (
            r"CommandFailed: (.+)",
            r"Assertion is false: (.+)",
            r"Element not found: (.+)",
            r"Timed out (.+)",
        ):
            m = re.search(pat, log_text)
            if m:
                return m.group(1).strip()[:300]
        return "Maestro step failed"
