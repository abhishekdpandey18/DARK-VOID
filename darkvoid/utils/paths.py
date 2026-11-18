"""Path management, cross-platform configuration storage (Linux/Windows/macOS), and logging setup."""

from __future__ import annotations

import json
import logging
import os
import sys
from dataclasses import asdict, dataclass
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any


def is_windows() -> bool:
    """Return True when running on Windows."""
    return os.name == "nt" or sys.platform.startswith("win")


def get_config_dir() -> Path:
    """Return user configuration directory across Linux, Windows, and macOS."""
    env_home = os.environ.get("DARKVOID_HOME")
    if env_home:
        return Path(env_home).expanduser().resolve()
    if is_windows():
        appdata = os.environ.get("APPDATA") or os.environ.get("LOCALAPPDATA")
        if appdata:
            return Path(appdata).expanduser().resolve() / "darkvoid"
        return Path.home() / "AppData" / "Roaming" / "darkvoid"
    xdg = os.environ.get("XDG_CONFIG_HOME")
    if xdg:
        return Path(xdg).expanduser().resolve() / "darkvoid"
    return Path.home() / ".config" / "darkvoid"


def get_workspace_dir(config: "AppConfig | None" = None) -> Path:
    """Return the default Convert-Workspace directory."""
    if config and config.workspace_dir:
        return Path(config.workspace_dir).expanduser().resolve()
    env_ws = os.environ.get("DARKVOID_WORKSPACE")
    if env_ws:
        return Path(env_ws).expanduser().resolve()
    return Path.cwd() / "Convert-Workspace"


@dataclass
class AppConfig:
    """Persistent application configuration with validation and safe defaults."""

    workspace_dir: str = ""
    input_dir: str = ""
    output_dir: str = ""
    temp_dir: str = ""
    failed_dir: str = ""
    log_dir: str = ""
    database_path: str = ""
    ffmpeg_path: str = "ffmpeg"
    ffprobe_path: str = "ffprobe"
    video_codec: str = "dnxhd"
    video_profile: str = "dnxhr_hq"
    audio_codec: str = "pcm_s16le"
    output_suffix: str = "_Resolve"
    output_extension: str = ".mov"
    existing_output_policy: str = "skip"  # skip | rename | fail
    stability_wait_seconds: float = 1.5
    stability_checks: int = 2
    poll_interval_seconds: float = 1.0
    log_level: str = "INFO"
    show_banner: bool = True
    notifications_enabled: bool = True
    max_workers: int = 1

    def __post_init__(self) -> None:
        ws = Path(self.workspace_dir) if self.workspace_dir else get_workspace_dir()
        if not self.workspace_dir:
            self.workspace_dir = str(ws)
        if not self.input_dir:
            self.input_dir = str(ws / "incoming")
        if not self.output_dir:
            self.output_dir = str(ws / "converted")
        if not self.temp_dir:
            self.temp_dir = str(ws / "converting")
        if not self.failed_dir:
            self.failed_dir = str(ws / "failed")
        if not self.log_dir:
            self.log_dir = str(ws / "logs")
        if not self.database_path:
            cfg_dir = get_config_dir()
            self.database_path = str(cfg_dir / "darkvoid_history.db")
        self.validate()

    def validate(self) -> None:
        """Validate configuration fields and normalize values."""
        valid_policies = {"skip", "rename", "fail"}
        if self.existing_output_policy not in valid_policies:
            self.existing_output_policy = "skip"
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if self.log_level.upper() not in valid_levels:
            self.log_level = "INFO"
        else:
            self.log_level = self.log_level.upper()
        if self.stability_wait_seconds < 0.05:
            self.stability_wait_seconds = 0.05
        if self.stability_checks < 1:
            self.stability_checks = 1
        if self.max_workers < 1:
            self.max_workers = 1
        # Enforce mandatory DNxHR HQ / PCM S16LE / .mov invariants
        self.video_codec = "dnxhd"
        self.video_profile = "dnxhr_hq"
        self.audio_codec = "pcm_s16le"
        self.output_extension = ".mov"

    def ensure_directories(self) -> dict[str, Path]:
        """Ensure workspace and configuration directories exist safely."""
        cfg_dir = get_config_dir()
        cfg_dir.mkdir(parents=True, exist_ok=True)
        Path(self.database_path).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)

        dirs = {
            "workspace": Path(self.workspace_dir).expanduser().resolve(),
            "incoming": Path(self.input_dir).expanduser().resolve(),
            "converted": Path(self.output_dir).expanduser().resolve(),
            "converting": Path(self.temp_dir).expanduser().resolve(),
            "failed": Path(self.failed_dir).expanduser().resolve(),
            "logs": Path(self.log_dir).expanduser().resolve(),
        }
        for path in dirs.values():
            path.mkdir(parents=True, exist_ok=True)
        return dirs


