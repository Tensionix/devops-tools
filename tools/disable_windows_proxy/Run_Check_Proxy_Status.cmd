@echo off
setlocal EnableExtensions
set "ROOT=%~dp0"
set "PS1=%ROOT%system_core\proxy\Proxy-Tool.ps1"
set "PWSH=%ROOT%system_core\powershell\pwsh.exe"

if exist "%PS1%" goto FindPowerShell

echo ERROR: PowerShell script was not found.
echo Expected: %PS1%
echo.
if not defined AUDION_NO_PAUSE pause
exit /b 1

:FindPowerShell
if exist "%PWSH%" goto Run
where pwsh.exe >nul 2>nul
if errorlevel 1 goto TryWindowsPowerShell
for /f "delims=" %%P in ('where pwsh.exe 2^>nul') do set "PWSH=%%P"& goto Run

:TryWindowsPowerShell
where powershell.exe >nul 2>nul
if errorlevel 1 goto NoPowerShell
for /f "delims=" %%P in ('where powershell.exe 2^>nul') do set "PWSH=%%P"& goto Run

:NoPowerShell
echo ERROR: No PowerShell engine found.
echo Install PowerShell or use Windows PowerShell if available.
echo.
if not defined AUDION_NO_PAUSE pause
exit /b 1

:Run
"%PWSH%" -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%PS1%" -Action Status
echo.
if not defined AUDION_NO_PAUSE pause
exit /b %ERRORLEVEL%
