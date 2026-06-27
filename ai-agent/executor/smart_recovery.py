"""Smart path — rules first; LLM/OCR/vision only for unknown states."""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from decision_engine.decision_engine import DecisionEngine
from executor.decision_cache import CachedDecision, DecisionCache
from executor.module_executor import ModuleRunResult
from integrations.adb_client import ADBClient
from integrations.llm_client import LLMClient
from recovery.recovery_engine import RecoveryEngine
from utils.config_loader import AgentConfig
from vision.screen_capture import VisionEngine


@dataclass
class SmartRecoveryOutcome:
    attempted: bool
    success: bool
    attempts: int
    ai_decision: str
    root_cause: str
    suggested_fix: str
    confidence: float
    severity: str
    priority: str
    screenshot: str
    used_llm: bool
    used_vision: bool

    def as_report_dict(self) -> dict[str, Any]:
        return {
            "attempted": self.attempted,
            "success": self.success,
            "attempts": self.attempts,
            "ai_decision": self.ai_decision,
            "root_cause": self.root_cause,
            "suggested_fix": self.suggested_fix,
            "confidence": self.confidence,
            "severity": self.severity,
            "priority": self.priority,
            "screenshot": self.screenshot,
            "result": "PASS" if self.success else ("FAIL" if self.attempted else "N/A"),
            "retry_count": 1 if self.attempted else 0,
        }


class SmartRecovery:
    """Hybrid recovery: fast rules → optional vision/OCR → LLM only if still unknown."""

    RULE_CONFIDENCE_THRESHOLD = 0.72
    LLM_CONFIDENCE_THRESHOLD = 0.55

    def __init__(self, cfg: AgentConfig, device_id: str, cache: DecisionCache) -> None:
        self.cfg = cfg
        self.device_id = device_id
        self.cache = cache
        self.adb = ADBClient(device_id, cfg.app_package)
        self.vision = VisionEngine(self.adb, cfg.screenshot_dir, cfg.ui_dump_dir)
        self.llm = LLMClient(
            model=cfg.llm_model,
            base_url=cfg.llm_base_url,
            api_key_env=cfg.llm_api_key_env,
        )
        self.engine = DecisionEngine(
            self.llm,
            cfg.app_profile,
            min_confidence_for_llm=cfg.min_confidence_for_llm,
        )
        self.recovery = RecoveryEngine(self.adb, cfg.max_recovery_attempts)

    def try_recover(self, module_result: ModuleRunResult, mode: str) -> SmartRecoveryOutcome:
        if mode == "observe" or module_result.passed:
            return SmartRecoveryOutcome(
                attempted=False,
                success=False,
                attempts=0,
                ai_decision="No AI Intervention",
                root_cause="",
                suggested_fix="",
                confidence=0.0,
                severity="",
                priority="",
                screenshot="",
                used_llm=False,
                used_vision=False,
            )

        error = module_result.message or "Module failed"
        cache_key = self.cache.key(module_result.name, error)
        cached = self.cache.get(cache_key)
        if cached:
            return self._apply_cached(cached, module_result)

        # Fast path: rules only (no screenshot/OCR yet)
        dec = self.engine.classify_screen(
            ui_dump=None,
            screenshot=None,
            maestro_error=error,
        )
        if dec.confidence >= self.RULE_CONFIDENCE_THRESHOLD:
            return self._execute_and_build(dec, module_result, cache_key, used_llm=False, used_vision=False)

        # Smart path: capture UI only when rules insufficient
        cap = self.vision.capture(f"recover_{module_result.folder}")
        shot = cap.screenshot_path
        dump = cap.ui_dump_path
        dec2 = self.engine.classify_screen(
            ui_dump=dump,
            screenshot=shot,
            maestro_error=error,
        )
        used_llm = bool(dec2.metadata.get("llm"))
        used_vision = True
        if dec2.confidence < self.LLM_CONFIDENCE_THRESHOLD and not used_llm:
            # Engine may have invoked LLM internally; if still low, record best effort
            pass
        return self._execute_and_build(
            dec2,
            module_result,
            cache_key,
            used_llm=used_llm,
            used_vision=used_vision,
            screenshot=str(shot or ""),
        )

    def _apply_cached(self, cached: CachedDecision, module_result: ModuleRunResult) -> SmartRecoveryOutcome:
        from decision_engine.decision_engine import Decision

        dec = Decision(
            screen=module_result.name,
            reason="Cached decision",
            options=[cached.chosen_action],
            chosen_action=cached.chosen_action,
            confidence=cached.confidence,
            root_cause=cached.root_cause,
            suggested_fix=cached.suggested_fix,
        )
        dump_path = None
        result = self.recovery.execute(dec, dump_path)
        return SmartRecoveryOutcome(
            attempted=True,
            success=result.success,
            attempts=result.attempts,
            ai_decision=cached.chosen_action,
            root_cause=cached.root_cause,
            suggested_fix=cached.suggested_fix,
            confidence=cached.confidence,
            severity="medium",
            priority="P2",
            screenshot="",
            used_llm=cached.used_llm,
            used_vision=False,
        )

    def _execute_and_build(
        self,
        dec,
        module_result: ModuleRunResult,
        cache_key: str,
        *,
        used_llm: bool,
        used_vision: bool,
        screenshot: str = "",
    ) -> SmartRecoveryOutcome:
        dump = Path(screenshot.replace(".png", ".xml")) if screenshot else None
        if screenshot and not (dump and dump.is_file()):
            dump = None
        result = self.recovery.execute(dec, dump)
        self.cache.put(
            cache_key,
            CachedDecision(
                chosen_action=dec.chosen_action,
                confidence=dec.confidence,
                root_cause=dec.root_cause,
                suggested_fix=dec.suggested_fix,
                used_llm=used_llm,
            ),
        )
        priority = "P1" if dec.confidence >= 0.85 else "P2" if dec.confidence >= 0.6 else "P3"
        severity = "high" if "bluetooth" in dec.root_cause.lower() or "permission" in dec.root_cause.lower() else "medium"
        return SmartRecoveryOutcome(
            attempted=True,
            success=result.success,
            attempts=result.attempts,
            ai_decision=dec.chosen_action,
            root_cause=dec.root_cause,
            suggested_fix=dec.suggested_fix,
            confidence=dec.confidence,
            severity=severity,
            priority=priority,
            screenshot=screenshot,
            used_llm=used_llm,
            used_vision=used_vision,
        )
