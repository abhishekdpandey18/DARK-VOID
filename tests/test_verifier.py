"""Tests for FFprobe metadata extraction and post-conversion DNxHR HQ verification."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from darkvoid.core.ffmpeg import build_ffmpeg_command, run_ffmpeg_conversion
from darkvoid.core.ffprobe import probe_media
from darkvoid.core.verifier import OutputVerificationError, verify_converted_output
from tests.helpers import generate_sample_video


class TestVerifier(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_verify_valid_dnxhr_hq_output_with_audio(self) -> None:
        src = generate_sample_video(self.root / "input.mp4", with_audio=True, duration=0.4)
        meta = probe_media(src)
        out = self.root / "input_Resolve.mov"
        cmd = build_ffmpeg_command(src, out, meta)
        run_ffmpeg_conversion(cmd, total_duration=meta.duration)

        report = verify_converted_output(out, meta)
        self.assertTrue(report.verified)
        self.assertTrue(report.container_ok)
        self.assertTrue(report.video_codec_ok)
        self.assertTrue(report.video_profile_ok)
        self.assertTrue(report.audio_codec_ok)

    def test_verify_rejects_non_dnxhr_video(self) -> None:
        src = generate_sample_video(self.root / "plain.mp4", with_audio=True, duration=0.4)
        wrong_mov = generate_sample_video(self.root / "wrong_Resolve.mov", with_audio=True, duration=0.4)
        meta = probe_media(src)
        with self.assertRaises(OutputVerificationError):
            verify_converted_output(wrong_mov, meta)


if __name__ == "__main__":
    unittest.main()