class ConfigManager:
    """Loads, validates, updates, and resets DARK VOID configuration."""

    def __init__(self, config_file: Path | None = None) -> None:
        self.config_file = config_file or (get_config_dir() / "config.json")

    def load(self) -> AppConfig:
        """Load configuration from disk, falling back safely on missing/corrupt files."""
        if not self.config_file.exists():
            cfg = AppConfig()
            self.save(cfg)
            return cfg
        try:
            raw = json.loads(self.config_file.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                raise ValueError("Configuration root must be a JSON object.")
            allowed = {k: v for k, v in raw.items() if k in AppConfig.__dataclass_fields__}
            cfg = AppConfig(**allowed)
            return cfg
        except Exception as exc:
            logging.getLogger("darkvoid").warning(
                "Malformed configuration at %s (%s); using safe defaults.",
                self.config_file,
                exc,
            )
            return AppConfig()

    def save(self, config: AppConfig) -> Path:
        """Persist configuration atomically to disk."""
        config.validate()
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self.config_file.with_suffix(".json.tmp")
        tmp_path.write_text(json.dumps(asdict(config), indent=2), encoding="utf-8")
        os.replace(str(tmp_path), str(self.config_file))
        return self.config_file

    def set_value(self, key: str, value: str) -> AppConfig:
        """Update a single configuration key with type coercion and validation."""
        cfg = self.load()
        if key not in AppConfig.__dataclass_fields__:
            raise KeyError(f"Unknown configuration key: '{key}'")
        protected_keys = {"video_codec", "video_profile", "audio_codec", "output_extension"}
        if key in protected_keys:
            raise ValueError(
                f"'{key}' is locked by mandatory DARK VOID specification (DNxHR HQ / PCM S16LE / MOV)."
            )
        current_val = getattr(cfg, key)
        if isinstance(current_val, bool):
            coerced: Any = value.strip().lower() in {"1", "true", "yes", "on"}
        elif isinstance(current_val, int):
            coerced = int(value)
        elif isinstance(current_val, float):
            coerced = float(value)
        else:
            coerced = str(value)
        setattr(cfg, key, coerced)
        cfg.validate()
        self.save(cfg)
        return cfg

    def reset(self) -> AppConfig:
        """Reset configuration to factory defaults."""
        cfg = AppConfig()
        self.save(cfg)
        return cfg


def setup_logging(config: AppConfig, verbose: bool = False) -> Path:
    """Configure rotating file logging for DARK VOID."""
    dirs = config.ensure_directories()
    log_file = dirs["logs"] / "darkvoid.log"
    logger = logging.getLogger("darkvoid")
    level_name = "DEBUG" if verbose else config.log_level
    level = getattr(logging, level_name.upper(), logging.INFO)
    logger.setLevel(level)

    for h in list(logger.handlers):
        logger.removeHandler(h)
        h.close()

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler = RotatingFileHandler(
        log_file, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.propagate = False
    return log_file
