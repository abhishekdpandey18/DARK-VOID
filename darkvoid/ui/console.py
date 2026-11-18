"""Rich console factory respecting non-interactive, piped, and Windows UTF-8 environments."""

from __future__ import annotations

import os
import sys
from rich.console import Console
from darkvoid.ui.themes import DARKVOID_THEME


def ensure_utf8_streams() -> None:
    """Ensure stdout and stderr use UTF-8 on Windows terminals so Unicode borders/banners never fail."""
    for stream in (sys.stdout, sys.stderr):
        reconf = getattr(stream, "reconfigure", None)
        if callable(reconf):
            try:
                reconf(encoding="utf-8", errors="replace")
            except Exception:
                pass


def is_interactive_terminal() -> bool:
    """Return True when stdout is attached to an interactive TTY and NO_COLOR is unset."""
    return sys.stdout.isatty() and os.environ.get("TERM", "") != "dumb"


def get_console(stderr: bool = False, quiet: bool = False) -> Console:
    """Create a Rich Console configured with the DARK VOID theme and cross-platform pipe safety."""
    ensure_utf8_streams()
    no_color = bool(os.environ.get("NO_COLOR")) or not sys.stdout.isatty()
    return Console(
        theme=DARKVOID_THEME,
        stderr=stderr,
        quiet=quiet,
        no_color=no_color,
        highlight=False,
    )
