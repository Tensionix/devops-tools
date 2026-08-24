@echo off
REM Audion WSL Backup launcher (PROMPT)
REM Messages intentionally in English (encoding-safe).

set DEFAULT_BACKUPDIR=%~dp0..\Backup

set /p NAME=Enter WSL distro name (e.g. Ubuntu): 
if "%NAME%"=="" goto :eof

set /p FORMAT=Format tar/vhd (default: tar): 
if "%FORMAT%"=="" set FORMAT=tar

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Audion-WSL-Toolkit.ps1" -Action backup -Name "%NAME%" -BackupDir "%DEFAULT_BACKUPDIR%" -Format "%FORMAT%"

echo.
echo Done. Press any key to close.
if not defined AUDION_NO_PAUSE pause >nul
