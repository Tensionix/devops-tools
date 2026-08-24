@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul

title Audion DevOps Tools - Project Cleanup

set "BASE_DIR=%~dp0"
if "%BASE_DIR:~-1%"=="\" set "BASE_DIR=%BASE_DIR:~0,-1%"
cd /d "%BASE_DIR%"

set "DRY_RUN=0"
set "ASSUME_YES=0"
set "NO_PAUSE=0"
set "BACKUP_ONLY=0"
set "ERROR_COUNT=0"

:parse_args
if "%~1"=="" goto args_done
if /I "%~1"=="/?" goto usage
if /I "%~1"=="-h" goto usage
if /I "%~1"=="--help" goto usage
if /I "%~1"=="/Y" set "ASSUME_YES=1" & shift & goto parse_args
if /I "%~1"=="--yes" set "ASSUME_YES=1" & shift & goto parse_args
if /I "%~1"=="/DRYRUN" set "DRY_RUN=1" & shift & goto parse_args
if /I "%~1"=="--dry-run" set "DRY_RUN=1" & shift & goto parse_args
if /I "%~1"=="/BACKUP" set "BACKUP_ONLY=1" & shift & goto parse_args
if /I "%~1"=="--backup" set "BACKUP_ONLY=1" & shift & goto parse_args
if /I "%~1"=="/NOPAUSE" set "NO_PAUSE=1" & shift & goto parse_args
if /I "%~1"=="--no-pause" set "NO_PAUSE=1" & shift & goto parse_args
echo [ERROR] Unknown argument: %~1
echo.
goto usage

:args_done
call :CHECK_MARKER "%BASE_DIR%\system_core\ui_nicegui\app.py" || goto abort
call :CHECK_MARKER "%BASE_DIR%\config\tool_manifest.yaml" || goto abort
if "%BACKUP_ONLY%"=="1" goto backup_only

echo ======================================================================
echo   AUDION DEVOPS TOOLS - PROJECT CLEANUP
echo ======================================================================
echo Root:
echo   %BASE_DIR%
echo.
echo Mode: generated/downloaded artifacts cleanup
if "%DRY_RUN%"=="1" echo Dry-run: ON
echo.
echo This cleanup keeps scripts, configs, documentation, tracked licenses and folders.
echo It removes generated/downloaded content from managed project zones:
echo   - input, output, logs, report, workspace, data
echo   - runtime, wheelhouse, release, ._runtime
echo   - install\download
echo   - ripgrep
echo   - system_core\powershell
echo   - system_core\_pwsh_tmp, system_core\_powershell_tmp, system_core\_fzf_tmp
echo   - system_core\fzf.exe
echo   - config\terminal_commands.json local command cache
echo   - tools\codex_nuke\Logs and tools\python_nuke\Logs generated logs
echo   - root licenses\ is preserved unchanged
echo   - Python caches and coverage output
echo   - snapshots in EVERY backup folder, the project's and each pack's:
echo     backup, tools\network_cleaner\backup, tools\disable_windows_proxy\backup,
echo     tools\bitrix_hosts_toggle_pack\backup, tools\wsl\...\WSL\Backup
echo     Those hold this machine's network state - MAC and IP addresses, DNS
echo     servers, Wi-Fi network names, firewall and registry exports - so a
echo     release must not carry them. Folder structure and .gitkeep stay.
echo.
echo Protected: scripts, config, docs, source code, tracked license docs,
echo            folder structure and external historical tools.
echo Use /BACKUP to clear the backup folders alone, with its own Y/N/Q prompt.
echo.

if "%ASSUME_YES%"=="1" goto clean
choice /C YNQ /N /M "Proceed with project cleanup? [Y/N/Q]: "
if errorlevel 3 goto quit
if errorlevel 2 goto cancelled

:clean
echo.
echo [CLEAN] Starting...
echo.

