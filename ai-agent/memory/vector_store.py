"""Optional ChromaDB vector store for semantic retrieval."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any


class VectorMemoryStore:
    """Graceful wrapper — works without chromadb installed."""

    def __init__(self, persist_dir: Path, collection_name: str = "step_print_knowledge") -> None:
        self.persist_dir = persist_dir
        self.collection_name = collection_name
        self._collection = None
        self._available = False
        self._init()

    def _init(self) -> None:
        try:
            import chromadb  # type: ignore

            self.persist_dir.mkdir(parents=True, exist_ok=True)
            client = chromadb.PersistentClient(path=str(self.persist_dir))
            self._collection = client.get_or_create_collection(self.collection_name)
            self._available = True
        except Exception:
            self._available = False

    @property
    def available(self) -> bool:
        return self._available

    def upsert(self, doc_id: str, text: str, metadata: dict[str, Any] | None = None) -> None:
        if not self._collection:
            return
        self._collection.upsert(
            ids=[doc_id],
            documents=[text],
            metadatas=[metadata or {}],
        )

    def query(self, text: str, n: int = 5) -> list[dict[str, Any]]:
        if not self._collection:
            return []
        res = self._collection.query(query_texts=[text], n_results=n)
        out: list[dict[str, Any]] = []
        docs = (res.get("documents") or [[]])[0]
        metas = (res.get("metadatas") or [[]])[0]
        dists = (res.get("distances") or [[]])[0]
        for doc, meta, dist in zip(docs, metas, dists):
            out.append({"text": doc, "metadata": meta, "distance": dist})
        return out

    @staticmethod
    def doc_id(category: str, key: str) -> str:
        raw = f"{category}:{key}".encode("utf-8")
        return hashlib.sha256(raw).hexdigest()[:32]
