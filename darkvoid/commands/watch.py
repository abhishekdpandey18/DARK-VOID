"""Implementation of `darkvoid watch` folder monitoring command."""

from __future__ import annotations

from pathlib import Path
from rich.console import Console
from rich.panel import Panel

from darkvoid.core.converter import ConversionEngine, ConversionOutcome
from darkvoid.core.queue import JobQueueManager
from darkvoid.core.watcher import HAS_WATCHDOG, FolderWatcher
from darkvoid.database.db import DatabaseManager
from darkvoid.database.history import HistoryRepository
from darkvoid.ui.tables import format_status_badge
from darkvoid.utils.paths import AppConfig
from darkvoid.utils.validation import ValidationError


def execute_watch_command(
    watch_dir: str | Path | None,
    config: AppConfig,
    console: Console,
    *,
    output_dir: str | Path | None = None,
    once: bool = False,
    max_runtime: float | None = None,
) -> int:
    """Monitor a directory and automatically convert incoming videos into DNxHR HQ MOV."""
    config.ensure_directories()
    target_in = Path(watch_dir).expanduser().resolve() if watch_dir else Path(config.input_dir).expanduser().resolve()
    target_out = Path(output_dir).expanduser().resolve() if output_dir else Path(config.output_dir).expanduser().resolve()

    if not target_in.exists() or not target_in.is_dir():
        console.print(f"[status.error]ERROR:[/status.error] Watch directory does not exist: {target_in}")
        return 1

    target_out.mkdir(parents=True, exist_ok=True)

    db = DatabaseManager(config.database_path)
    history = HistoryRepository(db)
    engine = ConversionEngine(config, history)
    qm = JobQueueManager(db, engine)

    def _on_event(evt_type: str, path: Path) -> None:
        console.print(f"[status.info]WATCHER :: Detected incoming file:[/status.info] [bold]{path.name}[/bold] (verifying stability...)")

    def _on_converted(outcome: ConversionOutcome) -> None:
        badge = format_status_badge(outcome.status)
        console.print(f"  {badge} [bold]{outcome.input_path.name}[/bold] -> [cyan]{outcome.output_path.name}[/cyan] ({outcome.message})")

    watcher = FolderWatcher(
        watch_dir=target_in,
        output_dir=target_out,
        queue_manager=qm,
        stability_wait=config.stability_wait_seconds,
        stability_checks=config.stability_checks,
        poll_interval=config.poll_interval_seconds,
        on_event_callback=_on_event,
        on_conversion_callback=_on_converted,
    )

    backend_name = "Watchdog (inotify)" if HAS_WATCHDOG else "Stat-Polling Fallback"
    panel_body = "\n".join([
        f"[brand.accent]Monitoring Directory:[/brand.accent] {target_in}",
        f"[brand.accent]Output Destination:[/brand.accent]   {target_out}",
        f"[brand.accent]Watcher Engine:[/brand.accent]       {backend_name}",
        "[muted]Press Ctrl+C to stop folder monitoring gracefully.[/muted]",
    ])
    console.print(
        Panel(
            panel_body,
            title="[brand.primary]DARK VOID :: FOLDER MONITOR[/brand.primary]",
            border_style="border.cyber",
            expand=False,
        )
    )

    try:
        if once:
            watcher.scan_once()
        else:
            watcher.start(max_runtime_seconds=max_runtime)
    except ValidationError as exc:
        console.print(f"[status.error]Watcher error:[/status.error] {exc}")
        return 1

    console.print("[status.info]Folder monitoring stopped cleanly.[/status.info]")
    return 0
