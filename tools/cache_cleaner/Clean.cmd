@echo off
REM ==========================================================================
REM Cache Cleaner - frees the system drive from caches that rebuild themselves
REM ==========================================================================
REM   Double-click. No admin rights needed: every cache is the current user's.
REM   Runs Invoke-CacheCleaner with pwsh 7 (or PS 5.1 fallback).
REM ==========================================================================

setlocal ENABLEEXTENSIONS
chcp 65001 >nul

set "PSHOST="
where pwsh >nul 2>&1 && set "PSHOST=pwsh"
if not defined PSHOST (
    where powershell >nul 2>&1 && set "PSHOST=powershell"
)
if not defined PSHOST (
    echo [Cache] ERROR: Neither pwsh nor powershell found in PATH.
    if not defined AUDION_NO_PAUSE pause
    exit /b 2
)

set "PS1=%~dp0Invoke-CacheCleaner.ps1"
if not exist "%PS1%" (
    echo [Cache] ERROR: Invoke-CacheCleaner.ps1 not found next to this launcher.
    if not defined AUDION_NO_PAUSE pause
    exit /b 1
)

:MENU
cls
echo ============================================================
echo                      CACHE CLEANER
echo ============================================================
echo  Caches: pip, npm, NuGet, Temp (older than 24 h), Adobe media
echo  cache. Every one is refilled by its program when needed.
echo ------------------------------------------------------------
echo     [1] Audit        - measure, change nothing
echo     [2] Clean        - clear the caches above
echo     [3] Clean + NuGet packages (next build downloads them again)
echo     [4] Chrome model - delete Chrome's local AI model and keep
echo                        it away (Chrome policy; close Chrome first)
echo     [5] Chrome model back - remove that policy
echo     [Q] Quit
echo ============================================================
set "choice="
set /p choice="Your choice: "

if /I "%choice%"=="1" %PSHOST% -NoProfile -ExecutionPolicy Bypass -File "%PS1%" -Mode Audit & goto AFTER
if /I "%choice%"=="2" %PSHOST% -NoProfile -ExecutionPolicy Bypass -File "%PS1%" -Mode Clean & goto AFTER
if /I "%choice%"=="3" %PSHOST% -NoProfile -ExecutionPolicy Bypass -File "%PS1%" -Mode Clean -NuGetPackages & goto AFTER
if /I "%choice%"=="4" %PSHOST% -NoProfile -ExecutionPolicy Bypass -File "%PS1%" -Mode Clean -Targets chrome & goto AFTER
if /I "%choice%"=="5" %PSHOST% -NoProfile -ExecutionPolicy Bypass -File "%PS1%" -ChromePolicyUndo & goto AFTER
if /I "%choice%"=="Q" goto END
goto MENU

:AFTER
echo.
if not defined AUDION_NO_PAUSE pause
goto MENU

:END
endlocal
exit /b 0
