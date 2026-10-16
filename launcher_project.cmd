@echo off
chcp 65001 >nul
setlocal EnableExtensions EnableDelayedExpansion

title Audion DevOps Tools - Project Launcher

set "BASE_DIR=%~dp0"
if "%BASE_DIR:~-1%"=="\" set "BASE_DIR=%BASE_DIR:~0,-1%"
cd /d "%BASE_DIR%"

set "CORE_DIR=%BASE_DIR%\system_core"
set "INSTALL_DIR=%BASE_DIR%\install"

:MAIN
cls
echo ======================================================================
echo   AUDION DEVOPS TOOLS - PROJECT LAUNCHER
echo ======================================================================
echo Root: %BASE_DIR%
echo.
echo [1] Launch the window
echo [2] Environment doctor
echo [3] Window self-test
echo [4] Project builder
echo [6] WSL Toolkit launcher
echo [7] Bitrix hosts launcher
echo [8] Default Apps Guard launcher
echo [9] Hardware / driver guard launcher
echo [A] Open project root
echo [B] Open docs
echo [C] Open logs
echo [D] Codex Nuke launcher
echo [E] Python Nuke launcher
echo [F] Association Defense launcher
echo [0] Exit
echo.
choice /C 12346789ABCDEF0 /N /M "Select: "
if errorlevel 15 exit /b 0
if errorlevel 14 goto ASSOCIATION_DEFENSE_MENU
if errorlevel 13 goto PYTHON_NUKE_MENU
if errorlevel 12 goto CODEX_NUKE_MENU
if errorlevel 11 goto OPEN_LOGS
if errorlevel 10 goto OPEN_DOCS
if errorlevel 9 goto OPEN_ROOT
if errorlevel 8 goto HARDWARE_MENU
if errorlevel 7 goto DEFAULT_APPS_MENU
if errorlevel 6 goto BITRIX_MENU
if errorlevel 5 goto WSL_MENU
if errorlevel 4 goto BUILDER
if errorlevel 3 goto WINDOW_CHECK
if errorlevel 2 goto DOCTOR
if errorlevel 1 goto GUI
goto MAIN

rem The window opens the way it opens everywhere: through Start.exe, which asks for the rights once.
:GUI
if exist "%BASE_DIR%\Start.exe" (
  start "" "%BASE_DIR%\Start.exe"
) else (
  echo [ERROR] Start.exe was not found next to the project: install\Build-StartLauncher.cmd makes it.
  if not defined AUDION_NO_PAUSE pause
)
goto MAIN

:DOCTOR
call :RUN_PY "%CORE_DIR%\doctor.py"
if not defined AUDION_NO_PAUSE pause
goto MAIN

rem The check of the built window without a screen: every place of an operation finds its operation
rem and its fields in the manifest of this version.
:WINDOW_CHECK
if not exist "%BASE_DIR%\App\AudionDevOpsTools.exe" goto WINDOW_MISSING
set "CHECK_FILE=%TEMP%\devops_tools_self_test_%RANDOM%%RANDOM%.txt"
if exist "%CHECK_FILE%" del /f /q "%CHECK_FILE%" >nul 2>nul
rem "start /wait": a windowed program is not waited for otherwise, and its exit code is lost.
start "" /wait "%BASE_DIR%\App\AudionDevOpsTools.exe" --self-test --to "%CHECK_FILE%"
set "CHECK_RC=%errorlevel%"
if not exist "%CHECK_FILE%" goto WINDOW_CHECK_DONE
rem find.exe of Windows by its path: with Git ahead in PATH "find" is GNU find, and it walks the whole drive.
for /f %%N in ('%SystemRoot%\System32\findstr.exe /B /C:"ok " "%CHECK_FILE%" ^| %SystemRoot%\System32\find.exe /C /V ""') do echo [OK] The window draws the manifest: %%N checks of it passed.
%SystemRoot%\System32\findstr.exe /B /C:"FAIL" "%CHECK_FILE%"
del /f /q "%CHECK_FILE%" >nul 2>nul
:WINDOW_CHECK_DONE
echo Exit code: %CHECK_RC%
if not defined AUDION_NO_PAUSE pause
goto MAIN

:WINDOW_MISSING
echo [ERROR] The window is not built: App\AudionDevOpsTools.exe. install\Build-App.cmd builds it.
if not defined AUDION_NO_PAUSE pause
goto MAIN

:BUILDER
call "%BASE_DIR%\builder_main.cmd"
goto MAIN

:OPEN_ROOT
start "" explorer "%BASE_DIR%"
goto MAIN

:OPEN_DOCS
start "" explorer "%BASE_DIR%\docs"
goto MAIN

:OPEN_LOGS
if not exist "%BASE_DIR%\logs" mkdir "%BASE_DIR%\logs" >nul 2>nul
start "" explorer "%BASE_DIR%\logs"
goto MAIN

:HARDWARE_MENU
call "%BASE_DIR%\cli\launcher_hardware.cmd"
goto MAIN

:WSL_MENU
call "%BASE_DIR%\cli\launcher_wsl.cmd"
goto MAIN

:BITRIX_MENU
call "%BASE_DIR%\cli\launcher_bitrix.cmd"
goto MAIN

:DEFAULT_APPS_MENU
call "%BASE_DIR%\cli\launcher_default_apps.cmd"
goto MAIN

:ASSOCIATION_DEFENSE_MENU
call "%BASE_DIR%\cli\launcher_association_defense.cmd"
goto MAIN

:CODEX_NUKE_MENU
call "%BASE_DIR%\cli\launcher_codex_nuke.cmd"
goto MAIN

:PYTHON_NUKE_MENU
call "%BASE_DIR%\cli\launcher_python_nuke.cmd"
goto MAIN

:RUN_PY
call :RESOLVE_PYTHON || exit /b 1
set "TARGET=%~1"
set "PY_EXTRA=%~2"
if not exist "%TARGET%" (
  echo [ERROR] Python script not found:
  echo   %TARGET%
  exit /b 2
)
"%PYTHON_CMD%" %PYTHON_ARGS% "%TARGET%" %PY_EXTRA%
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
