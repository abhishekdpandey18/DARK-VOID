#!/usr/bin/env bash
# Top-level one-step installer wrapper for DARK VOID
set -euo pipefail
exec "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/scripts/install.sh" "$@"
