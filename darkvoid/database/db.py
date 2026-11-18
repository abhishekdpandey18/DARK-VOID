"""SQLite connection management, WAL optimization, schema initialization, and corruption recovery."""

from __future__ import annotations

import logging
import shutil
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

logger = logging.getLogger("darkvoid.database")

SCHEMA_SQL = """
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;

CREATE TABLE IF NOT EXISTS conversion_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT NOT NULL,
    original_filename TEXT NOT NULL,
    original_path TEXT NOT NULL,
    output_filename TEXT NOT NULL,
    output_path TEXT NOT NULL,
    file_size INTEGER NOT NULL DEFAULT 0,
    duration REAL DEFAULT 0.0,
    conversion_timestamp TEXT NOT NULL,
    conversion_duration REAL NOT NULL DEFAULT 0.0,
    status TEXT NOT NULL,
    conversion_profile TEXT NOT NULL DEFAULT 'dnxhr_hq',
    video_codec TEXT NOT NULL DEFAULT 'dnxhd',
    audio_codec TEXT NOT NULL DEFAULT 'pcm_s16le',
    has_audio INTEGER NOT NULL DEFAULT 1,
    error_message TEXT DEFAULT '',
    source_fingerprint TEXT NOT NULL DEFAULT '',
    source_mtime_ns INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_history_fingerprint ON conversion_history(source_fingerprint);
CREATE INDEX IF NOT EXISTS idx_history_status ON conversion_history(status);
CREATE INDEX IF NOT EXISTS idx_history_orig_path ON conversion_history(original_path);

CREATE TABLE IF NOT EXISTS conversion_queue (
    job_id TEXT PRIMARY KEY,
    input_path TEXT NOT NULL,
    output_path TEXT NOT NULL,
    file_size INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'Pending',
    progress REAL NOT NULL DEFAULT 0.0,
    start_time TEXT DEFAULT '',
    end_time TEXT DEFAULT '',
    error_message TEXT DEFAULT '',
    source_fingerprint TEXT DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_queue_status ON conversion_queue(status);
"""


class DatabaseManager:
    """Manages SQLite connections, WAL mode performance, transactions, and corruption recovery."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path).expanduser().resolve()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize_db()

    def _initialize_db(self) -> None:
        try:
            with self.connect() as conn:
                conn.executescript(SCHEMA_SQL)
        except sqlite3.DatabaseError as exc:
            logger.error("Database corruption detected at %s (%s). Backing up and recreating.", self.db_path, exc)
            backup = self.db_path.with_suffix(f".corrupt.{int(time.time())}.db")
            try:
                if self.db_path.exists():
                    shutil.move(str(self.db_path), str(backup))
            except OSError:
                pass
            with self.connect() as conn:
                conn.executescript(SCHEMA_SQL)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        """Yield a configured SQLite connection with row factory and transaction commit."""
        conn = sqlite3.connect(str(self.db_path), timeout=15.0)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
