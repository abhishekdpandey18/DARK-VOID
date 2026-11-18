"""Core modular conversion engine independent of CLI presentation."""

from __future__ import annotations

import logging
import os
import shutil
import threading
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from darkvoid.core.ffmpeg import (
    ConversionCancelledError,
    ConversionProgress,
    FFmpegConversionError,
    build_ffmpeg_command,
    run_ffmpeg_conversion,
)
from darkvoid.core.ffprobe import MediaMetadata, probe_media
from darkvoid.core.verifier import OutputVerificationError, VerificationReport, verify_converted_output
from darkvoid.database.history import HistoryRepository
from darkvoid.utils.files import (
    build_output_path,
    build_temp_output_path,
    compute_fast_file_fingerprint,
    resolve_non_conflicting_output_path,
    safe_remove,
)
from darkvoid.utils.paths import AppConfig
from darkvoid.utils.validation import ValidationError, check_disk_space, validate_input_file

logger = logging.getLogger("darkvoid.converter")


@dataclass
class ConversionOutcome:
    """Complete result of a single video conversion operation."""

    job_id: str
    status: str  # Completed | Failed | Skipped | Cancelled | DryRun
    input_path: Path
    output_path: Path
    file_size: int
    output_size: int
    duration_seconds: float
    elapsed_seconds: float
    has_audio: bool
    message: str
    command: list[str]
    source_metadata: MediaMetadata | None = None
    verification: VerificationReport | None = None


