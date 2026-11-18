"""Primary CLI entry point for DARK VOID (`darkvoid`).

Uses Click (the engine underlying Typer) with optional Typer compatibility so the CLI
executes identically whether invoked via `darkvoid`, `python3 -m darkvoid.cli`, or Typer.
"""

from __future__ import annotations

import logging
import sys
from typing import Sequence

import click

from darkvoid import __app_name__, __description__, __version__
from darkvoid.banner import display_banner
from darkvoid.commands.config import execute_config_reset, execute_config_set, execute_config_show
from darkvoid.commands.convert import execute_convert_command
from darkvoid.commands.doctor import execute_doctor_command
from darkvoid.commands.history import execute_history_command
from darkvoid.commands.info import execute_info_command
from darkvoid.commands.logs import execute_logs_command
from darkvoid.commands.queue import execute_queue_clear, execute_queue_list, execute_queue_retry
from darkvoid.commands.watch import execute_watch_command
from darkvoid.menu import run_interactive_menu
from darkvoid.ui.console import get_console
from darkvoid.utils.paths import ConfigManager, setup_logging


class DarkVoidContext:
    """Shared execution context across CLI commands."""

    def __init__(self, no_banner: bool = False, verbose: bool = False, quiet: bool = False) -> None:
        self.config_mgr = ConfigManager()
        self.config = self.config_mgr.load()
        self.no_banner = no_banner
        self.verbose = verbose
        self.quiet = quiet
        self.console = get_console(quiet=quiet)
        setup_logging(self.config, verbose=verbose)


@click.group(
    name="darkvoid",
    invoke_without_command=True,
    context_settings={"help_option_names": ["-h", "--help"]},
    help="DARK VOID — Professional Python CLI Video Conversion Engine (DNxHR HQ QuickTime MOV).",
)
@click.option("--version", "-V", is_flag=True, help="Display application version and exit.")
@click.option("--no-banner", is_flag=True, help="Disable the startup ASCII banner.")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose debug logging.")
@click.option("--quiet", "-q", is_flag=True, help="Suppress decorative terminal output.")
@click.pass_context
def cli(ctx: click.Context, version: bool, no_banner: bool, verbose: bool, quiet: bool) -> None:
    """DARK VOID root command group."""
    dv_ctx = DarkVoidContext(no_banner=no_banner, verbose=verbose, quiet=quiet)
    ctx.obj = dv_ctx
    logger = logging.getLogger("darkvoid")
    logger.info("DARK VOID v%s started (subcommand=%s)", __version__, ctx.invoked_subcommand)

    if version:
        dv_ctx.console.print(f"{__app_name__} version {__version__}")
        ctx.exit(0)

    if ctx.invoked_subcommand is None:
        if not no_banner and not quiet:
            display_banner(dv_ctx.console, dv_ctx.config)
        if dv_ctx.console.is_terminal and not quiet:
            code = run_interactive_menu(dv_ctx.config_mgr, dv_ctx.console)
            ctx.exit(code)
        else:
            click.echo(ctx.get_help())
            ctx.exit(0)


@cli.command("convert", help="Convert one or more video files or directories to DNxHR HQ QuickTime MOV.")
@click.argument("inputs", nargs=-1, required=True, type=click.Path( exists=False))
@click.option("--output", "-o", "output_dir", type=click.Path(), default=None, help="Output directory for converted .mov files.")
@click.option("--recursive", "-r", is_flag=True, help="Recursively scan subdirectories for supported videos.")
@click.option(
    "--existing",
    type=click.Choice(["skip", "rename", "fail"], case_sensitive=False),
    default=None,
    help="Policy when output file already exists (default: skip).",
)
@click.option("--force", "-f", is_flag=True, help="Force conversion even if file was previously converted.")
@click.option("--dry-run", is_flag=True, help="Validate inputs and print FFmpeg commands without converting.")
@click.option("--json", "json_output", is_flag=True, help="Emit machine-readable JSON output.")
@click.pass_obj
def convert_cmd(
    dv_ctx: DarkVoidContext,
    inputs: Sequence[str],
    output_dir: str | None,
    recursive: bool,
    existing: str | None,
    force: bool,
    dry_run: bool,
    json_output: bool,
) -> None:
    """Convert videos into DaVinci Resolve DNxHR HQ MOV format."""
    if not dv_ctx.no_banner and not dv_ctx.quiet and not json_output:
        display_banner(dv_ctx.console, dv_ctx.config)
    code = execute_convert_command(
        inputs=inputs,
        config=dv_ctx.config,
        console=dv_ctx.console,
        output_dir=output_dir,
        recursive=recursive,
        existing_policy=existing,
        force=force,
        dry_run=dry_run,
        json_output=json_output,
    )
    sys.exit(code)


@cli.command("info", help="Display comprehensive video and audio stream metadata using FFprobe.")
@click.argument("video", type=click.Path(exists=False))
@click.option("--json", "json_output", is_flag=True, help="Emit machine-readable JSON metadata.")
@click.pass_obj
def info_cmd(dv_ctx: DarkVoidContext, video: str, json_output: bool) -> None:
    """Inspect a media file via FFprobe."""
    code = execute_info_command(video, dv_ctx.config, dv_ctx.console, json_output=json_output)
    sys.exit(code)


