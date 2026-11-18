"""Security and cross-platform input/executable validation utilities for DARK VOID."""

from __future__ import annotations

import os
import shutil
import sys
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


def resolve_executable_path(executable: str) -> str | None:
    """Locate an executable (ffmpeg/ffprobe) across Linux, macOS, and Windows (including Winget/Choco/Scoop)."""
    if "\x00" in executable:
        return None
    found = shutil.which(executable)
    if found:
        return str(Path(found).resolve())

    cand = Path(executable).expanduser()
    if cand.is_file() and os.access(cand, os.X_OK):
        return str(cand.resolve())

    # On Windows, also check .exe extension and common Winget / Scoop / Chocolatey / C:\ffmpeg locations
    if os.name == "nt" or sys.platform.startswith("win"):
        exe_name = executable if executable.lower().endswith(".exe") else f"{executable}.exe"
        cand_exe = Path(exe_name).expanduser()
        if cand_exe.is_file():
            return str(cand_exe.resolve())

        win_candidates = [
            Path("C:/ffmpeg/bin") / exe_name,
            Path("C:/Program Files/ffmpeg/bin") / exe_name,
            Path.home() / "scoop" / "shims" / exe_name,
            Path("C:/ProgramData/chocolatey/bin") / exe_name,
            Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData/Local")))
            / "Microsoft"
            / "WinGet"
            / "Links"
            / exe_name,
        ]
        for wc in win_candidates:
            if wc.is_file():
                return str(wc.resolve())

    return None


def validate_executable(executable: str) -> str:
    """Validate that an external binary (ffmpeg/ffprobe) exists and is executable."""
    if "\x00" in executable:
        raise ValidationError("Executable path contains null byte.")
    resolved = resolve_executable_path(executable)
    if not resolved:
        raise ValidationError(f"Required executable not found or not executable: '{executable}'")
    return resolved


def check_disk_space(target_dir: Path, required_bytes: int) -> tuple[bool, int]:
    """Verify whether target_dir has enough free bytes for conversion."""
    target_dir.mkdir(parents=True, exist_ok=True)
    usage = shutil.disk_usage(target_dir)
    return usage.free >= required_bytes, usage.free
