@echo off
setlocal EnableExtensions DisableDelayedExpansion

set "SCRIPT_DIR=%~dp0"
set "PS1_FILE=%SCRIPT_DIR%Remove-WinRE-And-Extend-System.ps1"
set "PS_ENGINE="
set "EXITCODE=0"

if not exist "%PS1_FILE%" (
    echo [ERROR] PowerShell script not found: "%PS1_FILE%"
    set "EXITCODE=1"
    goto finish
)

call :find_ps_engine
if not defined PS_ENGINE (
    echo [ERROR] PowerShell engine not found. Install PowerShell 7 or use Windows PowerShell.
    set "EXITCODE=1"
    goto finish
)

call :is_admin
if errorlevel 1 goto elevate_ps1

echo [INFO] Using PowerShell engine: "%PS_ENGINE%"
echo [INFO] Running: "%PS1_FILE%"
echo.

"%PS_ENGINE%" -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%PS1_FILE%" -NoPause %*
set "EXITCODE=%ERRORLEVEL%"

echo.
if not "%EXITCODE%"=="0" echo [ERROR] Script exited with code %EXITCODE%.
goto finish

:elevate_ps1
echo [INFO] Administrator rights are required.
echo [INFO] Opening an elevated PowerShell window for the main script...

set "ELEVATE_CMD=Start-Process -Verb RunAs -FilePath '%ComSpec%' -ArgumentList '/c ""%PS_ENGINE%"" -NoLogo -NoProfile -ExecutionPolicy Bypass -File ""%PS1_FILE%"" %*'"
"%PS_ENGINE%" -NoLogo -NoProfile -ExecutionPolicy Bypass -Command "%ELEVATE_CMD%"

if errorlevel 1 (
    echo [ERROR] Elevation request was cancelled or failed.
    set "EXITCODE=1"
    goto finish
)

echo [OK] Elevated PowerShell window was launched.
exit /b 0

:find_ps_engine
if exist "%SCRIPT_DIR%pwsh.exe" set "PS_ENGINE=%SCRIPT_DIR%pwsh.exe" & exit /b 0
if exist "%SCRIPT_DIR%runtime\pwsh.exe" set "PS_ENGINE=%SCRIPT_DIR%runtime\pwsh.exe" & exit /b 0
if exist "S:\Audion\Tools\pwsh.exe" set "PS_ENGINE=S:\Audion\Tools\pwsh.exe" & exit /b 0
if exist "E:\Audion\Tools\pwsh.exe" set "PS_ENGINE=E:\Audion\Tools\pwsh.exe" & exit /b 0

for /f "delims=" %%I in ('where pwsh.exe 2^>nul') do if not defined PS_ENGINE set "PS_ENGINE=%%~fI"
if defined PS_ENGINE exit /b 0

if exist "%ProgramFiles%\PowerShell\7\pwsh.exe" set "PS_ENGINE=%ProgramFiles%\PowerShell\7\pwsh.exe" & exit /b 0
if exist "%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" set "PS_ENGINE=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" & exit /b 0

exit /b 1

:is_admin
"%PS_ENGINE%" -NoLogo -NoProfile -ExecutionPolicy Bypass -Command "$p = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent()); if ($p.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { exit 0 } else { exit 1 }" >nul 2>&1
exit /b %ERRORLEVEL%

:finish
echo.
if not defined AUDION_NO_PAUSE pause
exit /b %EXITCODE%
