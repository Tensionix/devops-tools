@echo off
REM Audion WSL Clone launcher (PROMPT)
REM Messages intentionally in English (encoding-safe).

set DEFAULT_BACKUPDIR=%~dp0..\Backup
set DEFAULT_VHDXROOT=%~dp0..\VHDX

set /p NAME=Source distro name (e.g. Ubuntu): 
if "%NAME%"=="" goto :eof

set /p NEWNAME=New distro name (e.g. Ubuntu-Clone): 
if "%NEWNAME%"=="" goto :eof

echo Default location example: %DEFAULT_VHDXROOT%\%NEWNAME%
set /p LOCATION=New location: 
if "%LOCATION%"=="" goto :eof

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Audion-WSL-Toolkit.ps1" -Action clone -Name "%NAME%" -NewName "%NEWNAME%" -Location "%LOCATION%" -BackupDir "%DEFAULT_BACKUPDIR%"

echo.
echo Done. Press any key to close.
if not defined AUDION_NO_PAUSE pause >nul
