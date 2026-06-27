"""Recovery attempt loop with bounded retries — never infinite."""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

from ai.action_executor import ActionExecutor, ActionResult
from ai.ai_decision_engine import RecoveryPlan
from ai.config_loader import EngineConfig
from ai.decision_logger import DecisionLogger, DecisionRecord
from ai.screen_analyzer import ScreenAnalyzer, ScreenSnapshot


@dataclass
class RecoveryAttemptResult:
    recovered: bool
    attempts_used: int
    last_action: str = ""
    last_detail: str = ""


class RecoveryManager:
    def __init__(
        self,
        config: EngineConfig,
        device_id: str,
        module_name: str,
        flow_path: str,
        app_package: str = "com.kodak.steptouch",
    ) -> None:
        self.config = config
        self.device_id = device_id
        self.module_name = module_name
        self.flow_path = flow_path
        self.executor = ActionExecutor(device_id, app_package)
        self.analyzer = ScreenAnalyzer(device_id, Path(config.screenshot_dir))
        self.logger = DecisionLogger(Path(config.decision_log_dir))

    def attempt_recovery(
        self,
        plan: RecoveryPlan,
        *,
        failed_step: str,
        attempt: int,
    ) -> RecoveryAttemptResult:
        snapshot = self.analyzer.capture(tag=f"attempt{attempt}")
        action_result = self._execute_plan(plan, snapshot)
        self.executor.wait_ms(self.config.wait_after_action_ms)

        verify = self.analyzer.capture(tag=f"verify{attempt}")
        recovered = self._verify_recovery(plan, verify, action_result)

        record = DecisionRecord(
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            module_name=self.module_name,
            failed_step=failed_step,
            screen_classification=plan.classification,
            confidence_score=plan.confidence,
            reasoning=plan.reasoning,
            action_taken=f"{plan.action_name}: {action_result.detail}",
            result="Recovered" if recovered else "Failed",
            device_id=self.device_id,
            flow_path=self.flow_path,
            attempt=attempt,
            extra={
                "screenshot": str(snapshot.screenshot_path),
                "verify_screenshot": str(verify.screenshot_path),
            },
        )
        self.logger.log(record)

        return RecoveryAttemptResult(
            recovered=recovered,
            attempts_used=attempt,
            last_action=plan.action_name,
            last_detail=action_result.detail,
        )

    def _execute_plan(self, plan: RecoveryPlan, snapshot: ScreenSnapshot) -> ActionResult:
        tree = snapshot.ui_tree
        ex = self.executor
        action = plan.action_name

        if action == "retry_printer_scan":
            for label in ("Search again", "Refresh", "Scan again", "Retry"):
                r = ex.tap_label_exact(tree, label)
                if r.success:
                    ex.wait_ms(self.config.wait_before_retry_scan_ms)
                    return r
            r = ex.swipe_refresh()
            ex.wait_ms(self.config.wait_before_retry_scan_ms)
            return r

        if action == "select_printer":
            if plan.target_element:
                return ex.tap_element(plan.target_element)
            if plan.tap_label:
                return ex.tap_label_exact(tree, plan.tap_label)
            return ActionResult(False, action, "No printer target in plan")

        if action == "enable_bluetooth":
            if not self.config.allow_bluetooth_enable:
                return ActionResult(False, action, "allow_bluetooth_enable=false in config")
            r = ex.enable_bluetooth()
            ex.wait_ms(2000)
            ex.launch_app()
            return r

        if action == "grant_permission":
            policy = plan.tap_label or self._permission_label(plan.permission_policy)
            for label in (policy, "While using the app", "Allow", "Only this time"):
                if not label:
                    continue
                r = ex.tap_label_exact(tree, label)
                if r.success:
                    return r
            return ActionResult(False, action, f"Permission label not found: {policy!r}")

        if action == "dismiss_popup":
            if plan.tap_label:
                return ex.tap_label_exact(tree, plan.tap_label)
            if plan.tap_pattern:
                return ex.tap_text(tree, plan.tap_pattern)
            return ex.press_back()

        if action == "wait_and_retry":
            ex.wait_ms(self.config.wait_before_retry_scan_ms)
            return ActionResult(True, action, "Waited for dynamic UI")

        if action == "restart_app":
            if not self.config.allow_app_restart:
                return ActionResult(False, action, "allow_app_restart=false in config")
            return ex.launch_app()

        return ActionResult(False, action, "Unknown action")

    def _verify_recovery(
        self,
        plan: RecoveryPlan,
        verify: ScreenSnapshot,
        action_result: ActionResult,
    ) -> bool:
        if not action_result.success:
            return False
        new_class, conf, _ = self.analyzer.classify_screen(verify)
        # Recovery succeeded if we left the blocking state
        blocking = {
            "permission_dialog",
            "bluetooth_disabled",
            "firmware_update_popup",
            "printer_busy_popup",
            "paper_low_popup",
            "battery_low_popup",
            "unexpected_popup",
        }
        if plan.classification in blocking and new_class not in blocking:
            return True
        if plan.classification == "printer_not_found" and new_class in {
            "multiple_printers",
            "connection_scanning",
            "unknown_state",
        }:
            return conf >= 0.5
        if plan.classification == "multiple_printers" and plan.action_name == "select_printer":
            return action_result.success
        if plan.action_name in {"wait_and_retry", "retry_printer_scan"}:
            return action_result.success
        return new_class != plan.classification

    @staticmethod
    def _permission_label(policy: str) -> str:
        mapping = {
            "allow": "Allow",
            "allow_while_using": "While using the app",
            "allow_only_this_time": "Only this time",
            "deny": "Don't allow",
        }
        return mapping.get(policy, "While using the app")
