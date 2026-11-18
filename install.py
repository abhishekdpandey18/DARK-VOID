#!/usr/bin/env python3
"""DARK VOID — Universal Cross-Platform One-Step Installer (Linux, Windows, macOS).

Usage:
    python install.py              # Standard self-contained user installation
    python install.py --auto-deps  # Also install FFmpeg automatically via apt (Linux) or winget (Windows)
    python install.py --uninstall  # Remove DARK VOID cleanly while preserving converted videos & history
"""

from __future__ import annotations

import compileall
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

IS_WINDOWS = os.name == "nt" or sys.platform.startswith("win")


def get_install_paths() -> tuple[Path, Path, Path, Path]:
    """Return (install_base, app_lib_dir, venv_dir, bin_dir) for the current OS."""
    env_base = os.environ.get("DARKVOID_INSTALL_BASE")
    if env_base:
        install_base = Path(env_base).expanduser().resolve()
    elif IS_WINDOWS:
        local_app = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        install_base = Path(local_app).expanduser().resolve() / "darkvoid"
    else:
        install_base = Path.home() / ".local" / "share" / "darkvoid"

    app_lib_dir = install_base / "app"
    venv_dir = Path(os.environ.get("DARKVOID_VENV", str(install_base / "venv"))).expanduser().resolve()

    if "DARKVOID_BIN_DIR" in os.environ:
        bin_dir = Path(os.environ["DARKVOID_BIN_DIR"]).expanduser().resolve()
    elif IS_WINDOWS:
        bin_dir = install_base / "bin"
    else:
        bin_dir = Path.home() / ".local" / "bin"

    return install_base, app_lib_dir, venv_dir, bin_dir


def ensure_system_ffmpeg(auto_deps: bool) -> None:
    """Check for FFmpeg and optionally install via apt (Linux) or winget (Windows)."""
    if shutil.which("ffmpeg") and shutil.which("ffprobe"):
        return
    if not auto_deps:
        print("[WARNING] ffmpeg / ffprobe not detected in PATH.")
        if IS_WINDOWS:
            print("          Install on Windows with: winget install --id Gyan.FFmpeg -e")
            print("          Or re-run: python install.py --auto-deps")
        else:
            print("          Install on Kali/Debian with: sudo apt update && sudo apt install -y ffmpeg")
            print("          Or re-run: python3 install.py --auto-deps")
        return

    if IS_WINDOWS and shutil.which("winget"):
        print("[1/4] Installing FFmpeg via Windows Package Manager (winget)...")
        subprocess.run(["winget", "install", "--id", "Gyan.FFmpeg", "-e", "--silent"], check=False)
    elif not IS_WINDOWS and shutil.which("apt-get"):
        print("[1/4] Installing FFmpeg and Python venv packages via apt...")
        subprocess.run(["sudo", "apt-get", "update"], check=False)
        subprocess.run(
            ["sudo", "apt-get", "install", "-y", "ffmpeg", "python3-venv", "python3-pip", "python3-rich", "python3-click"],
            check=False,
        )


def configure_user_path(bin_dir: Path) -> None:
    """Ensure bin_dir is on the user's persistent PATH across Windows, Linux, and macOS."""
    bin_str = str(bin_dir)
    if IS_WINDOWS:
        try:
            import winreg  # type: ignore[import-not-found]
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment", 0, winreg.KEY_ALL_ACCESS) as key:
                try:
                    current_path, reg_type = winreg.QueryValueEx(key, "Path")
                except FileNotFoundError:
                    current_path, reg_type = "", winreg.REG_EXPAND_SZ
                parts = [p.strip() for p in current_path.split(";") if p.strip()]
                if not any(p.lower() == bin_str.lower() for p in parts):
                    parts.append(bin_str)
                    winreg.SetValueEx(key, "Path", 0, reg_type, ";".join(parts))
                    print(f"      Added {bin_str} to Windows User PATH.")
        except Exception as exc:
            print(f"      [Note] Add {bin_str} to your Windows PATH ({exc}).")
    else:
        path_line = 'export PATH="$HOME/.local/bin:$PATH"'
        for rc_name in (".bashrc", ".zshrc"):
            rc_file = Path.home() / rc_name
            if rc_file.exists():
                content = rc_file.read_text(encoding="utf-8", errors="replace")
                if "/.local/bin" not in content and bin_str not in content:
                    with rc_file.open("a", encoding="utf-8") as fh:
                        fh.write(f"\n# Added by DARK VOID installer\n{path_line}\n")
                    print(f"      Added ~/.local/bin to ~/{rc_name}")


def run_uninstall() -> int:
    """Remove DARK VOID runtime and launchers while preserving user media and SQLite history."""
    install_base, _, venv_dir, bin_dir = get_install_paths()
    print("[DARK VOID] Removing launcher scripts and isolated runtime...")
    for name in ("darkvoid", "darkvoid.cmd", "darkvoid.bat", "darkvoid.ps1", "darkvoid.exe"):
        target = bin_dir / name
        if target.exists() or target.is_symlink():
            try:
                target.unlink()
                print(f"  Removed {target}")
            except OSError:
                pass

    for folder in (venv_dir, install_base):
        if folder.exists():
            shutil.rmtree(folder, ignore_errors=True)
            print(f"  Removed {folder}")

    print("[DARK VOID] Uninstall complete. Converted videos and SQLite conversion history were preserved.")
    return 0


