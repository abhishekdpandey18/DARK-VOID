"""Rich console factory respecting non-interactive and piped environments."""

from __future__ import annotations

import os
import sys
from rich.console import Console
from darkvoid.ui.themes import DARKVOID_THEME


def is_interactive_terminal() -> bool:
    """Return True when stdout is attached to an interactive TTY and NO_COLOR is unset."""
    return sys.stdout.isatty() and os.environ.get("TERM", "") != "dumb"


def get_console(stderr: bool = False, quiet: bool = False) -> Console:
    """Create a Rich Console configured with the DARK VOID theme and pipe safety."""
    no_color = bool(os.environ.get("NO_COLOR")) or not sys.stdout.isatty()
    return Console(
        theme=DARKVOID_THEME,
        stderr=stderr,
        quiet=quiet,
        no_color=no_color,
        highlight=False,
    )
