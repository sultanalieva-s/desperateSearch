from __future__ import annotations

import json
import logging
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from bot.config import settings

log = logging.getLogger(__name__)


@dataclass
class UserConfig:
    user_id: int
    platforms: list[str]
    positions: list[str]
    cv_path: str | None
    blacklist: list[str]
    active: bool = True


class Database:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._init()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init(self) -> None:
        with self._connect() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS user_config (
                    user_id   INTEGER PRIMARY KEY,
                    platforms TEXT NOT NULL,
                    positions TEXT NOT NULL,
                    cv_path   TEXT,
                    blacklist TEXT NOT NULL DEFAULT '[]',
                    active    INTEGER NOT NULL DEFAULT 1,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS jobs (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id    INTEGER NOT NULL,
                    platform   TEXT NOT NULL,
                    title      TEXT NOT NULL,
                    company    TEXT NOT NULL,
                    url        TEXT NOT NULL UNIQUE,
                    description TEXT,
                    status     TEXT NOT NULL DEFAULT 'pending',
                    cover_letter TEXT,
                    found_at   DATETIME DEFAULT CURRENT_TIMESTAMP
                );
            """)

    # ── UserConfig ────────────────────────────────────────────────────────────

    def save_config(self, cfg: UserConfig) -> None:
        with self._connect() as conn:
            conn.execute("""
                INSERT INTO user_config (user_id, platforms, positions, cv_path, blacklist, active)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    platforms  = excluded.platforms,
                    positions  = excluded.positions,
                    cv_path    = excluded.cv_path,
                    blacklist  = excluded.blacklist,
                    active     = excluded.active,
                    updated_at = CURRENT_TIMESTAMP
            """, (
                cfg.user_id,
                json.dumps(cfg.platforms),
                json.dumps(cfg.positions),
                cfg.cv_path,
                json.dumps(cfg.blacklist),
                int(cfg.active),
            ))

    def load_config(self, user_id: int) -> UserConfig | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM user_config WHERE user_id = ?", (user_id,)
            ).fetchone()
        if not row:
            return None
        return UserConfig(
            user_id=row["user_id"],
            platforms=json.loads(row["platforms"]),
            positions=json.loads(row["positions"]),
            cv_path=row["cv_path"],
            blacklist=json.loads(row["blacklist"]),
            active=bool(row["active"]),
        )

    # ── Jobs ──────────────────────────────────────────────────────────────────

    def upsert_job(self, user_id: int, job: dict[str, Any]) -> bool:
        """Insert a job. Returns True if it's new, False if duplicate."""
        with self._connect() as conn:
            try:
                conn.execute("""
                    INSERT INTO jobs (user_id, platform, title, company, url, description)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    user_id,
                    job["platform"],
                    job["title"],
                    job["company"],
                    job["url"],
                    job.get("description", ""),
                ))
                return True
            except sqlite3.IntegrityError:
                return False  # duplicate URL

    def update_job(self, url: str, status: str, cover_letter: str | None = None) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE jobs SET status = ?, cover_letter = ? WHERE url = ?",
                (status, cover_letter, url),
            )

    def get_jobs(self, user_id: int, limit: int = 50) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM jobs WHERE user_id = ? ORDER BY found_at DESC LIMIT ?",
                (user_id, limit),
            ).fetchall()
        return [dict(r) for r in rows]

    def job_exists(self, url: str) -> bool:
        with self._connect() as conn:
            row = conn.execute("SELECT 1 FROM jobs WHERE url = ?", (url,)).fetchone()
        return row is not None


db = Database(settings.DB_PATH)
