"""Planner Agent — selects modules/flows from knowledge base."""

from __future__ import annotations

from agents.base import AgentState
from memory.sqlite_store import SQLiteMemoryStore


class PlannerAgent:
    def __init__(self, memory: SQLiteMemoryStore) -> None:
        self.memory = memory

    def run(self, state: AgentState) -> AgentState:
        modules = self.memory.search_category("module", limit=30)
        if not modules and state.mode == "autonomous":
            state.status = "no_knowledge"
            state.log("Planner: no modules in knowledge — run learning phase first")
            return state
        planned = [m["key"] for m in modules][:10]
        state.current_module = planned[0] if planned else "exploratory"
        state.log(f"Planner: planned modules={planned}")
        state.decision["planned_modules"] = planned
        return state