call :ClearDirItems "%BASE_DIR%\input"
call :ClearDirItems "%BASE_DIR%\output"
call :ClearDirItems "%BASE_DIR%\logs"
call :ClearDirItems "%BASE_DIR%\report"
call :ClearDirItems "%BASE_DIR%\workspace"
call :ClearDirItems "%BASE_DIR%\data"
call :ClearDirItems "%BASE_DIR%\runtime"
call :ClearDirItems "%BASE_DIR%\wheelhouse"
call :ClearDirItems "%BASE_DIR%\release"
call :ClearDirItems "%BASE_DIR%\ripgrep"
call :ClearDirItems "%BASE_DIR%\._runtime"
call :ClearDirItems "%BASE_DIR%\install\download"
call :ClearDirItems "%BASE_DIR%\system_core\powershell"
call :RemoveDir "%BASE_DIR%\system_core\_pwsh_tmp"
call :RemoveDir "%BASE_DIR%\system_core\_powershell_tmp"
call :RemoveDir "%BASE_DIR%\system_core\_fzf_tmp"

call :RemoveDir "%BASE_DIR%\.pytest_cache"
call :RemoveDir "%BASE_DIR%\.ruff_cache"
call :RemoveDir "%BASE_DIR%\.mypy_cache"
call :RemoveDir "%BASE_DIR%\htmlcov"
call :RemoveDir "%BASE_DIR%\build"
call :RemoveDir "%BASE_DIR%\dist"
call :RemoveDir "%BASE_DIR%\__pycache__"
call :RemoveFile "%BASE_DIR%\__pycache__"

call :RemoveNamedDirsUnder "%BASE_DIR%\system_core" "__pycache__"
call :RemoveNamedDirsUnder "%BASE_DIR%\tests" "__pycache__"
call :RemoveFilesByPatternUnder "%BASE_DIR%\system_core" "*.pyc"
call :RemoveFilesByPatternUnder "%BASE_DIR%\system_core" "*.pyo"
call :RemoveFilesByPatternUnder "%BASE_DIR%\tests" "*.pyc"
call :RemoveFilesByPatternUnder "%BASE_DIR%\tests" "*.pyo"
call :RemoveFile "%BASE_DIR%\.coverage"
call :RemoveFile "%BASE_DIR%\system_core\fzf.exe"
call :RemoveFilesByPatternUnder "%BASE_DIR%\tools\codex_nuke\Logs" "*.log"
call :RemoveFilesByPatternUnder "%BASE_DIR%\tools\python_nuke\Logs" "*.log"
call :ResetTerminalCommandCache "%BASE_DIR%\config\terminal_commands.json"
call :ClearAllBackups
rem licenses\ is intentionally preserved by release cleanup.
if exist "%BASE_DIR%\install\init_folders.cmd" (
  if "%DRY_RUN%"=="1" (
    echo [DRY] call install\init_folders.cmd
  ) else (
    call "%BASE_DIR%\install\init_folders.cmd" >nul 2>nul
  )
)

echo.
if not "%ERROR_COUNT%"=="0" goto cleanup_failed
if "%DRY_RUN%"=="1" goto dry_run_done
echo [OK] Cleanup finished.
goto cleanup_done

:dry_run_done
echo [OK] Dry run finished. Nothing was deleted.

:cleanup_done
if "%NO_PAUSE%"=="0" call :WAIT_KEY
exit /b 0

:cleanup_failed
echo [ERROR] Cleanup finished with %ERROR_COUNT% error^(s^).
echo Close GUI, terminals, Python processes, and try again.
if "%NO_PAUSE%"=="0" call :WAIT_KEY
exit /b 1

:cancelled
echo.
echo [CANCELLED] Nothing was deleted.
if "%NO_PAUSE%"=="0" call :WAIT_KEY
exit /b 0

:quit
echo.
echo [QUIT] Nothing was deleted.
if "%NO_PAUSE%"=="0" call :WAIT_KEY
exit /b 0

:backup_only
echo ======================================================================
echo   AUDION DEVOPS TOOLS - BACKUP CLEANUP
echo ======================================================================
echo Root:
echo   %BASE_DIR%
echo.
if "%DRY_RUN%"=="1" echo Dry-run: ON
echo.
echo This mode removes backup snapshots only - from the project's backup folder
echo and from every pack that keeps its own under tools\ - then recreates the
echo managed backup folder structure with .gitkeep files.
echo.
echo WARNING: this can delete Network, Default Apps, Driver Guard, Browser,
echo          NVIDIA Audio, certificate, SSH, virtualization and hosts backups.
echo.
if "%ASSUME_YES%"=="1" goto backup_clean
choice /C YNQ /N /M "Delete project backup contents? [Y/N/Q]: "
if errorlevel 3 goto quit
if errorlevel 2 goto cancelled

