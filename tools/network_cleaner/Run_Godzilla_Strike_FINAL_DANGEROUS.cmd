@echo off
setlocal EnableExtensions
cd /d "%~dp0"
set "ROOT=%~dp0"
set "PS1=%ROOT%system_core\Audion_Network_Cleaner.ps1"
set "MODE=GodzillaStrike"

if not exist "%PS1%" goto MissingScript

net session >nul 2>&1
if %errorlevel% neq 0 goto Elevate

goto RunScript

:Elevate
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -FilePath 'cmd.exe' -ArgumentList '/c cd /d ""%ROOT%"" && ""%~f0""' -Verb RunAs"
exit /b

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
