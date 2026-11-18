#!/usr/bin/env bash
# Legacy Reference: Convert Format Pro (convert.sh)
# Preserved for reference during migration to DARK VOID Python CLI.
# Baseline command: ffmpeg -i "$INPUT" -c:v dnxhd -profile:v dnxhr_hq -c:a pcm_s16le "$OUTPUT"
set -euo pipefail

INPUT_DIR="${1:-./incoming}"
OUTPUT_DIR="${2:-./converted}"
mkdir -p "$OUTPUT_DIR"

shopt -s nullglob nocaseglob
for filepath in "$INPUT_DIR"/*.{mp4,mov,mkv,avi}; do
    [ -e "$filepath" ] || continue
    filename="$(basename -- "$filepath")"
    stem="${filename%.*}"
    outpath="$OUTPUT_DIR/${stem}_Resolve.mov"
    if [ -f "$outpath" ]; then
        echo "[SKIP] Output already exists: $outpath"
        continue
    fi
    ffmpeg -nostdin -i "$filepath" -c:v dnxhd -profile:v dnxhr_hq -c:a pcm_s16le "$outpath"
done
