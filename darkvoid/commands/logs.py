"""Implementation of `darkvoid logs` command."""

from __future__ import annotations

from pathlib import Path
from rich.console import Console
from rich.panel import Panel

from darkvoid.utils.paths import AppConfig


def execute_logs_command(
    config: AppConfig,
    console: Console,
    *,
    lines: int = 50,
    level: str | None = None,
    search: str | None = None,
) -> int:
    """Display recent DARK VOID application logs with optional level and keyword filtering."""
    log_file = Path(config.log_dir).expanduser().resolve() / "darkvoid.log"
    if not log_file.exists():
        console.print(f"[status.info]No log file exists yet at {log_file}[/status.info]")
        return 0

    raw_lines = log_file.read_text(encoding="utf-8", errors="replace").splitlines()
    filtered = raw_lines
    if level:
        lvl_upper = f"| {level.upper()}"
        filtered = [ln for ln in filtered if lvl_upper in ln]
    if search:
        filtered = [ln for ln in filtered if search.lower() in ln.lower()]

    tail = filtered[-max(1, lines):]
    if not tail:
        console.print("[status.info]No log entries matched the specified filter.[/status.info]")
        return 0

    console.print(
        Panel(
            "\n".join(tail),
            title=f"[brand.primary]DARK VOID :: LOGS ({log_file.name} - showing {len(tail)} lines)[/brand.primary]",
            border_style="border.cyber",
        )
    )
    return 0
