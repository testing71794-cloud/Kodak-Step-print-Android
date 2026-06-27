"""Knowledge + Memory agents."""

from __future__ import annotations

from agents.base import AgentState
from learning.project_scanner import KnowledgeBuilder, ProjectScanner
from memory.sqlite_store import SQLiteMemoryStore
from memory.vector_store import VectorMemoryStore
from utils.config_loader import AgentConfig


class KnowledgeAgent:
    def __init__(self, cfg: AgentConfig, memory: SQLiteMemoryStore, vector: VectorMemoryStore) -> None:
        self.cfg = cfg
        self.memory = memory
        self.vector = vector
        self.scanner = ProjectScanner(cfg.repo_root, cfg.scan_paths)
        self.builder = KnowledgeBuilder(memory, vector)

    def run(self, state: AgentState) -> AgentState:
        manifest = self.memory.load_scan_manifest()
        scan = self.scanner.scan()
        need = self.cfg.auto_scan and (
            manifest is None
            or (self.cfg.rescan_if_changed and manifest.get("content_hash") != scan.content_hash)
        )
        if need:
            m = self.builder.build_from_scan(scan)
            state.log(f"Knowledge: scanned {m.get('flow_count', 0)} flows")
        else:
            state.log("Knowledge: using cached manifest")
        hits = self.vector.query(state.current_module or "printer", n=3) if self.vector.available else []
        state.knowledge_hits = hits
        return state


class MemoryAgent:
    def __init__(self, memory: SQLiteMemoryStore) -> None:
        self.memory = memory

    def run(self, state: AgentState) -> AgentState:
        stats = self.memory.stats()
        state.decision["memory_stats"] = stats
        state.log(f"Memory: entries={stats['knowledge_entries']} decisions={stats['decisions']}")
        return state
