"""Unit and integration tests for input file validation and directory scanning."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from darkvoid.core.scanner import scan_inputs
from darkvoid.utils.validation import ValidationError, is_supported_extension, validate_input_file
from tests.helpers import generate_sample_video


class TestScannerAndValidation(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_supported_extensions_case_insensitive(self) -> None:
        for ext in [".mp4", ".MP4", ".mov", ".MOV", ".mkv", ".MKV", ".avi", ".AVI"]:
            self.assertTrue(is_supported_extension(Path(f"sample{ext}")))
        for bad in [".wmv", ".flv", ".txt", ".mp3", ""]:
            self.assertFalse(is_supported_extension(Path(f"sample{bad}")))

    def test_validate_input_file_rejects_missing_empty_and_unsupported(self) -> None:
        with self.assertRaises(ValidationError):
            validate_input_file(self.root / "nonexistent.mp4")

        empty_mp4 = self.root / "empty.mp4"
        empty_mp4.write_bytes(b"")
        with self.assertRaises(ValidationError):
            validate_input_file(empty_mp4)

        bad_ext = self.root / "notes.txt"
        bad_ext.write_text("hello", encoding="utf-8")
        with self.assertRaises(ValidationError):
            validate_input_file(bad_ext)

    def test_scan_directory_recursive_and_skip_resolve_outputs(self) -> None:
        v1 = generate_sample_video(self.root / "clip1.mp4", duration=0.3)
        sub = self.root / "nested"
        v2 = generate_sample_video(sub / "clip2.MKV", duration=0.3)
        already = generate_sample_video(self.root / "clip1_Resolve.mov", duration=0.3)
        (self.root / "ignore.txt").write_text("not a video", encoding="utf-8")

        non_rec = scan_inputs([self.root], recursive=False)
        self.assertEqual(non_rec.valid_files, [v1.resolve()])
        self.assertEqual(len(non_rec.skipped_files), 1)
        self.assertEqual(non_rec.skipped_files[0][0], already.resolve())

        rec = scan_inputs([self.root], recursive=True)
        self.assertEqual(set(rec.valid_files), {v1.resolve(), v2.resolve()})


if __name__ == "__main__":
    unittest.main()
