"""Implementation of `darkvoid convert` command."""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Sequence

import click
from rich.console import Console
from rich.panel import Panel

from darkvoid.core.converter import ConversionEngine, ConversionOutcome
from darkvoid.core.ffmpeg import ConversionProgress
from darkvoid.core.queue import JobQueueManager
from darkvoid.core.scanner import scan_inputs
from darkvoid.database.db import DatabaseManager
from darkvoid.database.history import HistoryRepository
from darkvoid.ui.progress import create_conversion_progress
from darkvoid.ui.tables import format_status_badge
from darkvoid.utils.formatting import format_duration, format_size
from darkvoid.utils.paths import AppConfig


def execute_convert_command(
    inputs: Sequence[str | Path],
    config: AppConfig,
    console: Console,
    *,
    output_dir: str | Path | None = None,
    recursive: bool = False,
    existing_policy: str | None = None,
    force: bool = False,
    dry_run: bool = False,
    json_output: bool = False,
) -> int:
    """Scan inputs, queue jobs, execute conversions with real-time progress, and return exit code."""
    config.ensure_directories()
    scan = scan_inputs(inputs, recursive=recursive, suffix=config.output_suffix)

    if not json_output:
        for skipped_path, reason in scan.skipped_files:
            console.print(f"[status.warning]SKIP[/status.warning] {skipped_path.name}: {reason}")
        for invalid_path, reason in scan.invalid_files:
            console.print(f"[status.error]INVALID[/status.error] {invalid_path}: {reason}")

    if not scan.valid_files:
        if json_output:
            click.echo(
                json.dumps(
                    {
                        "status": "error",
                        "valid_files": 0,
                        "skipped": [(str(p), r) for p, r in scan.skipped_files],
                        "invalid": [(str(p), r) for p, r in scan.invalid_files],
                        "outcomes": [],
                    },
                    indent=2,
                )
            )
        else:
            console.print("[status.error]No valid input video files found to convert.[/status.error]")
        return 1 if scan.invalid_files or not scan.skipped_files else 0

    db = DatabaseManager(config.database_path)
    history = HistoryRepository(db)
    engine = ConversionEngine(config, history)
    queue_mgr = JobQueueManager(db, engine)

    target_out = Path(output_dir).expanduser().resolve() if output_dir else Path(config.output_dir).expanduser().resolve()
    target_out.mkdir(parents=True, exist_ok=True)

    outcomes: list[ConversionOutcome] = []
    cancel_event = threading.Event()

    if json_output or not console.is_terminal:
        for file_path in scan.valid_files:
            job, _ = queue_mgr.enqueue(file_path, target_out)
            outcome = engine.convert_file(
                file_path,
                target_out,
                job_id=job.job_id,
                existing_policy=existing_policy,
                force=force,
                dry_run=dry_run,
                cancel_event=cancel_event,
            )
            queue_mgr.update_job_status(
                job.job_id,
                "Completed" if outcome.status == "DryRun" else outcome.status,
                progress=100.0 if outcome.status in {"Completed", "Skipped", "DryRun"} else 0.0,
                output_path=str(outcome.output_path),
                error_message="" if outcome.status in {"Completed", "Skipped", "DryRun"} else outcome.message,
            )
            outcomes.append(outcome)
            if not json_output:
                console.print(
                    f"[{outcome.status.upper()}] {outcome.input_path.name} -> {outcome.output_path.name} ({outcome.message})"
                )
    else:
        with create_conversion_progress(console) as progress:
            for file_path in scan.valid_files:
                job, _ = queue_mgr.enqueue(file_path, target_out)
                task_id = progress.add_task(
                    description=file_path.name,
                    total=100.0,
                    frame=0,
                    speed="0.0x",
                    out_time="00:00:00.00",
                    eta="--:--",
                )

                def _update_bar(prog: ConversionProgress, tid: int = task_id) -> None:
                    eta_str = format_duration(prog.eta_seconds) if prog.eta_seconds is not None else "--:--"
                    progress.update(
                        tid,
                        completed=prog.percentage,
                        frame=prog.frame,
                        speed=prog.speed,
                        out_time=format_duration(prog.out_time_seconds),
                        eta=eta_str,
                    )

                outcome = engine.convert_file(
                    file_path,
                    target_out,
                    job_id=job.job_id,
                    existing_policy=existing_policy,
                    force=force,
                    dry_run=dry_run,
                    progress_callback=_update_bar,
                    cancel_event=cancel_event,
                )
                progress.update(
                    task_id,
                    completed=100.0 if outcome.status in {"Completed", "Skipped", "DryRun"} else 0.0,
                    eta="00:00:00.00" if outcome.status == "Completed" else "--:--",
                )
                queue_mgr.update_job_status(
                    job.job_id,
                    "Completed" if outcome.status == "DryRun" else outcome.status,
                    progress=100.0 if outcome.status in {"Completed", "Skipped", "DryRun"} else 0.0,
                    output_path=str(outcome.output_path),
                    error_message="" if outcome.status in {"Completed", "Skipped", "DryRun"} else outcome.message,
                )
                outcomes.append(outcome)

    completed_cnt = sum(1 for o in outcomes if o.status in {"Completed", "DryRun"})
    skipped_cnt = sum(1 for o in outcomes if o.status == "Skipped") + len(scan.skipped_files)
    failed_cnt = sum(1 for o in outcomes if o.status in {"Failed", "Cancelled"}) + len(scan.invalid_files)

    if json_output:
        click.echo(
            json.dumps(
                {
                    "status": "ok" if failed_cnt == 0 else "partial_or_failed",
                    "summary": {
                        "completed": completed_cnt,
                        "skipped": skipped_cnt,
                        "failed": failed_cnt,
                    },
                    "outcomes": [
                        {
                            "job_id": o.job_id,
                            "status": o.status,
                            "input_path": str(o.input_path),
                            "output_path": str(o.output_path),
                            "input_size": o.file_size,
                            "output_size": o.output_size,
                            "elapsed_seconds": round(o.elapsed_seconds, 3),
                            "has_audio": o.has_audio,
                            "message": o.message,
                            "command": o.command,
                        }
                        for o in outcomes
                    ],
                },
                indent=2,
            )
        )
    else:
        for o in outcomes:
            badge = format_status_badge(o.status)
            console.print(
                f"  {badge} [bold]{o.input_path.name}[/bold] -> [cyan]{o.output_path.name}[/cyan] "
                f"({format_size(o.output_size)}) - {o.message}"
            )
            if dry_run and o.command:
                console.print(f"    [muted]Command: {' '.join(o.command)}[/muted]")

        summary_line = (
            f"[status.success]Completed: {completed_cnt}[/status.success]  |  "
            f"[status.warning]Skipped: {skipped_cnt}[/status.warning]  |  "
            f"[status.error]Failed: {failed_cnt}[/status.error]"
        )
        console.print(Panel(summary_line, title="[brand.primary]CONVERSION SUMMARY[/brand.primary]", border_style="border.cyber", expand=False))

    return 0 if failed_cnt == 0 else 1
