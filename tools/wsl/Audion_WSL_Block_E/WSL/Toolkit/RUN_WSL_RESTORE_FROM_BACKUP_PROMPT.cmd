@echo off
REM Audion WSL Restore-From-Backup launcher (PROMPT)
REM Messages intentionally in English (encoding-safe).

set DEFAULT_BACKUPDIR=%~dp0..\Backup
set DEFAULT_VHDXROOT=%~dp0..\VHDX

set /p NAME=Enter new distro name (e.g. Ubuntu): 
if "%NAME%"=="" goto :eof

echo Default location example: %DEFAULT_VHDXROOT%\%NAME%
set /p LOCATION=Enter install location: 
if "%LOCATION%"=="" goto :eof

echo Backup example: %DEFAULT_BACKUPDIR%\%NAME%\%NAME%_YYYYMMDD-HHMMSS.vhdx
set /p BACKUPFILE=Enter backup file (.tar/.vhd/.vhdx): 
if "%BACKUPFILE%"=="" goto :eof

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Audion-WSL-Toolkit.ps1" -Action restorefrombackup -Name "%NAME%" -Location "%LOCATION%" -BackupFile "%BACKUPFILE%"

echo.
echo Done. Press any key to close.
if not defined AUDION_NO_PAUSE pause >nul
