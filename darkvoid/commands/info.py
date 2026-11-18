"""Implementation of `darkvoid info` command."""

from __future__ import annotations

import json
from pathlib import Path
import click
from rich.console import Console

from darkvoid.core.ffprobe import probe_media
from darkvoid.ui.tables import build_media_info_table
from darkvoid.utils.paths import AppConfig
from darkvoid.utils.validation import ValidationError


def execute_info_command(
    video_path: str | Path,
    config: AppConfig,
    console: Console,
    *,
    json_output: bool = False,
) -> int:
    """Extract and display comprehensive video metadata via FFprobe."""
    try:
        meta = probe_media(Path(video_path), ffprobe_bin=config.ffprobe_path, enforce_supported_ext=False)
    except ValidationError as exc:
        if json_output:
            click.echo(json.dumps({"status": "error", "error": str(exc)}, indent=2))
        else:
            console.print(f"[status.error]ERROR:[/status.error] {exc}")
        return 1

    if json_output:
        click.echo(json.dumps(meta.to_dict(), indent=2))
    else:
        console.print(build_media_info_table(meta))
    return 0
