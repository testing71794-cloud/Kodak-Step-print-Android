"""Timing statistics for adaptive waits — persisted between runs."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path


class TimingStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS timing_stats (
                    screen_key TEXT PRIMARY KEY,
                    samples INTEGER DEFAULT 0,
                    total_sec REAL DEFAULT 0,
                    min_sec REAL,
                    max_sec REAL,
                    last_sec REAL,
                    p90_sec REAL
                )
                """
            )

    def record(self, screen_key: str, elapsed_sec: float) -> None:
        if not screen_key:
            return
        with sqlite3.connect(str(self.db_path)) as conn:
            row = conn.execute(
                "SELECT samples, total_sec, min_sec, max_sec FROM timing_stats WHERE screen_key=?",
                (screen_key,),
            ).fetchone()
            if row:
                samples, total, mn, mx = row
                samples += 1
                total += elapsed_sec
                mn = min(mn, elapsed_sec)
                mx = max(mx, elapsed_sec)
            else:
                samples, total, mn, mx = 1, elapsed_sec, elapsed_sec, elapsed_sec
            p90 = elapsed_sec * 0.9 + (mx * 0.1)
            conn.execute(
                """
                INSERT INTO timing_stats (screen_key, samples, total_sec, min_sec, max_sec, last_sec, p90_sec)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(screen_key) DO UPDATE SET
                    samples=excluded.samples, total_sec=excluded.total_sec,
                    min_sec=excluded.min_sec, max_sec=excluded.max_sec,
                    last_sec=excluded.last_sec, p90_sec=excluded.p90_sec
                """,
                (screen_key, samples, total, mn, mx, elapsed_sec, p90),
            )

    def get_stats(self, screen_key: str) -> dict | None:
        with sqlite3.connect(str(self.db_path)) as conn:
            row = conn.execute(
                "SELECT samples, total_sec, min_sec, max_sec, last_sec, p90_sec FROM timing_stats WHERE screen_key=?",
                (screen_key,),
            ).fetchone()
        if not row:
            return None
        samples, total, mn, mx, last, p90 = row
        return {
            "samples": samples,
            "avg_sec": total / samples if samples else 0,
            "min_sec": mn,
            "max_sec": mx,
            "last_sec": last,
            "p90_sec": p90,
        }

    def summary(self) -> list[dict]:
        with sqlite3.connect(str(self.db_path)) as conn:
            rows = conn.execute(
                "SELECT screen_key, samples, p90_sec, last_sec FROM timing_stats ORDER BY samples DESC LIMIT 20"
            ).fetchall()
        return [{"screen": r[0], "samples": r[1], "p90_sec": r[2], "last_sec": r[3]} for r in rows]
