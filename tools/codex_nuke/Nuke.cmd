@echo off
REM ==========================================================================
REM Codex Nuke - UAC-elevating launcher
REM ==========================================================================
REM   Double-click this file. It will:
REM     1. Re-launch itself elevated if not already admin (UAC prompt).
REM     2. Show a menu: Audit / DryRun / Nuke / Exit.
REM     3. Invoke Invoke-CodexNuke.ps1 with PowerShell 7 (pwsh) if installed,
REM        falling back to Windows PowerShell 5.1 (powershell.exe).
REM ==========================================================================

setlocal ENABLEEXTENSIONS ENABLEDELAYEDEXPANSION

REM --- Self-elevate -----------------------------------------------------------
REM The UAC step always uses powershell.exe (Windows PowerShell 5.1) because
REM it's present on every supported Windows. The actual work below picks pwsh
REM if available.
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

REM --- Pick PowerShell host for the actual work: prefer pwsh 7, fallback PS 5
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

set "PS1=%~dp0Invoke-CodexNuke.ps1"
if not exist "%PS1%" (
    echo [Nuke] ERROR: Invoke-CodexNuke.ps1 not found next to this launcher.
    echo        Expected: %PS1%
    if not defined AUDION_NO_PAUSE pause
    exit /b 1
)

REM Show which host got picked
for /f "delims=" %%V in ('%PSHOST% -NoProfile -Command "$PSVersionTable.PSVersion.ToString()"') do set "PSVER=%%V"

:MENU
cls
echo ============================================================
echo                       CODEX NUKE
echo ============================================================
echo  Current user : %USERNAME% (elevated)
echo  PS host      : %PSHOST%  (v%PSVER%)
echo  Folder       : %~dp0
echo ------------------------------------------------------------
echo  Pick a mode:
echo     [1] Audit          - read-only scan, no changes
echo     [2] DryRun         - simulate full nuke, no changes
echo     [3] NUKE           - actually delete everything Codex-related
echo     [4] Nuke + KeepCliState  (preserve ~/.codex for Codex CLI)
echo     [5] Nuke + KeepCaches  (skip TrustedInstaller-protected caches)
echo     [6] SessionReset   - soft: kill + clear .codex/sessions and
echo                          AppX LocalCache/TempState. Keeps auth,
echo                          install, registry. Try this FIRST when
echo                          Codex hangs on context compaction.
echo     [Q] Quit
echo ============================================================
set "choice="
set /p choice="Your choice: "

if /I "%choice%"=="1" goto AUDIT
if /I "%choice%"=="2" goto DRYRUN
if /I "%choice%"=="3" goto NUKE
if /I "%choice%"=="4" goto NUKE_KEEPCLISTATE
if /I "%choice%"=="5" goto NUKE_KEEPCACHES
if /I "%choice%"=="6" goto SESSIONRESET
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

:NUKE_KEEPCLISTATE
echo.
set "confirm="
set /p confirm="Type NUKE to confirm (KeepCliState mode): "
if /I not "%confirm%"=="NUKE" (
    echo [Nuke] Cancelled.
    goto AFTER
)
echo.
%PSHOST% -NoProfile -ExecutionPolicy Bypass -File "%PS1%" -Mode Nuke -KeepCliState
goto AFTER

:NUKE_KEEPCACHES
echo.
set "confirm="
set /p confirm="Type NUKE to confirm (KeepCaches mode): "
if /I not "%confirm%"=="NUKE" (
    echo [Nuke] Cancelled.
    goto AFTER
)
echo.
%PSHOST% -NoProfile -ExecutionPolicy Bypass -File "%PS1%" -Mode Nuke -KeepCaches
goto AFTER

:SESSIONRESET
echo.
echo [Nuke] Running SessionReset (soft, no reinstall needed)...
%PSHOST% -NoProfile -ExecutionPolicy Bypass -File "%PS1%" -Mode SessionReset
goto AFTER

:AFTER
echo.
echo ============================================================
echo  Exit code from script: %ERRORLEVEL%
echo    0       = no remaining Codex artifacts detected
echo    1..N    = that many artifacts remain (see log)
echo    255     = fatal error
echo ============================================================
echo.
if not defined AUDION_NO_PAUSE pause
goto MENU

:END
endlocal
exit /b 0
