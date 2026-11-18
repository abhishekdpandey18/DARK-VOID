"""Strict post-conversion output verification using FFprobe."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from darkvoid.core.ffprobe import MediaMetadata, probe_media
from darkvoid.utils.validation import ValidationError

logger = logging.getLogger("darkvoid.verifier")


class OutputVerificationError(Exception):
    """Raised when a converted output file fails mandatory specification checks."""


@dataclass
class VerificationReport:
    """Detailed verification result for a converted output file."""

    verified: bool
    output_path: str
    file_size: int
    container_ok: bool
    video_codec_ok: bool
    video_profile_ok: bool
    audio_codec_ok: bool
    metadata: MediaMetadata | None = None
    error_message: str = ""


def verify_converted_output(
    output_path: Path,
    source_metadata: MediaMetadata,
    ffprobe_bin: str = "ffprobe",
) -> VerificationReport:
    """Verify that the converted output file strictly matches DNxHR HQ MOV specifications."""
    resolved = output_path.expanduser().resolve()
    if not resolved.exists():
        raise OutputVerificationError(f"Output file was not created: {resolved}")

    size = resolved.stat().st_size
    if size <= 0:
        raise OutputVerificationError(f"Output file is empty (0 bytes): {resolved}")

    try:
        out_meta = probe_media(resolved, ffprobe_bin=ffprobe_bin, enforce_supported_ext=False)
    except ValidationError as exc:
        raise OutputVerificationError(f"FFprobe failed to inspect converted output: {exc}") from exc

    # 1. Container check: QuickTime MOV (ffprobe reports 'mov,mp4,m4a,3gp,3g2,mj2' or 'mov')
    container_tokens = {tok.strip().lower() for tok in out_meta.container_format.split(",")}
    container_ok = "mov" in container_tokens and resolved.suffix.lower() == ".mov"
    if not container_ok:
        raise OutputVerificationError(
            f"Invalid output container '{out_meta.container_format}' (suffix '{resolved.suffix}'); expected QuickTime MOV (.mov)."
        )

    # 2. Video codec check: dnxhd (FFmpeg's codec name for DNxHD / DNxHR)
    video_codec_ok = out_meta.video_codec.lower() == "dnxhd"
    if not video_codec_ok:
        raise OutputVerificationError(
            f"Invalid output video codec '{out_meta.video_codec}'; expected 'dnxhd' (DNxHR)."
        )

    # 3. Video profile check: DNxHR HQ
    norm_profile = out_meta.video_profile.lower().replace("_", " ").strip()
    video_profile_ok = norm_profile == "dnxhr hq"
    if not video_profile_ok:
        raise OutputVerificationError(
            f"Invalid output video profile '{out_meta.video_profile}'; expected 'DNxHR HQ'."
        )

    # 4. Audio codec check: pcm_s16le when source has audio, or no audio when source has no audio
    if source_metadata.has_audio:
        audio_codec_ok = out_meta.has_audio and (out_meta.audio_codec or "").lower() == "pcm_s16le"
        if not audio_codec_ok:
            raise OutputVerificationError(
                f"Invalid output audio codec '{out_meta.audio_codec}'; expected 'pcm_s16le'."
            )
    else:
        audio_codec_ok = not out_meta.has_audio
        if not audio_codec_ok:
            raise OutputVerificationError(
                "Source had no audio stream, but output unexpectedly contains an audio stream."
            )

    logger.info(
        "Output verified successfully: %s (codec=%s, profile=%s, audio=%s, size=%d)",
        resolved.name,
        out_meta.video_codec,
        out_meta.video_profile,
        out_meta.audio_codec or "none",
        size,
    )
    return VerificationReport(
        verified=True,
        output_path=str(resolved),
        file_size=size,
        container_ok=container_ok,
        video_codec_ok=video_codec_ok,
        video_profile_ok=video_profile_ok,
        audio_codec_ok=audio_codec_ok,
        metadata=out_meta,
    )
