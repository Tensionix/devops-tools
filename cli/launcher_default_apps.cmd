@echo off
chcp 65001 >nul
setlocal EnableExtensions EnableDelayedExpansion

title Audion DevOps Tools - Default Apps Guard

for %%I in ("%~dp0..") do set "BASE_DIR=%%~fI"
if "%BASE_DIR:~-1%"=="\" set "BASE_DIR=%BASE_DIR:~0,-1%"
cd /d "%BASE_DIR%"

:MAIN
cls
echo ======================================================================
echo   AUDION DEVOPS TOOLS - DEFAULT APPS GUARD
echo ======================================================================
echo Root: %BASE_DIR%
echo.
echo All entries below run the POLICY brick of the Default Apps section.
echo.
echo [1] Check defaults protection
echo [2] Backup current associations snapshot
echo [3] Overwrite reference from current Windows defaults
echo [4] Replace reference from external XML
echo [5] Enable / repair defaults protection policy
echo [6] Disable defaults protection policy
echo [7] Cleanup old unnamed backups - dry run
echo [8] Cleanup old unnamed backups - delete
echo [9] Open backup folder
echo [A] Open reference profiles folder
echo [B] Open active policy folder
echo [0] Exit
echo.
choice /C 123456789AB0 /N /M "Select: "
if errorlevel 12 exit /b 0
if errorlevel 11 goto OPEN_POLICY
if errorlevel 10 goto OPEN_PROFILES
if errorlevel 9 goto OPEN_BACKUP
if errorlevel 8 goto CLEANUP_DELETE
if errorlevel 7 goto CLEANUP_DRY
if errorlevel 6 goto REMOVE_POLICY
if errorlevel 5 goto APPLY_POLICY
if errorlevel 4 goto IMPORT_XML
if errorlevel 3 goto EXPORT_PROFILE
if errorlevel 2 goto SNAPSHOT
if errorlevel 1 goto STATUS
goto MAIN

:STATUS
call :RUN_OP default_apps_policy --param "policy_action=status"
if not defined AUDION_NO_PAUSE pause
goto MAIN

:SNAPSHOT
call :ASK_LABEL
call :RUN_OP default_apps_policy --yes-i-understand --param "policy_action=snapshot" --param "backup_label=%BACKUP_LABEL%"
if not defined AUDION_NO_PAUSE pause
goto MAIN

:EXPORT_PROFILE
echo This replaces profiles\default_apps\AppAssociations.xml with current Windows defaults.
choice /C YN /N /M "Continue? [Y/N]: "
if errorlevel 2 goto MAIN
call :ASK_LABEL
call :RUN_OP default_apps_policy --yes-i-understand --param "policy_action=export" --param "backup_label=%BACKUP_LABEL%"
if not defined AUDION_NO_PAUSE pause
goto MAIN

:IMPORT_XML
set "XML_PATH="
set /p "XML_PATH=External AppAssociations XML path: "
if not defined XML_PATH goto MAIN
call :RUN_OP default_apps_policy --yes-i-understand --param "policy_action=import" --param "import_profile_xml=%XML_PATH%"
if not defined AUDION_NO_PAUSE pause
goto MAIN

:APPLY_POLICY
echo This writes HKLM DefaultAssociationsConfiguration, copies policy XML to ProgramData and runs gpupdate.
echo Sign out/sign in or reboot is required for Windows to reapply defaults.
choice /C YN /N /M "Continue? [Y/N]: "
if errorlevel 2 goto MAIN
call :ASK_LABEL
call :RUN_OP default_apps_policy --yes-i-understand --param "policy_action=apply" --param "backup_label=%BACKUP_LABEL%"
if not defined AUDION_NO_PAUSE pause
goto MAIN

:REMOVE_POLICY
echo This removes the HKLM policy value after backing up current policy state.
echo Current user associations are not immediately changed.
choice /C YN /N /M "Continue? [Y/N]: "
if errorlevel 2 goto MAIN
call :ASK_LABEL
call :RUN_OP default_apps_policy --yes-i-understand --param "policy_action=remove" --param "backup_label=%BACKUP_LABEL%"
if not defined AUDION_NO_PAUSE pause
goto MAIN

:CLEANUP_DRY
call :ASK_RETENTION
call :RUN_OP default_apps_policy --param "policy_action=cleanup" --param "backup_retention_days=%RETENTION_DAYS%" --param "cleanup_dry_run=true"
if not defined AUDION_NO_PAUSE pause
goto MAIN

:CLEANUP_DELETE
call :ASK_RETENTION
echo This deletes only old unlabeled timestamp backups. Named backups and note files are kept.
choice /C YN /N /M "Delete matched files? [Y/N]: "
if errorlevel 2 goto MAIN
call :RUN_OP default_apps_policy --yes-i-understand --param "policy_action=cleanup" --param "backup_retention_days=%RETENTION_DAYS%" --param "cleanup_dry_run=false"
if not defined AUDION_NO_PAUSE pause
goto MAIN

:OPEN_BACKUP
call :RUN_OP default_apps_policy --quiet-json --param "policy_action=open_backups"
goto MAIN

:OPEN_PROFILES
call :RUN_OP default_apps_policy --quiet-json --param "policy_action=open_profiles"
goto MAIN

:OPEN_POLICY
call :RUN_OP default_apps_policy --quiet-json --param "policy_action=open_policy"
goto MAIN

:ASK_LABEL
set "BACKUP_LABEL="
set /p "BACKUP_LABEL=Optional backup label, e.g. golden/platinum/faststone (Enter = none): "
exit /b 0

:ASK_RETENTION
set "RETENTION_DAYS=30"
set /p "RETENTION_DAYS=Retention days [30]: "
if not defined RETENTION_DAYS set "RETENTION_DAYS=30"
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
