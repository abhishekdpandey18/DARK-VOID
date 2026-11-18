"""Interactive terminal menu for DARK VOID when invoked without arguments."""

from __future__ import annotations

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

from darkvoid.commands.config import execute_config_set, execute_config_show
from darkvoid.commands.convert import execute_convert_command
from darkvoid.commands.doctor import execute_doctor_command
from darkvoid.commands.history import execute_history_command
from darkvoid.commands.info import execute_info_command
from darkvoid.commands.queue import execute_queue_list
from darkvoid.commands.watch import execute_watch_command
from darkvoid.utils.paths import ConfigManager

MENU_OPTIONS = "\n".join([
    "[brand.accent][01][/brand.accent] Convert Video",
    "[brand.accent][02][/brand.accent] Batch Conversion",
    "[brand.accent][03][/brand.accent] Video Information",
    "[brand.accent][04][/brand.accent] Conversion Queue",
    "[brand.accent][05][/brand.accent] Folder Monitoring",
    "[brand.accent][06][/brand.accent] Conversion History",
    "[brand.accent][07][/brand.accent] System Diagnostics",
    "[brand.accent][08][/brand.accent] Settings",
    "[brand.accent][09][/brand.accent] Exit",
])


def run_interactive_menu(config_mgr: ConfigManager, console: Console) -> int:
    """Display and drive the interactive DARK VOID terminal menu."""
    while True:
        cfg = config_mgr.load()
        console.print()
        console.print(
            Panel(
                MENU_OPTIONS,
                title="[brand.primary]DARK VOID :: INTERACTIVE TERMINAL[/brand.primary]",
                border_style="border.cyber",
                box=box.ROUNDED,
                padding=(1, 3),
                expand=False,
            )
        )
        try:
            raw_choice = Prompt.ask(
                "[brand.primary]Select operation [01-09][/brand.primary]",
                default="09",
                console=console,
            ).strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[status.info]Exiting DARK VOID terminal.[/status.info]")
            return 0

        normalized = raw_choice.lstrip("0") or "0"
        if normalized == "9" or raw_choice.lower() in {"exit", "quit", "q"}:
            console.print("[status.info]Exiting DARK VOID. Goodbye.[/status.info]")
            return 0
        elif normalized == "1":
            target = Prompt.ask("Enter video file path to convert", console=console).strip()
            if target:
                out_dir = Prompt.ask("Output directory", default=cfg.output_dir, console=console).strip()
                execute_convert_command([target], cfg, console, output_dir=out_dir)
        elif normalized == "2":
            target_dir = Prompt.ask("Enter directory path for batch conversion", default=cfg.input_dir, console=console).strip()
            out_dir = Prompt.ask("Output directory", default=cfg.output_dir, console=console).strip()
            rec_ans = Prompt.ask("Scan subdirectories recursively? (y/n)", default="n", console=console).strip().lower()
            execute_convert_command([target_dir], cfg, console, output_dir=out_dir, recursive=(rec_ans == "y"))
        elif normalized == "3":
            target = Prompt.ask("Enter video file path to inspect", console=console).strip()
            if target:
                execute_info_command(target, cfg, console)
        elif normalized == "4":
            execute_queue_list(cfg, console)
        elif normalized == "5":
            watch_dir = Prompt.ask("Directory to monitor", default=cfg.input_dir, console=console).strip()
            out_dir = Prompt.ask("Output directory", default=cfg.output_dir, console=console).strip()
            execute_watch_command(watch_dir, cfg, console, output_dir=out_dir)
        elif normalized == "6":
            execute_history_command(cfg, console)
        elif normalized == "7":
            execute_doctor_command(config_mgr, console)
        elif normalized == "8":
            execute_config_show(config_mgr, console)
            change = Prompt.ask("Update a setting? Enter 'key=value' or press Enter to skip", default="", console=console).strip()
            if "=" in change:
                k, v = change.split("=", 1)
                execute_config_set(config_mgr, k.strip(), v.strip(), console)
        else:
            console.print(f"[status.error]Invalid selection '{raw_choice}'. Please enter a number from 01 to 09.[/status.error]")
