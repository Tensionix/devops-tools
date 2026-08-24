@echo off
setlocal

rem Audion DevOps Tools - Windows Driver and Firmware Audit launcher
rem English output only to avoid console encoding issues.

set "SCRIPT_DIR=%~dp0"

rem This snippet sits three levels down, in tools\driver_firmware_audit\launcher_snippets,
rem and the addon it launches is already installed in the project. It used to go up
rem one level, which lands inside the addon folder itself, so a double-click here
rem only ever reported that the script was missing.
for %%I in ("%SCRIPT_DIR%..\..\..") do set "PROJECT_ROOT=%%~fI"
set "PS1=%PROJECT_ROOT%\system_core\diagnostics\Invoke-WindowsDriverFirmwareAudit.ps1"
set "LOGS=%PROJECT_ROOT%\logs"

if not exist "%PS1%" goto missing_script

set "PWSH=%PROJECT_ROOT%\system_core\powershell\pwsh.exe"
if exist "%PWSH%" goto run_audit

set "PWSH=pwsh.exe"

:run_audit
"%PWSH%" -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%PS1%" -OutputDir "%LOGS%" -OpenReport -Json -Csv
goto end

:missing_script
echo ERROR: Audit script not found:
echo %PS1%
if not defined AUDION_NO_PAUSE pause
goto end

:end
endlocal
