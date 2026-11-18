#!/usr/bin/env bash
# Top-level uninstaller wrapper for DARK VOID
set -euo pipefail
exec "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/scripts/uninstall.sh" "$@"
