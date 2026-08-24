@echo off
setlocal EnableExtensions
for %%I in ("%~dp0..") do set "KIT=%%~fI"
for %%I in ("%KIT%\..\..") do set "PROJECT=%%~fI"
set "PWSH="
if exist "%PROJECT%\system_core\powershell\pwsh.exe" set "PWSH=%PROJECT%\system_core\powershell\pwsh.exe"
if not defined PWSH ( where pwsh.exe >nul 2>&1 && set "PWSH=pwsh.exe" )
if not defined PWSH set "PWSH=powershell.exe"
"%PWSH%" -NoProfile -ExecutionPolicy Bypass -File "%KIT%\AI-Backup.ps1" -Mode Export %*
set "EXIT_CODE=%ERRORLEVEL%"
echo.
if not defined AUDION_NO_PAUSE pause
exit /b %EXIT_CODE%
