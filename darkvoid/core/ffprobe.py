"""FFprobe metadata extraction and stream validation."""

from __future__ import annotations

import json
import logging
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from darkvoid.utils.validation import ValidationError, validate_executable, validate_input_file

logger = logging.getLogger("darkvoid.ffprobe")


@dataclass
class MediaMetadata:
    """Structured video and audio stream metadata extracted via FFprobe."""

    filename: str
    filepath: str
    file_size: int
    container_format: str
    duration: float
    bitrate: int
    num_streams: int
    video_codec: str
    video_profile: str
    width: int
    height: int
    frame_rate: str
    fps_float: float
    aspect_ratio: str
    pixel_format: str
    has_audio: bool
    audio_codec: str | None
    audio_sample_rate: int | None
    audio_channels: int | None

    @property
    def resolution(self) -> str:
        if self.width and self.height:
            return f"{self.width}x{self.height}"
        return "N/A"

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["resolution"] = self.resolution
        return data


def _parse_frame_rate(rate_str: str) -> tuple[str, float]:
    if not rate_str or rate_str == "0/0":
        return "N/A", 0.0
    if "/" in rate_str:
        parts = rate_str.split("/", 1)
        try:
            num = float(parts[0])
            den = float(parts[1])
            if den > 0:
                fps = num / den
                return f"{fps:.2f} fps ({rate_str})", fps
        except ValueError:
            pass
    try:
        fps = float(rate_str)
        return f"{fps:.2f} fps", fps
    except ValueError:
        return rate_str, 0.0


def probe_media(
    file_path: Path,
    ffprobe_bin: str = "ffprobe",
    enforce_supported_ext: bool = True,
) -> MediaMetadata:
    """Inspect a media file using FFprobe and validate that it contains a decodable video stream."""
    resolved_bin = validate_executable(ffprobe_bin)
    if enforce_supported_ext:
        resolved_path = validate_input_file(file_path)
    else:
        resolved_path = file_path.expanduser().resolve()
        if not resolved_path.exists() or not resolved_path.is_file():
            raise ValidationError(f"File does not exist: {file_path}")
        if resolved_path.stat().st_size == 0:
            raise ValidationError(f"File is empty (0 bytes): {file_path}")

    cmd = [
        resolved_bin,
        "-v",
        "error",
        "-show_format",
        "-show_streams",
        "-of",
        "json",
        str(resolved_path),
    ]

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
    except subprocess.TimeoutExpired as exc:
        logger.error("FFprobe timed out on %s", resolved_path)
        raise ValidationError(f"FFprobe timed out inspecting '{resolved_path.name}'.") from exc
    except OSError as exc:
        logger.error("Failed to execute FFprobe: %s", exc)
        raise ValidationError(f"Failed to execute FFprobe: {exc}") from exc

    if proc.returncode != 0:
        err_detail = (proc.stderr or "").strip() or "Unrecognized or corrupted media container."
        logger.warning("FFprobe rejected %s: %s", resolved_path, err_detail)
        raise ValidationError(f"Invalid or corrupted media file '{resolved_path.name}': {err_detail}")

    try:
        payload = json.loads(proc.stdout or "{}")
    except json.JSONDecodeError as exc:
        raise ValidationError(f"FFprobe returned malformed JSON for '{resolved_path.name}'.") from exc

    streams = payload.get("streams") or []
    fmt = payload.get("format") or {}

    if not streams:
        raise ValidationError(f"No media streams found in '{resolved_path.name}'.")

    video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
    if not video_stream:
        raise ValidationError(f"No valid video stream found in '{resolved_path.name}'.")

    audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)

    v_codec = str(video_stream.get("codec_name") or "unknown")
    v_profile = str(video_stream.get("profile") or "unknown")
    width = int(video_stream.get("width") or 0)
    height = int(video_stream.get("height") or 0)
    if width <= 0 or height <= 0:
        raise ValidationError(f"Invalid video dimensions ({width}x{height}) in '{resolved_path.name}'.")

    raw_fps = str(video_stream.get("avg_frame_rate") or video_stream.get("r_frame_rate") or "0/0")
    if raw_fps == "0/0":
        raw_fps = str(video_stream.get("r_frame_rate") or "0/0")
    fps_display, fps_float = _parse_frame_rate(raw_fps)

    aspect = str(video_stream.get("display_aspect_ratio") or "N/A")
    pix_fmt = str(video_stream.get("pix_fmt") or "unknown")

    duration_raw = fmt.get("duration") or video_stream.get("duration") or 0.0
    try:
        duration = float(duration_raw)
    except (TypeError, ValueError):
        duration = 0.0

    bitrate_raw = fmt.get("bit_rate") or video_stream.get("bit_rate") or 0
    try:
        bitrate = int(bitrate_raw)
    except (TypeError, ValueError):
        bitrate = 0

    file_size = resolved_path.stat().st_size
    container = str(fmt.get("format_name") or "unknown")

    has_audio = audio_stream is not None
    a_codec = str(audio_stream.get("codec_name")) if audio_stream else None
    a_rate = int(audio_stream["sample_rate"]) if (audio_stream and audio_stream.get("sample_rate")) else None
    a_channels = int(audio_stream["channels"]) if (audio_stream and audio_stream.get("channels")) else None

    return MediaMetadata(
        filename=resolved_path.name,
        filepath=str(resolved_path),
        file_size=file_size,
        container_format=container,
        duration=duration,
        bitrate=bitrate,
        num_streams=len(streams),
        video_codec=v_codec,
        video_profile=v_profile,
        width=width,
        height=height,
        frame_rate=fps_display,
        fps_float=fps_float,
        aspect_ratio=aspect,
        pixel_format=pix_fmt,
        has_audio=has_audio,
        audio_codec=a_codec,
        audio_sample_rate=a_rate,
        audio_channels=a_channels,
    )
