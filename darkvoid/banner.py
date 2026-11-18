"""Startup cyberpunk ASCII banner for DARK VOID."""

from __future__ import annotations

import platform
import shutil
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from darkvoid import __version__
from darkvoid.utils.paths import AppConfig

try:
    import pyfiglet  # type: ignore[import-not-found]
    HAS_PYFIGLET = True
except ImportError:
    HAS_PYFIGLET = False

FALLBACK_ASCII_LOGO = "\n".join([
    " ██████╗  █████╗ ██████╗ ██╗  ██╗    ██╗   ██╗ ██████╗ ██╗██████╗ ",
    " ██╔══██╗██╔══██╗██╔══██╗██║ ██╔╝    ██║   ██║██╔═══██╗██║██╔══██╗",
    " ██║  ██║███████║██████╔╝█████╔╝     ██║   ██║██║   ██║██║██║  ██║",
    " ██║  ██║██╔══██║██╔══██╗██╔═██╗     ╚██╗ ██╔╝██║   ██║██║██║  ██║",
    " ██████╔╝██║  ██║██║  ██║██║  ██╗     ╚████╔╝ ╚██████╔╝██║██████╔╝",
    " ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝      ╚═══╝   ╚═════╝ ╚═╝╚═════╝ ",
])


def render_ascii_title() -> str:
    """Render DARK VOID ASCII art via PyFiglet if available, or clean block ASCII fallback."""
    if HAS_PYFIGLET:
        try:
            rendered = pyfiglet.figlet_format("DARK VOID", font="slant")
            if rendered and rendered.strip():
                return rendered.rstrip("\n")
        except Exception:
            pass
    return FALLBACK_ASCII_LOGO


def display_banner(console: Console, config: AppConfig, force: bool = False) -> None:
    """Display the DARK VOID startup banner with runtime and engine status indicators."""
    if not force and not config.show_banner:
        return
    if not force and not console.is_terminal:
        return

    ffmpeg_ok = shutil.which(config.ffmpeg_path) is not None
    ffprobe_ok = shutil.which(config.ffprobe_path) is not None
    engine_ready = ffmpeg_ok and ffprobe_ok

    py_ver = platform.python_version()
    ffmpeg_badge = "[bold bright_green]ONLINE[/bold bright_green]" if ffmpeg_ok else "[bold bright_red]MISSING[/bold bright_red]"
    ffprobe_badge = "[bold bright_green]ONLINE[/bold bright_green]" if ffprobe_ok else "[bold bright_red]MISSING[/bold bright_red]"
    engine_badge = "[bold bright_green]READY[/bold bright_green]" if engine_ready else "[bold bright_red]DEGRADED[/bold bright_red]"

    logo = render_ascii_title()
    body = (
        f"[bold bright_magenta]{logo}[/bold bright_magenta]\n"
        f"[bold cyan]ADVANCED VIDEO CONVERSION ENGINE[/bold cyan]  [dim]|[/dim]  "
        f"[purple]DNxHR HQ  •  PCM S16LE  •  QUICKTIME MOV[/purple]\n"
        f"[dim]──────────────────────────────────────────────────────────────────────────[/dim]\n"
        f"[white]Version:[/white] [bold cyan]{__version__}[/bold cyan]   "
        f"[white]Python:[/white] [cyan]{py_ver}[/cyan]   "
        f"[white]FFmpeg:[/white] {ffmpeg_badge}   "
        f"[white]FFprobe:[/white] {ffprobe_badge}   "
        f"[white]Engine:[/white] {engine_badge}"
    )

    panel = Panel(
        Text.from_markup(body),
        box=box.DOUBLE_EDGE,
        border_style="bright_magenta",
        padding=(0, 2),
        expand=False,
    )
    console.print(panel)
