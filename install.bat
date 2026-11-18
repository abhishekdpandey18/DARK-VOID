@echo off
REM DARK VOID — One-Step Windows Installer (Command Prompt / Explorer Double-Click)
setlocal
where python >nul 2>nul
if %ERRORLEVEL% equ 0 (
    python "%~dp0install.py" %*
    exit /b %ERRORLEVEL%
)
where py >nul 2>nul
if %ERRORLEVEL% equ 0 (
    py -3 "%~dp0install.py" %*
    exit /b %ERRORLEVEL%
)
echo [ERROR] Python 3.10+ is not installed or not in PATH.
echo Install Python on Windows with: winget install -e --id Python.Python.3.11
exit /b 1
