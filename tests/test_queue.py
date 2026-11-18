"""Tests for persistent job queue management, deduplication, clear, and retry."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from darkvoid.core.converter import ConversionEngine
from darkvoid.core.queue import JobQueueManager
from darkvoid.database.db import DatabaseManager
from darkvoid.database.history import HistoryRepository
from darkvoid.utils.paths import AppConfig
from tests.helpers import generate_sample_video


class TestJobQueue(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.cfg = AppConfig(
            workspace_dir=str(self.root / "ws"),
            input_dir=str(self.root / "ws/incoming"),
            output_dir=str(self.root / "ws/converted"),
            temp_dir=str(self.root / "ws/converting"),
            failed_dir=str(self.root / "ws/failed"),
            log_dir=str(self.root / "ws/logs"),
            database_path=str(self.root / "ws/history.db"),
        )
        self.cfg.ensure_directories()
        self.db = DatabaseManager(self.cfg.database_path)
        self.history = HistoryRepository(self.db)
        self.engine = ConversionEngine(self.cfg, self.history)
        self.qm = JobQueueManager(self.db, self.engine)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_enqueue_deduplication_and_process_pending(self) -> None:
        v1 = generate_sample_video(self.root / "q1.mp4", duration=0.3)
        job1, created1 = self.qm.enqueue(v1)
        self.assertTrue(created1)
        self.assertEqual(job1.status, "Pending")

        # Enqueueing same file again while Pending must be deduplicated
        job1_dup, created2 = self.qm.enqueue(v1)
        self.assertFalse(created2)
        self.assertEqual(job1.job_id, job1_dup.job_id)

        outcomes = self.qm.process_pending()
        self.assertEqual(len(outcomes), 1)
        self.assertEqual(outcomes[0].status, "Completed")

        jobs = self.qm.list_jobs(status="Completed")
        self.assertEqual(len(jobs), 1)

    def test_queue_clear_and_retry(self) -> None:
        v1 = generate_sample_video(self.root / "q_clear.mp4", duration=0.3)
        self.qm.enqueue(v1)
        removed = self.qm.clear_pending()
        self.assertEqual(removed, 1)
        self.assertEqual(len(self.qm.list_jobs(status="Pending")), 0)

        # Simulate a failed job and then retry it after fixing the file
        bad_path = self.root / "fixable.mp4"
        bad_path.write_bytes(b"corrupt")
        job, _ = self.qm.enqueue(bad_path)
        outcomes1 = self.qm.process_pending()
        self.assertEqual(outcomes1[0].status, "Failed")

        # Replace with valid video and retry
        generate_sample_video(bad_path, duration=0.3)
        requeued = self.qm.reset_failed_for_retry()
        self.assertEqual(len(requeued), 1)
        outcomes2 = self.qm.process_pending(force=True)
        self.assertEqual(outcomes2[0].status, "Completed")


if __name__ == "__main__":
    unittest.main()
