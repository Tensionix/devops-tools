@echo off
REM Audion: Register ALL WSL distros from ..\VHDX\*\ext4.vhdx
REM Messages intentionally in English (encoding-safe).

set ROOT=%~dp0..\VHDX

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Register-All-WSL-VHDX.ps1" -Root "%ROOT%"

echo.
echo Done. Press any key to close.
if not defined AUDION_NO_PAUSE pause >nul
