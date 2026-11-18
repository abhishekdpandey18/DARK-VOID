"""Formatting helpers for human-readable sizes, durations, bitrates, and timestamps."""

from __future__ import annotations


def format_size(num_bytes: int | float | None) -> str:
    """Format byte count into human-readable string."""
    if num_bytes is None or num_bytes < 0:
        return "N/A"
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024.0 or unit == "TB":
            return f"{size:.2f} {unit}" if unit != "B" else f"{int(size)} B"
        size /= 1024.0
    return f"{size:.2f} TB"


def format_duration(seconds: float | None) -> str:
    """Format seconds into HH:MM:SS.ms string."""
    if seconds is None or seconds < 0:
        return "N/A"
    total_secs = int(seconds)
    millis = int(round((seconds - total_secs) * 100))
    hours, rem = divmod(total_secs, 3600)
    minutes, secs = divmod(rem, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:02d}"


def format_bitrate(bits_per_sec: int | float | None) -> str:
    """Format bits per second into kbps or Mbps."""
    if not bits_per_sec or bits_per_sec <= 0:
        return "N/A"
    bps = float(bits_per_sec)
    if bps >= 1_000_000:
        return f"{bps / 1_000_000:.2f} Mbps"
    if bps >= 1_000:
        return f"{bps / 1_000:.1f} kbps"
    return f"{int(bps)} bps"
