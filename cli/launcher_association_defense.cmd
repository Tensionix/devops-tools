@echo off
chcp 65001 >nul
setlocal EnableExtensions EnableDelayedExpansion

title Audion DevOps Tools - Default Apps

for %%I in ("%~dp0..") do set "BASE_DIR=%%~fI"
if "%BASE_DIR:~-1%"=="\" set "BASE_DIR=%BASE_DIR:~0,-1%"
cd /d "%BASE_DIR%"

:MAIN
cls
echo ======================================================================
echo   AUDION DEVOPS TOOLS - DEFAULT APPS
echo ======================================================================
echo Root: %BASE_DIR%
echo.
echo [1] Overview: status all bricks
echo [2] Microsoft apps: status
echo [3] Microsoft apps: remove selected - dry run
echo [4] Microsoft apps: reinstall-block rearm check
echo [5] Policy: status
echo [6] Policy: apply machine-wide defaults
echo [7] Tracking: status
echo [8] Tracking: check associations now
echo [9] Snapshot: compare with the current state
echo [A] Snapshot: capture - dry run
echo [B] Groups: status
echo [C] Groups: commit one group - dry run
echo [D] Groups: compose the shared snapshot - dry run
echo [E] Open snapshots folder
echo [0] Exit
echo.
choice /C 123456789ABCDE0 /N /M "Select: "
if errorlevel 15 exit /b 0
if errorlevel 14 goto OPEN_SNAPSHOTS
if errorlevel 13 goto GROUPS_COMPOSE_DRY
if errorlevel 12 goto GROUPS_COMMIT_DRY
if errorlevel 11 goto GROUPS_STATUS
if errorlevel 10 goto SNAPSHOT_CAPTURE_DRY
if errorlevel 9 goto SNAPSHOT_STATUS
if errorlevel 8 goto TRACKING_RUN_CHECK
if errorlevel 7 goto TRACKING_STATUS
if errorlevel 6 goto POLICY_APPLY
if errorlevel 5 goto POLICY_STATUS
if errorlevel 4 goto APPS_REARM_CHECK
if errorlevel 3 goto APPS_REMOVE_DRY
if errorlevel 2 goto APPS_STATUS
if errorlevel 1 goto STATUS_ALL
goto MAIN

:STATUS_ALL
call :RUN_OP default_apps_overview --param "overview_action=status_all"
if not defined AUDION_NO_PAUSE pause
goto MAIN

:APPS_STATUS
call :RUN_OP default_apps_microsoft --yes-i-understand --param "apps_action=status"
if not defined AUDION_NO_PAUSE pause
goto MAIN

:APPS_REMOVE_DRY
call :RUN_OP default_apps_microsoft --yes-i-understand --param "apps_action=remove" --param "dry_run=true"
if not defined AUDION_NO_PAUSE pause
goto MAIN

:APPS_REARM_CHECK
call :RUN_OP default_apps_microsoft --yes-i-understand --param "apps_action=rearm_check"
if not defined AUDION_NO_PAUSE pause
goto MAIN

:POLICY_STATUS
call :RUN_OP default_apps_policy --yes-i-understand --param "policy_action=status"
if not defined AUDION_NO_PAUSE pause
goto MAIN

:POLICY_APPLY
echo This writes the machine-wide default associations policy under HKLM.
choice /C YN /N /M "Continue? [Y/N]: "
if errorlevel 2 goto MAIN
call :RUN_OP default_apps_policy --yes-i-understand --param "policy_action=apply"
if not defined AUDION_NO_PAUSE pause
goto MAIN

:TRACKING_STATUS
call :RUN_OP default_apps_watch --yes-i-understand --param "guard_action=status"
if not defined AUDION_NO_PAUSE pause
goto MAIN

:TRACKING_RUN_CHECK
call :RUN_OP default_apps_watch --yes-i-understand --param "guard_action=run_check"
if not defined AUDION_NO_PAUSE pause
goto MAIN

:SNAPSHOT_STATUS
call :RUN_OP default_apps_snapshot --yes-i-understand --param "snapshot_action=status"
if not defined AUDION_NO_PAUSE pause
goto MAIN

:SNAPSHOT_CAPTURE_DRY
call :RUN_OP default_apps_snapshot --yes-i-understand --param "snapshot_action=capture" --param "dry_run=true"
if not defined AUDION_NO_PAUSE pause
goto MAIN

:GROUPS_STATUS
call :RUN_OP default_apps_groups --yes-i-understand --param "group_action=status"
if not defined AUDION_NO_PAUSE pause
goto MAIN

:GROUPS_COMMIT_DRY
call :ASK_GROUP
if not defined GROUP_NAME goto MAIN
call :RUN_OP default_apps_groups --yes-i-understand --param "group_action=commit" --param "dry_run=true" --param "group_name=%GROUP_NAME%" --param "group_ext=%GROUP_EXT%"
if not defined AUDION_NO_PAUSE pause
goto MAIN

:GROUPS_COMPOSE_DRY
call :RUN_OP default_apps_groups --yes-i-understand --param "group_action=compose" --param "dry_run=true"
if not defined AUDION_NO_PAUSE pause
goto MAIN

:OPEN_SNAPSHOTS
call :RUN_OP default_apps_overview --param "overview_action=open_snapshots" --quiet-json
goto MAIN

:ASK_GROUP
call :ASK_GROUP_NAME
if not defined GROUP_NAME exit /b 0
set "GROUP_EXT="
set /p "GROUP_EXT=Custom extensions for a custom/override group, e.g. .mp4,.mkv,http (Enter = built-in): "
exit /b 0

:ASK_GROUP_NAME
set "GROUP_NAME=photo"
set /p "GROUP_NAME=Group [photo/audio/video/pdf/browser/custom]: "
if not defined GROUP_NAME set "GROUP_NAME=photo"
exit /b 0

:RUN_OP
call :RESOLVE_PYTHON || exit /b 1
"%PYTHON_CMD%" %PYTHON_ARGS% "%BASE_DIR%\system_core\cli_operation.py" %*
exit /b %ERRORLEVEL%

:RESOLVE_PYTHON
set "PYTHON_CMD="
set "PYTHON_ARGS="
if exist "%BASE_DIR%\runtime\python.exe" set "PYTHON_CMD=%BASE_DIR%\runtime\python.exe" & exit /b 0
if exist "%BASE_DIR%\runtime\python\python.exe" set "PYTHON_CMD=%BASE_DIR%\runtime\python\python.exe" & exit /b 0
py -3.12 -V >nul 2>nul
if not errorlevel 1 set "PYTHON_CMD=py" & set "PYTHON_ARGS=-3.12" & exit /b 0
where python.exe >nul 2>nul
if not errorlevel 1 set "PYTHON_CMD=python.exe" & exit /b 0
echo [ERROR] Python runtime was not resolved.
exit /b 1
