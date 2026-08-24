@echo off
REM Audion CMD launcher (encoding-safe)

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Audion-WSL-Toolkit.ps1" -Action status

echo.
echo Done. Press any key to close.
if not defined AUDION_NO_PAUSE pause >nul
