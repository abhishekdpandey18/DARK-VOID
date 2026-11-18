# DARK VOID — Windows PowerShell One-Step Installer
$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
python "$ScriptDir\install.py" @args
