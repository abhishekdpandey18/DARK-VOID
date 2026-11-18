"""Real-time Rich progress bar for FFmpeg DNxHR HQ conversions."""

from __future__ import annotations

from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
)


def create_conversion_progress(console: Console) -> Progress:
    """Create a Rich Progress instance displaying % completion, frame, speed, out_time, and ETA."""
    return Progress(
        SpinnerColumn(style="bright_magenta"),
        TextColumn("[bold bright_magenta]{task.description}[/bold bright_magenta]"),
        BarColumn(bar_width=32, complete_style="bright_magenta", finished_style="bright_green"),
        TaskProgressColumn(),
        TextColumn("[cyan]frame={task.fields[frame]}[/cyan]"),
        TextColumn("[purple]speed={task.fields[speed]}[/purple]"),
        TextColumn("[cyan]time={task.fields[out_time]}[/cyan]"),
        TextColumn("[yellow]eta={task.fields[eta]}[/yellow]"),
        TimeElapsedColumn(),
        console=console,
        transient=False,
    )
