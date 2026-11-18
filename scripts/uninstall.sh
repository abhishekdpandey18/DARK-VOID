#!/usr/bin/env bash
# DARK VOID - Streamlined Uninstaller Wrapper
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "${SCRIPT_DIR}/install.py" ]; then
    exec python3 "${SCRIPT_DIR}/install.py" --uninstall
else
    exec python3 "${SCRIPT_DIR}/../install.py" --uninstall
fi
