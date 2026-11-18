"""Implementation of `darkvoid history` command."""

from __future__ import annotations

import json
from dataclasses import asdict
import click
from rich.console import Console

from darkvoid.database.db import DatabaseManager
from darkvoid.database.history import HistoryRepository
from darkvoid.ui.tables import build_history_table
from darkvoid.utils.paths import AppConfig


def execute_history_command(
    config: AppConfig,
    console: Console,
    *,
    success_only: bool = False,
    failed_only: bool = False,
    search: str | None = None,
    limit: int = 50,
    json_output: bool = False,
) -> int:
    """Query and display persistent conversion history."""
    db = DatabaseManager(config.database_path)
    repo = HistoryRepository(db)

    status_filter: str | None = None
    if success_only:
        status_filter = "Completed"
    elif failed_only:
        status_filter = "Failed"

    records = repo.list_history(status=status_filter, search=search, limit=limit)
    if json_output:
        click.echo(json.dumps([asdict(r) for r in records], indent=2))
        return 0

    if not records:
        console.print("[status.info]No matching conversion history records found.[/status.info]")
        return 0

    console.print(build_history_table(records))
    return 0
