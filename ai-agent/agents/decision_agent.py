"""Decision, Recovery, Failure Analysis, Recommendation agents."""

from __future__ import annotations

import time

from agents.base import AgentState
from decision_engine.decision_engine import DecisionEngine
from memory.sqlite_store import SQLiteMemoryStore
from recovery.recovery_engine import RecoveryEngine


class DecisionAgent:
    def __init__(self, engine: DecisionEngine, memory: SQLiteMemoryStore) -> None:
        self.engine = engine
        self.memory = memory

    def run(self, state: AgentState) -> AgentState:
        historical = self.memory.search_category("recovery", limit=5)
        dec = self.engine.classify_screen(
            ui_dump=state.ui_dump,
            screenshot=state.screenshot,
            maestro_error=state.maestro_error,
            historical=historical,
        )
        state.decision.update(
            {
                "screen": dec.screen,
                "reason": dec.reason,
                "options": dec.options,
                "chosen_action": dec.chosen_action,
                "confidence": dec.confidence,
                "root_cause": dec.root_cause,
                "suggested_fix": dec.suggested_fix,
            }
        )
        state.log(f"Decision: action={dec.chosen_action} confidence={dec.confidence:.2f}")
        return state


class RecoveryAgent:
    def __init__(self, recovery: RecoveryEngine, memory: SQLiteMemoryStore) -> None:
        self.recovery = recovery
        self.memory = memory

    def run(self, state: AgentState) -> AgentState:
        if state.mode == "observe":
            state.recovery = {"skipped": True, "reason": "observe mode"}
            return state
        from decision_engine.decision_engine import Decision

        dec = Decision(
            screen=state.decision.get("screen", ""),
            reason=state.decision.get("reason", ""),
            options=state.decision.get("options", []),
            chosen_action=state.decision.get("chosen_action", "wait_and_retry"),
            confidence=float(state.decision.get("confidence", 0.5)),
            root_cause=state.decision.get("root_cause", ""),
            suggested_fix=state.decision.get("suggested_fix", ""),
        )
        t0 = time.time()
        result = self.recovery.execute(dec, state.ui_dump)
        state.recovery = {
            "success": result.success,
            "attempts": result.attempts,
            "last_action": result.last_action,
            "duration_ms": result.duration_ms,
            "message": result.message,
        }
        self.memory.log_decision(
            session_id=state.session_id,
            screen=dec.screen,
            reason=dec.reason,
            options=dec.options,
            chosen=dec.chosen_action,
            confidence=dec.confidence,
            recovery_success=result.success,
            duration_ms=result.duration_ms,
        )
        from memory.sqlite_store import MemoryRecord

        self.memory.upsert(
            MemoryRecord(
                "recovery",
                dec.chosen_action,
                {"success": result.success, "root_cause": dec.root_cause},
                confidence=dec.confidence,
            )
        )
        state.log(f"Recovery: success={result.success} attempts={result.attempts}")
        return state


class FailureAnalysisAgent:
    def run(self, state: AgentState) -> AgentState:
        root = state.decision.get("root_cause") or state.maestro_error or "Unknown failure"
        state.failure_analysis = {
            "root_cause": root,
            "observed": state.maestro_error[:500] if state.maestro_error else state.decision.get("screen"),
            "severity": self._severity(root),
        }
        state.log(f"FailureAnalysis: {root[:80]}")
        return state


    @staticmethod
    def _severity(text: str) -> str:
        t = text.lower()
        if any(x in t for x in ("paper out", "battery", "bluetooth", "permission")):
            return "high"
        if "timeout" in t or "not found" in t:
            return "medium"
        return "low"


class RecommendationAgent:
    def run(self, state: AgentState) -> AgentState:
        fix = state.decision.get("suggested_fix", "Review logs and screenshot.")
        conf = float(state.decision.get("confidence", 0.5))
        state.recommendation = {
            "recommendation": fix,
            "confidence": conf,
            "priority": "P1" if conf >= 0.85 else "P2" if conf >= 0.6 else "P3",
        }
        state.log(f"Recommendation: {fix[:80]}")
        return state
