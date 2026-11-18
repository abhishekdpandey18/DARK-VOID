# DARK VOID — Software Architecture

## High-Level Component Diagram

```
+-------------------------------------------------------------------+
|                   CLI & Presentation Layer                        |
|  darkvoid/cli.py  |  darkvoid/banner.py  |  darkvoid/menu.py      |
|  darkvoid/ui/ (themes.py, console.py, tables.py, progress.py)     |
+-------------------------------------------------------------------+
                                 |
                                 v
+-------------------------------------------------------------------+
|                     Command Handlers Layer                        |
|  convert.py | info.py | queue.py | watch.py | history.py | doctor |
+-------------------------------------------------------------------+
                                 |
                                 v
+-------------------------------------------------------------------+
|                     Core Processing Engine                        |
|  scanner.py -> ffprobe.py -> converter.py -> ffmpeg.py            |
|  verifier.py (Strict DNxHR HQ / PCM S16LE / MOV check)            |
|  queue.py (Sequential Job Queue) | watcher.py (Folder Monitor)    |
+-------------------------------------------------------------------+
                                 |
                                 v
+-------------------------------------------------------------------+
|                Persistence & Infrastructure Layer                 |
|  database/db.py & history.py (SQLite) | utils/paths.py (Config)   |
|  utils/files.py (Atomic Temp Files & Fast Fingerprinting)         |
+-------------------------------------------------------------------+
```

## Key Architectural Decisions

1. **Strict Separation of Concerns**: `darkvoid/core/` contains zero CLI framework dependencies and can be imported and tested directly as a Python library.
2. **Subprocess Safety & Real-Time Progress**: `darkvoid/core/ffmpeg.py` invokes `ffmpeg` via `subprocess.Popen` using explicit argument lists (`shell=False`), reading machine-readable `-progress pipe:1` key-value blocks on `stdout` while draining `stderr` on a background daemon thread to prevent pipe deadlocks.
3. **Atomic Output Verification**: `darkvoid/core/converter.py` writes to a hidden `.darkvoid_tmp_*.mov` file in the destination directory, runs `darkvoid/core/verifier.py` (which re-probes the output via `ffprobe` to confirm container `mov`, video codec `dnxhd`, profile `DNxHR HQ`, and audio codec `pcm_s16le`), and atomically renames the file to `<stem>_Resolve.mov`.
4. **Resilient Offline/Online Hybrid Fallbacks**: While `pyproject.toml` specifies `typer`, `pyfiglet`, and `watchdog` for full installations, DARK VOID includes built-in standard-library/Click fallbacks so it runs out-of-the-box on air-gapped or minimal Linux installations without crashing.
