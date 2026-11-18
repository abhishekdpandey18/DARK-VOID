"""Implementation of `darkvoid config` commands."""

from __future__ import annotations

import json
from dataclasses import asdict
import click
from rich import box
from rich.console import Console
from rich.table import Table

from darkvoid.utils.paths import ConfigManager


def execute_config_show(
    config_mgr: ConfigManager,
    console: Console,
    *,
    json_output: bool = False,
) -> int:
    """Display active DARK VOID configuration settings."""
    cfg = config_mgr.load()
    data = asdict(cfg)
    if json_output:
        click.echo(json.dumps(data, indent=2))
        return 0

    table = Table(
        title=f"[brand.primary]DARK VOID :: CONFIGURATION ({config_mgr.config_file})[/brand.primary]",
        box=box.SIMPLE_HEAVY,
        border_style="border.cyber",
        header_style="table.header",
    )
    table.add_column("Setting Key", style="brand.accent", no_wrap=True)
    table.add_column("Current Value", style="white")

    for k, v in data.items():
        table.add_row(k, str(v))
    console.print(table)
    return 0


def execute_config_set(
    config_mgr: ConfigManager,
    key: str,
    value: str,
    console: Console,
) -> int:
    """Update a persistent configuration key."""
    try:
        cfg = config_mgr.set_value(key, value)
    except (KeyError, ValueError) as exc:
        console.print(f"[status.error]Configuration Error:[/status.error] {exc}")
        return 1

    console.print(
        f"[status.success]Updated configuration:[/status.success] [brand.accent]{key}[/brand.accent] = [bold]{getattr(cfg, key)}[/bold]"
    )
    return 0


def execute_config_reset(
    config_mgr: ConfigManager,
    console: Console,
) -> int:
    """Reset configuration to default values."""
    config_mgr.reset()
    console.print("[status.success]Configuration restored to factory defaults.[/status.success]")
    return 0