@cli.group("queue", invoke_without_command=True, help="Inspect and manage the conversion job queue.")
@click.option("--status", "-s", default=None, help="Filter queue jobs by status.")
@click.option("--json", "json_output", is_flag=True, help="Emit machine-readable JSON output.")
@click.pass_context
def queue_group(ctx: click.Context, status: str | None, json_output: bool) -> None:
    """Display queued and active conversion jobs when invoked without subcommand."""
    dv_ctx: DarkVoidContext = ctx.obj
    if ctx.invoked_subcommand is None:
        code = execute_queue_list(dv_ctx.config, dv_ctx.console, status=status, json_output=json_output)
        ctx.exit(code)


@queue_group.command("clear", help="Clear pending jobs from the conversion queue.")
@click.option("--yes", "-y", is_flag=True, help="Confirm clearing pending jobs without interactive prompt.")
@click.pass_obj
def queue_clear_cmd(dv_ctx: DarkVoidContext, yes: bool) -> None:
    code = execute_queue_clear(dv_ctx.config, dv_ctx.console, yes=yes)
    sys.exit(code)


@queue_group.command("retry", help="Retry eligible failed or cancelled jobs in the queue.")
@click.pass_obj
def queue_retry_cmd(dv_ctx: DarkVoidContext) -> None:
    code = execute_queue_retry(dv_ctx.config, dv_ctx.console)
    sys.exit(code)


@cli.command("watch", help="Monitor a directory and automatically convert incoming videos.")
@click.argument("directory", required=False, default=None, type=click.Path())
@click.option("--output", "-o", "output_dir", type=click.Path(), default=None, help="Output directory for converted videos.")
@click.option("--once", is_flag=True, help="Run a single scan pass over the directory and exit.")
@click.pass_obj
def watch_cmd(dv_ctx: DarkVoidContext, directory: str | None, output_dir: str | None, once: bool) -> None:
    if not dv_ctx.no_banner and not dv_ctx.quiet:
        display_banner(dv_ctx.console, dv_ctx.config)
    code = execute_watch_command(directory, dv_ctx.config, dv_ctx.console, output_dir=output_dir, once=once)
    sys.exit(code)


@cli.command("history", help="Display persistent conversion history from SQLite.")
@click.option("--success", "success_only", is_flag=True, help="Display only successful conversions.")
@click.option("--failed", "failed_only", is_flag=True, help="Display only failed conversions.")
@click.option("--search", "-q", default=None, help="Filter history by filename or path substring.")
@click.option("--limit", "-n", default=50, type=int, help="Maximum number of records to display.")
@click.option("--json", "json_output", is_flag=True, help="Emit machine-readable JSON output.")
@click.pass_obj
def history_cmd(
    dv_ctx: DarkVoidContext,
    success_only: bool,
    failed_only: bool,
    search: str | None,
    limit: int,
    json_output: bool,
) -> None:
    code = execute_history_command(
        dv_ctx.config,
        dv_ctx.console,
        success_only=success_only,
        failed_only=failed_only,
        search=search,
        limit=limit,
        json_output=json_output,
    )
    sys.exit(code)


@cli.group("config", invoke_without_command=True, help="View or modify persistent DARK VOID settings.")
@click.pass_context
def config_group(ctx: click.Context) -> None:
    dv_ctx: DarkVoidContext = ctx.obj
    if ctx.invoked_subcommand is None:
        code = execute_config_show(dv_ctx.config_mgr, dv_ctx.console)
        ctx.exit(code)


@config_group.command("show", help="Display current configuration settings.")
@click.option("--json", "json_output", is_flag=True, help="Emit configuration as JSON.")
@click.pass_obj
def config_show_cmd(dv_ctx: DarkVoidContext, json_output: bool) -> None:
    code = execute_config_show(dv_ctx.config_mgr, dv_ctx.console, json_output=json_output)
    sys.exit(code)


@config_group.command("set", help="Update a persistent configuration setting (key value).")
@click.argument("key")
@click.argument("value")
@click.pass_obj
def config_set_cmd(dv_ctx: DarkVoidContext, key: str, value: str) -> None:
    code = execute_config_set(dv_ctx.config_mgr, key, value, dv_ctx.console)
    sys.exit(code)


@config_group.command("reset", help="Restore default configuration settings.")
@click.pass_obj
def config_reset_cmd(dv_ctx: DarkVoidContext) -> None:
    code = execute_config_reset(dv_ctx.config_mgr, dv_ctx.console)
    sys.exit(code)


@cli.command("doctor", help="Perform system, FFmpeg DNxHR encoder, and permission diagnostics.")
@click.option("--json", "json_output", is_flag=True, help="Emit diagnostics as JSON.")
@click.pass_obj
def doctor_cmd(dv_ctx: DarkVoidContext, json_output: bool) -> None:
    code = execute_doctor_command(dv_ctx.config_mgr, dv_ctx.console, json_output=json_output)
    sys.exit(code)


@cli.command("logs", help="Display recent DARK VOID application logs.")
@click.option("--lines", "-n", default=50, type=int, help="Number of recent log lines to display.")
@click.option("--level", "-l", default=None, help="Filter logs by level (INFO, WARNING, ERROR).")
@click.option("--search", "-q", default=None, help="Filter logs by keyword.")
@click.pass_obj
def logs_cmd(dv_ctx: DarkVoidContext, lines: int, level: str | None, search: str | None) -> None:
    code = execute_logs_command(dv_ctx.config, dv_ctx.console, lines=lines, level=level, search=search)
    sys.exit(code)


def app() -> None:
    """Console entry point (`darkvoid = darkvoid.cli:app`)."""
    cli(prog_name="darkvoid")


if __name__ == "__main__":
    app()
