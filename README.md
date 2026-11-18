# DARK VOID

**Professional Python CLI Video Conversion Engine for DaVinci Resolve (DNxHR HQ QuickTime MOV)**

## 1. Project Name & Identity

* **Name**: `DARK VOID` (`darkvoid`)

* **Version**: `1.0.0`

* **Type**: Modular Python 3 Command-Line Application (Terminal-Only)

* **Target Platform**: Kali Linux, Debian-based Linux distributions, and POSIX terminals

## 2. Description

**DARK VOID** is a terminal-first Python CLI video conversion engine engineered to transcode common consumer and delivery formats (`MP4`, `MOV`, `MKV`, `AVI`) into edit-ready, DaVinci Resolve-compatible **DNxHR HQ** video with uncompressed **PCM S16LE** audio inside a **QuickTime MOV** (`.mov`) container.

## 3. Purpose

Linux builds of DaVinci Resolve (especially DaVinci Resolve Free on Linux) do not natively decode consumer H.264/H.265 MP4/MKV streams with AAC audio. DARK VOID replaces the legacy Bash-based *Convert Format Pro* (`convert.sh` and `watch.sh`) scripts with a hardened, modular Python package featuring real-time FFmpeg progress parsing, strict post-conversion FFprobe stream verification, atomic temporary-file handling, SQLite conversion history, sequential queue management, and automated incoming-folder monitoring.

## 4. Key Features

* **Guaranteed Original File Protection**: Never modifies, moves, or deletes source files. Writes to isolated `.darkvoid_tmp_*.mov` files and atomically renames to `<stem>_Resolve.mov` only after FFprobe verification passes.

* **Mandatory DaVinci Resolve Specification**: Enforces `-c:v dnxhd -profile:v dnxhr_hq -pix_fmt yuv422p` and `-c:a pcm_s16le` inside `.mov` containers, while automatically detecting and preserving video-only inputs (`-an`) without failing.

* **Strict Post-Conversion Verification**: Verifies nonzero output size, `mov` container, `dnxhd` codec, `DNxHR HQ` profile, and `pcm_s16le` audio via FFprobe before marking any job `Completed`.

* **Real-Time Telemetry**: Parses FFmpeg `-progress pipe:1` output in real time to display percentage, frame count, encoding speed, output timestamp, elapsed time, and ETA.

* **Fast Multi-Offset Deduplication**: Computes SHA-256 fingerprints across file size plus first/middle/last 64 KB blocks in `<2 ms`—preventing duplicate conversions without hashing gigabytes of media into RAM.

* **Automated Folder Monitoring**: Watches incoming directories via `watchdog` (with built-in stat-polling fallback) and verifies file copy completion before queuing conversions.

* **Persistent SQLite History & Queue**: Tracks every job, supports `--success` / `--failed` filtering, keyword search, and one-command retry of failed jobs.

* **Cyberpunk Terminal UI & Automation Modes**: Styled with `Rich` panels and tables, an optional interactive menu (`darkvoid`), `--no-banner`, `--quiet`, and `--json` output for scripting.

## 5. Terminal Demonstration

```
╔══════════════════════════════════════════════════════════════════════════════╗
║   ██████╗  █████╗ ██████╗ ██╗  ██╗    ██╗   ██╗ ██████╗ ██╗██████╗           ║
║   ██╔══██╗██╔══██╗██╔══██╗██║ ██╔╝    ██║   ██║██╔═══██╗██║██╔══██╗          ║
║   ██║  ██║███████║██████╔╝█████╔╝     ██║   ██║██║   ██║██║██║  ██║          ║
║   ██║  ██║██╔══██║██╔══██╗██╔═██╗     ╚██╗ ██╔╝██║   ██║██║██║  ██║          ║
║   ██████╔╝██║  ██║██║  ██║██║  ██╗     ╚████╔╝ ╚██████╔╝██║██████╔╝          ║
║   ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝      ╚═══╝   ╚═════╝ ╚═╝╚═════╝           ║
║  ADVANCED VIDEO CONVERSION ENGINE  |  DNxHR HQ  •  PCM S16LE  •  QUICKTIME   ║
║  ──────────────────────────────────────────────────────────────────────────  ║
║  Version: 1.0.0   Python: 3.11.2   FFmpeg: ONLINE   FFprobe: ONLINE          ║
╚══════════════════════════════════════════════════════════════════════════════╝

╭─ DARK VOID :: INTERACTIVE TERMINAL ─╮
│                                     │
│   [01] Convert Video                │
│   [02] Batch Conversion             │
│   [03] Video Information            │
│   [04] Conversion Queue             │
│   [05] Folder Monitoring            │
│   [06] Conversion History           │
│   [07] System Diagnostics           │
│   [08] Settings                     │
│   [09] Exit                         │
│                                     │
╰─────────────────────────────────────╯

```

