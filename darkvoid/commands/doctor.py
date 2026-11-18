"""Implementation of `darkvoid doctor` system diagnostics command."""

from __future__ import annotations

import importlib.util
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

import click
from rich import box
from rich.console import Console
from rich.table import Table

from darkvoid.utils.formatting import format_size
from darkvoid.utils.paths import ConfigManager


def execute_doctor_command(
    config_mgr: ConfigManager,
    console: Console,
    *,
    json_output: bool = False,
) -> int:
    """Run comprehensive system, encoder, permission, and dependency diagnostics."""
    cfg = config_mgr.load()
    checks: list[dict[str, str]] = []
    all_critical_ok = True

    py_ver = platform.python_version()
    py_ok = sys.version_info >= (3, 10)
    if not py_ok:
        all_critical_ok = False
    checks.append({
        "check": "Python Version (>=3.10)",
        "status": "PASS" if py_ok else "FAIL",
        "details": f"Python {py_ver} ({sys.executable})",
    })

    ffmpeg_bin = shutil.which(cfg.ffmpeg_path)
    ffmpeg_ok = ffmpeg_bin is not None
    if not ffmpeg_ok:
        all_critical_ok = False
    checks.append({
        "check": "FFmpeg Executable",
        "status": "PASS" if ffmpeg_ok else "FAIL",
        "details": ffmpeg_bin or f"Not found: '{cfg.ffmpeg_path}'",
    })

    ffprobe_bin = shutil.which(cfg.ffprobe_path)
    ffprobe_ok = ffprobe_bin is not None
    if not ffprobe_ok:
        all_critical_ok = False
    checks.append({
        "check": "FFprobe Executable",
        "status": "PASS" if ffprobe_ok else "FAIL",
        "details": ffprobe_bin or f"Not found: '{cfg.ffprobe_path}'",
    })

    dnxhr_ok = False
    pcm_ok = False
    if ffmpeg_bin:
        try:
            enc_proc = subprocess.run(
                [ffmpeg_bin, "-hide_banner", "-encoders"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            out_text = enc_proc.stdout or ""
            dnxhr_ok = "dnxhd" in out_text
            pcm_ok = "pcm_s16le" in out_text
        except Exception:
            pass
    if not dnxhr_ok or not pcm_ok:
        all_critical_ok = False

    checks.append({
        "check": "DNxHR HQ Video Encoder (dnxhd)",
        "status": "PASS" if dnxhr_ok else "FAIL",
        "details": "dnxhd (profile: dnxhr_hq) available" if dnxhr_ok else "dnxhd encoder missing in FFmpeg build",
    })
    checks.append({
        "check": "PCM S16LE Audio Encoder",
        "status": "PASS" if pcm_ok else "FAIL",
        "details": "pcm_s16le encoder available" if pcm_ok else "pcm_s16le encoder missing in FFmpeg build",
    })

    out_dir = Path(cfg.output_dir).expanduser().resolve()
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
        writable = os.access(out_dir, os.W_OK)
        free_space = shutil.disk_usage(out_dir).free
    except OSError:
        writable = False
        free_space = 0
        all_critical_ok = False

    if not writable:
        all_critical_ok = False

    checks.append({
        "check": "Output Directory Permissions",
        "status": "PASS" if writable else "FAIL",
        "details": f"Writable: {out_dir}" if writable else f"Not writable: {out_dir}",
    })
    space_ok = free_space >= 100 * 1024 * 1024
    checks.append({
        "check": "Available Disk Space",
        "status": "PASS" if space_ok else "WARNING",
        "details": f"{format_size(free_space)} free on {out_dir}",
    })

    cfg_valid = True
    try:
        cfg.validate()
    except Exception:
        cfg_valid = False
        all_critical_ok = False
    checks.append({
        "check": "Configuration Validity",
        "status": "PASS" if cfg_valid else "FAIL",
        "details": f"Loaded from {config_mgr.config_file}",
    })

    for mod_name, required in [("rich", True), ("click", True), ("sqlite3", True), ("typer", False), ("watchdog", False), ("pyfiglet", False)]:
        found = importlib.util.find_spec(mod_name) is not None
        if required and not found:
            all_critical_ok = False
        status_str = "PASS" if found else ("FAIL" if required else "OPTIONAL (Fallback Active)")
        checks.append({
            "check": f"Python Module: {mod_name}",
            "status": status_str,
            "details": "Installed" if found else "Using built-in standard-library fallback",
        })

    if json_output:
        click.echo(json.dumps({"healthy": all_critical_ok, "checks": checks}, indent=2))
        return 0 if all_critical_ok else 1

    table = Table(
        title="[brand.primary]DARK VOID :: SYSTEM DIAGNOSTICS (DOCTOR)[/brand.primary]",
        box=box.SIMPLE_HEAVY,
        border_style="border.cyber",
        header_style="table.header",
    )
    table.add_column("Diagnostic Check", style="brand.accent")
    table.add_column("Status", no_wrap=True)
    table.add_column("Details", style="white")

    for item in checks:
        st = item["status"]
        if st == "PASS":
            badge = "[status.success]PASS[/status.success]"
        elif "OPTIONAL" in st or st == "WARNING":
            badge = f"[status.warning]{st}[/status.warning]"
        else:
            badge = "[status.error]FAIL[/status.error]"
        table.add_row(item["check"], badge, item["details"])

    console.print(table)
    return 0 if all_critical_ok else 1
