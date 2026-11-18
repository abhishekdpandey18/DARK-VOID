"""Automated folder monitoring using Watchdog (with automatic polling fallback)."""

from __future__ import annotations

import logging
import threading
import time
from pathlib import Path
from typing import Callable

from darkvoid.core.converter import ConversionOutcome
from darkvoid.core.queue import JobQueueManager
from darkvoid.utils.files import compute_fast_file_fingerprint, wait_for_file_stability
from darkvoid.utils.validation import (
    ValidationError,
    is_already_resolve_output,
    is_supported_extension,
    validate_input_file,
)

logger = logging.getLogger("darkvoid.watcher")

try:
    from watchdog.events import FileSystemEvent, FileSystemEventHandler
    from watchdog.observers import Observer

    HAS_WATCHDOG = True
except ImportError:
    HAS_WATCHDOG = False
    FileSystemEventHandler = object  # type: ignore[assignment,misc]
    FileSystemEvent = object  # type: ignore[assignment,misc]
    Observer = None  # type: ignore[assignment]


class FolderWatcher:
    """Monitors an incoming folder for new/moved video files, verifies stability, and converts them."""

    def __init__(
        self,
        watch_dir: Path,
        output_dir: Path,
        queue_manager: JobQueueManager,
        *,
        stability_wait: float = 1.0,
        stability_checks: int = 2,
        poll_interval: float = 1.0,
        on_event_callback: Callable[[str, Path], None] | None = None,
        on_conversion_callback: Callable[[ConversionOutcome], None] | None = None,
    ) -> None:
        self.watch_dir = watch_dir.expanduser().resolve()
        self.output_dir = output_dir.expanduser().resolve()
        self.queue_manager = queue_manager
        self.stability_wait = stability_wait
        self.stability_checks = stability_checks
        self.poll_interval = poll_interval
        self.on_event_callback = on_event_callback
        self.on_conversion_callback = on_conversion_callback

        self._stop_event = threading.Event()
        self._processed_fingerprints: set[str] = set()
        self._processed_paths: dict[Path, int] = {}
        self._lock = threading.Lock()

    def handle_candidate_file(self, candidate: Path) -> ConversionOutcome | None:
        """Filter, wait for copy completion, deduplicate, enqueue, and convert a candidate file."""
        if self._stop_event.is_set():
            return None
        try:
            resolved = candidate.expanduser().resolve()
        except OSError:
            return None

        if not resolved.exists() or not resolved.is_file():
            return None
        if resolved.name.startswith("."):
            return None
        if not is_supported_extension(resolved):
            return None
        if is_already_resolve_output(resolved, suffix=self.queue_manager.engine.config.output_suffix):
            return None

        # Quick check if exact path + mtime was already handled in this session
        try:
            mtime_ns = resolved.stat().st_mtime_ns
        except OSError:
            return None

        with self._lock:
            if self._processed_paths.get(resolved) == mtime_ns:
                return None

        if self.on_event_callback:
            self.on_event_callback("detected", resolved)

        # Wait for file to finish copying (stability check)
        if not wait_for_file_stability(
            resolved,
            wait_seconds=self.stability_wait,
            checks=self.stability_checks,
        ):
            logger.warning("File did not stabilize or was deleted before conversion: %s", resolved)
            return None

        if not resolved.exists():
            return None

        try:
            validate_input_file(resolved)
            fp = compute_fast_file_fingerprint(resolved)
            current_mtime = resolved.stat().st_mtime_ns
        except (ValidationError, OSError) as exc:
            logger.warning("Watcher skipped invalid file %s: %s", resolved.name, exc)
            with self._lock:
                self._processed_paths[resolved] = mtime_ns
            return None

        with self._lock:
            if fp in self._processed_fingerprints or self._processed_paths.get(resolved) == current_mtime:
                logger.info("Watcher suppressed duplicate event for %s", resolved.name)
                return None
            self._processed_fingerprints.add(fp)
            self._processed_paths[resolved] = current_mtime

        job, created = self.queue_manager.enqueue(resolved, self.output_dir)
        if not created:
            logger.info("File already in active queue: %s", resolved.name)
            return None

        outcomes = self.queue_manager.process_pending(cancel_event=self._stop_event)
        for outcome in outcomes:
            if self.on_conversion_callback:
                self.on_conversion_callback(outcome)
        return outcomes[-1] if outcomes else None

    def scan_once(self) -> list[ConversionOutcome]:
        """Perform a single scan pass over watch_dir (used for startup catch-up and deterministic testing)."""
        if not self.watch_dir.exists() or not self.watch_dir.is_dir():
            raise ValidationError(f"Watch directory does not exist or is not accessible: {self.watch_dir}")

        results: list[ConversionOutcome] = []
        for entry in sorted(self.watch_dir.iterdir()):
            if self._stop_event.is_set():
                break
            if entry.is_file():
                outcome = self.handle_candidate_file(entry)
                if outcome is not None:
                    results.append(outcome)
        return results

    def start(self, max_runtime_seconds: float | None = None) -> None:
        """Start continuous folder monitoring until Ctrl+C or stop() is called."""
        if not self.watch_dir.exists() or not self.watch_dir.is_dir():
            raise ValidationError(f"Watch directory does not exist: {self.watch_dir}")

        logger.info(
            "Starting folder watcher on %s -> %s (backend=%s)",
            self.watch_dir,
            self.output_dir,
            "watchdog" if HAS_WATCHDOG else "polling-fallback",
        )
        start_time = time.monotonic()

        # Initial pass for files already sitting in incoming/
        self.scan_once()

        if HAS_WATCHDOG and Observer is not None:
            watcher_self = self

            class _Handler(FileSystemEventHandler):  # type: ignore[misc]
                def on_created(self, event: FileSystemEvent) -> None:
                    if not getattr(event, "is_directory", False):
                        watcher_self.handle_candidate_file(Path(str(getattr(event, "src_path", ""))))

                def on_moved(self, event: FileSystemEvent) -> None:
                    if not getattr(event, "is_directory", False):
                        dest = getattr(event, "dest_path", "")
                        if dest:
                            watcher_self.handle_candidate_file(Path(str(dest)))

            observer = Observer()
            observer.schedule(_Handler(), str(self.watch_dir), recursive=False)
            observer.start()
            try:
                while not self._stop_event.is_set():
                    if max_runtime_seconds and (time.monotonic() - start_time) >= max_runtime_seconds:
                        break
                    time.sleep(0.25)
            except KeyboardInterrupt:
                logger.info("Folder watcher received KeyboardInterrupt; shutting down gracefully.")
            finally:
                self._stop_event.set()
                observer.stop()
                observer.join(timeout=5.0)
        else:
            try:
                while not self._stop_event.is_set():
                    if max_runtime_seconds and (time.monotonic() - start_time) >= max_runtime_seconds:
                        break
                    self.scan_once()
                    time.sleep(self.poll_interval)
            except KeyboardInterrupt:
                logger.info("Folder watcher received KeyboardInterrupt; shutting down gracefully.")
            finally:
                self._stop_event.set()

    def stop(self) -> None:
        """Signal the folder watcher to stop gracefully."""
        self._stop_event.set()