## 6. Technology Stack

| Component | Technology | Notes | 
| ----- | ----- | ----- | 
| **Language** | Python 3.10+ | Type-annotated modular architecture | 
| **CLI Framework** | Click / Typer | Console script entry point `darkvoid = darkvoid.cli:app` | 
| **Terminal UI** | Rich | Panels, tables, progress bars, prompts, pipe-safe output | 
| **ASCII Branding** | PyFiglet + Built-in Block Fallback | Renders banner with or without `pyfiglet` installed | 
| **Video Engine** | FFmpeg (`dnxhd` / `dnxhr_hq`) | Subprocess list execution (`shell=False`), `-progress pipe:1` | 
| **Metadata & Verification** | FFprobe | JSON stream inspection before and after conversion | 
| **Folder Monitoring** | Watchdog + Stat-Polling Fallback | Inotify events via `watchdog` or lightweight stat polling | 
| **Database** | SQLite3 (`sqlite3`) | Parameterized queries for history and persistent job queue | 
| **Testing** | Pytest / `unittest` | Unit, integration, and real FFmpeg conversion test suite | 

## 7. System Requirements

* **OS**: Kali Linux Rolling, Debian 12+, Ubuntu 22.04+, or any modern Linux distribution

* **Python**: `3.10` or newer (`python3`, `python3-venv`, `python3-pip`)

* **FFmpeg & FFprobe**: Version 4.4+ or 5.x/6.x with `dnxhd` and `pcm_s16le` encoders enabled

* **Disk Space**: DNxHR HQ is an intra-frame mezzanine codec; ensure sufficient free disk space in your output directory

## 8. Installation

### Automated Installation (Recommended for Kali / Debian)

```
git clone <repository-url> DARK-VOID
cd DARK-VOID
./scripts/install.sh

```

The installer creates an isolated virtual environment at `~/.local/share/darkvoid/venv` and symlinks the `darkvoid` binary into `~/.local/bin/darkvoid` (never uses `sudo pip` or modifies system Python packages). Ensure `~/.local/bin` is on your `PATH`:

```
export PATH="$HOME/.local/bin:$PATH"

```

### Manual Virtual Environment Installation

```
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[full,dev]"
darkvoid doctor

```

### Uninstallation

```
./scripts/uninstall.sh

```

Uninstalling removes only the isolated virtual environment and launcher link while preserving your converted videos (`Convert-Workspace/`) and SQLite conversion history (`~/.config/darkvoid/`).

## 9. FFmpeg Setup

On Kali Linux or Debian/Ubuntu, install FFmpeg and FFprobe via APT:

```
sudo apt update && sudo apt install -y ffmpeg

```

Verify DNxHR HQ encoder readiness with:

```
darkvoid doctor

```

## 10. Usage Examples

