"""Tests for SQLite history persistence, filtering, searching, and corruption recovery."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from darkvoid.database.db import DatabaseManager
from darkvoid.database.history import HistoryRepository


class TestHistoryDatabase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.db_path = self.root / "test_history.db"
        self.db = DatabaseManager(self.db_path)
        self.repo = HistoryRepository(self.db)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_record_and_query_history_filters(self) -> None:
        out_ok = self.root / "alpha_Resolve.mov"
        out_ok.write_bytes(b"1234")
        self.repo.record_conversion(
            job_id="job-001",
            original_path=self.root / "alpha.mp4",
            output_path=out_ok,
            file_size=1024,
            duration=5.0,
            conversion_duration=1.2,
            status="Completed",
            source_fingerprint="fp-alpha",
        )
        self.repo.record_conversion(
            job_id="job-002",
            original_path=self.root / "beta.mkv",
            output_path=self.root / "beta_Resolve.mov",
            file_size=2048,
            duration=0.0,
            conversion_duration=0.1,
            status="Failed",
            error_message="Corrupt header",
            source_fingerprint="fp-beta",
        )

        all_recs = self.repo.list_history()
        self.assertEqual(len(all_recs), 2)

        ok_recs = self.repo.list_history(status="Completed")
        self.assertEqual(len(ok_recs), 1)
        self.assertEqual(ok_recs[0].original_filename, "alpha.mp4")

        fail_recs = self.repo.get_failed_records()
        self.assertEqual(len(fail_recs), 1)
        self.assertEqual(fail_recs[0].original_filename, "beta.mkv")

        search_recs = self.repo.list_history(search="alpha")
        self.assertEqual(len(search_recs), 1)

        dup = self.repo.find_completed_duplicate("fp-alpha", self.root / "alpha.mp4")
        self.assertIsNotNone(dup)

    def test_corrupt_database_recovery(self) -> None:
        corrupt_db_path = self.root / "corrupt.db"
        corrupt_db_path.write_bytes(b"THIS IS NOT A SQLITE FILE")
        recovered_db = DatabaseManager(corrupt_db_path)
        repo = HistoryRepository(recovered_db)
        self.assertEqual(repo.list_history(), [])


if __name__ == "__main__":
    unittest.main()
