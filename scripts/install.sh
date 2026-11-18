#!/usr/bin/env bash
# DARK VOID - Safe Virtual-Environment Installer for Kali Linux / Debian
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${DARKVOID_VENV:-$HOME/.local/share/darkvoid/venv}"
BIN_DIR="${DARKVOID_BIN_DIR:-$HOME/.local/bin}"

echo "[DARK VOID] Starting installation..."
echo "  Project Root : ${PROJECT_ROOT}"
echo "  Virtualenv   : ${VENV_DIR}"
echo "  Launcher Dir : ${BIN_DIR}"

if ! command -v python3 >/dev/null 2>&1; then
    echo "[ERROR] python3 is not installed. Install with: sudo apt update && sudo apt install -y python3 python3-venv python3-pip" >&2
    exit 1
fi

if ! command -v ffmpeg >/dev/null 2>&1 || ! command -v ffprobe >/dev/null 2>&1; then
    echo "[WARNING] ffmpeg / ffprobe not detected in PATH."
    echo "          Install on Kali/Debian with: sudo apt update && sudo apt install -y ffmpeg"
fi

mkdir -p "$(dirname "${VENV_DIR}")" "${BIN_DIR}"

if [ ! -d "${VENV_DIR}" ]; then
    if python3 -m venv --system-site-packages "${VENV_DIR}" 2>/dev/null; then
        echo "[DARK VOID] Created virtual environment with pip."
    else
        rm -rf "${VENV_DIR}"
        echo "[DARK VOID] ensurepip not installed; creating virtual environment with --without-pip..."
        python3 -m venv --system-site-packages --without-pip "${VENV_DIR}"
    fi
fi

if [ -x "${VENV_DIR}/bin/pip" ]; then
    if "${VENV_DIR}/bin/pip" install --no-build-isolation --no-deps -e "${PROJECT_ROOT}" >/dev/null 2>&1; then
        echo "[DARK VOID] Installed darkvoid package via pip."
    else
        "${VENV_DIR}/bin/pip" install "${PROJECT_ROOT}"
    fi
else
    SITE_PKG="$("${VENV_DIR}/bin/python3" -c 'import site; print(site.getsitepackages()[0])')"
    mkdir -p "${SITE_PKG}"
    echo "${PROJECT_ROOT}" > "${SITE_PKG}/darkvoid.pth"
    cat > "${VENV_DIR}/bin/darkvoid" <<EOF
#!${VENV_DIR}/bin/python3
import sys
from darkvoid.cli import app
if __name__ == "__main__":
    sys.exit(app())
EOF
    chmod +x "${VENV_DIR}/bin/darkvoid"
    echo "[DARK VOID] Configured editable .pth link and console entry point in ${VENV_DIR}/bin/darkvoid."
fi

ln -sf "${VENV_DIR}/bin/darkvoid" "${BIN_DIR}/darkvoid"
echo "[DARK VOID] Linked executable: ${BIN_DIR}/darkvoid"
echo "[DARK VOID] Installation complete! Run 'darkvoid --help' or 'darkvoid doctor' to verify."