```
# Launch interactive cyberpunk menu
darkvoid

# Run system diagnostics
darkvoid doctor

# Inspect video metadata via FFprobe
darkvoid info sample.mp4
darkvoid info sample.mp4 --json

# Convert a single video to sample_Resolve.mov
darkvoid convert sample.mp4

# Convert multiple videos to a custom output folder
darkvoid convert clip1.mp4 clip2.mkv --output ./Converted/

# Batch convert a directory recursively
darkvoid convert ./videos/ --output ./Converted/ --recursive

# Dry-run mode (validate and show exact FFmpeg command without encoding)
darkvoid convert sample.mp4 --dry-run

# Monitor an incoming folder automatically
darkvoid watch ./Convert-Workspace/incoming/ --output ./Convert-Workspace/converted/

# View conversion queue, clear pending jobs, or retry failed jobs
darkvoid queue
darkvoid queue clear --yes
darkvoid queue retry

# View persistent conversion history
darkvoid history
darkvoid history --success
darkvoid history --failed

# View and update configuration
darkvoid config show
darkvoid config set existing_output_policy rename
darkvoid config reset

# View application logs
darkvoid logs --lines 50

```

## 11. Command Reference

| Command | Description | Key Options | 
| ----- | ----- | ----- | 
| `darkvoid` | Launch startup banner and interactive terminal menu | `--version`, `--no-banner`, `--verbose`, `--quiet` | 
| `darkvoid convert <inputs...>` | Convert file(s) or directories to DNxHR HQ `.mov` | `-o/--output`, `-r/--recursive`, `--existing [skip|rename|fail]`, `-f/--force`, `--dry-run`, `--json` | 
| `darkvoid info <video>` | Display detailed stream metadata via FFprobe | `--json` | 
| `darkvoid queue` | List queued and active conversion jobs | `-s/--status`, `--json` | 
| `darkvoid queue clear` | Remove pending jobs from the queue | `-y/--yes` | 
| `darkvoid queue retry` | Re-queue and execute failed/cancelled jobs | *(none)* | 
| `darkvoid watch [dir]` | Watch incoming directory and convert new files | `-o/--output`, `--once` | 
| `darkvoid history` | Show persistent SQLite conversion history | `--success`, `--failed`, `-q/--search`, `-n/--limit`, `--json` | 
| `darkvoid config show` | Show active configuration settings | `--json` | 
| `darkvoid config set <k> <v>` | Persist a configuration setting | *(none)* | 
| `darkvoid config reset` | Restore default configuration | *(none)* | 
| `darkvoid doctor` | Verify Python, FFmpeg, FFprobe, DNxHR, and disk space | `--json` | 
| `darkvoid logs` | View application log entries | `-n/--lines`, `-l/--level`, `-q/--search` | 

## 12. Conversion Specifications

| Property | Mandatory Value | Notes | 
| ----- | ----- | ----- | 
| **Supported Inputs** | `.mp4`, `.mov`, `.mkv`, `.avi` | Case-insensitive; validated via FFprobe stream inspection | 
| **Output Container** | QuickTime MOV (`.mov`) | Enforced via `-f mov` and verified post-conversion | 
| **Video Codec** | `dnxhd` (DNxHR) | FFmpeg VC3/DNxHD/DNxHR encoder | 
| **Video Profile** | `dnxhr_hq` (`DNxHR HQ`) | 8-bit 4:2:2 (`yuv422p`) mezzanine quality | 
| **Audio Codec** | `pcm_s16le` | Uncompressed 16-bit little-endian PCM (or `-an` if source has no audio) | 
| **Output Naming** | `<original_stem>_Resolve.mov` | Preserves spaces and special characters safely | 

Baseline FFmpeg command executed (as a safe subprocess argument list):

```
ffmpeg -nostdin -y -loglevel error -progress pipe:1 -i INPUT -map 0:v:0 -c:v dnxhd -profile:v dnxhr_hq -pix_fmt yuv422p -map 0:a:0? -c:a pcm_s16le -f mov TEMP_OUTPUT.mov

```

## 13. Configuration

User configuration is stored as JSON in `~/.config/darkvoid/config.json` (or `$DARKVOID_HOME/config.json`).
Default workspace structure (`Convert-Workspace/`):

* `Convert-Workspace/incoming/` — Default monitored folder

* `Convert-Workspace/converting/` — Temporary workspace

* `Convert-Workspace/converted/` — Verified `<stem>_Resolve.mov` outputs

