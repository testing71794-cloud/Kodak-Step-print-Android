"""Load knowledge once; rescan only when repo content hash changes."""

from __future__ import annotations

import os
import time

from learning.project_scanner import KnowledgeBuilder, ProjectScanner
from memory.sqlite_store import SQLiteMemoryStore
from memory.vector_store import VectorMemoryStore
from utils.config_loader import AgentConfig


class KnowledgeManager:
    def __init__(self, cfg: AgentConfig) -> None:
        self.cfg = cfg
        self.memory = SQLiteMemoryStore(cfg.sqlite_path)
        self.vector = VectorMemoryStore(cfg.chroma_path)
        self.scanner = ProjectScanner(cfg.repo_root, cfg.scan_paths)
        self.builder = KnowledgeBuilder(self.memory, self.vector)

    def ensure_loaded(self) -> tuple[bool, float]:
        """
        Returns (knowledge_updated, load_duration_sec).
        Skips full scan when manifest hash matches (target: under 10s load).
        """
        t0 = time.time()
        force = os.environ.get("AI_AGENT_FORCE_RESCAN", "").strip().lower() in (
            "1",
            "true",
            "yes",
        )
        manifest = self.memory.load_scan_manifest()
        if not force and manifest:
            quick = self.scanner.scan()
            if quick.content_hash == manifest.get("content_hash"):
                return False, time.time() - t0

        scan = self.scanner.scan()
        self.builder.build_from_scan(scan)
        return True, time.time() - t0
