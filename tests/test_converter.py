"""Tests for the core conversion engine, audio-less inputs, original file protection, and cancellation."""

from __future__ import annotations

import hashlib
import tempfile
import threading
import unittest
from pathlib import Path

from darkvoid.core.converter import ConversionEngine
from darkvoid.core.ffmpeg import build_ffmpeg_command
from darkvoid.core.ffprobe import probe_media
from darkvoid.database.db import DatabaseManager
from darkvoid.database.history import HistoryRepository
from darkvoid.utils.files import build_output_path
from darkvoid.utils.paths import AppConfig
from tests.helpers import generate_sample_video


class TestConverterEngine(unittest.TestCase):
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

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_output_naming_preserves_spaces_and_special_chars(self) -> None:
        in_file = self.root / "My Clip (Final) - 2026 [1080p].mkv"
        out_path = build_output_path(in_file, Path(self.cfg.output_dir))
        self.assertEqual(out_path.name, "My Clip (Final) - 2026 [1080p]_Resolve.mov")

    def test_convert_mp4_with_audio_and_protect_original_file(self) -> None:
        src = generate_sample_video(self.root / "sample clip.mp4", with_audio=True, duration=0.4)
        orig_sha256 = hashlib.sha256(src.read_bytes()).hexdigest()

        progress_updates: list[float] = []
        outcome = self.engine.convert_file(
            src,
            progress_callback=lambda p: progress_updates.append(p.percentage),
        )
        self.assertEqual(outcome.status, "Completed")
        self.assertTrue(outcome.output_path.exists())
        self.assertEqual(outcome.output_path.name, "sample clip_Resolve.mov")
        self.assertTrue(len(progress_updates) >= 1)
        self.assertEqual(progress_updates[-1], 100.0)

        # Verify original file is 100% untouched byte-for-byte
        self.assertTrue(src.exists())
        self.assertEqual(hashlib.sha256(src.read_bytes()).hexdigest(), orig_sha256)

        # Verify duplicate detection skips second conversion
        second = self.engine.convert_file(src)
        self.assertEqual(second.status, "Skipped")

        # Verify existing_policy="rename" creates non-conflicting _1.mov when forced
        third = self.engine.convert_file(src, existing_policy="rename", force=True)
        self.assertEqual(third.status, "Completed")
        self.assertEqual(third.output_path.name, "sample clip_Resolve_1.mov")

    def test_convert_video_without_audio_stream(self) -> None:
        src_no_audio = generate_sample_video(self.root / "silent_video.mkv", with_audio=False, duration=0.4)
        meta = probe_media(src_no_audio)
        self.assertFalse(meta.has_audio)

        cmd = build_ffmpeg_command(src_no_audio, self.root / "out.mov", meta)
        self.assertIn("-an", cmd)
        self.assertNotIn("pcm_s16le", cmd)

        outcome = self.engine.convert_file(src_no_audio)
        self.assertEqual(outcome.status, "Completed")
        self.assertFalse(outcome.has_audio)
        self.assertTrue(outcome.output_path.exists())

    def test_corrupted_file_fails_cleanly_without_leaving_temp_files(self) -> None:
        corrupt = self.root / "broken.mp4"
        corrupt.write_bytes(b"NOT_A_VALID_MP4_HEADER_1234567890")
        outcome = self.engine.convert_file(corrupt)
        self.assertEqual(outcome.status, "Failed")
        self.assertFalse(outcome.output_path.exists())
        temp_files = list(Path(self.cfg.output_dir).glob(".darkvoid_tmp_*"))
        self.assertEqual(temp_files, [])

    def test_cancellation_cleans_up_temporary_output(self) -> None:
        src = generate_sample_video(self.root / "cancel_me.avi", with_audio=True, duration=1.0)
        cancel_ev = threading.Event()
        cancel_ev.set()  # Pre-trigger cancellation
        outcome = self.engine.convert_file(src, cancel_event=cancel_ev)
        self.assertEqual(outcome.status, "Cancelled")
        self.assertFalse(outcome.output_path.exists())
        temp_files = list(Path(self.cfg.output_dir).glob(".darkvoid_tmp_*"))
        self.assertEqual(temp_files, [])


if __name__ == "__main__":
    unittest.main()
