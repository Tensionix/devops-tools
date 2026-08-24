@echo off
setlocal

:: Re-launch as Administrator if needed
net session >nul 2>&1
if %errorlevel% neq 0 (
    if "%*"=="" (
        powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    ) else (
        powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -ArgumentList '%*' -Verb RunAs"
    )
    exit /b
)

set "SCRIPT_DIR=%~dp0"

where pwsh.exe >nul 2>&1
if not errorlevel 1 (
    set "PS_EXE=pwsh.exe"
    goto run
)

where powershell.exe >nul 2>&1
if not errorlevel 1 (
    set "PS_EXE=powershell.exe"
    goto run
)

echo ERROR: PowerShell was not found in PATH.
if not defined AUDION_NO_PAUSE pause
exit /b 1

:run
"%PS_EXE%" -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%Bitrix_Hosts_Toggle.ps1" %*