class ConversionEngine:
    """Orchestrates input validation, duplicate detection, FFmpeg execution, verification, and history."""

    def __init__(self, config: AppConfig, history_repo: HistoryRepository) -> None:
        self.config = config
        self.history = history_repo

    def convert_file(
        self,
        input_path: Path,
        output_dir: Path | None = None,
        *,
        job_id: str | None = None,
        existing_policy: str | None = None,
        force: bool = False,
        dry_run: bool = False,
        progress_callback: Callable[[ConversionProgress], None] | None = None,
        cancel_event: threading.Event | None = None,
    ) -> ConversionOutcome:
        """Convert a single video file safely into DNxHR HQ QuickTime MOV."""
        jid = job_id or f"job-{uuid.uuid4().hex[:8]}"
        start_clock = time.monotonic()
        policy = (existing_policy or self.config.existing_output_policy).lower()
        target_out_dir = (output_dir or Path(self.config.output_dir)).expanduser().resolve()
        target_out_dir.mkdir(parents=True, exist_ok=True)

        # 1. Validate input file & protect original
        try:
            validated_in = validate_input_file(input_path)
            orig_stat = validated_in.stat()
        except ValidationError as exc:
            logger.error("[%s] Input validation failed for %s: %s", jid, input_path, exc)
            planned_out = build_output_path(Path(input_path), target_out_dir, self.config.output_suffix)
            self._record_safe(
                job_id=jid,
                original_path=Path(input_path),
                output_path=planned_out,
                file_size=0,
                duration=0.0,
                conversion_duration=time.monotonic() - start_clock,
                status="Failed",
                has_audio=False,
                error_message=str(exc),
            )
            return ConversionOutcome(
                job_id=jid,
                status="Failed",
                input_path=Path(input_path),
                output_path=planned_out,
                file_size=0,
                output_size=0,
                duration_seconds=0.0,
                elapsed_seconds=time.monotonic() - start_clock,
                has_audio=False,
                message=str(exc),
                command=[],
            )

        planned_out = build_output_path(
            validated_in,
            target_out_dir,
            suffix=self.config.output_suffix,
            extension=self.config.output_extension,
        )

        # 2. Extract metadata via FFprobe
        try:
            meta = probe_media(validated_in, ffprobe_bin=self.config.ffprobe_path)
        except ValidationError as exc:
            logger.error("[%s] FFprobe validation failed for %s: %s", jid, validated_in, exc)
            self._record_safe(
                job_id=jid,
                original_path=validated_in,
                output_path=planned_out,
                file_size=orig_stat.st_size,
                duration=0.0,
                conversion_duration=time.monotonic() - start_clock,
                status="Failed",
                has_audio=False,
                error_message=str(exc),
            )
            return ConversionOutcome(
                job_id=jid,
                status="Failed",
                input_path=validated_in,
                output_path=planned_out,
                file_size=orig_stat.st_size,
                output_size=0,
                duration_seconds=0.0,
                elapsed_seconds=time.monotonic() - start_clock,
                has_audio=False,
                message=str(exc),
                command=[],
            )

        # 3. Compute fast fingerprint and check duplicate history / existing output
        fingerprint = compute_fast_file_fingerprint(validated_in)
        if not force:
            prev = self.history.find_completed_duplicate(fingerprint, validated_in)
            if prev is not None and policy == "skip":
                msg = f"Skipped duplicate: already converted to '{Path(prev.output_path).name}' (job {prev.job_id})."
                logger.info("[%s] %s", jid, msg)
                return ConversionOutcome(
                    job_id=jid,
                    status="Skipped",
                    input_path=validated_in,
                    output_path=Path(prev.output_path),
                    file_size=orig_stat.st_size,
                    output_size=Path(prev.output_path).stat().st_size,
                    duration_seconds=meta.duration,
                    elapsed_seconds=time.monotonic() - start_clock,
                    has_audio=meta.has_audio,
                    message=msg,
                    command=[],
                    source_metadata=meta,
                )

        if planned_out.exists():
            if policy == "skip" and not force:
                msg = f"Skipped existing output file: '{planned_out.name}' already exists."
                logger.info("[%s] %s", jid, msg)
                return ConversionOutcome(
                    job_id=jid,
                    status="Skipped",
                    input_path=validated_in,
                    output_path=planned_out,
                    file_size=orig_stat.st_size,
                    output_size=planned_out.stat().st_size,
                    duration_seconds=meta.duration,
                    elapsed_seconds=time.monotonic() - start_clock,
                    has_audio=meta.has_audio,
                    message=msg,
                    command=[],
                    source_metadata=meta,
                )
            elif policy == "fail" and not force:
                msg = f"Output file already exists and policy is 'fail': {planned_out}"
                logger.warning("[%s] %s", jid, msg)
                return ConversionOutcome(
                    job_id=jid,
                    status="Failed",
                    input_path=validated_in,
                    output_path=planned_out,
                    file_size=orig_stat.st_size,
                    output_size=0,
                    duration_seconds=meta.duration,
                    elapsed_seconds=time.monotonic() - start_clock,
                    has_audio=meta.has_audio,
                    message=msg,
                    command=[],
                    source_metadata=meta,
                )
            else:
                # Never silently overwrite an existing converted output; allocate a safe suffixed name
                planned_out = resolve_non_conflicting_output_path(planned_out)

        # 4. Prepare temporary output file in destination directory for atomic move
        temp_out = build_temp_output_path(planned_out, temp_dir=target_out_dir)
        cmd = build_ffmpeg_command(
            validated_in,
            temp_out,
            meta,
            ffmpeg_bin=self.config.ffmpeg_path,
        )

        if dry_run:
            msg = "Dry-run validated input and generated FFmpeg command without writing files."
            logger.info("[%s] Dry-run for %s -> %s", jid, validated_in, planned_out)
            return ConversionOutcome(
                job_id=jid,
                status="DryRun",
                input_path=validated_in,
                output_path=planned_out,
                file_size=orig_stat.st_size,
                output_size=0,
                duration_seconds=meta.duration,
                elapsed_seconds=time.monotonic() - start_clock,
                has_audio=meta.has_audio,
                message=msg,
                command=cmd,
                source_metadata=meta,
            )

        # 5. Check disk space before running FFmpeg (require at least 2x input size or 10MB minimum)
        min_required = max(orig_stat.st_size * 2, 10 * 1024 * 1024)
        has_space, free_bytes = check_disk_space(target_out_dir, min_required)
        if not has_space:
            msg = f"Insufficient disk space in {target_out_dir}: {free_bytes} bytes free."
            logger.error("[%s] %s", jid, msg)
            return ConversionOutcome(
                job_id=jid,
                status="Failed",
                input_path=validated_in,
                output_path=planned_out,
                file_size=orig_stat.st_size,
                output_size=0,
                duration_seconds=meta.duration,
                elapsed_seconds=time.monotonic() - start_clock,
                has_audio=meta.has_audio,
                message=msg,
                command=cmd,
                source_metadata=meta,
            )

        # 6. Execute FFmpeg conversion and verify output
        logger.info("[%s] Starting conversion: %s -> %s", jid, validated_in.name, planned_out.name)
        try:
            run_ffmpeg_conversion(
                cmd,
                total_duration=meta.duration,
                progress_callback=progress_callback,
                cancel_event=cancel_event,
            )
            verification = verify_converted_output(
                temp_out,
                source_metadata=meta,
                ffprobe_bin=self.config.ffprobe_path,
            )
            # Atomic move in destination filesystem
            if planned_out.exists():
                planned_out = resolve_non_conflicting_output_path(planned_out)
            os.replace(str(temp_out), str(planned_out))
            elapsed = time.monotonic() - start_clock
            out_size = planned_out.stat().st_size

            # Verify original file remained untouched
            post_stat = validated_in.stat()
            if post_stat.st_size != orig_stat.st_size:
                logger.critical("Original file size changed unexpectedly: %s", validated_in)

            audio_note = "PCM S16LE audio" if meta.has_audio else "no audio stream (video-only)"
            msg = f"Converted to DNxHR HQ MOV ({audio_note}) and verified via FFprobe."
            self._record_safe(
                job_id=jid,
                original_path=validated_in,
                output_path=planned_out,
                file_size=orig_stat.st_size,
                duration=meta.duration,
                conversion_duration=elapsed,
                status="Completed",
                has_audio=meta.has_audio,
                error_message="",
                source_fingerprint=fingerprint,
                source_mtime_ns=orig_stat.st_mtime_ns,
            )
            logger.info("[%s] Conversion succeeded in %.2fs: %s", jid, elapsed, planned_out)
            return ConversionOutcome(
                job_id=jid,
                status="Completed",
                input_path=validated_in,
                output_path=planned_out,
                file_size=orig_stat.st_size,
                output_size=out_size,
                duration_seconds=meta.duration,
                elapsed_seconds=elapsed,
                has_audio=meta.has_audio,
                message=msg,
                command=cmd,
                source_metadata=meta,
                verification=verification,
            )

        except ConversionCancelledError as exc:
            safe_remove(temp_out)
            elapsed = time.monotonic() - start_clock
            logger.warning("[%s] Conversion cancelled: %s", jid, validated_in.name)
            self._record_safe(
                job_id=jid,
                original_path=validated_in,
                output_path=planned_out,
                file_size=orig_stat.st_size,
                duration=meta.duration,
                conversion_duration=elapsed,
                status="Cancelled",
                has_audio=meta.has_audio,
                error_message=str(exc),
                source_fingerprint=fingerprint,
                source_mtime_ns=orig_stat.st_mtime_ns,
            )
            return ConversionOutcome(
                job_id=jid,
                status="Cancelled",
                input_path=validated_in,
                output_path=planned_out,
                file_size=orig_stat.st_size,
                output_size=0,
                duration_seconds=meta.duration,
                elapsed_seconds=elapsed,
                has_audio=meta.has_audio,
                message=str(exc),
                command=cmd,
                source_metadata=meta,
            )

        except (FFmpegConversionError, OutputVerificationError, OSError) as exc:
            safe_remove(temp_out)
            elapsed = time.monotonic() - start_clock
            logger.error("[%s] Conversion failed for %s: %s", jid, validated_in.name, exc)
            self._record_safe(
                job_id=jid,
                original_path=validated_in,
                output_path=planned_out,
                file_size=orig_stat.st_size,
                duration=meta.duration,
                conversion_duration=elapsed,
                status="Failed",
                has_audio=meta.has_audio,
                error_message=str(exc),
                source_fingerprint=fingerprint,
                source_mtime_ns=orig_stat.st_mtime_ns,
            )
            return ConversionOutcome(
                job_id=jid,
                status="Failed",
                input_path=validated_in,
                output_path=planned_out,
                file_size=orig_stat.st_size,
                output_size=0,
                duration_seconds=meta.duration,
                elapsed_seconds=elapsed,
                has_audio=meta.has_audio,
                message=str(exc),
                command=cmd,
                source_metadata=meta,
            )

    def _record_safe(self, **kwargs: object) -> None:
        try:
            self.history.record_conversion(**kwargs)  # type: ignore[arg-type]
        except Exception as exc:
            logger.error("Failed to write conversion history to SQLite: %s", exc)
