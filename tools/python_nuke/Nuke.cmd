@echo off
REM ==========================================================================
REM Python Nuke - UAC-elevating launcher
REM ==========================================================================
REM   Double-click. Self-elevates via UAC, shows a menu, runs Invoke-PythonNuke
REM   with pwsh 7 (or PS 5.1 fallback). Mirrors the Codex Nuke pattern.
REM ==========================================================================

setlocal ENABLEEXTENSIONS ENABLEDELAYEDEXPANSION

REM --- Self-elevate via powershell.exe (always present) ---------------------
fltmc >nul 2>&1
if errorlevel 1 (
    echo [Nuke] Requesting administrator rights via UAC...
    powershell -NoProfile -Command "Start-Process -FilePath cmd.exe -ArgumentList @('/c','%~f0') -Verb RunAs"
    if errorlevel 1 (
        echo [Nuke] UAC elevation failed or was declined.
        if not defined AUDION_NO_PAUSE pause
        exit /b 3
    )
    exit /b 0
)

REM --- Pick PowerShell host: pwsh 7 preferred, fallback PS 5.1 --------------
set "PSHOST="
where pwsh >nul 2>&1 && set "PSHOST=pwsh"
if not defined PSHOST (
    where powershell >nul 2>&1 && set "PSHOST=powershell"
)
if not defined PSHOST (
    echo [Nuke] ERROR: Neither pwsh nor powershell found in PATH.
    if not defined AUDION_NO_PAUSE pause
    exit /b 2
)

cd /d "%~dp0"

set "PS1=%~dp0Invoke-PythonNuke.ps1"
if not exist "%PS1%" (
    echo [Nuke] ERROR: Invoke-PythonNuke.ps1 not found next to this launcher.
    echo        Expected: %PS1%
    if not defined AUDION_NO_PAUSE pause
    exit /b 1
)

for /f "delims=" %%V in ('%PSHOST% -NoProfile -Command "$PSVersionTable.PSVersion.ToString()"') do set "PSVER=%%V"

:MENU
cls
echo ============================================================
echo                       PYTHON NUKE
echo ============================================================
echo  Current user : %USERNAME% (elevated)
echo  PS host      : %PSHOST%  (v%PSVER%)
echo  Folder       : %~dp0
echo ------------------------------------------------------------
echo  Pick a mode:
echo     [1] Audit     - read-only scan, no changes
echo     [2] DryRun    - simulate full nuke, no changes
echo     [3] NUKE      - actually remove Python everything
echo     [4] Nuke + KeepWinget  (skip the winget uninstall pass)
echo     [Q] Quit
echo ============================================================
echo  This will remove: vanilla Python, Store Python (AppX), Python
echo  Launcher (py.exe), pipx, uv, conda (Miniconda/Anaconda system
echo  and user), pip caches/config, env vars, Start Menu shortcuts,
echo  PATH entries, and uninstall registry entries.
echo.
echo  This will NOT touch: project venvs, ChatGPT app, anything in
echo  this tool folder itself.
echo ------------------------------------------------------------
set "choice="
set /p choice="Your choice: "

if /I "%choice%"=="1" goto AUDIT
if /I "%choice%"=="2" goto DRYRUN
if /I "%choice%"=="3" goto NUKE
if /I "%choice%"=="4" goto NUKE_KEEPWINGET
if /I "%choice%"=="Q" goto END
goto MENU

:AUDIT
echo.
echo [Nuke] Running AUDIT (read-only)...
%PSHOST% -NoProfile -ExecutionPolicy Bypass -File "%PS1%" -Mode Audit
goto AFTER

:DRYRUN
echo.
echo [Nuke] Running DRY-RUN (no changes)...
%PSHOST% -NoProfile -ExecutionPolicy Bypass -File "%PS1%" -Mode DryRun
goto AFTER

:NUKE
echo.
echo [Nuke] CONFIRMATION REQUIRED.
set "confirm="
set /p confirm="Type NUKE to confirm full destructive removal: "
if /I not "%confirm%"=="NUKE" (
    echo [Nuke] Cancelled.
    goto AFTER
)
echo.
echo [Nuke] Executing full nuke...
%PSHOST% -NoProfile -ExecutionPolicy Bypass -File "%PS1%" -Mode Nuke
goto AFTER

:NUKE_KEEPWINGET
echo.
set "confirm="
set /p confirm="Type NUKE to confirm (KeepWinget mode): "
if /I not "%confirm%"=="NUKE" (
    echo [Nuke] Cancelled.
    goto AFTER
)
echo.
%PSHOST% -NoProfile -ExecutionPolicy Bypass -File "%PS1%" -Mode Nuke -KeepWinget
goto AFTER

:AFTER
echo.
echo ============================================================
echo  Exit code from script: %ERRORLEVEL%
echo    0       = no remaining Python artifacts detected
echo    1..N    = that many artifacts remain (see Logs\)
echo    255     = fatal error
echo ============================================================
echo.
echo  NOTE: After a real Nuke, REBOOT before reinstalling Python.
echo        Some env vars only fully clear after a fresh login.
echo.
if not defined AUDION_NO_PAUSE pause
goto MENU

:END
endlocal
exit /b 0
