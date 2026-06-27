"""Reporting Agent — Excel + dashboard + session row."""

from __future__ import annotations

from datetime import datetime, timezone

from agents.base import AgentState
from reporting.dashboard import render_dashboard
from reporting.excel_report import write_excel_report
from utils.config_loader import AgentConfig


class ReportingAgent:
    def __init__(self, cfg: AgentConfig) -> None:
        self.cfg = cfg

    def run(self, state: AgentState) -> AgentState:
        row = {
            "Module": state.current_module,
            "Test Case": state.current_flow,
            "Status": state.status,
            "Execution Time": datetime.now(timezone.utc).isoformat(),
            "AI Decision": state.decision.get("chosen_action", ""),
            "Recovery Attempt": state.recovery.get("attempts", 0),
            "Recovery Result": "PASS" if state.recovery.get("success") else "FAIL",
            "Root Cause": state.failure_analysis.get("root_cause", state.decision.get("root_cause", "")),
            "Suggested Fix": state.recommendation.get("recommendation", ""),
            "Confidence": state.decision.get("confidence", 0),
            "Severity": state.failure_analysis.get("severity", ""),
            "Priority": state.recommendation.get("priority", ""),
            "Retry Count": state.recovery.get("attempts", 0),
            "Screenshot": str(state.screenshot or ""),
            "Device": state.device_id,
            "Session": state.session_id,
        }
        state.rows.append(row)
        write_excel_report(self.cfg.excel_path, state.rows)
        render_dashboard(self.cfg.dashboard_path, state.rows, self.cfg.summary_json)
        state.log("Reporting: Excel + dashboard updated")
        return state
