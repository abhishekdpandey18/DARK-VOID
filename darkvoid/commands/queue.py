"""Implementation of `darkvoid queue` commands."""

from __future__ import annotations

import json
import click
from rich.console import Console
from rich.prompt import Confirm

from darkvoid.core.converter import ConversionEngine
from darkvoid.core.queue import JobQueueManager
from darkvoid.database.db import DatabaseManager
from darkvoid.database.history import HistoryRepository
from darkvoid.ui.tables import build_queue_table
from darkvoid.utils.paths import AppConfig


def execute_queue_list(
    config: AppConfig,
    console: Console,
    *,
    status: str | None = None,
    json_output: bool = False,
) -> int:
    """Display queued and active conversion jobs."""
    db = DatabaseManager(config.database_path)
    history = HistoryRepository(db)
    engine = ConversionEngine(config, history)
    qm = JobQueueManager(db, engine)

    jobs = qm.list_jobs(status=status)
    if json_output:
        click.echo(json.dumps([vars(j) for j in jobs], indent=2))
        return 0

    if not jobs:
        console.print("[status.info]Queue is currently empty.[/status.info]")
        return 0

    console.print(build_queue_table(jobs))
    return 0


def execute_queue_clear(
    config: AppConfig,
    console: Console,
    *,
    yes: bool = False,
) -> int:
    """Clear pending jobs from the queue after confirmation."""
    db = DatabaseManager(config.database_path)
    history = HistoryRepository(db)
    engine = ConversionEngine(config, history)
    qm = JobQueueManager(db, engine)

    pending = qm.list_jobs(status="Pending")
    if not pending:
        console.print("[status.info]No pending jobs to clear.[/status.info]")
        return 0

    if not yes and console.is_terminal:
        confirmed = Confirm.ask(f"Clear {len(pending)} pending job(s) from the queue?", default=False, console=console)
        if not confirmed:
            console.print("[status.warning]Queue clear cancelled.[/status.warning]")
            return 0

    removed = qm.clear_pending()
    console.print(f"[status.success]Cleared {removed} pending job(s) from the queue.[/status.success]")
    return 0


def execute_queue_retry(
    config: AppConfig,
    console: Console,
) -> int:
    """Retry failed or cancelled jobs in the queue."""
    db = DatabaseManager(config.database_path)
    history = HistoryRepository(db)
    engine = ConversionEngine(config, history)
    qm = JobQueueManager(db, engine)

    requeued = qm.reset_failed_for_retry()
    if not requeued:
        console.print("[status.info]No failed or cancelled queue jobs eligible for retry.[/status.info]")
        return 0

    console.print(f"[status.info]Retrying {len(requeued)} job(s)...[/status.info]")
    outcomes = qm.process_pending(force=True)
    failures = sum(1 for o in outcomes if o.status == "Failed")
    for o in outcomes:
        console.print(f"  [{o.status}] {o.input_path.name} -> {o.output_path.name}: {o.message}")
    return 0 if failures == 0 else 1
