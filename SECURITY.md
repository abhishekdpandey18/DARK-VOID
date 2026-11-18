# Security Policy — DARK VOID

## Security Design Principles
DARK VOID is engineered as a local-first, offline-capable media processing CLI with strict security controls:

1. **Zero Shell Injection Surface**: Every external `ffmpeg` and `ffprobe` invocation uses `subprocess.Popen` or `subprocess.run` with explicit argument lists. `shell=True` is strictly prohibited throughout the codebase.
2. **Original Media Immutability**: Source video files are opened strictly read-only. Conversions write to an isolated `.darkvoid_tmp_<stem>_<token>.mov` temporary file and only move into the final `<stem>_Resolve.mov` path after passing FFprobe verification.
3. **Parameterized SQL Queries**: All SQLite queries in `darkvoid/database/` use `?` parameter binding to prevent SQL injection even when filenames contain quotes or special characters.
4. **Input & Executable Validation**: Paths are checked for null bytes, directory traversal, file type, read permissions, and stream validity via FFprobe prior to conversion.
5. **No Network Telemetry**: DARK VOID operates 100% locally without accounts, API keys, or outbound network connections.

## Reporting a Vulnerability
Please report suspected security vulnerabilities privately to the repository maintainer before disclosing them publicly. Include steps to reproduce and output from `darkvoid doctor`.
