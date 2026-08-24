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
echo [1] Launch GUI
echo [2] Environment doctor
echo [3] NiceGUI smoke
echo [4] Project builder
echo [5] Tools/service launcher
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
echo [G] Docs PDF export
echo [0] Exit
echo.
choice /C 123456789ABCDEFG0 /N /M "Select: "
if errorlevel 17 exit /b 0
if errorlevel 16 goto DOCS_PDF_MENU
if errorlevel 15 goto ASSOCIATION_DEFENSE_MENU
if errorlevel 14 goto PYTHON_NUKE_MENU
if errorlevel 13 goto CODEX_NUKE_MENU
if errorlevel 12 goto OPEN_LOGS
if errorlevel 11 goto OPEN_DOCS
if errorlevel 10 goto OPEN_ROOT
if errorlevel 9 goto HARDWARE_MENU
if errorlevel 8 goto DEFAULT_APPS_MENU
if errorlevel 7 goto BITRIX_MENU
if errorlevel 6 goto WSL_MENU
if errorlevel 5 goto TOOLS
if errorlevel 4 goto BUILDER
if errorlevel 3 goto GUI_SMOKE
if errorlevel 2 goto DOCTOR
if errorlevel 1 goto GUI
goto MAIN

:GUI
call "%BASE_DIR%\launcher_gui.cmd"
goto MAIN

:DOCTOR
call :RUN_PY "%CORE_DIR%\doctor.py"
if not defined AUDION_NO_PAUSE pause
goto MAIN

:GUI_SMOKE
call :RUN_PY "%CORE_DIR%\ui_nicegui\app.py" --smoke
if not defined AUDION_NO_PAUSE pause
goto MAIN

:BUILDER
call "%BASE_DIR%\builder_main.cmd"
goto MAIN

:TOOLS
call "%BASE_DIR%\launcher_tools.cmd"
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

:DOCS_PDF_MENU
call "%BASE_DIR%\cli\launcher_docs_pdf.cmd"
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