:backup_clean
echo.
echo [BACKUP CLEAN] Starting...
echo.
call :ClearAllBackups

if exist "%BASE_DIR%\install\init_folders.cmd" (
  if "%DRY_RUN%"=="1" (
    echo [DRY] call install\init_folders.cmd
  ) else (
    call "%BASE_DIR%\install\init_folders.cmd" >nul 2>nul
  )
)

echo.
if not "%ERROR_COUNT%"=="0" goto cleanup_failed
if "%DRY_RUN%"=="1" goto dry_run_done
echo [OK] Backup cleanup finished.
goto cleanup_done

:abort
echo.
echo [ABORTED] Cleanup refused to run outside an Audion DevOps Tools project.
if "%NO_PAUSE%"=="0" call :WAIT_KEY
exit /b 1

:usage
echo Usage:
echo   cleanup_project.cmd [/Y] [/DRYRUN] [/NOPAUSE]
echo   cleanup_project.cmd /BACKUP [/DRYRUN] [/NOPAUSE]
echo.
echo Options:
echo   /Y              Run without confirmation.
echo   /DRYRUN         Print actions without deleting anything.
echo   /BACKUP         Delete backup contents only. Honors /Y.
echo   /NOPAUSE        Do not wait for a key at the end.
echo.
if "%NO_PAUSE%"=="0" call :WAIT_KEY
exit /b 0

:CHECK_MARKER
if exist "%~1" exit /b 0
echo [ERROR] Project marker not found:
echo   %~1
exit /b 1

:ClearDirItems
set "TARGET_DIR=%~1"
call :IsBackupPath "%TARGET_DIR%"
if not errorlevel 1 (
  echo [SKIP] Protected backup path: %TARGET_DIR%
  exit /b 0
)
if not exist "%TARGET_DIR%\" (
  if "%DRY_RUN%"=="1" (
    echo [DRY] mkdir "%TARGET_DIR%"
  ) else (
    echo [CREATE] %TARGET_DIR%
    mkdir "%TARGET_DIR%" >nul 2>nul
    if errorlevel 1 call :MarkError "Could not create directory: %TARGET_DIR%"
  )
  exit /b 0
)

echo [CLEAR] %TARGET_DIR%
for /f "delims=" %%I in ('dir /a /b "%TARGET_DIR%" 2^>nul') do (
    if exist "%TARGET_DIR%\%%I\" (
      if "%DRY_RUN%"=="1" (
        echo   [DRY] rmdir /s /q "%TARGET_DIR%\%%I"
      ) else (
        echo   rmdir "%TARGET_DIR%\%%I"
        attrib -r -s -h "%TARGET_DIR%\%%I\*" /s /d 2>nul
        rd /s /q "%TARGET_DIR%\%%I" 2>nul
        if exist "%TARGET_DIR%\%%I\" call :MarkError "Could not remove directory: %TARGET_DIR%\%%I"
      )
    ) else (
      if "%DRY_RUN%"=="1" (
        echo   [DRY] del "%TARGET_DIR%\%%I"
      ) else (
        echo   del "%TARGET_DIR%\%%I"
        attrib -r -s -h "%TARGET_DIR%\%%I" 2>nul
        del /f /q "%TARGET_DIR%\%%I" 2>nul
        if exist "%TARGET_DIR%\%%I" call :MarkError "Could not remove file: %TARGET_DIR%\%%I"
      )
    )
)
exit /b 0

