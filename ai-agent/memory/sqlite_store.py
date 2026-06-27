"""SQLite long-term memory for AI Step Print Agent."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class MemoryRecord:
    category: str
    key: str
    value: dict[str, Any]
    confidence: float = 1.0


class SQLiteMemoryStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS knowledge (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category TEXT NOT NULL,
                    key TEXT NOT NULL,
                    value_json TEXT NOT NULL,
                    confidence REAL DEFAULT 1.0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(category, key)
                );
                CREATE TABLE IF NOT EXISTS executions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    mode TEXT,
                    status TEXT,
                    summary_json TEXT,
                    started_at TEXT NOT NULL,
                    ended_at TEXT
                );
                CREATE TABLE IF NOT EXISTS decisions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    screen TEXT,
                    reason TEXT,
                    options_json TEXT,
                    chosen_action TEXT,
                    confidence REAL,
                    recovery_success INTEGER,
                    duration_ms INTEGER,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS scan_manifest (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    manifest_json TEXT NOT NULL,
                    scanned_at TEXT NOT NULL
                );
                """
            )

    def upsert(self, record: MemoryRecord) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO knowledge (category, key, value_json, confidence, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(category, key) DO UPDATE SET
                    value_json=excluded.value_json,
                    confidence=excluded.confidence,
                    updated_at=excluded.updated_at
                """,
                (
                    record.category,
                    record.key,
                    json.dumps(record.value, ensure_ascii=False),
                    record.confidence,
                    now,
                    now,
                ),
            )

    def get(self, category: str, key: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT value_json FROM knowledge WHERE category=? AND key=?",
                (category, key),
            ).fetchone()
        if not row:
            return None
        return json.loads(row["value_json"])

    def search_category(self, category: str, limit: int = 50) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT key, value_json, confidence FROM knowledge WHERE category=? ORDER BY updated_at DESC LIMIT ?",
                (category, limit),
            ).fetchall()
        return [
            {"key": r["key"], "value": json.loads(r["value_json"]), "confidence": r["confidence"]}
            for r in rows
        ]

    def log_decision(
        self,
        *,
        session_id: str,
        screen: str,
        reason: str,
        options: list[str],
        chosen: str,
        confidence: float,
        recovery_success: bool | None,
        duration_ms: int,
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO decisions
                (session_id, screen, reason, options_json, chosen_action, confidence,
                 recovery_success, duration_ms, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    screen,
                    reason,
                    json.dumps(options),
                    chosen,
                    confidence,
                    None if recovery_success is None else int(recovery_success),
                    duration_ms,
                    now,
                ),
            )

    def save_scan_manifest(self, manifest: dict[str, Any]) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO scan_manifest (id, manifest_json, scanned_at) VALUES (1, ?, ?)
                ON CONFLICT(id) DO UPDATE SET manifest_json=excluded.manifest_json, scanned_at=excluded.scanned_at
                """,
                (json.dumps(manifest, ensure_ascii=False), now),
            )

    def load_scan_manifest(self) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute("SELECT manifest_json FROM scan_manifest WHERE id=1").fetchone()
        if not row:
            return None
        return json.loads(row["manifest_json"])

    def stats(self) -> dict[str, int]:
        with self._connect() as conn:
            k = conn.execute("SELECT COUNT(*) AS c FROM knowledge").fetchone()["c"]
            d = conn.execute("SELECT COUNT(*) AS c FROM decisions").fetchone()["c"]
            e = conn.execute("SELECT COUNT(*) AS c FROM executions").fetchone()["c"]
        return {"knowledge_entries": k, "decisions": d, "executions": e}
