#!/usr/bin/env bash
# DARK VOID - Safe Uninstaller
# Removes the isolated virtualenv and launcher symlink ONLY.
# Preserves user conversion history (~/.config/darkvoid) and converted media (Convert-Workspace/).
set -euo pipefail

VENV_DIR="${DARKVOID_VENV:-$HOME/.local/share/darkvoid/venv}"
BIN_DIR="${DARKVOID_BIN_DIR:-$HOME/.local/bin}"

echo "[DARK VOID] Removing launcher symlink and isolated virtual environment..."
if [ -L "${BIN_DIR}/darkvoid" ] || [ -f "${BIN_DIR}/darkvoid" ]; then
    rm -f "${BIN_DIR}/darkvoid"
    echo "  Removed ${BIN_DIR}/darkvoid"
fi

if [ -d "${VENV_DIR}" ]; then
    rm -rf "${VENV_DIR}"
    echo "  Removed ${VENV_DIR}"
fi

echo "[DARK VOID] Uninstall complete."
echo "  NOTE: Your converted media (Convert-Workspace/) and SQLite conversion history (~/.config/darkvoid/) were preserved."
