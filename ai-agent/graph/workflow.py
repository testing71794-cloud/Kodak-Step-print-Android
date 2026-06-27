"""LangGraph multi-agent workflow with sequential fallback."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any, Callable

from agents.base import AgentState
from agents.decision_agent import (
    DecisionAgent,
    FailureAnalysisAgent,
    RecommendationAgent,
    RecoveryAgent,
)
from agents.execution_agent import ExecutionAgent
from agents.knowledge_agent import KnowledgeAgent, MemoryAgent
from agents.planner_agent import PlannerAgent
from agents.reporting_agent import ReportingAgent
from agents.vision_agent import OCRAgent, ScreenClassifierAgent, VisionAgent
from decision_engine.decision_engine import DecisionEngine
from integrations.adb_client import ADBClient
from integrations.llm_client import LLMClient
from integrations.maestro_cli import MaestroCLI
from memory.sqlite_store import SQLiteMemoryStore
from memory.vector_store import VectorMemoryStore
from recovery.recovery_engine import RecoveryEngine
from utils.config_loader import AgentConfig
from vision.screen_capture import VisionEngine


def build_workflow(cfg: AgentConfig, device_id: str) -> tuple[Any, dict[str, Any]]:
    memory = SQLiteMemoryStore(cfg.sqlite_path)
    vector = VectorMemoryStore(cfg.chroma_path)
    adb = ADBClient(device_id, cfg.app_package)
    vision = VisionEngine(adb, cfg.screenshot_dir, cfg.ui_dump_dir)
    llm = LLMClient(
        model=cfg.llm_model,
        base_url=cfg.llm_base_url,
        api_key_env=cfg.llm_api_key_env,
    )
    decision_engine = DecisionEngine(llm, cfg.app_profile, cfg.min_confidence_for_llm)
    recovery_engine = RecoveryEngine(adb, cfg.max_recovery_attempts)
    maestro = MaestroCLI(cfg.maestro_cmd, cfg.repo_root)

    agents = {
        "knowledge": KnowledgeAgent(cfg, memory, vector),
        "memory": MemoryAgent(memory),
        "planner": PlannerAgent(memory),
        "execution": ExecutionAgent(maestro, cfg.repo_root),
        "vision": VisionAgent(vision),
        "ocr": OCRAgent(),
        "classifier": ScreenClassifierAgent(),
        "decision": DecisionAgent(decision_engine, memory),
        "recovery": RecoveryAgent(recovery_engine, memory),
        "failure": FailureAnalysisAgent(),
        "recommendation": RecommendationAgent(),
        "reporting": ReportingAgent(cfg),
    }
    return _compile_graph(agents, cfg), {"memory": memory, "adb": adb}


def _compile_graph(agents: dict[str, Any], cfg: AgentConfig) -> Any:
    order = [
        "knowledge",
        "memory",
        "planner",
        "execution",
        "vision",
        "ocr",
        "classifier",
        "decision",
        "recovery",
        "failure",
        "recommendation",
        "reporting",
    ]

    try:
        from langgraph.graph import END, StateGraph  # type: ignore

        graph = StateGraph(dict)

        def wrap(name: str) -> Callable[[dict], dict]:
            agent = agents[name]

            def node(state: dict) -> dict:
                st = _dict_to_state(state, cfg)
                st.steps += 1
                out = agent.run(st)
                return _state_to_dict(out)

            return node

        for name in order:
            graph.add_node(name, wrap(name))
        for i in range(len(order) - 1):
            graph.add_edge(order[i], order[i + 1])
        graph.add_edge(order[-1], END)
        graph.set_entry_point(order[0])
        return graph.compile()
    except ImportError:
        return SequentialWorkflow(agents, order)


class SequentialWorkflow:
    """Fallback when LangGraph is not installed."""

    def __init__(self, agents: dict[str, Any], order: list[str]) -> None:
        self.agents = agents
        self.order = order

    def invoke(self, state: dict) -> dict:
        st = state.get("_state_obj")
        if st is None:
            return state
        for name in self.order:
            st.steps += 1
            st = self.agents[name].run(st)
        return _state_to_dict(st)


def new_session(cfg: AgentConfig, device_id: str, mode: str | None = None) -> AgentState:
    return AgentState(
        session_id=str(uuid.uuid4())[:8],
        mode=mode or cfg.mode,
        device_id=device_id,
        repo_root=cfg.repo_root,
        app_package=cfg.app_package,
    )


def _state_to_dict(state: AgentState) -> dict:
    return {
        "_state_obj": state,
        "session_id": state.session_id,
        "status": state.status,
        "rows": state.rows,
        "messages": state.messages,
    }


def _dict_to_state(data: dict, cfg: AgentConfig) -> AgentState:
    st = data.get("_state_obj")
    if isinstance(st, AgentState):
        return st
    return new_session(cfg, data.get("device_id", ""), data.get("mode"))
