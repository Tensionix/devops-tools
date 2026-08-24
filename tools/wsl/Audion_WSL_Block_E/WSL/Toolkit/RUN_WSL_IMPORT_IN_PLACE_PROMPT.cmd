@echo off
REM Audion WSL Import-In-Place launcher (PROMPT)
REM Registers an existing ext4.vhdx after Windows restore.
REM Messages intentionally in English (encoding-safe).

set DEFAULT_VHDXROOT=%~dp0..\VHDX

set /p NAME=Enter new distro name (e.g. Ubuntu): 
if "%NAME%"=="" goto :eof

echo Default VHDX example: %DEFAULT_VHDXROOT%\Ubuntu\ext4.vhdx
set /p VHDX=Enter full path to ext4.vhdx: 
if "%VHDX%"=="" goto :eof

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Audion-WSL-Toolkit.ps1" -Action importinplace -Name "%NAME%" -VhdxPath "%VHDX%"

echo.
echo Done. Press any key to close.
if not defined AUDION_NO_PAUSE pause >nul
