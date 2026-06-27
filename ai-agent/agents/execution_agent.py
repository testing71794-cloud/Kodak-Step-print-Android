"""Execution Agent — Maestro + ADB in assist/autonomous modes."""

from __future__ import annotations

from pathlib import Path

from agents.base import AgentState
from integrations.maestro_cli import MaestroCLI


class ExecutionAgent:
    def __init__(self, maestro: MaestroCLI, repo_root: Path) -> None:
        self.maestro = maestro
        self.repo_root = repo_root

    def run(self, state: AgentState) -> AgentState:
        if state.mode == "observe":
            state.log("Execution: observe-only — no Maestro launch")
            return state
        flow = self._pick_flow(state)
        if not flow:
            state.maestro_error = "No flow selected for execution"
            state.log("Execution: no flow found")
            return state
        debug = self.repo_root / "ai-agent" / "logs" / "maestro_debug" / state.session_id
        rc, output = self.maestro.run_flow(flow, state.device_id, debug_output=debug)
        state.current_flow = str(flow.relative_to(self.repo_root))
        state.maestro_output = output[-4000:]
        if rc != 0:
            state.maestro_error = self._extract_error(output)
            state.status = "failed"
        else:
            state.status = "passed"
        state.log(f"Execution: flow={flow.name} rc={rc}")
        return state

    def _pick_flow(self, state: AgentState) -> Path | None:
        mod = state.current_module
        atp = self.repo_root / "ATP TestCase Flows"
        if mod and mod != "exploratory":
            folder = atp / mod
            if folder.is_dir():
                flows = sorted(folder.glob("*.yaml"))
                if flows:
                    return flows[0]
        for folder in sorted(atp.iterdir()) if atp.is_dir() else []:
            if folder.is_dir():
                flows = sorted(folder.glob("*.yaml"))
                if flows:
                    state.current_module = folder.name
                    return flows[0]
        return None

    @staticmethod
    def _extract_error(output: str) -> str:
        for line in reversed(output.splitlines()):
            low = line.lower()
            if "failed" in low or "error" in low or "timeout" in low or "not found" in low:
                return line.strip()
        return output.strip()[-500:] or "Maestro flow failed"
