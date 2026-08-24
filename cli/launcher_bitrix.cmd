@echo off
chcp 65001 >nul
setlocal EnableExtensions EnableDelayedExpansion

title Audion DevOps Tools - Bitrix Hosts

for %%I in ("%~dp0..") do set "BASE_DIR=%%~fI"
if "%BASE_DIR:~-1%"=="\" set "BASE_DIR=%BASE_DIR:~0,-1%"
cd /d "%BASE_DIR%"

set "HOST_NAME=portal.itpgrad.ru"
set "IP_ADDRESS=192.168.0.130"
set "BITRIX_PORTS=443"
set "SCAN_PORTS=80,443,8080,8443,8890,8891,8892"

:MAIN
cls
echo ======================================================================
echo   AUDION DEVOPS TOOLS - BITRIX HOSTS
echo ======================================================================
echo Root: %BASE_DIR%
echo Current defaults: %HOST_NAME% -^> %IP_ADDRESS% ; ports %BITRIX_PORTS%
echo.
echo [1] Detect current local endpoint
echo [2] Status / DNS / ports
echo [3] Enable hosts override
echo [4] Disable override by exact pre-patch backup
echo [5] Restore hosts from latest backup
echo [6] Edit host/IP/ports for this launcher session
echo [7] Open hosts backup folder
echo [0] Exit
echo.
choice /C 12345670 /N /M "Select: "
if errorlevel 8 exit /b 0
if errorlevel 7 goto OPEN_BACKUP
if errorlevel 6 goto EDIT_VALUES
if errorlevel 5 goto RESTORE_HOSTS
if errorlevel 4 goto DISABLE_OVERRIDE
if errorlevel 3 goto ENABLE_OVERRIDE
if errorlevel 2 goto STATUS
if errorlevel 1 goto DETECT
goto MAIN

:DETECT
call :RUN_BITRIX bitrix_detect_endpoint
if not defined AUDION_NO_PAUSE pause
goto MAIN

:STATUS
call :RUN_BITRIX bitrix_status
if not defined AUDION_NO_PAUSE pause
goto MAIN

:ENABLE_OVERRIDE
echo This edits Windows hosts and stores the exact pre-patch backup name in the managed comment.
echo Windows hosts can map IP to hostname only; ports are saved as Audion metadata for diagnostics.
choice /C YN /N /M "Enable override? [Y/N]: "
if errorlevel 2 goto MAIN
call :RUN_BITRIX bitrix_enable confirmed
if not defined AUDION_NO_PAUSE pause
goto MAIN

:DISABLE_OVERRIDE
echo This restores the exact hosts backup referenced by the managed Audion line.
choice /C YN /N /M "Disable override / depatch hosts? [Y/N]: "
if errorlevel 2 goto MAIN
call :RUN_BITRIX bitrix_disable confirmed
if not defined AUDION_NO_PAUSE pause
goto MAIN

:RESTORE_HOSTS
echo This restores hosts from the latest pre-patch backup when managed-line depatch is not available.
choice /C YN /N /M "Restore hosts from backup? [Y/N]: "
if errorlevel 2 goto MAIN
call :RUN_BITRIX bitrix_restore confirmed
if not defined AUDION_NO_PAUSE pause
goto MAIN

:EDIT_VALUES
echo Press Enter to keep the current value.
set "NEW_HOST="
set "NEW_IP="
set "NEW_PORTS="
set "NEW_SCAN="
set /p "NEW_HOST=Host [%HOST_NAME%]: "
set /p "NEW_IP=IP [%IP_ADDRESS%]: "
set /p "NEW_PORTS=Ports [%BITRIX_PORTS%]: "
set /p "NEW_SCAN=Scan candidates [%SCAN_PORTS%]: "
if defined NEW_HOST set "HOST_NAME=%NEW_HOST%"
if defined NEW_IP set "IP_ADDRESS=%NEW_IP%"
if defined NEW_PORTS set "BITRIX_PORTS=%NEW_PORTS%"
if defined NEW_SCAN set "SCAN_PORTS=%NEW_SCAN%"
goto MAIN

:OPEN_BACKUP
if not exist "%BASE_DIR%\backup\hosts" mkdir "%BASE_DIR%\backup\hosts" >nul 2>nul
start "" explorer "%BASE_DIR%\backup\hosts"
goto MAIN

:RUN_BITRIX
set "CONFIRM_ARG="
if /I "%~2"=="confirmed" set "CONFIRM_ARG=--yes-i-understand"
call :RUN_OP %~1 %CONFIRM_ARG% --param "host_name=%HOST_NAME%" --param "ip_address=%IP_ADDRESS%" --param "bitrix_ports=%BITRIX_PORTS%" --param "bitrix_port_scan_candidates=%SCAN_PORTS%" --param "bitrix_auto_scan_ports=true"
exit /b %ERRORLEVEL%

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
