"""Tests for folder monitoring, file stability detection, and duplicate event suppression."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from darkvoid.core.converter import ConversionEngine
from darkvoid.core.queue import JobQueueManager
from darkvoid.core.watcher import FolderWatcher
from darkvoid.database.db import DatabaseManager
from darkvoid.database.history import HistoryRepository
from darkvoid.utils.files import wait_for_file_stability
from darkvoid.utils.paths import AppConfig
from tests.helpers import generate_sample_video


class TestFolderWatcher(unittest.TestCase):
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
            stability_wait_seconds=0.1,
            stability_checks=1,
            poll_interval_seconds=0.1,
        )
        self.cfg.ensure_directories()
        self.db = DatabaseManager(self.cfg.database_path)
        self.history = HistoryRepository(self.db)
        self.engine = ConversionEngine(self.cfg, self.history)
        self.qm = JobQueueManager(self.db, self.engine)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_file_stability_detection_and_automated_watch_conversion(self) -> None:
        incoming = Path(self.cfg.input_dir)
        converted = Path(self.cfg.output_dir)
        vid = generate_sample_video(incoming / "incoming_clip.mov", duration=0.3)

        self.assertTrue(wait_for_file_stability(vid, wait_seconds=0.1, checks=2))

        events: list[tuple[str, Path]] = []
        watcher = FolderWatcher(
            watch_dir=incoming,
            output_dir=converted,
            queue_manager=self.qm,
            stability_wait=0.1,
            stability_checks=1,
            poll_interval=0.1,
            on_event_callback=lambda et, p: events.append((et, p)),
        )

        outcomes = watcher.scan_once()
        self.assertEqual(len(outcomes), 1)
        self.assertEqual(outcomes[0].status, "Completed")
        self.assertTrue((converted / "incoming_clip_Resolve.mov").exists())

        # Second scan must not re-process the same unchanged file
        outcomes_repeat = watcher.scan_once()
        self.assertEqual(len(outcomes_repeat), 0)


if __name__ == "__main__":
    unittest.main()
