"""Cyberpunk color palette and Rich theme definitions for DARK VOID."""

from __future__ import annotations

from rich.theme import Theme

DARKVOID_THEME = Theme(
    {
        "brand.primary": "bold bright_magenta",
        "brand.secondary": "purple",
        "brand.accent": "bold cyan",
        "status.success": "bold bright_green",
        "status.info": "cyan",
        "status.warning": "bold yellow",
        "status.error": "bold bright_red",
        "table.header": "bold bright_magenta",
        "border.cyber": "bright_magenta",
        "muted": "dim white",
    }
)
