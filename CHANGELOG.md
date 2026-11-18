# Changelog

All notable changes to **DARK VOID** are documented in this file.

## [1.0.0] - 2026-11-18
### Added
- Complete modular Python CLI architecture (`darkvoid`) replacing the legacy Bash `Convert Format Pro` scripts (`convert.sh`, `watch.sh`).
- Core conversion engine (`darkvoid/core/converter.py`, `ffmpeg.py`, `ffprobe.py`, `verifier.py`) enforcing DNxHR HQ (`-c:v dnxhd -profile:v dnxhr_hq -pix_fmt yuv422p`) and `pcm_s16le` audio inside QuickTime `.mov` containers.
- Automatic detection and handling of video-only inputs (gracefully omitting `-c:a pcm_s16le` with `-an` when no audio stream is present).
- Real-time FFmpeg machine-readable progress parsing (`-progress pipe:1`) with Rich progress bars showing percentage, frame count, speed, output timestamp, and ETA.
- Strict post-conversion FFprobe output verification before atomic temporary-to-final file replacement.
- Fast multi-offset SHA-256 + file-size fingerprinting (`compute_fast_file_fingerprint`) for instant duplicate detection without reading gigabytes of video into memory.
- SQLite persistent history and job queue (`darkvoid/database/db.py`, `history.py`, `darkvoid/core/queue.py`) with corruption recovery, filtering, search, and retry support.
- Automated folder monitoring (`darkvoid/core/watcher.py`) with Watchdog (`inotify`) and built-in stat-polling fallback, including file copy stability verification.
- Cyberpunk Rich CLI interface, startup ASCII banner (`--no-banner` supported), interactive terminal menu (`01`–`09`), and `darkvoid doctor` diagnostics.