:RemoveNamedDirsUnder
set "SEARCH_ROOT=%~1"
set "DIR_NAME=%~2"
call :IsBackupPath "%SEARCH_ROOT%"
if not errorlevel 1 (
  echo [SKIP] Protected backup path: %SEARCH_ROOT%
  exit /b 0
)
if not exist "%SEARCH_ROOT%\" exit /b 0
echo [DIRS] %SEARCH_ROOT% -^> %DIR_NAME%
for /f "delims=" %%D in ('dir /ad /b /s "%SEARCH_ROOT%" 2^>nul') do (
  if /I "%%~nxD"=="%DIR_NAME%" (
    if "%DRY_RUN%"=="1" (
      echo   [DRY] rmdir /s /q "%%~fD"
    ) else (
      echo   rmdir "%%~fD"
      attrib -r -s -h "%%~fD\*" /s /d 2>nul
      rd /s /q "%%~fD" 2>nul
      if exist "%%~fD\" call :MarkError "Could not remove directory: %%~fD"
    )
  )
)
exit /b 0

:RemoveFilesByPatternUnder
set "SEARCH_ROOT=%~1"
set "PATTERN=%~2"
call :IsBackupPath "%SEARCH_ROOT%"
if not errorlevel 1 (
  echo [SKIP] Protected backup path: %SEARCH_ROOT%
  exit /b 0
)
if not exist "%SEARCH_ROOT%" exit /b 0
echo [FILES] %SEARCH_ROOT% -^> %PATTERN%
for /f "delims=" %%F in ('dir /a-d /b /s "%SEARCH_ROOT%\%PATTERN%" 2^>nul') do (
  if "%DRY_RUN%"=="1" (
    echo   [DRY] del "%%~fF"
  ) else (
    echo   del "%%~fF"
    attrib -r -s -h "%%~fF" 2>nul
    del /f /q "%%~fF" 2>nul
    if exist "%%~fF" call :MarkError "Could not remove file: %%~fF"
  )
)
exit /b 0

:RemoveDir
set "TARGET=%~1"
call :IsBackupPath "%TARGET%"
if not errorlevel 1 (
  echo   [SKIP] Protected backup path: %TARGET%
  exit /b 0
)
if not exist "%TARGET%\" exit /b 0
if "%DRY_RUN%"=="1" (
  echo   [DRY] rmdir /s /q "%TARGET%"
  exit /b 0
)
echo   rmdir "%TARGET%"
attrib -r -s -h "%TARGET%\*" /s /d 2>nul
rd /s /q "%TARGET%" 2>nul
if exist "%TARGET%\" call :MarkError "Could not remove directory: %TARGET%"
exit /b 0

:RemoveFile
set "TARGET=%~1"
call :IsBackupPath "%TARGET%"
if not errorlevel 1 (
  echo   [SKIP] Protected backup path: %TARGET%
  exit /b 0
)
if not exist "%TARGET%" exit /b 0
if "%DRY_RUN%"=="1" (
  echo   [DRY] del "%TARGET%"
  exit /b 0
)
echo   del "%TARGET%"
attrib -r -s -h "%TARGET%" 2>nul
del /f /q "%TARGET%" 2>nul
if exist "%TARGET%" call :MarkError "Could not remove file: %TARGET%"
exit /b 0

:ClearGeneratedLicenses
rem Safety guard: release cleanup must never touch licenses\.
echo [LICENSES] Preserving licenses\ unchanged
exit /b 0

:ClearBackupContents
set "TARGET_DIR=%~1"
call :IsBackupPath "%TARGET_DIR%"
if errorlevel 1 (
  call :MarkError "Refused to clean non-backup path: %TARGET_DIR%"
  exit /b 0
)
if not exist "%TARGET_DIR%\" (
  if "%DRY_RUN%"=="1" (
    echo [DRY] mkdir "%TARGET_DIR%"
  ) else (
    echo [CREATE] %TARGET_DIR%
    mkdir "%TARGET_DIR%" >nul 2>nul
    if errorlevel 1 call :MarkError "Could not create directory: %TARGET_DIR%"
  )
  exit /b 0
)

