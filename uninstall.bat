@echo off
REM DARK VOID — Windows Uninstaller
setlocal
where python >nul 2>nul
if %ERRORLEVEL% equ 0 (
    python "%~dp0install.py" --uninstall
    exit /b %ERRORLEVEL%
)
py -3 "%~dp0install.py" --uninstall
