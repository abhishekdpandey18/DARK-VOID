"""Persistent and sequential conversion job queue manager."""

from __future__ import annotations

import logging
import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from darkvoid.core.converter import ConversionEngine, ConversionOutcome
from darkvoid.core.ffmpeg import ConversionProgress
from darkvoid.database.db import DatabaseManager
from darkvoid.utils.files import build_output_path, compute_fast_file_fingerprint

logger = logging.getLogger("darkvoid.queue")

VALID_JOB_STATUSES = frozenset({
    "Pending",
    "Scanning",
    "Converting",
    "Completed",
    "Failed",
    "Cancelled",
    "Skipped",
})


@dataclass
class QueueJob:
    """Represents a conversion job in the DARK VOID queue."""

    job_id: str
    input_path: str
    output_path: str
    file_size: int
    status: str
    progress: float
    start_time: str
    end_time: str
    error_message: str
    source_fingerprint: str
    created_at: str


class JobQueueManager:
    """Manages persistent conversion queue jobs, sequential execution, deduplication, and retries."""

    def __init__(self, db: DatabaseManager, engine: ConversionEngine) -> None:
        self.db = db
        self.engine = engine
        self._pause_scheduling = threading.Event()

    def pause_scheduling(self) -> None:
        """Stop scheduling new pending jobs while allowing any currently running job to finish."""
        self._pause_scheduling.set()

    def resume_scheduling(self) -> None:
        """Resume scheduling pending jobs."""
        self._pause_scheduling.clear()

    def enqueue(
        self,
        input_path: Path,
        output_dir: Path | None = None,
    ) -> tuple[QueueJob, bool]:
        """Add a video file to the persistent queue if not already queued as Pending/Converting.

        Returns (QueueJob, created_new).
        """
        resolved_in = input_path.expanduser().resolve()
        target_out_dir = (output_dir or Path(self.engine.config.output_dir)).expanduser().resolve()
        planned_out = build_output_path(
            resolved_in,
            target_out_dir,
            suffix=self.engine.config.output_suffix,
            extension=self.engine.config.output_extension,
        )
        size = resolved_in.stat().st_size if resolved_in.exists() and resolved_in.is_file() else 0
        fp = compute_fast_file_fingerprint(resolved_in) if size > 0 else ""

        with self.db.connect() as conn:
            existing = conn.execute(
                """
                SELECT * FROM conversion_queue
                WHERE (input_path = ? OR (source_fingerprint != '' AND source_fingerprint = ?))
                  AND status IN ('Pending', 'Scanning', 'Converting')
                LIMIT 1
                """,
                (str(resolved_in), fp),
            ).fetchone()
            if existing is not None:
                return self._row_to_job(existing), False

            job_id = f"job-{uuid.uuid4().hex[:8]}"
            now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            conn.execute(
                """
                INSERT INTO conversion_queue (
                    job_id, input_path, output_path, file_size, status,
                    progress, start_time, end_time, error_message,
                    source_fingerprint, created_at
                ) VALUES (?, ?, ?, ?, 'Pending', 0.0, '', '', '', ?, ?)
                """,
                (job_id, str(resolved_in), str(planned_out), size, fp, now_str),
            )
            row = conn.execute(
                "SELECT * FROM conversion_queue WHERE job_id = ?", (job_id,)
            ).fetchone()
            return self._row_to_job(row), True

    def list_jobs(self, status: str | None = None, limit: int = 100) -> list[QueueJob]:
        """List jobs in the queue, optionally filtered by status."""
        with self.db.connect() as conn:
            if status:
                rows = conn.execute(
                    "SELECT * FROM conversion_queue WHERE LOWER(status) = LOWER(?) ORDER BY created_at DESC LIMIT ?",
                    (status, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM conversion_queue ORDER BY created_at DESC LIMIT ?",
                    (limit,),
                ).fetchall()
        return [self._row_to_job(r) for r in rows]

    def clear_pending(self) -> int:
        """Remove all Pending jobs from the queue and return the count removed."""
        with self.db.connect() as conn:
            cur = conn.execute("DELETE FROM conversion_queue WHERE status = 'Pending'")
            return int(cur.rowcount or 0)

    def reset_failed_for_retry(self) -> list[QueueJob]:
        """Mark all Failed and Cancelled jobs in the queue back to Pending for retry."""
        with self.db.connect() as conn:
            conn.execute(
                """
                UPDATE conversion_queue
                SET status = 'Pending', progress = 0.0, error_message = '', start_time = '', end_time = ''
                WHERE status IN ('Failed', 'Cancelled')
                """
            )
            rows = conn.execute(
                "SELECT * FROM conversion_queue WHERE status = 'Pending' ORDER BY created_at ASC"
            ).fetchall()
        return [self._row_to_job(r) for r in rows]

    def update_job_status(
        self,
        job_id: str,
        status: str,
        *,
        progress: float | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
        error_message: str | None = None,
        output_path: str | None = None,
    ) -> None:
        """Update job state in SQLite."""
        fields: list[str] = ["status = ?"]
        params: list[object] = [status]
        if progress is not None:
            fields.append("progress = ?")
            params.append(float(progress))
        if start_time is not None:
            fields.append("start_time = ?")
            params.append(start_time)
        if end_time is not None:
            fields.append("end_time = ?")
            params.append(end_time)
        if error_message is not None:
            fields.append("error_message = ?")
            params.append(error_message)
        if output_path is not None:
            fields.append("output_path = ?")
            params.append(output_path)
        params.append(job_id)

        with self.db.connect() as conn:
            conn.execute(
                f"UPDATE conversion_queue SET {', '.join(fields)} WHERE job_id = ?",
                tuple(params),
            )

    def process_pending(
        self,
        *,
        existing_policy: str | None = None,
        force: bool = False,
        dry_run: bool = False,
        on_job_start: Callable[[QueueJob], None] | None = None,
        on_job_progress: Callable[[QueueJob, ConversionProgress], None] | None = None,
        on_job_complete: Callable[[QueueJob, ConversionOutcome], None] | None = None,
        cancel_event: threading.Event | None = None,
    ) -> list[ConversionOutcome]:
        """Process all Pending queue jobs sequentially (1 active FFmpeg process by default)."""
        outcomes: list[ConversionOutcome] = []
        while not self._pause_scheduling.is_set():
            if cancel_event and cancel_event.is_set():
                break
            with self.db.connect() as conn:
                row = conn.execute(
                    "SELECT * FROM conversion_queue WHERE status = 'Pending' ORDER BY created_at ASC LIMIT 1"
                ).fetchone()
            if row is None:
                break

            job = self._row_to_job(row)
            now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            self.update_job_status(job.job_id, "Scanning", start_time=now_str, progress=0.0)
            job.status = "Scanning"
            if on_job_start:
                on_job_start(job)

            self.update_job_status(job.job_id, "Converting", progress=0.0)
            job.status = "Converting"

            def _prog_cb(prog: ConversionProgress, current_job: QueueJob = job) -> None:
                self.update_job_status(current_job.job_id, "Converting", progress=prog.percentage)
                if on_job_progress:
                    on_job_progress(current_job, prog)

            in_path = Path(job.input_path)
            out_dir = Path(job.output_path).parent
            outcome = self.engine.convert_file(
                in_path,
                out_dir,
                job_id=job.job_id,
                existing_policy=existing_policy,
                force=force,
                dry_run=dry_run,
                progress_callback=_prog_cb,
                cancel_event=cancel_event,
            )

            end_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            final_status = "Completed" if outcome.status == "DryRun" else outcome.status
            final_prog = 100.0 if final_status in {"Completed", "Skipped"} else 0.0
            self.update_job_status(
                job.job_id,
                final_status,
                progress=final_prog,
                end_time=end_str,
                error_message="" if final_status in {"Completed", "Skipped"} else outcome.message,
                output_path=str(outcome.output_path),
            )
            job.status = final_status
            job.progress = final_prog
            if on_job_complete:
                on_job_complete(job, outcome)
            outcomes.append(outcome)

        return outcomes

    @staticmethod
    def _row_to_job(row: object) -> QueueJob:
        r = row  # type: ignore[assignment]
        return QueueJob(
            job_id=r["job_id"],  # type: ignore[index]
            input_path=r["input_path"],  # type: ignore[index]
            output_path=r["output_path"],  # type: ignore[index]
            file_size=int(r["file_size"]),  # type: ignore[index]
            status=r["status"],  # type: ignore[index]
            progress=float(r["progress"]),  # type: ignore[index]
            start_time=r["start_time"],  # type: ignore[index]
            end_time=r["end_time"],  # type: ignore[index]
            error_message=r["error_message"],  # type: ignore[index]
            source_fingerprint=r["source_fingerprint"],  # type: ignore[index]
            created_at=r["created_at"],  # type: ignore[index]
        )