def run_install(auto_deps: bool = False) -> int:
    """Perform a fast, self-contained installation on Linux, Windows, or macOS."""
    project_root = Path(__file__).resolve().parent
    if not (project_root / "darkvoid").is_dir():
        project_root = project_root.parent

    install_base, app_lib_dir, venv_dir, bin_dir = get_install_paths()

    print("==============================================================================")
    print(f"  DARK VOID v1.0.0 — Universal Installer ({'Windows' if IS_WINDOWS else 'Linux / POSIX'})")
    print("==============================================================================")

    ensure_system_ffmpeg(auto_deps)

    # 1. Stage standalone copy of package
    print(f"[1/4] Staging standalone application into {app_lib_dir}...")
    app_lib_dir.mkdir(parents=True, exist_ok=True)
    bin_dir.mkdir(parents=True, exist_ok=True)
    dest_pkg = app_lib_dir / "darkvoid"
    if dest_pkg.exists():
        shutil.rmtree(dest_pkg)
    shutil.copytree(project_root / "darkvoid", dest_pkg)
    shutil.copy2(project_root / "pyproject.toml", app_lib_dir / "pyproject.toml")
    if (project_root / "README.md").exists():
        shutil.copy2(project_root / "README.md", app_lib_dir / "README.md")

    # 2. Create virtual environment
    print(f"[2/4] Configuring isolated Python environment at {venv_dir}...")
    if not venv_dir.exists():
        res = subprocess.run(
            [sys.executable, "-m", "venv", "--system-site-packages", str(venv_dir)],
            capture_output=True,
        )
        if res.returncode != 0:
            shutil.rmtree(venv_dir, ignore_errors=True)
            subprocess.run(
                [sys.executable, "-m", "venv", "--system-site-packages", "--without-pip", str(venv_dir)],
                check=True,
            )

    venv_py = venv_dir / ("Scripts/python.exe" if IS_WINDOWS else "bin/python3")
    if not venv_py.exists():
        venv_py = venv_dir / ("Scripts/python.exe" if IS_WINDOWS else "bin/python")
    venv_pip = venv_dir / ("Scripts/pip.exe" if IS_WINDOWS else "bin/pip")

    if venv_pip.exists():
        # Install click and rich if not already present, then install app_lib_dir
        subprocess.run([str(venv_pip), "install", "--quiet", "--upgrade", str(app_lib_dir)], check=False)
        subprocess.run(
            [str(venv_pip), "install", "--quiet", "--no-build-isolation", "--no-deps", str(app_lib_dir)],
            check=False,
        )

    # Ensure .pth file points to app_lib_dir
    site_out = subprocess.run(
        [str(venv_py), "-c", "import site; print(site.getsitepackages()[0])"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    site_pkg = Path(site_out)
    site_pkg.mkdir(parents=True, exist_ok=True)
    (site_pkg / "darkvoid.pth").write_text(str(app_lib_dir) + "\n", encoding="utf-8")

    # Pre-compile optimized bytecode
    compileall.compile_dir(str(dest_pkg), quiet=1, optimize=1)

    # 3. Create OS-appropriate launcher scripts
    print(f"[3/4] Creating launcher in {bin_dir} and configuring PATH...")
    if IS_WINDOWS:
        cmd_launcher = bin_dir / "darkvoid.cmd"
        cmd_launcher.write_text(
            f'@echo off\r\n"{venv_py}" -O -m darkvoid.cli %*\r\n',
            encoding="utf-8",
        )
        ps1_launcher = bin_dir / "darkvoid.ps1"
        ps1_launcher.write_text(
            f'& "{venv_py}" -O -m darkvoid.cli @args\r\nexit $LASTEXITCODE\r\n',
            encoding="utf-8",
        )
        verify_bin = str(cmd_launcher)
    else:
        venv_launcher = venv_dir / "bin" / "darkvoid"
        venv_launcher.write_text(
            f"#!{venv_py} -O\nimport sys\nfrom darkvoid.cli import app\nif __name__ == '__main__':\n    sys.exit(app())\n",
            encoding="utf-8",
        )
        venv_launcher.chmod(venv_launcher.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        target_link = bin_dir / "darkvoid"
        if target_link.exists() or target_link.is_symlink():
            target_link.unlink()
        target_link.symlink_to(venv_launcher)
        verify_bin = str(target_link)

    configure_user_path(bin_dir)

    # 4. Verify executable
    print("[4/4] Verifying installation...")
    subprocess.run([verify_bin, "--version"], check=True)
    print("==============================================================================")
    print("  Installation complete! Run 'darkvoid' or 'darkvoid doctor' from any folder.")
    print("  (You can safely delete the downloaded ZIP/folder; DARK VOID is self-contained.)")
    print("==============================================================================")
    return 0


def main() -> int:
    args = set(sys.argv[1:])
    if "--uninstall" in args or "uninstall" in args:
        return run_uninstall()
    auto_deps = "--auto-deps" in args or "-y" in args
    return run_install(auto_deps=auto_deps)


if __name__ == "__main__":
    sys.exit(main())
