"""Rich table builders for metadata, queue jobs, history, config, and diagnostics."""

from __future__ import annotations

from typing import Sequence
from rich import box
from rich.table import Table

from darkvoid.core.ffprobe import MediaMetadata
from darkvoid.core.queue import QueueJob
from darkvoid.database.history import HistoryRecord
from darkvoid.utils.formatting import format_bitrate, format_duration, format_size


def format_status_badge(status: str) -> str:
    """Format a status string with cyberpunk terminal color tags."""
    s = status.lower()
    if s in {"completed", "ok", "pass", "ready"}:
        return f"[status.success]{status}[/status.success]"
    if s in {"converting", "scanning", "active"}:
        return f"[status.info]{status}[/status.info]"
    if s in {"pending", "skipped", "warning", "dryrun"}:
        return f"[status.warning]{status}[/status.warning]"
    if s in {"failed", "error", "cancelled", "missing"}:
        return f"[status.error]{status}[/status.error]"
    return status


def build_media_info_table(meta: MediaMetadata) -> Table:
    """Build a Rich table displaying FFprobe metadata for a video file."""
    table = Table(
        title=f"[brand.primary]MEDIA METADATA :: {meta.filename}[/brand.primary]",
        box=box.SIMPLE_HEAVY,
        border_style="border.cyber",
        header_style="table.header",
        expand=False,
    )
    table.add_column("Property", style="brand.accent", no_wrap=True)
    table.add_column("Value", style="white")

    table.add_row("Filename", meta.filename)
    table.add_row("File Path", meta.filepath)
    table.add_row("File Size", format_size(meta.file_size))
    table.add_row("Container", meta.container_format)
    table.add_row("Duration", format_duration(meta.duration))
    table.add_row("Bitrate", format_bitrate(meta.bitrate))
    table.add_row("Total Streams", str(meta.num_streams))
    table.add_row("Resolution", meta.resolution)
    table.add_row("Aspect Ratio", meta.aspect_ratio)
    table.add_row("Frame Rate", meta.frame_rate)
    table.add_row("Video Codec", f"{meta.video_codec} ({meta.video_profile})")
    table.add_row("Pixel Format", meta.pixel_format)
    if meta.has_audio:
        audio_desc = f"{meta.audio_codec} | {meta.audio_sample_rate or 'N/A'} Hz | {meta.audio_channels or 'N/A'} ch"
    else:
        audio_desc = "None (Video-only stream)"
    table.add_row("Audio Codec", audio_desc)
    return table


def build_queue_table(jobs: Sequence[QueueJob]) -> Table:
    """Build a Rich table displaying conversion queue entries."""
    table = Table(
        title="[brand.primary]DARK VOID :: CONVERSION QUEUE[/brand.primary]",
        box=box.SIMPLE_HEAVY,
        border_style="border.cyber",
        header_style="table.header",
    )
    table.add_column("Job ID", style="brand.accent", no_wrap=True)
    table.add_column("Filename", style="white")
    table.add_column("Status", no_wrap=True)
    table.add_column("Progress", justify="right", style="cyan")
    table.add_column("Size", justify="right", style="muted")
    table.add_column("Input Location", style="muted", overflow="fold")
    table.add_column("Output Location", style="muted", overflow="fold")

    for job in jobs:
        from pathlib import Path
        fname = Path(job.input_path).name
        table.add_row(
            job.job_id,
            fname,
            format_status_badge(job.status),
            f"{job.progress:.1f}%",
            format_size(job.file_size),
            job.input_path,
            job.output_path,
        )
    return table


def build_history_table(records: Sequence[HistoryRecord]) -> Table:
    """Build a Rich table displaying persistent conversion history."""
    table = Table(
        title="[brand.primary]DARK VOID :: CONVERSION HISTORY[/brand.primary]",
        box=box.SIMPLE_HEAVY,
        border_style="border.cyber",
        header_style="table.header",
    )
    table.add_column("ID", justify="right", style="muted", no_wrap=True)
    table.add_column("Job ID", style="brand.accent", no_wrap=True)
    table.add_column("Source File", style="white")
    table.add_column("Output File", style="cyan")
    table.add_column("Status", no_wrap=True)
    table.add_column("Size", justify="right")
    table.add_column("Duration", justify="right")
    table.add_column("Conv. Time", justify="right")
    table.add_column("Timestamp", style="muted")

    for rec in records:
        table.add_row(
            str(rec.id or ""),
            rec.job_id,
            rec.original_filename,
            rec.output_filename,
            format_status_badge(rec.status),
            format_size(rec.file_size),
            format_duration(rec.duration),
            f"{rec.conversion_duration:.2f}s",
            rec.conversion_timestamp,
        )
    return table