* `Convert-Workspace/failed/` — Reserved for failed job artifacts

* `Convert-Workspace/logs/darkvoid.log` — Rotating application log

## 14. Project Structure

```
DARK-VOID/
├── darkvoid/
│   ├── __init__.py
│   ├── cli.py
│   ├── banner.py
│   ├── menu.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── converter.py
│   │   ├── ffmpeg.py
│   │   ├── ffprobe.py
│   │   ├── scanner.py
│   │   ├── queue.py
│   │   ├── watcher.py
│   │   └── verifier.py
│   ├── commands/
│   │   ├── __init__.py
│   │   ├── convert.py
│   │   ├── info.py
│   │   ├── queue.py
│   │   ├── watch.py
│   │   ├── history.py
│   │   ├── config.py
│   │   ├── doctor.py
│   │   └── logs.py
│   ├── database/
│   │   ├── __init__.py
│   │   ├── db.py
│   │   └── history.py
│   ├── ui/
│   │   ├── __init__.py
│   │   ├── console.py
│   │   ├── tables.py
│   │   ├── progress.py
│   │   └── themes.py
│   └── utils/
│       ├── __init__.py
│       ├── files.py
│       ├── validation.py
│       ├── paths.py
│       └── formatting.py
├── tests/
│   ├── helpers.py
│   ├── test_converter.py
│   ├── test_scanner.py
│   ├── test_queue.py
│   ├── test_verifier.py
│   ├── test_history.py
│   ├── test_watcher.py
│   └── test_cli.py
├── scripts/
│   ├── install.sh
│   └── uninstall.sh
├── legacy_reference/
│   ├── convert.sh
│   └── watch.sh
├── docs/
│   ├── ARCHITECTURE.md
│   └── MIGRATION_ANALYSIS.md
├── .github/
│   ├── ISSUE_TEMPLATE/bug_report.md
│   ├── PULL_REQUEST_TEMPLATE.md
│   └── workflows/tests.yml
├── pyproject.toml
├── requirements.txt
├── README.md
├── CONTRIBUTING.md
├── CHANGELOG.md
├── SECURITY.md
├── LICENSE
└── .gitignore

```

## 15. Testing

Run the full automated test suite (compatible with both `pytest` and standard library `unittest`):

```
python3 -m unittest discover -s tests -v
# or if pytest is installed:
pytest -v

```

## 16. Troubleshooting

* **`FFmpeg Executable: FAIL` in `darkvoid doctor`**: Install FFmpeg via `sudo apt update && sudo apt install -y ffmpeg` or point DARK VOID to a custom binary with `darkvoid config set ffmpeg_path /path/to/ffmpeg`.

* **`Insufficient disk space`**: DNxHR HQ produces high-bitrate mezzanine files. Use `--output /mnt/external/Converted` or `darkvoid config set output_dir /mnt/external/Converted`.

* **Skipped duplicate files**: When a file has already been converted, DARK VOID skips it by default. Pass `--force` (`darkvoid convert video.mp4 --force`) or set `--existing rename` to re-convert.

## 17. Known Limitations

* **Pause Behavior**: In accordance with POSIX/FFmpeg safety practices, `JobQueueManager.pause_scheduling()` stops scheduling subsequent pending queue jobs while allowing any currently executing FFmpeg subprocess to finish cleanly rather than sending `SIGSTOP` to an open file descriptor.

* **Substandard Resolutions in Legacy DNxHD**: Because DARK VOID uses `dnxhr_hq` (resolution-independent DNxHR), arbitrary resolutions are supported as long as dimensions are even integers compatible with `yuv422p`.

## 18. Contribution Instructions

See [CONTRIBUTING.md](CONTRIBUTING.md) for coding standards, security invariants, and pull request verification steps.

## 19. License Information

The license decision is intentionally left open for repository owner confirmation in [LICENSE](https://www.google.com/search?q=LICENSE). Confirm your preferred open-source license (e.g., MIT, Apache-2.0, or GPL-3.0) and copyright holder name before publishing.