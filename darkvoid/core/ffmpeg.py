"""FFmpeg command construction, multi-threaded DNxHR HQ optimization, progress parsing, and cancellation."""

from __future__ import annotations

import logging
import signal
import subprocess
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from darkvoid.core.ffprobe import MediaMetadata
from darkvoid.utils.validation import validate_executable

logger = logging.getLogger("darkvoid.ffmpeg")


@dataclass
class ConversionProgress:
    """Real-time progress state parsed from FFmpeg -progress pipe:1."""

    percentage: float = 0.0
    frame: int = 0
    fps: float = 0.0
    speed: str = "0.0x"
    out_time_seconds: float = 0.0
    elapsed_seconds: float = 0.0
    eta_seconds: float | None = None
    total_size_bytes: int = 0


class ConversionCancelledError(Exception):
    """Raised when an active FFmpeg conversion is cancelled by user or signal."""


class FFmpegConversionError(Exception):
    """Raised when FFmpeg exits with a non-zero status code."""


def build_ffmpeg_command(
    input_path: Path,
    output_path: Path,
    metadata: MediaMetadata,
    ffmpeg_bin: str = "ffmpeg",
) -> list[str]:
    """Construct the mandatory DNxHR HQ QuickTime MOV FFmpeg command with multi-core thread optimization.

    Baseline specification:
        ffmpeg -i INPUT -c:v dnxhd -profile:v dnxhr_hq -c:a pcm_s16le OUTPUT
    Omits audio encoding (-an) when the input video has no audio stream.
    """
    resolved_ffmpeg = validate_executable(ffmpeg_bin)
    cmd: list[str] = [
        resolved_ffmpeg,
        "-nostdin",
        "-y",
        "-loglevel",
        "error",
        "-progress",
        "pipe:1",
        "-threads",
        "0",
        "-i",
        str(input_path.resolve()),
        "-map",
        "0:v:0",
        "-c:v",
        "dnxhd",
        "-profile:v",
        "dnxhr_hq",
        "-pix_fmt",
        "yuv422p",
    ]

    if metadata.has_audio:
        cmd.extend(["-map", "0:a:0?", "-c:a", "pcm_s16le"])
    else:
        cmd.append("-an")

    cmd.extend(["-movflags", "+faststart", "-f", "mov", str(output_path.resolve())])
    return cmd


def _parse_out_time_us(value: str) -> float:
    try:
        us = int(value.strip())
        return max(0.0, us / 1_000_000.0)
    except ValueError:
        return 0.0


def _parse_out_time_str(value: str) -> float:
    parts = value.strip().split(":")
    if len(parts) != 3:
        return 0.0
    try:
        h = float(parts[0])
        m = float(parts[1])
        s = float(parts[2])
        return max(0.0, h * 3600.0 + m * 60.0 + s)
    except ValueError:
        return 0.0


def run_ffmpeg_conversion(
    cmd: list[str],
    total_duration: float,
    progress_callback: Callable[[ConversionProgress], None] | None = None,
    cancel_event: threading.Event | None = None,
) -> ConversionProgress:
    """Execute FFmpeg safely without shell=True, streaming real-time progress from stdout."""
    start_time = time.monotonic()
    stderr_lines: list[str] = []

    if cancel_event and cancel_event.is_set():
        raise ConversionCancelledError("Conversion cancelled before process start.")

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        stdin=subprocess.DEVNULL,
        text=True,
        bufsize=1,
    )

    def _drain_stderr() -> None:
        assert proc.stderr is not None
        for line in proc.stderr:
            stderr_lines.append(line.rstrip())

    stderr_thread = threading.Thread(target=_drain_stderr, daemon=True)
    stderr_thread.start()

    state = ConversionProgress()
    current_block: dict[str, str] = {}

    try:
        assert proc.stdout is not None
        for raw_line in proc.stdout:
            if cancel_event and cancel_event.is_set():
                _terminate_process(proc)
                raise ConversionCancelledError("Conversion cancelled by user.")

            line = raw_line.strip()
            if not line or "=" not in line:
                continue
            key, val = line.split("=", 1)
            key = key.strip()
            val = val.strip()
            current_block[key] = val

            if key == "progress":
                elapsed = time.monotonic() - start_time
                frame_str = current_block.get("frame", "0") or "0"
                frame = int(frame_str) if frame_str.isdigit() else state.frame
                try:
                    fps = float(current_block.get("fps", "0.0") or 0.0)
                except ValueError:
                    fps = state.fps
                speed = current_block.get("speed", state.speed) or "0.0x"
                try:
                    total_size = int(current_block.get("total_size", "0") or 0)
                except ValueError:
                    total_size = state.total_size_bytes

                out_sec = 0.0
                if "out_time_us" in current_block and current_block["out_time_us"].lstrip("-").isdigit():
                    out_sec = _parse_out_time_us(current_block["out_time_us"])
                elif "out_time_ms" in current_block and current_block["out_time_ms"].lstrip("-").isdigit():
                    out_sec = _parse_out_time_us(current_block["out_time_ms"])
                elif "out_time" in current_block:
                    out_sec = _parse_out_time_str(current_block["out_time"])

                pct = 0.0
                eta: float | None = None
                if total_duration > 0:
                    pct = min(99.9, max(0.0, (out_sec / total_duration) * 100.0))
                    if pct > 0.5 and elapsed > 0.1:
                        eta = max(0.0, (elapsed * (100.0 - pct)) / pct)
                if val == "end":
                    pct = 100.0
                    eta = 0.0

                state = ConversionProgress(
                    percentage=pct,
                    frame=frame,
                    fps=fps,
                    speed=speed,
                    out_time_seconds=out_sec,
                    elapsed_seconds=elapsed,
                    eta_seconds=eta,
                    total_size_bytes=total_size,
                )
                if progress_callback:
                    progress_callback(state)
                current_block.clear()

        proc.wait()
        stderr_thread.join(timeout=2.0)

        if cancel_event and cancel_event.is_set():
            raise ConversionCancelledError("Conversion cancelled by user.")

        if proc.returncode != 0:
            err_msg = "\n".join(stderr_lines[-15:]).strip() or f"FFmpeg exited with code {proc.returncode}"
            logger.error("FFmpeg failed (code %s): %s", proc.returncode, err_msg)
            raise FFmpegConversionError(err_msg)

        state.percentage = 100.0
        state.elapsed_seconds = time.monotonic() - start_time
        state.eta_seconds = 0.0
        if progress_callback:
            progress_callback(state)
        return state

    except KeyboardInterrupt as exc:
        _terminate_process(proc)
        raise ConversionCancelledError("Conversion interrupted by KeyboardInterrupt (Ctrl+C).") from exc
    finally:
        if proc.poll() is None:
            _terminate_process(proc)
        try:
            if proc.stdout:
                proc.stdout.close()
        except OSError:
            pass
        try:
            if proc.stderr:
                proc.stderr.close()
        except OSError:
            pass


def _terminate_process(proc: subprocess.Popen[str]) -> None:
    """Safely terminate an active FFmpeg process without leaving orphans."""
    try:
        if proc.poll() is None:
            proc.send_signal(signal.SIGTERM)
            try:
                proc.wait(timeout=3.0)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=2.0)
    except OSError:
        pass
