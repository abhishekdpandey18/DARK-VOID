#!/usr/bin/env bash
# DARK VOID - Streamlined One-Step Installer Wrapper
# Delegates to universal cross-platform install.py
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "${SCRIPT_DIR}/install.py" ]; then
    exec python3 "${SCRIPT_DIR}/install.py" "$@"
else
    exec python3 "${SCRIPT_DIR}/../install.py" "$@"
fi
