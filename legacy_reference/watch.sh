#!/usr/bin/env bash
# Legacy Reference: Convert Format Pro (watch.sh)
# Preserved for reference during migration to DARK VOID Python CLI.
# Replaced by darkvoid/core/watcher.py (Watchdog + stability verification + SQLite deduplication).
set -euo pipefail

WATCH_DIR="${1:-./incoming}"
OUTPUT_DIR="${2:-./converted}"
mkdir -p "$WATCH_DIR" "$OUTPUT_DIR"

echo "Monitoring $WATCH_DIR for incoming videos..."
if command -v inotifywait >/dev/null 2>&1; then
    inotifywait -m -e close_write,moved_to --format '%w%f' "$WATCH_DIR" | while read -r newfile; do
        "$(dirname "$0")/convert.sh" "$WATCH_DIR" "$OUTPUT_DIR"
    done
else
    echo "inotifywait not installed. Use 'darkvoid watch' instead."
    exit 1
fi
