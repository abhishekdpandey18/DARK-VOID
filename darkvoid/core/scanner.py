"""Directory and file scanner for batch video discovery."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from darkvoid.utils.validation import (
    ValidationError,
    is_already_resolve_output,
    is_supported_extension,
    validate_input_file,
)

logger = logging.getLogger("darkvoid.scanner")


@dataclass
class ScanResult:
    """Result of scanning input paths for eligible video files."""

    valid_files: list[Path]
    skipped_files: list[tuple[Path, str]]
    invalid_files: list[tuple[Path, str]]


def scan_inputs(
    inputs: Iterable[Path | str],
    recursive: bool = False,
    suffix: str = "_Resolve",
) -> ScanResult:
    """Scan one or more files or directories and return deduplicated eligible video paths."""
    valid: list[Path] = []
    skipped: list[tuple[Path, str]] = []
    invalid: list[tuple[Path, str]] = []
    seen_resolved: set[Path] = set()

    for raw_item in inputs:
        p = Path(raw_item).expanduser()
        if not p.exists():
            invalid.append((p, f"Path does not exist: {p}"))
            continue

        if p.is_file():
            resolved = p.resolve()
            if resolved in seen_resolved:
                skipped.append((resolved, "Duplicate input path in command arguments"))
                continue
            if is_already_resolve_output(resolved, suffix=suffix):
                skipped.append((resolved, "File is already a converted _Resolve.mov output"))
                continue
            try:
                validated = validate_input_file(resolved)
                seen_resolved.add(validated)
                valid.append(validated)
            except ValidationError as exc:
                invalid.append((resolved, str(exc)))

        elif p.is_dir():
            resolved_dir = p.resolve()
            iterator = resolved_dir.rglob("*") if recursive else resolved_dir.iterdir()
            for child in sorted(iterator):
                if not child.is_file():
                    continue
                if child.name.startswith("."):
                    continue
                if not is_supported_extension(child):
                    continue
                resolved_child = child.resolve()
                if resolved_child in seen_resolved:
                    continue
                if is_already_resolve_output(resolved_child, suffix=suffix):
                    skipped.append((resolved_child, "Already a _Resolve.mov output"))
                    continue
                try:
                    validated = validate_input_file(resolved_child)
                    seen_resolved.add(validated)
                    valid.append(validated)
                except ValidationError as exc:
                    invalid.append((resolved_child, str(exc)))
        else:
            invalid.append((p, f"Unsupported filesystem entry: {p}"))

    return ScanResult(valid_files=valid, skipped_files=skipped, invalid_files=invalid)