echo [CLEAR BACKUP] %TARGET_DIR%
for /f "delims=" %%I in ('dir /a /b "%TARGET_DIR%" 2^>nul') do (
  if exist "%TARGET_DIR%\%%I\" (
    if "%DRY_RUN%"=="1" (
      echo   [DRY] rmdir /s /q "%TARGET_DIR%\%%I"
    ) else (
      echo   rmdir "%TARGET_DIR%\%%I"
      attrib -r -s -h "%TARGET_DIR%\%%I\*" /s /d 2>nul
      rd /s /q "%TARGET_DIR%\%%I" 2>nul
      if exist "%TARGET_DIR%\%%I\" call :MarkError "Could not remove directory: %TARGET_DIR%\%%I"
    )
  ) else (
    call :IsPreservedBackupFile "%%I"
    if errorlevel 1 (
      if "%DRY_RUN%"=="1" (
        echo   [DRY] del "%TARGET_DIR%\%%I"
      ) else (
        echo   del "%TARGET_DIR%\%%I"
        attrib -r -s -h "%TARGET_DIR%\%%I" 2>nul
        del /f /q "%TARGET_DIR%\%%I" 2>nul
        if exist "%TARGET_DIR%\%%I" call :MarkError "Could not remove file: %TARGET_DIR%\%%I"
      )
    ) else (
      echo   [KEEP] %TARGET_DIR%\%%I
    )
  )
)
exit /b 0

:IsBackupPath
rem This used to know exactly one backup folder, the project's own. Every pack
rem under tools\ keeps its own as well - network_cleaner alone had four snapshots
rem holding MAC addresses, DNS servers, Wi-Fi network names and a firewall export
rem - and none of them was seen by either mode, so all of it shipped.
rem
rem A path counts as backup when it ends in \backup or passes through one. The
rem test is case-insensitive, so the WSL blocks' \Backup match too, and it costs
rem nothing per call - the guards below run it for every single item.
for %%T in ("%~1") do set "CHECK_PATH=%%~fT"
echo(!CHECK_PATH!| findstr /I /E /C:"\backup" >nul
if not errorlevel 1 exit /b 0
echo(!CHECK_PATH!| findstr /I /C:"\backup\" >nul
if not errorlevel 1 exit /b 0
exit /b 1

:ClearAllBackups
rem Found rather than listed, so a pack that starts keeping snapshots tomorrow is
rem covered without anybody remembering to add it here. Runs after runtime and
rem wheelhouse are already empty, so nothing vendored inside them is walked.
echo [BACKUPS] Clearing snapshots in every backup folder
for /f "delims=" %%D in ('dir /ad /b /s "%BASE_DIR%" 2^>nul') do (
  if /I "%%~nxD"=="backup" call :ClearBackupContents "%%~fD"
)
exit /b 0

:IsPreservedBackupFile
rem .gitkeep and .keep carry the folder structure in git.
rem
rem "hosts" is the Bitrix pack's factory reference - the file its restore copies
rem from, holding the stock Windows hosts and nothing of this machine. It is not
rem tracked in git and nothing would recreate it, so deleting it would quietly
rem disable that tool's restore. Only the file is spared; the root backup\hosts
rem folder is a snapshot target and gets cleared like the rest.
if /I "%~1"==".gitkeep" exit /b 0
if /I "%~1"==".keep" exit /b 0
if /I "%~1"=="hosts" exit /b 0
exit /b 1

:ResetTerminalCommandCache
set "TARGET=%~1"
set "TARGET_PARENT=%~dp1"
echo [RESET] %TARGET%
if "%DRY_RUN%"=="1" (
  echo   [DRY] reset terminal command cache JSON
  exit /b 0
)
if not exist "%TARGET_PARENT%" (
  mkdir "%TARGET_PARENT%" >nul 2>nul
  if errorlevel 1 call :MarkError "Could not create directory: %TARGET_PARENT%"
)
>"%TARGET%" echo {
>>"%TARGET%" echo   "history": [],
>>"%TARGET%" echo   "pinned": [],
>>"%TARGET%" echo   "last": "",
>>"%TARGET%" echo   "shell": "pwsh",
>>"%TARGET%" echo   "cwd": ""
>>"%TARGET%" echo }
if not exist "%TARGET%" call :MarkError "Could not reset terminal command cache: %TARGET%"
exit /b 0

:MarkError
echo   [ERROR] %~1
set /a ERROR_COUNT+=1
exit /b 0

:WAIT_KEY
echo Press any key to continue . . .
if not defined AUDION_NO_PAUSE pause >nul
goto :eof
