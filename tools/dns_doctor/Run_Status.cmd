@echo off
setlocal EnableExtensions
cd /d "%~dp0"
set "ROOT=%~dp0"
set "PS1=%ROOT%system_core\Audion_Dns_Doctor.ps1"
set "MODE=Status"

rem Look only: adapters, resolver, port 53, tray icon. Changes nothing.

if not exist "%PS1%" goto MissingScript

goto RunScript

:RunScript
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%PS1%" -Mode %MODE%
echo.
if not defined AUDION_NO_PAUSE pause
exit /b %errorlevel%

:MissingScript
echo ERROR: PowerShell engine was not found.
echo Expected path:
echo %PS1%
echo.
if not defined AUDION_NO_PAUSE pause
exit /b 1
