"""Test helpers for generating real sample videos via FFmpeg in temporary directories."""

from __future__ import annotations

import subprocess
from pathlib import Path


def generate_sample_video(
    target_path: Path,
    *,
    with_audio: bool = True,
    duration: float = 0.5,
    width: int = 320,
    height: int = 240,
    fps: int = 24,
) -> Path:
    """Generate a tiny, valid synthetic video file using FFmpeg lavfi sources."""
    target_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg",
        "-nostdin",
        "-y",
        "-loglevel",
        "error",
        "-f",
        "lavfi",
        "-i",
        f"testsrc=duration={duration}:size={width}x{height}:rate={fps}",
    ]
    if with_audio:
        cmd.extend([
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency=440:duration={duration}:sample_rate=48000",
        ])

    ext = target_path.suffix.lower()
    if ext == ".avi":
        cmd.extend(["-c:v", "mpeg4", "-pix_fmt", "yuv420p"])
        if with_audio:
            cmd.extend(["-c:a", "pcm_s16le"])
    else:
        cmd.extend(["-c:v", "mpeg4", "-pix_fmt", "yuv420p"])
        if with_audio:
            cmd.extend(["-c:a", "aac", "-b:a", "64k"])

    cmd.append(str(target_path))
    subprocess.run(cmd, check=True, capture_output=True)
    return target_path
