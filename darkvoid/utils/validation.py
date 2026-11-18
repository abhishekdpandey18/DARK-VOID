"""Security and input validation utilities for DARK VOID."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

SUPPORTED_EXTENSIONS: frozenset[str] = frozenset({".mp4", ".mov", ".mkv", ".avi"})


class ValidationError(Exception):
    """Raised when an input file, path, or executable fails validation."""


def is_supported_extension(path: Path) -> bool:
    """Check whether path has a supported case-insensitive video extension."""
    return path.suffix.lower() in SUPPORTED_EXTENSIONS


def is_already_resolve_output(path: Path, suffix: str = "_Resolve") -> bool:
    """Return True if the file already ends with _Resolve.mov to prevent re-conversion loops."""
    return (
        path.suffix.lower() == ".mov"
        and path.stem.endswith(suffix)
    )


def validate_input_file(path: Path) -> Path:
    """Validate that an input video path exists, is a regular file, is readable, and has a valid extension."""
    if "\x00" in str(path):
        raise ValidationError("Invalid path containing null bytes.")

    resolved = path.expanduser().resolve()
    if not resolved.exists():
        raise ValidationError(f"Input file does not exist: {path}")
    if resolved.is_dir():
        raise ValidationError(f"Path is a directory, not a file: {path}")
    if not resolved.is_file():
        raise ValidationError(f"Path is not a regular file: {path}")
    if not os.access(resolved, os.R_OK):
        raise ValidationError(f"Permission denied reading input file: {path}")
    if resolved.stat().st_size == 0:
        raise ValidationError(f"Input file is empty (0 bytes): {path}")
    if not is_supported_extension(resolved):
        allowed = ", ".join(sorted(ext.upper().lstrip(".") for ext in SUPPORTED_EXTENSIONS))
        raise ValidationError(
            f"Unsupported file extension '{resolved.suffix or '(none)'}' for '{resolved.name}'. "
            f"Supported formats: {allowed}"
        )
    return resolved


def validate_executable(executable: str) -> str:
    """Validate that an external binary (ffmpeg/ffprobe) exists and is executable."""
    if "\x00" in executable:
        raise ValidationError("Executable path contains null byte.")
    found = shutil.which(executable)
    if not found:
        cand = Path(executable).expanduser()
        if cand.is_file() and os.access(cand, os.X_OK):
            return str(cand.resolve())
        raise ValidationError(f"Required executable not found or not executable: '{executable}'")
    return str(Path(found).resolve())


def check_disk_space(target_dir: Path, required_bytes: int) -> tuple[bool, int]:
    """Verify whether target_dir has enough free bytes for conversion."""
    target_dir.mkdir(parents=True, exist_ok=True)
    usage = shutil.disk_usage(target_dir)
    return usage.free >= required_bytes, usage.free
