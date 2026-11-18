"""Persistent conversion history and duplicate detection queries."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from darkvoid.database.db import DatabaseManager


@dataclass
class HistoryRecord:
    """Represents a single conversion history record."""

    id: int | None
    job_id: str
    original_filename: str
    original_path: str
    output_filename: str
    output_path: str
    file_size: int
    duration: float
    conversion_timestamp: str
    conversion_duration: float
    status: str
    conversion_profile: str
    video_codec: str
    audio_codec: str
    has_audio: bool
    error_message: str
    source_fingerprint: str
    source_mtime_ns: int


class HistoryRepository:
    """Repository for recording, querying, and deduplicating conversions."""

    def __init__(self, db_manager: DatabaseManager) -> None:
        self.db = db_manager

    def record_conversion(
        self,
        *,
        job_id: str,
        original_path: Path,
        output_path: Path,
        file_size: int,
        duration: float,
        conversion_duration: float,
        status: str,
        conversion_profile: str = "dnxhr_hq",
        video_codec: str = "dnxhd",
        audio_codec: str = "pcm_s16le",
        has_audio: bool = True,
        error_message: str = "",
        source_fingerprint: str = "",
        source_mtime_ns: int = 0,
    ) -> int:
        """Insert a conversion outcome record using parameterized SQL."""
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        with self.db.connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO conversion_history (
                    job_id, original_filename, original_path,
                    output_filename, output_path, file_size,
                    duration, conversion_timestamp, conversion_duration,
                    status, conversion_profile, video_codec,
                    audio_codec, has_audio, error_message,
                    source_fingerprint, source_mtime_ns
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job_id,
                    original_path.name,
                    str(original_path.resolve()),
                    output_path.name,
                    str(output_path.resolve()),
                    int(file_size),
                    float(duration or 0.0),
                    timestamp,
                    float(conversion_duration),
                    status,
                    conversion_profile,
                    video_codec,
                    audio_codec,
                    1 if has_audio else 0,
                    error_message,
                    source_fingerprint,
                    int(source_mtime_ns),
                ),
            )
            return int(cursor.lastrowid or 0)

    def find_completed_duplicate(
        self,
        source_fingerprint: str,
        original_path: Path,
    ) -> HistoryRecord | None:
        """Return a completed conversion record matching the fingerprint or path if output still exists."""
        if not source_fingerprint:
            return None
        with self.db.connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM conversion_history
                WHERE status = 'Completed'
                  AND (source_fingerprint = ? OR original_path = ?)
                ORDER BY id DESC
                """,
                (source_fingerprint, str(original_path.resolve())),
            ).fetchall()
        for row in rows:
            rec = self._row_to_record(row)
            out_file = Path(rec.output_path)
            if out_file.exists() and out_file.stat().st_size > 0:
                return rec
        return None

    def list_history(
        self,
        *,
        status: str | None = None,
        search: str | None = None,
        limit: int = 50,
        sort_by: str = "id",
        descending: bool = True,
    ) -> list[HistoryRecord]:
        """List conversion history with optional status filter, search term, and sorting."""
        allowed_sorts = {"id", "conversion_timestamp", "file_size", "conversion_duration", "original_filename"}
        order_col = sort_by if sort_by in allowed_sorts else "id"
        direction = "DESC" if descending else "ASC"

        clauses: list[str] = []
        params: list[Any] = []

        if status:
            clauses.append("LOWER(status) = LOWER(?)")
            params.append(status)
        if search:
            clauses.append("(original_filename LIKE ? OR output_filename LIKE ? OR original_path LIKE ?)")
            like_val = f"%{search}%"
            params.extend([like_val, like_val, like_val])

        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        query = f"SELECT * FROM conversion_history {where_sql} ORDER BY {order_col} {direction} LIMIT ?"
        params.append(int(limit))

        with self.db.connect() as conn:
            rows = conn.execute(query, tuple(params)).fetchall()
        return [self._row_to_record(r) for r in rows]

    def get_failed_records(self, limit: int = 50) -> list[HistoryRecord]:
        """Return failed conversion records eligible for retry."""
        return self.list_history(status="Failed", limit=limit)

    @staticmethod
    def _row_to_record(row: Any) -> HistoryRecord:
        return HistoryRecord(
            id=row["id"],
            job_id=row["job_id"],
            original_filename=row["original_filename"],
            original_path=row["original_path"],
            output_filename=row["output_filename"],
            output_path=row["output_path"],
            file_size=row["file_size"],
            duration=row["duration"],
            conversion_timestamp=row["conversion_timestamp"],
            conversion_duration=row["conversion_duration"],
            status=row["status"],
            conversion_profile=row["conversion_profile"],
            video_codec=row["video_codec"],
            audio_codec=row["audio_codec"],
            has_audio=bool(row["has_audio"]),
            error_message=row["error_message"],
            source_fingerprint=row["source_fingerprint"],
            source_mtime_ns=row["source_mtime_ns"],
        )
